# Test Evidence v1.0

## Official Release Environment

- Date: 2026-05-08
- Shell: PowerShell
- Conda environment: `modulus-gui`
- Repository root: `c:\Users\giaco\Documents\GitHub\compression_module`
- Python path: `src`

## Official Test Command

```powershell
$env:PYTHONPATH='src'
conda run -n modulus-gui python -m pytest -q
```

## Output

```text
.....................................................................    [100%]

69 passed in 6.95s
```

The raw captured console output is also stored in `docs/release/pytest_v1_0_raw.txt`.

## Skips

No tests were skipped in the official `modulus-gui` release environment.

## Targeted UI/Golden Smoke

Command:

```powershell
$env:PYTHONPATH='src'
$env:MTDP_QT_API='PyQt6'
$env:QT_QPA_PLATFORM='offscreen'
conda run -n modulus-gui python -m pytest -q tests/mtdp/test_ui_smoke.py tests/mtdp/test_about_dialog.py tests/mtdp/test_image_evidence_dialog.py tests/mtdp/test_supplemental_files_dialog.py tests/mtdp/test_yaml_reconciliation.py tests/mtdp/test_v1_golden_fixture.py
```

Output:

```text
..............                                                           [100%]
14 passed in 1.11s
```

## Count Reconciliation

Earlier inspection in a different environment reported `57 passed, 10 skipped`. That environment did not exercise the same optional Qt/UI path. The v1.0 release evidence uses the intended release environment, `modulus-gui`, where all intended tests are available and pass.
