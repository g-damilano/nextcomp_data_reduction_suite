from __future__ import annotations

from typing import Any

from mtdp_enrichment.enrichment_import.canonical_yaml import extract_value_and_unit
from mtdp_enrichment.enrichment_import.empirical_matcher import EmpiricalYamlMatcher, YamlFieldMatch
from mtdp_enrichment.enrichment_import.mapping_profile import (
    MappingRule,
    profile_for_mapping,
    profile_id_from_signature,
)
from mtdp_enrichment.enrichment_import.models import ReconciledMappingRow, SupplementalYamlDocument
from mtdp_enrichment.enrichment_import.value_normalizers import (
    conversion_preview,
    extract_unit_from_key,
    parse_date_candidate,
    storage_preview,
    transform_value_for_field,
)
from mtdp_enrichment.package import MTDPSchema
from mtdp_enrichment.ui.qt_compat import QtCore, QtWidgets


class YamlReconciliationDialog(QtWidgets.QDialog):
    state_changed = QtCore.pyqtSignal()

    COL_SOURCE = 0
    COL_RAW = 1
    COL_VALUE = 2
    COL_UNIT = 3
    COL_FIELD = 4
    COL_TYPE = 5
    COL_TARGET_UNIT = 6
    COL_TRANSFORM = 7
    COL_STATUS = 8
    COL_ACTION = 9
    COL_RESULT = 10

    def __init__(
        self,
        document: SupplementalYamlDocument,
        schema: MTDPSchema,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.schema = schema
        self.matcher = EmpiricalYamlMatcher()
        self._row_matches: dict[int, YamlFieldMatch] = {}
        self.setWindowTitle("Reconcile Supplemental YAML")
        self.resize(1220, 760)

        self.profile_id_edit = QtWidgets.QLineEdit(
            profile_id_from_signature("supplemental_yaml", document.structure_signature)
        )
        self.apply_all_checkbox = QtWidgets.QCheckBox("Apply to YAML files with the same structure")
        self.apply_all_checkbox.setChecked(True)
        self.apply_all_checkbox.stateChanged.connect(self._queue_preview_update)

        self.table = QtWidgets.QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "Source YAML key",
                "Example raw value",
                "Detected value",
                "Detected unit",
                "Suggested canonical field",
                "Field type",
                "Target unit",
                "Conversion/transform",
                "Status",
                "Action",
                "Result preview",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        self.preview_table = QtWidgets.QTableWidget(0, 8)
        self.preview_table.setHorizontalHeaderLabels(
            ["Source key", "Raw value", "Canonical field", "Canonical value", "Unit", "Storage", "Status", "Warnings"]
        )
        self.preview_table.horizontalHeader().setStretchLastSection(True)

        self.accept_button = QtWidgets.QPushButton("Accept current preview")
        self.save_button = QtWidgets.QPushButton("Save mapping profile")
        self.cancel_button = QtWidgets.QPushButton("Cancel import")
        self.accept_button.clicked.connect(self.accept)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setInterval(80)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self.recompute_preview)
        self.state_changed.connect(self._queue_preview_update)

        form = QtWidgets.QFormLayout()
        form.addRow("Mapping profile ID", self.profile_id_edit)
        form.addRow("", self.apply_all_checkbox)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.accept_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "Review every YAML key and confirm how it will map into canonical MTDP fields before accepting."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.table, 3)
        layout.addWidget(QtWidgets.QLabel("Live acceptance preview"))
        layout.addWidget(self.preview_table, 2)
        layout.addLayout(buttons)

        self._populate()
        self.recompute_preview()

    def mapping_profile(self):
        rules: list[MappingRule] = []
        for row in range(self.table.rowCount()):
            source_key = self.table.item(row, self.COL_SOURCE).text()
            field = self._field_for_row(row)
            action = self._action_for_row(row)
            unit = self._unit_for_row(row)
            status = self.table.item(row, self.COL_STATUS).text()
            transform = self.table.item(row, self.COL_TRANSFORM).text()
            rules.append(
                MappingRule(
                    source_key=source_key,
                    target_field_id=field.field_id if field and action == "map" else None,
                    value_path=source_key,
                    unit=unit if action == "map" else None,
                    action=action,
                    date_format=transform if field and field.type == "date" else None,
                    value_transform=transform if transform in {"bool_validity_map", "value_map"} else None,
                    status=status,
                    user_corrected=status in {"user_corrected", "user_confirmed"},
                )
            )
        return profile_for_mapping(
            profile_id=self.profile_id_edit.text().strip()
            or profile_id_from_signature("supplemental_yaml", self.document.structure_signature),
            schema=self.schema,
            payload=self.document.raw_payload,
            mappings=tuple(rules),
        )

    def reconciled_rows(self) -> tuple[ReconciledMappingRow, ...]:
        rows: list[ReconciledMappingRow] = []
        for row in range(self.table.rowCount()):
            source_key = self.table.item(row, self.COL_SOURCE).text()
            raw_value = _get_dotted_value(self.document.raw_payload, source_key)
            value, raw_unit = extract_value_and_unit(raw_value)
            unit = self._unit_for_row(row) or raw_unit
            field = self._field_for_row(row)
            transformed = transform_value_for_field(
                source_key=source_key,
                raw_value=value,
                raw_unit=raw_unit,
                field=field,
                selected_unit=unit,
            )
            rows.append(
                ReconciledMappingRow(
                    source_key=source_key,
                    raw_value=raw_value,
                    target_field_id=field.field_id if field else None,
                    transformed=transformed,
                    storage_preview=storage_preview(field),
                    status=self.table.item(row, self.COL_STATUS).text(),
                    action=self._action_for_row(row),
                )
            )
        return tuple(rows)

    def recompute_preview(self) -> None:
        rows = self.reconciled_rows()
        self.preview_table.setRowCount(len(rows))
        ready = True
        for row_index, row in enumerate(rows):
            transformed = row.transformed
            warnings = "; ".join(transformed.warnings) if transformed else ""
            if row.action == "map" and (row.target_field_id is None or transformed is None):
                ready = False
            if transformed and transformed.requires_confirmation and row.status not in {"user_confirmed", "user_corrected"}:
                ready = False
            if row.status in {"requires_unit", "requires_date_format", "ambiguous", "unsupported"}:
                ready = False
            values = [
                row.source_key,
                _example_text(row.raw_value),
                row.target_field_id or "",
                "" if transformed is None else str(transformed.canonical_value),
                "" if transformed is None else str(transformed.canonical_unit or ""),
                row.storage_preview or "",
                row.status,
                warnings,
            ]
            for column, value in enumerate(values):
                self.preview_table.setItem(row_index, column, QtWidgets.QTableWidgetItem(value))
            self.table.item(row_index, self.COL_RESULT).setText(
                "" if transformed is None else f"{transformed.canonical_value} {transformed.canonical_unit or ''}".strip()
            )
        self.preview_table.resizeColumnsToContents()
        self.accept_button.setEnabled(ready)

    def _populate(self) -> None:
        keys = [
            key
            for key in self.document.key_paths
            if key
            not in {
                "mtdp_supplemental_version",
                "scope",
                "schema_hint.schema_id",
                "schema_hint.schema_version",
                "notes",
            }
            and not key.startswith("images.")
        ]
        self.table.setRowCount(len(keys))
        for row, key in enumerate(keys):
            raw_value = _get_dotted_value(self.document.raw_payload, key)
            value, explicit_unit = extract_value_and_unit(raw_value)
            normalized_key, inferred_unit, unit_status = extract_unit_from_key(key)
            match = self._suggest_match(key, raw_value)
            self._row_matches[row] = match
            suggested = self.schema.field_by_id(match.target_field_id) if match.target_field_id else None
            detected_unit = explicit_unit or inferred_unit
            transformed = transform_value_for_field(
                source_key=key,
                raw_value=value,
                raw_unit=detected_unit,
                field=suggested,
                selected_unit=detected_unit,
            )
            status = _status_for(suggested, transformed, unit_status, self.document.is_canonical, match)
            action = "map" if suggested else "ignore"

            self.table.setItem(row, self.COL_SOURCE, QtWidgets.QTableWidgetItem(key))
            self.table.setItem(row, self.COL_RAW, QtWidgets.QTableWidgetItem(_example_text(raw_value)))
            self.table.setItem(row, self.COL_VALUE, QtWidgets.QTableWidgetItem("" if value is None else str(value)))
            self.table.setCellWidget(row, self.COL_UNIT, self._unit_widget(suggested, detected_unit))
            self.table.setCellWidget(row, self.COL_FIELD, self._field_widget(suggested))
            self.table.setItem(row, self.COL_TYPE, QtWidgets.QTableWidgetItem(suggested.type if suggested else ""))
            self.table.setItem(row, self.COL_TARGET_UNIT, QtWidgets.QTableWidgetItem(suggested.standard_unit or "" if suggested else ""))
            self.table.setItem(row, self.COL_TRANSFORM, QtWidgets.QTableWidgetItem(_transform_text(transformed, unit_status)))
            self.table.setItem(row, self.COL_STATUS, QtWidgets.QTableWidgetItem(status))
            self.table.setCellWidget(row, self.COL_ACTION, self._action_widget(action))
            self.table.setItem(row, self.COL_RESULT, QtWidgets.QTableWidgetItem(""))
        self.table.resizeColumnsToContents()

    def _field_widget(self, suggested):
        combo = QtWidgets.QComboBox()
        combo.addItem("Ignore", None)
        for field in self.schema.dataset_fields + self.schema.run_fields:
            combo.addItem(f"{field.label} ({field.field_id})", field.field_id)
        if suggested is not None:
            index = combo.findData(suggested.field_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(self._row_widget_changed)
        return combo

    def _unit_widget(self, field, detected_unit: str | None):
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        combo.addItem("", None)
        units = list(field.accepted_units) if field is not None else []
        for unit in units:
            combo.addItem(unit, unit)
        if detected_unit:
            index = combo.findText(detected_unit)
            if index < 0:
                combo.addItem(detected_unit, detected_unit)
                index = combo.findText(detected_unit)
            combo.setCurrentIndex(index)
        elif field is not None and field.standard_unit:
            index = combo.findText(field.standard_unit)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.currentTextChanged.connect(self._row_widget_changed)
        return combo

    def _action_widget(self, action: str):
        combo = QtWidgets.QComboBox()
        for label, value in (("Map", "map"), ("Ignore", "ignore"), ("Defer/manual", "defer")):
            combo.addItem(label, value)
        index = combo.findData(action)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.currentIndexChanged.connect(self._row_widget_changed)
        return combo

    def _field_for_row(self, row: int):
        combo = self.table.cellWidget(row, self.COL_FIELD)
        field_id = combo.currentData() if isinstance(combo, QtWidgets.QComboBox) else None
        return self.schema.field_by_id(str(field_id)) if field_id else None

    def _unit_for_row(self, row: int) -> str | None:
        combo = self.table.cellWidget(row, self.COL_UNIT)
        if isinstance(combo, QtWidgets.QComboBox):
            text = combo.currentText().strip()
            return text or None
        return None

    def _action_for_row(self, row: int) -> str:
        combo = self.table.cellWidget(row, self.COL_ACTION)
        return str(combo.currentData()) if isinstance(combo, QtWidgets.QComboBox) else "map"

    def _suggest_match(self, key: str, raw_value: Any) -> YamlFieldMatch:
        return self.matcher.propose(source_key=key, source_value=raw_value, schema=self.schema)

    def _row_widget_changed(self) -> None:
        current = self.table.currentRow()
        if current >= 0:
            status_item = self.table.item(current, self.COL_STATUS)
            if status_item is not None and status_item.text() not in {"user_confirmed", "ignored"}:
                status_item.setText("user_corrected")
        self.state_changed.emit()

    def _queue_preview_update(self) -> None:
        self._preview_timer.start()


YamlMappingDialog = YamlReconciliationDialog


def _status_for(field, transformed, unit_status: str | None, canonical: bool, match: YamlFieldMatch | None = None) -> str:
    if field is None:
        return "unmapped"
    if match is not None and match.requires_confirmation:
        return "ambiguous"
    if match is not None and match.evidence:
        if any(item.startswith("alias:canonical_path") for item in match.evidence):
            return "canonical_mapped"
        if any(item.startswith("alias:weak_key") or item.startswith("alias:deprecated") for item in match.evidence):
            return "ambiguous"
        if any(item.startswith("alias:") for item in match.evidence):
            return "alias_mapped"
    if transformed is not None and transformed.transform_name == "bool_validity_map":
        return "value_transformed"
    if transformed is not None and "ISO" in transformed.transform_name:
        return "date_format_inferred" if transformed.requires_confirmation else "auto_mapped"
    if transformed is not None and transformed.warnings:
        if any("Unit" in warning for warning in transformed.warnings):
            return "requires_unit"
        return "ambiguous"
    if unit_status:
        return unit_status
    return "canonical_mapped" if canonical else "alias_mapped"


def _transform_text(transformed, unit_status: str | None) -> str:
    if transformed is None:
        return ""
    if unit_status:
        return f"{unit_status}; {conversion_preview(transformed.canonical_value, transformed.canonical_unit, None)}"
    return transformed.transform_name


def _get_dotted_value(payload: dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in [item for item in path.split(".") if item]:
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _example_text(value: Any) -> str:
    if isinstance(value, dict):
        if "value" in value:
            unit = value.get("unit")
            return f"{value.get('value')} {unit}".strip() if unit else str(value.get("value"))
        return "{...}"
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    return "" if value is None else str(value)
