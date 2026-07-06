# Compression Model GUI — React/PySide6 window seed

This bundle is a code-first React rework of the supplied compression-model GUI segments.

It now follows the launcher/child-window structure from the mockup:

- the main PySide6 window is the launcher
- the launcher exposes exactly three primary launch controls
- each launch control opens its own separate PySide6 child window
- child windows render only their own interface content and do not include the previous Home/Dataset/Method/Analysis route menu

Integrated source segments:

- `Launcher` — from `MTDP Compression Testing - Home v1.1.dc.html`
- `Dataset Packaging` — from the v4 packaging React conversion
- `Method editor` — from `Analysis Method Editor - Hi-Fi v2 (refined).dc.html`
- `Analysis / Method Run Wizard` — from the supplied React/JSX wizard files

The goal of this seed is interface consolidation and window-shell correction, not backend integration. Backend calls remain stubbed behind the PySide6/QWebChannel bridge seam.

## Run as a React app

```bash
npm install
npm run dev
```

The browser build uses popup windows as a development fallback when the PySide6 bridge is unavailable.

## Build / validate static frontend

```bash
npm run build
npm run validate
```

The built static app is written to `dist/`. `npm run validate` performs the production build plus the mock-interface integration/adversarial checks.

## Run inside PySide6

```bash
cd desktop
python run_pyside6_shell.py
```

The PySide6 shell now serves `../dist/index.html` through a local loopback HTTP server, which avoids `file://` module-loading edge cases in child windows.

## Window behaviour

Launcher controls:

- `Dataset Packaging`
- `Method`
- `Analysis`

Keyboard shortcuts from the launcher:

- `Ctrl+D` — open Dataset Packaging child window
- `Ctrl+M` — open Method Editor child window
- `Ctrl+A` — open Method Run Wizard child window

Child windows use per-interface default/minimum dimensions and no longer render the repeated internal Home/Dataset/Method/Analysis navigation overlay. Window dragging is delegated through the existing top/header regions into the PySide6 frame bridge; no separate drag handle is rendered.

## Implementation notes

The v4 Dataset Packaging and method-run wizard are React components. The two `.dc.html` interfaces are mounted through the included `dc-runtime`, which compiles their HTML templates and logic classes into React components at runtime. This preserves the source HTML logic without visual reconstruction and keeps them inside the corrected window shell.

This is therefore a practical seed for the next phase: replace the placeholder bridge in `src/backend/desktopApi.js` and `desktop/run_pyside6_shell.py` with the real compression-model backend calls.

## Validation

See `docs/VALIDATION_REPORT.md` for the final validation result.


## Window-shell behavior

The default PySide6 entry point opens the main launcher window. The launcher keeps the original three primary module launch controls and opens each interface as a separate child window:

- Dataset Packaging
- Analysis Method Editor
- Method Run Wizard

Run:

```bat
cd compression_gui_react_runtime_fixed\desktop
python run_pyside6_shell.py
```

Backend/scientific logic remains stubbed; this bundle is the stable GUI shell seed for the next wiring phase.
