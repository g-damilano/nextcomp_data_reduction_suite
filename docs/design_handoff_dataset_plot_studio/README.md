# MTDA Archive Browser Handoff Assets

This folder is retained because the production MTDA writer uses these three
files to generate the browsable archive `index.html`, aggregate plot page, and
run browser pages:

- `MTDA Archive.dc.html`
- `MTDA Dataset.dc.html`
- `support.js`

The original handoff sample `data/` fixtures are not bundled in the public
release because they contain historical example archive paths and stale
`dataset_report.html` / run-summary examples. Production MTDA pages are
hydrated from the analysed dataset at generation time by
`src/archives/mtda/writer.py`.

Do not treat these files as user-facing reports. They are shell inputs used by
the writer while preserving the current MTDA browser layout and behaviour.
