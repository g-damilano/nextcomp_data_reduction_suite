from __future__ import annotations

import csv
import io
import json
import sqlite3
import time
import zipfile
from pathlib import Path

from archives.core.layouts import MTDPLayout, detect_mtdp_layout
from mtdp_enrichment.index.hidden_file import index_path_for_folder, set_hidden_if_possible
from mtdp_enrichment.package.checksums import sha256_bytes
from mtdp_enrichment.package.validator import MTDPPackageValidator


INDEX_STATUSES = {
    "valid",
    "missing",
    "changed",
    "stale",
    "corrupt",
    "unknown_schema",
    "needs_validation",
    "replaced",
}


class FolderIndex:
    """Rebuildable folder-level cache for .mtdp package summaries."""

    def __init__(self, folder: str | Path) -> None:
        self.folder = Path(folder)
        self.path = index_path_for_folder(self.folder)
        self.validator = MTDPPackageValidator()

    def open(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self._connect().close()
        set_hidden_if_possible(self.path)
        self.sync()

    def sync(self) -> None:
        package_paths = {path.relative_to(self.folder).as_posix(): path for path in self.folder.rglob("*.mtdp")}
        with self._connect() as conn:
            cached_paths = {row[0] for row in conn.execute("SELECT path FROM package_cache")}
            for rel_path in cached_paths - set(package_paths):
                conn.execute(
                    "UPDATE package_cache SET status = ?, indexed_at = ? WHERE path = ?",
                    ("missing", time.time(), rel_path),
                )
            for rel_path, package_path in package_paths.items():
                self._upsert_package(conn, rel_path, package_path)

    def packages(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT path, status, schema_id, schema_version, size, mtime, indexed_at,
                       run_count, sample_type, schema_status, sample_type_key, material_label, treatment,
                       has_supplemental, has_images
                FROM package_cache
                ORDER BY path
                """
            ).fetchall()
        return [
            {
                "path": row[0],
                "status": row[1],
                "schema_id": row[2],
                "schema_version": row[3],
                "size": row[4],
                "mtime": row[5],
                "indexed_at": row[6],
                "run_count": row[7],
                "sample_type": row[8],
                "schema_status": row[9],
                "sample_type_key": row[10],
                "material_label": row[11],
                "treatment": row[12],
                "has_supplemental": bool(row[13]),
                "has_images": bool(row[14]),
            }
            for row in rows
        ]

    def suggestions(self, field_id: str, prefix: str = "", limit: int = 12) -> list[str]:
        query_prefix = f"{prefix}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT value
                FROM suggestions
                WHERE field_id = ? AND value LIKE ?
                ORDER BY last_used DESC, value
                LIMIT ?
                """,
                (field_id, query_prefix, limit),
            ).fetchall()
        return [row[0] for row in rows]

    def remember_suggestion(self, field_id: str, value: str) -> None:
        value = value.strip()
        if not value:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO suggestions(field_id, value, last_used)
                VALUES(?, ?, ?)
                ON CONFLICT(field_id, value) DO UPDATE SET last_used = excluded.last_used
                """,
                (field_id, value, time.time()),
            )

    def _upsert_package(self, conn: sqlite3.Connection, rel_path: str, package_path: Path) -> None:
        stat = package_path.stat()
        cached = conn.execute(
            "SELECT size, mtime, manifest_hash, status FROM package_cache WHERE path = ?",
            (rel_path,),
        ).fetchone()

        if cached and cached[0] == stat.st_size and abs(float(cached[1]) - stat.st_mtime) < 0.0001:
            return

        status = "valid"
        schema_id = None
        schema_version = None
        schema_status = None
        run_count = 0
        sample_type = None
        sample_type_key = None
        material_label = None
        treatment = None
        has_supplemental = False
        has_images = False
        manifest_hash = None
        try:
            with zipfile.ZipFile(package_path, "r") as archive:
                names = {name for name in archive.namelist() if not name.endswith("/")}
                layout = detect_mtdp_layout(names)
                manifest_bytes = archive.read(layout.manifest)
                manifest_hash = sha256_bytes(manifest_bytes)
                manifest = json.loads(manifest_bytes.decode("utf-8"))
                schema_id = manifest.get("schema_id")
                schema_version = manifest.get("schema_version")
                try:
                    schema = json.loads(archive.read(layout.schema).decode("utf-8"))
                    schema_status = schema.get("status")
                except KeyError:
                    schema_status = None
                try:
                    dataset = json.loads(archive.read(layout.dataset).decode("utf-8"))
                    sample_type = dataset.get("sample_type")
                    sample_type_key = dataset.get("sample_type_key")
                    material_label = dataset.get("material_label")
                    treatment = dataset.get("treatment")
                    self._cache_dataset_suggestions(conn, dataset)
                except KeyError:
                    sample_type = None
                run_count = len(
                    [
                        name
                        for name in names
                        if name.startswith(layout.normalized_prefix) and name.endswith(".csv")
                    ]
                )
                has_supplemental = any(name.startswith("supplemental/") for name in names)
                has_images = any(name.startswith("images/") for name in names)
                self._cache_suggestions(conn, archive, layout)
                self._cache_provenance_suggestions(conn, archive, layout)
            validation = self.validator.validate(package_path)
            if not validation.ok:
                status = "corrupt"
            elif not schema_id:
                status = "unknown_schema"
            elif cached and cached[3] == "missing" and cached[2] and cached[2] != manifest_hash:
                status = "replaced"
        except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError):
            status = "corrupt"

        conn.execute(
            """
            INSERT INTO package_cache(
                path, status, schema_id, schema_version, size, mtime, manifest_hash, indexed_at,
                run_count, sample_type, schema_status, sample_type_key, material_label, treatment
                , has_supplemental, has_images
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                status = excluded.status,
                schema_id = excluded.schema_id,
                schema_version = excluded.schema_version,
                size = excluded.size,
                mtime = excluded.mtime,
                manifest_hash = excluded.manifest_hash,
                indexed_at = excluded.indexed_at,
                run_count = excluded.run_count,
                sample_type = excluded.sample_type,
                schema_status = excluded.schema_status,
                sample_type_key = excluded.sample_type_key,
                material_label = excluded.material_label,
                treatment = excluded.treatment,
                has_supplemental = excluded.has_supplemental,
                has_images = excluded.has_images
            """,
            (
                rel_path,
                status,
                schema_id,
                schema_version,
                stat.st_size,
                stat.st_mtime,
                manifest_hash,
                time.time(),
                run_count,
                sample_type,
                schema_status,
                sample_type_key,
                material_label,
                treatment,
                int(has_supplemental),
                int(has_images),
            ),
        )

    def known_sample_types(self, prefix: str = "", limit: int = 25) -> list[dict[str, str]]:
        query_prefix = f"{prefix}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT sample_type, sample_type_key
                FROM package_cache
                WHERE sample_type IS NOT NULL AND sample_type LIKE ?
                ORDER BY sample_type
                LIMIT ?
                """,
                (query_prefix, limit),
            ).fetchall()
        return [{"sample_type": row[0], "sample_type_key": row[1] or ""} for row in rows]

    def _cache_dataset_suggestions(self, conn: sqlite3.Connection, dataset: dict[str, object]) -> None:
        for field_id in ("sample_type", "material_label", "treatment"):
            value = dataset.get(field_id)
            if isinstance(value, str) and value.strip():
                conn.execute(
                    """
                    INSERT INTO suggestions(field_id, value, last_used)
                    VALUES(?, ?, ?)
                    ON CONFLICT(field_id, value) DO UPDATE SET last_used = excluded.last_used
                    """,
                    (field_id, value, time.time()),
                )

    def _cache_suggestions(
        self,
        conn: sqlite3.Connection,
        archive: zipfile.ZipFile,
        layout: type[MTDPLayout],
    ) -> None:
        normalized_members = [
            name for name in archive.namelist() if name.startswith(layout.normalized_prefix) and name.endswith(".csv")
        ]
        token_to_field = {
            "Specimen name": "specimen_name",
            "Sample ID": "sample_id",
            "Operator": "operator",
            "Machine": "machine",
            "Load cell": "load_cell",
            "Test speed": "test_speed",
        }
        for member in normalized_members:
            text = archive.read(member).decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text))
            for row in reader:
                if not row:
                    break
                if len(row) < 2:
                    continue
                field_id = token_to_field.get(row[0])
                if field_id:
                    conn.execute(
                        """
                        INSERT INTO suggestions(field_id, value, last_used)
                        VALUES(?, ?, ?)
                        ON CONFLICT(field_id, value) DO UPDATE SET last_used = excluded.last_used
                        """,
                        (field_id, row[1], time.time()),
                    )

    def _cache_provenance_suggestions(
        self,
        conn: sqlite3.Connection,
        archive: zipfile.ZipFile,
        layout: type[MTDPLayout],
    ) -> None:
        try:
            provenance = json.loads(archive.read(layout.provenance).decode("utf-8"))
        except (KeyError, json.JSONDecodeError):
            return
        runs = provenance.get("runs", {})
        if not isinstance(runs, dict):
            return
        for run_payload in runs.values():
            if not isinstance(run_payload, dict):
                continue
            context = run_payload.get("acquisition_context", {})
            if not isinstance(context, dict):
                continue
            for field_id in ("operator", "instrument", "machine", "load_cell", "test_speed"):
                value = context.get(field_id)
                if field_id == "machine" and value is None:
                    value = context.get("instrument")
                if isinstance(value, dict):
                    raw = value.get("value")
                    unit = value.get("unit")
                    text = f"{raw} {unit}".strip() if unit else str(raw)
                else:
                    text = "" if value is None else str(value)
                if text.strip():
                    conn.execute(
                        """
                        INSERT INTO suggestions(field_id, value, last_used)
                        VALUES(?, ?, ?)
                        ON CONFLICT(field_id, value) DO UPDATE SET last_used = excluded.last_used
                        """,
                        (field_id, text, time.time()),
                    )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS package_cache (
                path TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                schema_id TEXT,
                schema_version TEXT,
                size INTEGER,
                mtime REAL,
                manifest_hash TEXT,
                indexed_at REAL,
                run_count INTEGER,
                sample_type TEXT,
                schema_status TEXT,
                sample_type_key TEXT,
                material_label TEXT,
                treatment TEXT,
                has_supplemental INTEGER,
                has_images INTEGER
            )
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(package_cache)").fetchall()}
        for column, definition in {
            "run_count": "INTEGER",
            "sample_type": "TEXT",
            "schema_status": "TEXT",
            "sample_type_key": "TEXT",
            "material_label": "TEXT",
            "treatment": "TEXT",
            "has_supplemental": "INTEGER",
            "has_images": "INTEGER",
        }.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE package_cache ADD COLUMN {column} {definition}")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suggestions (
                field_id TEXT NOT NULL,
                value TEXT NOT NULL,
                last_used REAL NOT NULL,
                PRIMARY KEY(field_id, value)
            )
            """
        )
        return conn
