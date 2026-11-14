# Local pitch artifacts

`aimo-order-desk-draft.pdf` is the seven-slide review PDF. `aimo-order-desk-draft.pptx` is the editable source deck. Both remain local drafts. Nothing was uploaded or submitted.

`build_pitch.mjs` authors native text with the bundled first-party Artifact Tool. The deck uses Noto Sans and Noto Serif, a 16:9 canvas and the application's ivory/forest/orange palette. Speaker notes contain the relevant source/assumption disclosures. The private validation receipt and render previews are under ignored `.local/pitch-build/`.

To create another validated revision with the same bundled runtime:

```bash
/home/hasan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node docs/pitch/build_pitch.mjs v2
```

Use a new suffix for each revision. When `.local/pitch-ui.png` is present, slide 3 includes that clean application screenshot. Review the screenshot for credentials and restricted catalog text before using it. Without it, the slide uses the truthful typographic explanation of Rewind & Repair.

Native PDF export in this runtime failed to resolve `#standard-fonts/Helvetica`. The reviewed PDF therefore uses the verified slide PNG renders through `build_pdf.py` and ReportLab. The PPTX retains editable text. All seven PDF pages were rendered with Poppler and visually inspected; no PowerPoint inspection is claimed.
