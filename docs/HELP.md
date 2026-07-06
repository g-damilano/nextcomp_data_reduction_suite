# In-App Help Content

The application Help menu summarises the same guidance as the root
`GUIDELINES.md`.

Use the suite in this order:

1. Dataset Packaging creates or repairs an MTDP package from raw files.
2. Method Editor manages editable method definitions while keeping ISO 14126
   read-only.
3. Method Analysis runs one MTDP package through one method, then generates an
   MTDA archive.
4. The MTDA browser opens the archive index, formal report, audit report, plots,
   canonical data, and decision records.

Important rules:

- Raw source files and source MTDP packages are not modified by method runs.
- ISO 14126 is the reference method and is not editable or deletable.
- Editable generated methods live under `src/methods/generated` at runtime.
- Acceptance cockpit content should support scientific decisions, especially
  keep/remove decisions for flagged runs.
- MTDA report pages should be derived from analysed dataset data, not mock-up
  placeholders.

Keyboard shortcuts:

- `Ctrl+D`: open Dataset Packaging.
- `Ctrl+M`: open Method.
- `Ctrl+A`: open Analysis.
- `F11` or `Alt+Enter`: maximise or restore.
- `Ctrl+Shift+M`: minimise.
- `Ctrl+W`: close window.
- `Ctrl+Q`: quit.
- `Esc`: close menus and dialogs.

For the screenshot walkthrough, read `GUIDELINES.md` in the repository root.
