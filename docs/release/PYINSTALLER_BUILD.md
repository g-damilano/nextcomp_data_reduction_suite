# PyInstaller Build

Use `build_dist_pyinstaller.bat` from the repository root to create the Windows desktop bundle.

The script rebuilds the React interface, then runs PyInstaller against `mtdp_enrichment.spec`. The compiled app follows the existing NextCOMP compression-module release layout and is written to:

```text
dist\mtdp_enrichment\mtdp_enrichment.exe
```

The bundle is one-file mode. It includes the React shell, PySide6 desktop wrapper, ISO method defaults, mapping profiles, Jinja report templates, Vega/plot recipe catalog, and MTDA archive handoff assets used by the production report writer.

Editable defaults are embedded in the executable. On first run the frozen runtime materializes the editable resource trees under the same user app-data root used by the previous NextCOMP compression module:

```text
%APPDATA%\NextCOMP\mtdp_enrichment
```

The runtime prefers that external resource folder after first run, so generated methods, edited method registries, mapping profiles, and schema/asset defaults are not written back into the PyInstaller extraction directory. Override the folder with `MTDP_ENRICHMENT_RESOURCE_ROOT` when a controlled deployment needs a different writable location.

The script intentionally mirrors the previous build script and requires the local `pyinstaller` conda environment at `C:\Users\giaco\anaconda3\envs\pyinstaller`.

Before running PyInstaller, the script installs `requirements-pyinstaller.txt` into that conda environment with `PYTHONNOUSERSITE=1`. This prevents the build from depending on packages found only in the Windows roaming user-site folder.
