# Release-Candidate Build and Handoff

## Build

From the repository root:

```powershell
python tools/build_rc.py --output release_candidate
```

This writes `release_candidate/rc_release_manifest.json` and copies the UAT
handoff documents. To also build the PyInstaller application bundle:

```powershell
python tools/build_rc.py --run-pyinstaller --output release_candidate
```

The frozen application must include:

- `config/method_registry.yaml`
- `mappings/`
- `src/methods/**` recipe and method package YAML/JSON files
- `mtdp_enrichment/schema_library/`
- application icons/logos

## Runtime Resource Rule

Application code should resolve registry, method package, mapping, schema, and
asset paths through `runtime.resources.ResourceResolver`. Direct repository-root
path assumptions are acceptable in tests and one-off development tools only.

## Generated Artifact Policy

RC builds, smoke-test MTDP/MTDA archives, workbench folders, and exports are
generated artifacts. They should be written under `release_candidate/`,
temporary test directories, or another ignored local output directory unless a
maintainer intentionally promotes one as a fixture.
