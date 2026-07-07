import{i as e,n as t,r as n,t as r}from"./app.js";var i=e(n(),1),a=r();function o({name:e,template:t,logic:n,hostStyle:r,className:o,onReady:s,...c}){let[l,u]=i.useState(null),[d,f]=i.useState(null);return i.useEffect(()=>{let r=!1;function i(){try{if(!window.__dcUpdate||!window.getDC)throw Error(`dc-runtime is not available. main.jsx must load src/vendor/dc-runtime.js before rendering.`);u(null),window.__dcUpdate(e,`html`,t,!1),window.__dcUpdate(e,`js`,n,!1),window.__dcRegistry?.[e]&&(window.__dcRegistry[e].fetched=!0);let i=window.getDC(e);if(!i)throw Error(`dc-runtime did not return a component for ${e}.`);r||(u(()=>i),f(null))}catch(e){console.error(`[DcRuntimeHost]`,e),r||(u(null),f(e),window.__COMPRESSION_GUI_MOUNT_STATE=`error`,window.__COMPRESSION_GUI_BOOT_ERROR=e?.stack||String(e))}}return i(),()=>{r=!0}},[e,t,n]),i.useEffect(()=>{if(!l||d)return;let t=window.setTimeout(()=>{s?.({name:e}),window.dispatchEvent(new CustomEvent(`compression-gui-screen-ready`,{detail:{name:e}}))},0);return()=>window.clearTimeout(t)},[l,d,e,s]),d?(0,a.jsxs)(`div`,{className:`dc-host-error`,children:[(0,a.jsx)(`h2`,{children:`DC component failed to mount`}),(0,a.jsx)(`pre`,{children:d.stack||String(d)})]}):l?(0,a.jsx)(`div`,{className:[`dc-runtime-host`,o].filter(Boolean).join(` `),children:(0,a.jsx)(l,{...c,__hostStyle:r||{height:`100%`}})}):(0,a.jsx)(`div`,{className:`dc-host-loading`,children:`Preparing interface…`})}var s={suite:{eyebrow:`Suite guidelines`,title:`Using the Data Reduction Suite`,subtitle:`Move from raw compression-test files to a reviewed MTDA archive.`,intent:`The suite is organised around the scientific record: package the data, choose the method rules, run the analysis, then review evidence before reporting.`,workflow:[`Use Dataset Packaging when you need to create or inspect an MTDP input package from raw measurement files.`,`Use Method when you need an editable method version. The ISO reference remains read-only and is kept as the baseline.`,`Use Analysis when you have one MTDP package ready and want to produce an MTDA analysed dataset archive.`,`Use the acceptance cockpit to decide flagged runs with plots, metrics, defaults, and justifications.`,`Use the MTDA browser to review the archive index, test report, audit report, plots, tables, and decision register.`],checks:[`Confirm package identity, run count, channels, and required metadata before analysis.`,`Confirm any method changes were saved as a method version before selecting them in Analysis.`,`Confirm flagged-run decisions in Accept match the Output run manifest before sharing results.`,`Review generated reports and plots. The software prepares evidence; the final scientific judgement remains with the user.`]},dataset:{eyebrow:`Dataset Packaging`,title:`Create a clean MTDP package`,subtitle:`Prepare raw compression-test measurements for analysis without changing the original files.`,intent:`Use this section when you have raw files, sidecars, metadata, or image evidence that must be organised into a traceable package.`,workflow:[`Open raw files, a source folder, or an existing MTDP package.`,`Review the proposed grouping so each physical specimen is represented by the correct run.`,`Check channel assignments for load, strain, time, crosshead, and any supporting traces.`,`Complete dataset-level and run-level metadata. Use required-field filters to focus on what blocks export.`,`Attach image evidence and supplemental files when they explain the test context.`,`Validate the package and export the MTDP only when the review panel is clear enough for analysis.`],checks:[`Original raw files are copied into the package and are not modified.`,`Every exported run should have the expected measurement channels and specimen dimensions.`,`Warnings may be acceptable, but hard missing fields should be resolved before moving to Analysis.`,`Open the exported package in Analysis only after confirming the package path and run list.`]},method:{eyebrow:`Method`,title:`Create and manage method versions`,subtitle:`Adjust analysis rules while keeping the ISO reference protected.`,intent:`Use this section when the scientific method needs a controlled editable version for test range, modulus, bending, or acceptance/report settings.`,workflow:[`Start from the ISO reference or an existing generated method.`,`Create a new method when you need an editable version. Reference methods cannot be edited or deleted.`,`Review the pipeline map: data entry, test range, stress-strain, modulus, bending, strength, acceptance, and reports.`,`Edit only the controlled method parameters that belong in the method record.`,`Validate the draft before use, then save the method version so it is available in Analysis.`,`Export or import method packages when you need to move controlled method versions between workspaces.`],checks:[`The Save method button should only be active after a real edit.`,`Unsaved edits should be saved before closing or switching method versions.`,`The stress-strain stage is derived from package data and is not edited in Method.`,`Use the change ledger to understand what differs from the reference method before using it for analysis.`]},analysis:{eyebrow:`Analysis`,title:`Run a method and review the MTDA output`,subtitle:`Reduce one MTDP package with one method, then make acceptance decisions before reporting.`,intent:`Use this section when a packaged dataset is ready and you need reduced results, evidence plots, reports, and a reviewed MTDA archive.`,workflow:[`Choose one MTDP package. Recent files help reopen known packages; Choose package lets you browse folders.`,`Choose the ISO reference method or an editable generated method version.`,`Review mapping so the package channels and metadata are bound to the method inputs.`,`Check readiness, run the method, and inspect validation before acceptance.`,`Use Accept to review flagged runs with defect-specific evidence, plots, metrics, defaults, and justification fields.`,`Use Output to complete report-only metadata, open reports, and finalise the MTDA archive.`],checks:[`Only an MTDP package is the input to a method run. MTDA archives are analysis outputs.`,`The acceptance cockpit should help decide keep or remove. Internal software diagnostics do not belong there unless they support that decision.`,`Accept and Output run manifests must agree before finalisation.`,`Open the MTDA archive index, test report, audit report, and relevant plots before sharing results.`]}};function c({section:e=`suite`}){let t=s[e]||s.suite;return(0,a.jsxs)(`div`,{className:`section-guide`,children:[(0,a.jsxs)(`div`,{className:`section-guide__lead`,children:[(0,a.jsx)(`div`,{className:`section-guide__eyebrow`,children:t.eyebrow}),(0,a.jsx)(`h3`,{children:t.title}),(0,a.jsx)(`p`,{children:t.subtitle})]}),(0,a.jsxs)(`section`,{children:[(0,a.jsx)(`h4`,{children:`Purpose`}),(0,a.jsx)(`p`,{children:t.intent})]}),(0,a.jsxs)(`section`,{children:[(0,a.jsx)(`h4`,{children:`Workflow`}),(0,a.jsx)(`ol`,{children:t.workflow.map(e=>(0,a.jsx)(`li`,{children:e},e))})]}),(0,a.jsxs)(`section`,{children:[(0,a.jsx)(`h4`,{children:`Before moving on`}),(0,a.jsx)(`ul`,{children:t.checks.map(e=>(0,a.jsx)(`li`,{children:e},e))})]})]})}function l({section:e=`suite`,onClose:t}){let n=s[e]||s.suite;return(0,a.jsx)(`div`,{className:`section-guide-scrim`,role:`presentation`,onMouseDown:e=>e.target===e.currentTarget&&t?.(),children:(0,a.jsxs)(`section`,{className:`section-guide-dialog`,role:`dialog`,"aria-modal":`true`,"aria-labelledby":`section-guide-title`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsxs)(`header`,{className:`section-guide-dialog__chrome`,children:[(0,a.jsx)(`span`,{className:`section-guide-dialog__dot`,"aria-hidden":`true`}),(0,a.jsxs)(`h2`,{id:`section-guide-title`,children:[`About `,n.eyebrow]}),(0,a.jsx)(`button`,{type:`button`,className:`section-guide-dialog__close`,"aria-label":`Close`,onClick:t,children:`x`})]}),(0,a.jsxs)(`div`,{className:`section-guide-dialog__body`,children:[(0,a.jsx)(c,{section:e}),(0,a.jsxs)(`div`,{className:`section-guide-dialog__actions`,children:[(0,a.jsx)(`span`,{children:`Full walkthrough: GUIDELINES.md`}),(0,a.jsx)(`button`,{type:`button`,onClick:t,children:`Close`})]})]})]})})}var u=`
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box}
  body{margin:0;background:#cdd1d8;font-family:'IBM Plex Sans',system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  @keyframes omFade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
</style>
</helmet>

<div style="min-height:100vh;display:flex;align-items:flex-start;justify-content:center;padding:34px 24px;background:#cdd1d8">
  <div style="width:980px;max-width:100%;background:#ffffff;border-radius:11px;box-shadow:0 22px 70px rgba(15,22,38,.30),0 2px 6px rgba(15,22,38,.14);overflow:hidden;border:1px solid #b9bec7">

    <!-- TITLE BAR -->
    <div style="height:38px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;background:#f7f8fa;border-bottom:1px solid #e2e5ea">
      <div style="display:flex;align-items:center;gap:9px">
        <div style="width:13px;height:13px;border-radius:50%;background:#b3123c;box-shadow:inset 0 0 0 2.2px #fff"></div>
        <span style="font-size:12.5px;font-weight:600;color:#1b2230">NextCOMP Data Reduction Suite</span>
      </div>
      <div data-window-controls="true" style="display:flex;align-items:center;gap:17px;color:#79818f">
        <span data-window-control="minimize" onClick="{{ minimizeWindow }}" style="font-size:13px;cursor:pointer;padding:5px 3px">—</span>
        <span data-window-control="maximize" onClick="{{ toggleMaximizeWindow }}" style="font-size:11px;border:1.4px solid #aab0bb;width:11px;height:11px;display:inline-block;cursor:pointer"></span>
        <span data-window-control="close" onClick="{{ closeWindow }}" style="font-size:14px;line-height:1;cursor:pointer;padding:5px 3px">✕</span>
      </div>
    </div>

    <!-- MENU BAR -->
    <div style="position:relative;height:36px;display:flex;align-items:center;justify-content:space-between;padding:0 6px;background:#fff;border-bottom:1px solid #e4e7ec">
      <div style="display:flex;align-items:stretch;height:100%">
        <div onClick="{{ toggleFile }}" style="display:flex;align-items:center;padding:0 12px;font-size:13px;color:#1b2230;cursor:pointer;border-radius:5px" style-hover="background:#eef1f5">File</div>
        <div onClick="{{ toggleHelp }}" style="display:flex;align-items:center;padding:0 12px;font-size:13px;color:#1b2230;cursor:pointer;border-radius:5px" style-hover="background:#eef1f5">Help</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;padding-right:8px">
        <span style="font-size:11px;color:#9aa2b0">Compression module</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#48505f;background:#f0f2f5;border:1px solid #e4e7ec;border-radius:20px;padding:2px 9px">v1.1.0</span>
      </div>

      <sc-if value="{{ anyMenuOpen }}" hint-placeholder-val="{{ false }}">
        <div onClick="{{ closeMenus }}" style="position:fixed;inset:0;z-index:40"></div>
      </sc-if>

      <sc-if value="{{ fileMenuOpen }}" hint-placeholder-val="{{ false }}">
        <div style="position:absolute;top:34px;left:6px;z-index:50;min-width:248px;background:#fff;border:1px solid #d6dae1;border-radius:9px;box-shadow:0 14px 40px rgba(20,28,45,.18);padding:6px;animation:omFade .12s ease both">
          <div onClick="{{ launchDataset }}" style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5"><span>Open Dataset Packaging…</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9aa2b0">⌘D</span></div>
          <sc-if value="{{ methodNotReady }}" hint-placeholder-val="{{ true }}">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:6px;font-size:13px;color:#aab0bb"><span>Open Method…</span><span style="font-size:11px;color:#9a6206">Planned</span></div>
          </sc-if>
          <sc-if value="{{ methodReady }}" hint-placeholder-val="{{ false }}">
            <div onClick="{{ launchMethod }}" style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5"><span>Open Method…</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9aa2b0">⌘M</span></div>
          </sc-if>
          <div onClick="{{ launchAnalysis }}" style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5"><span>Open Analysis…</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9aa2b0">⌘A</span></div>
          <div style="height:1px;background:#eceef2;margin:5px 8px"></div>
          <div aria-disabled="true" style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:6px;font-size:13px;color:#aab0bb;cursor:default"><span>Recent sessions</span><span style="font-size:11px;color:#aab0bb">Not available</span></div>
          <div style="height:1px;background:#eceef2;margin:5px 8px"></div>
          <div onClick="{{ exitApp }}" style="padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5">Exit</div>
        </div>
      </sc-if>

      <sc-if value="{{ helpMenuOpen }}" hint-placeholder-val="{{ false }}">
        <div style="position:absolute;top:34px;left:56px;z-index:50;min-width:262px;background:#fff;border:1px solid #d6dae1;border-radius:9px;box-shadow:0 14px 40px rgba(20,28,45,.18);padding:6px;animation:omFade .12s ease both">
          <div onClick="{{ closeMenus }}" style="padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5">Documentation</div>
          <div onClick="{{ openShortcuts }}" style="padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5">Keyboard shortcuts</div>
          <div onClick="{{ openLicensing }}" style="padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5">Licensing &amp; notices…</div>
          <div style="height:1px;background:#eceef2;margin:5px 8px"></div>
          <div onClick="{{ openAbout }}" style="padding:7px 10px;border-radius:6px;font-size:13px;color:#1b2230;cursor:pointer" style-hover="background:#eef1f5">About this suite…</div>
        </div>
      </sc-if>
    </div>

    <!-- HERO (full-bleed) -->
    <div style="position:relative;background:linear-gradient(135deg,#1a5c33 0%,#123f24 100%);padding:28px 30px">
      <div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,.10) 1.4px,transparent 1.6px);background-size:22px 22px;opacity:.6"></div>
      <div style="position:relative;display:flex;justify-content:space-between;align-items:center;gap:24px">
        <div>
          <div style="font-size:10.5px;font-weight:600;letter-spacing:.16em;color:rgba(255,255,255,.72);text-transform:uppercase">NextCOMP · Compression Testing</div>
          <div style="font-size:30px;font-weight:700;color:#fff;margin-top:9px;letter-spacing:-.01em">Data Reduction Suite</div>
          <div style="font-size:13.5px;color:rgba(255,255,255,.82);margin-top:8px;max-width:560px">Choose a module to begin — set up a new batch of tests, or open results you've already collected.</div>
        </div>
        <img src="assets/nextcomp-logo.png" alt="NextCOMP" style="width:74px;height:auto;display:block;flex:none" />
      </div>
    </div>

    <!-- WORKFLOW STRIP (integrated band) -->
    <sc-if value="{{ showWorkflow }}" hint-placeholder-val="{{ true }}">
      <div style="display:flex;align-items:flex-start;gap:9px;padding:14px 30px;background:#fbfcfd;border-bottom:1px solid #eceef2">
        <div style="display:flex;align-items:flex-start;gap:9px"><span style="width:18px;height:18px;border-radius:50%;background:#fbe9ef;color:#b3123c;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none;margin-top:1px">1</span><div><div style="font-size:12.5px;font-weight:600;color:#1b2230">Dataset Packaging</div><div style="font-size:11.5px;color:#79818f;margin-top:2px">Package your dataset</div></div></div>
        <span style="flex:1;height:1px;background:#e4e7ec;min-width:18px;margin-top:9px"></span>
        <div style="display:flex;align-items:flex-start;gap:9px"><span style="width:18px;height:18px;border-radius:50%;background:#eef1f4;color:#8a93a3;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none;margin-top:1px">2</span><div><div style="font-size:12.5px;font-weight:600;color:#8a93a3">Method</div><div style="font-size:11.5px;color:#9aa2b0;margin-top:2px">Set the rules</div></div></div>
        <span style="flex:1;height:1px;background:#e4e7ec;min-width:18px;margin-top:9px"></span>
        <div style="display:flex;align-items:flex-start;gap:9px"><span style="width:18px;height:18px;border-radius:50%;background:#e7f4ec;color:#1f7a44;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none;margin-top:1px">3</span><div><div style="font-size:12.5px;font-weight:600;color:#1b2230">Analysis</div><div style="font-size:11.5px;color:#79818f;margin-top:2px">Get your results</div></div></div>
      </div>
    </sc-if>

    <!-- MODULES (connected list — no cards) -->
    <div>

      <!-- DATASET -->
      <div onClick="{{ launchDataset }}" role="button" aria-label="Launch Dataset Packaging" tabindex="0" data-launcher-button="dataset-packaging" style="display:flex;border-bottom:1px solid #eceef2;transition:background .12s;cursor:pointer" style-hover="background:#f3f6fb">
        <div style="width:3px;background:#b3123c;flex:none"></div>
        <div style="flex:1;padding:18px 30px 20px 27px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">
            <div>
              <div style="display:flex;align-items:center;gap:10px"><span style="font-size:18px;font-weight:700;color:#b3123c">Dataset Packaging</span></div>
              <div style="font-size:13px;color:#48505f;margin-top:5px;max-width:540px">Get your measurements clean, complete and ready to analyse — with nothing missing and nothing lost.</div>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;margin-top:14px">
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Bring in your raw test files and let the suite sort and group them for you.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Enter the specimen details once and apply them across every test.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">See exactly what's still needed before you move on — no surprises later.</span></div>
          </div>
          <div style="margin-top:14px;font-size:11.5px;color:#79818f">Your original files are never changed.</div>
        </div>
        <div style="display:flex;align-items:center;padding:0 30px 0 12px;flex:none"><svg width="26" height="68" viewBox="0 0 26 68" fill="none" style="display:block"><path d="M5 6 L21 34 L5 62" stroke="#c6ccd6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      </div>

      <!-- METHOD (planned) -->
      <sc-if value="{{ methodNotReady }}" hint-placeholder-val="{{ true }}">
      <div style="display:flex;border-bottom:1px solid #eceef2;background:#fcfcfd">
        <div style="width:3px;background:#c4cad3;flex:none"></div>
        <div style="flex:1;padding:18px 30px 20px 27px">
          <div>
            <div style="display:flex;align-items:center;gap:10px"><span style="font-size:18px;font-weight:700;color:#8a93a3">Method</span></div>
            <div style="font-size:13px;color:#79818f;margin-top:5px;max-width:540px">Decide how your compression tests are measured — and keep every version on the record.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;margin-top:14px">
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#eef1f4;color:#aab0bb;font-size:10px;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">·</span><span style="font-size:12.5px;color:#79818f">Set the rules behind your strength, stiffness and bending results.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#eef1f4;color:#aab0bb;font-size:10px;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">·</span><span style="font-size:12.5px;color:#79818f">Adjust with confidence — every change is tracked and can be undone.</span></div>
          </div>
          <div style="margin-top:14px;font-size:11.5px;color:#9aa2b0">Arriving in a later release — your work won't be lost.</div>
        </div>
        <div style="display:flex;align-items:center;padding:0 30px 0 12px;flex:none"><svg width="26" height="68" viewBox="0 0 26 68" fill="none" style="display:block"><path d="M5 6 L21 34 L5 62" stroke="#dde1e7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      </div>
      </sc-if>

      <!-- METHOD (ready — flips on via tweak) -->
      <sc-if value="{{ methodReady }}" hint-placeholder-val="{{ false }}">
      <div onClick="{{ launchMethod }}" role="button" aria-label="Launch Method Editor" tabindex="0" data-launcher-button="method-editor" style="display:flex;border-bottom:1px solid #eceef2;transition:background .12s;cursor:pointer" style-hover="background:#f3f6fb">
        <div style="width:3px;background:#5b3fae;flex:none"></div>
        <div style="flex:1;padding:18px 30px 20px 27px">
          <div>
            <div style="display:flex;align-items:center;gap:10px"><span style="font-size:18px;font-weight:700;color:#5b3fae">Method</span></div>
            <div style="font-size:13px;color:#48505f;margin-top:5px;max-width:540px">Decide how your compression tests are measured — and keep every version on the record.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;margin-top:14px">
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#efeafc;color:#5b3fae;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Set the rules behind your strength, stiffness and bending results.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#efeafc;color:#5b3fae;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Adjust with confidence — every change is tracked and can be undone.</span></div>
          </div>
          <div style="margin-top:14px;font-size:11.5px;color:#79818f">Every change is staged and reversible.</div>
        </div>
        <div style="display:flex;align-items:center;padding:0 30px 0 12px;flex:none"><svg width="26" height="68" viewBox="0 0 26 68" fill="none" style="display:block"><path d="M5 6 L21 34 L5 62" stroke="#c6ccd6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      </div>
      </sc-if>

      <!-- ANALYSIS -->
      <div onClick="{{ launchAnalysis }}" role="button" aria-label="Launch Method Analysis" tabindex="0" data-launcher-button="analysis" style="display:flex;border-bottom:1px solid #eceef2;transition:background .12s;cursor:pointer" style-hover="background:#f3f6fb">
        <div style="width:3px;background:#1f7a44;flex:none"></div>
        <div style="flex:1;padding:18px 30px 20px 27px">
          <div>
            <div style="display:flex;align-items:center;gap:10px"><span style="font-size:18px;font-weight:700;color:#1f7a44">Analysis</span></div>
            <div style="font-size:13px;color:#48505f;margin-top:5px;max-width:540px">Get trustworthy compression results — strength, stiffness and bending — ready to report.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;margin-top:14px">
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">See at a glance which specimens are ready, and which still need attention.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Open any result to see the curve and the reasoning behind the number.</span></div>
            <div style="display:flex;align-items:flex-start;gap:9px"><span style="flex:none;width:15px;height:15px;border-radius:50%;background:#e7f5ec;color:#1f9d57;font-size:9px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;margin-top:1px">✓</span><span style="font-size:12.5px;color:#48505f">Produce a clean test report you can share and stand behind.</span></div>
          </div>
          <div style="margin-top:14px;font-size:11.5px;color:#79818f">Already have a package? Start here.</div>
        </div>
        <div style="display:flex;align-items:center;padding:0 30px 0 12px;flex:none"><svg width="26" height="68" viewBox="0 0 26 68" fill="none" style="display:block"><path d="M5 6 L21 34 L5 62" stroke="#c6ccd6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
      </div>
    </div>

    <!-- RECENT SESSIONS (integrated) -->
    <sc-if value="{{ showRecent }}" hint-placeholder-val="{{ true }}">
      <div style="padding:16px 30px 4px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:10px;font-weight:600;letter-spacing:.14em;color:#9aa2b0;text-transform:uppercase">Recent sessions</span>
          <span style="font-size:11.5px;color:#2f6bd8;cursor:pointer">View all</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;padding:11px 30px;border-top:1px solid #eceef2;transition:background .12s" style-hover="background:#fafbfc">
        <span style="width:8px;height:8px;border-radius:50%;background:#b3123c;flex:none"></span>
        <div style="flex:1;min-width:0">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:#1b2230">CAG-CF-ER-Comp</div>
          <div style="font-size:11.5px;color:#79818f;margin-top:1px">Dataset · 7 tests · 4/7 ready to export · saved 19:18</div>
        </div>
        <span style="flex:none;font-size:12px;font-weight:600;color:#2f6bd8;cursor:pointer">Resume →</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;padding:11px 30px;border-top:1px solid #eceef2;transition:background .12s" style-hover="background:#fafbfc">
        <span style="width:8px;height:8px;border-radius:50%;background:#1f7a44;flex:none"></span>
        <div style="flex:1;min-width:0">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:#1b2230">CAG-CF-Modied-ULV20</div>
          <div style="font-size:11.5px;color:#79818f;margin-top:1px">Analysis · method v0.2.0 · 1 change in progress · 2 days ago</div>
        </div>
        <span style="flex:none;font-size:12px;font-weight:600;color:#2f6bd8;cursor:pointer">Resume →</span>
      </div>
    </sc-if>

    <!-- FUNDING + LICENSE FOOTER -->
    <div style="background:#f7f8fa;border-top:1px solid #e4e7ec;padding:15px 30px 13px">
      <div style="font-size:11px;line-height:1.55;color:#79818f;max-width:860px">Funding: UK Engineering and Physical Sciences Research Council (EPSRC) programme Grant EP/T011653/1, Next Generation Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression, Imperial College London and the University of Bristol.</div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;gap:14px;flex-wrap:wrap">
        <span style="font-size:11px;color:#79818f">Licensed under the Apache License, Version 2.0 · © 2026 Imperial College London</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#9aa2b0">NextCOMP Data Reduction Suite · v1.1.0</span>
      </div>
    </div>

    <!-- STATUS BAR -->
    <div style="height:30px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#fff;border-top:1px solid #e4e7ec">
      <div style="display:flex;align-items:center;gap:7px">
        <span style="width:7px;height:7px;border-radius:50%;background:#1f9d57"></span>
        <span style="font-size:11px;color:#48505f">Ready · no package open</span>
      </div>
      <span style="font-size:11px;color:#9aa2b0">Compression module · schema library connected</span>
    </div>
  </div>

  <!-- ABOUT MODAL -->
  <sc-if value="{{ aboutOpen }}" hint-placeholder-val="{{ false }}">
    <div style="position:fixed;inset:0;z-index:80;background:rgba(15,22,38,.42);display:flex;align-items:center;justify-content:center;padding:24px">
      <div style="width:600px;max-width:100%;max-height:90vh;overflow:auto;background:#fff;border-radius:12px;box-shadow:0 26px 80px rgba(15,22,38,.40);animation:omFade .14s ease both">
        <div style="height:38px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;background:#f7f8fa;border-bottom:1px solid #e2e5ea;border-radius:12px 12px 0 0;position:sticky;top:0">
          <div style="display:flex;align-items:center;gap:9px">
            <div style="width:12px;height:12px;border-radius:50%;background:#b3123c;box-shadow:inset 0 0 0 2px #fff"></div>
            <span style="font-size:12.5px;font-weight:600;color:#1b2230">About — NextCOMP Data Reduction Suite</span>
          </div>
          <span onClick="{{ closeAbout }}" style="font-size:14px;color:#79818f;cursor:pointer;line-height:1">✕</span>
        </div>

        <div style="padding:16px">
          <div style="position:relative;border-radius:10px;overflow:hidden;background:linear-gradient(135deg,#1a5c33 0%,#123f24 100%);padding:22px 24px">
            <div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,.10) 1.4px,transparent 1.6px);background-size:20px 20px;opacity:.55"></div>
            <div style="position:relative;display:flex;justify-content:space-between;align-items:center;gap:18px">
              <div>
                <div style="font-size:10px;font-weight:600;letter-spacing:.16em;color:rgba(255,255,255,.72);text-transform:uppercase">NextCOMP</div>
                <div style="font-size:22px;font-weight:700;color:#fff;margin-top:7px">Data Reduction Suite</div>
                <div style="font-size:12.5px;color:rgba(255,255,255,.82);margin-top:6px">Data reduction pipeline for compression testing.</div>
              </div>
              <img src="assets/nextcomp-logo.png" alt="NextCOMP" style="width:58px;height:auto;display:block;flex:none" />
            </div>
          </div>

          <div style="background:#fff;border:1px solid #e4e7ec;border-radius:9px;padding:16px 18px;margin-top:14px">
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Version</span><span style="font-size:12.5px;color:#1b2230;font-weight:500">1.1.0</span></div>
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Scope</span><span style="font-size:12.5px;color:#1b2230">Compression testing</span></div>
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Modules</span><span style="font-size:12.5px;color:#1b2230">Dataset · Method <span style="color:#9a6206">(planned)</span> · Analysis</span></div>
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Developer</span><span style="font-size:12.5px;color:#1b2230">Giacomo Damilano</span></div>
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Email</span><span style="font-size:12.5px;color:#2f6bd8">giacomo.damilano@gmail.com</span></div>
            <div style="display:flex;gap:10px;padding:5px 0"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">Project</span><span style="font-size:12.5px;color:#1b2230">NextCOMP — Next Generation Fibre-Reinforced Composites</span></div>
            <div style="display:flex;gap:10px;padding:5px 0;align-items:center"><span style="width:88px;flex:none;text-align:right;font-size:12.5px;color:#79818f">License</span><span style="font-size:12.5px;color:#1b2230">Apache License, Version 2.0</span></div>
          </div>

          <div style="font-size:11px;line-height:1.6;color:#79818f;margin-top:14px;padding:0 2px">Funding: UK Engineering and Physical Sciences Research Council (EPSRC) programme Grant EP/T011653/1, Next Generation Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression, Imperial College London and the University of Bristol.</div>

          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px">
            <span onClick="{{ openLicensing }}" style="font-size:12px;font-weight:600;color:#2f6bd8;cursor:pointer">Licensing &amp; notices →</span>
            <button onClick="{{ closeAbout }}" style="font-family:'IBM Plex Sans';font-size:13px;font-weight:600;color:#fff;background:#2f6bd8;border:none;border-radius:7px;padding:9px 22px;cursor:pointer" style-hover="background:#255bbf">Close</button>
          </div>
        </div>
      </div>
    </div>
  </sc-if>

  <!-- LICENSING MODAL -->
  <sc-if value="{{ licensingOpen }}" hint-placeholder-val="{{ false }}">
    <div style="position:fixed;inset:0;z-index:80;background:rgba(15,22,38,.42);display:flex;align-items:center;justify-content:center;padding:24px">
      <div style="width:600px;max-width:100%;max-height:90vh;overflow:auto;background:#fff;border-radius:12px;box-shadow:0 26px 80px rgba(15,22,38,.40);animation:omFade .14s ease both">
        <div style="height:38px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;background:#f7f8fa;border-bottom:1px solid #e2e5ea;border-radius:12px 12px 0 0;position:sticky;top:0">
          <div style="display:flex;align-items:center;gap:9px">
            <div style="width:12px;height:12px;border-radius:50%;background:#b3123c;box-shadow:inset 0 0 0 2px #fff"></div>
            <span style="font-size:12.5px;font-weight:600;color:#1b2230">Licensing &amp; notices — NextCOMP Data Reduction Suite</span>
          </div>
          <span onClick="{{ closeAbout }}" style="font-size:14px;color:#79818f;cursor:pointer;line-height:1">✕</span>
        </div>
        <div style="padding:16px">
          <div style="position:relative;border-radius:10px;overflow:hidden;background:linear-gradient(135deg,#1a5c33 0%,#123f24 100%);padding:22px 24px">
            <div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,.10) 1.4px,transparent 1.6px);background-size:20px 20px;opacity:.55"></div>
            <div style="position:relative;display:flex;justify-content:space-between;align-items:center;gap:18px">
              <div>
                <div style="font-size:10px;font-weight:600;letter-spacing:.16em;color:rgba(255,255,255,.72);text-transform:uppercase">NextCOMP</div>
                <div style="font-size:22px;font-weight:700;color:#fff;margin-top:7px">Licensing &amp; notices</div>
                <div style="font-size:12.5px;color:rgba(255,255,255,.82);margin-top:6px">Apache License, Version 2.0 · © 2026 Imperial College London</div>
              </div>
              <img src="assets/nextcomp-logo.png" alt="NextCOMP" style="width:58px;height:auto;display:block;flex:none" />
            </div>
          </div>
          <div style="background:#fff;border:1px solid #e4e7ec;border-radius:9px;padding:16px 18px;margin-top:14px">
            <div style="font-size:11.5px;line-height:1.6;color:#48505f">© 2026 Imperial College London. This product includes software developed at Imperial College London, made available under the Apache License, Version 2.0.</div>
            <div style="font-size:11.5px;line-height:1.6;color:#48505f;margin-top:8px">Apache-2.0 permits use, modification and redistribution — including for commercial purposes and within proprietary or sold products — provided the licence text and this NOTICE are retained.</div>
            <div style="font-size:11.5px;line-height:1.6;color:#48505f;margin-top:8px">The developer, Giacomo Damilano, is expressly authorised to use, reuse, modify, sublicense and incorporate the project-authored code and documentation, including for commercial purposes and within private, proprietary or sold products, subject to the third-party boundaries set out below.</div>
            <div style="font-size:11.5px;line-height:1.6;color:#79818f;margin-top:8px">The Apache-2.0 licence does not grant rights over third-party materials, standards documents, institutional or project logos, generated outputs, or external libraries identified as separately licensed or restricted. Redistributions must retain the NOTICE file and applicable third-party notices.</div>
            <div style="font-size:11.5px;line-height:1.6;color:#79818f;margin-top:8px">Unless required by applicable law or agreed in writing, the software is provided on an "AS IS" basis, without warranties or conditions of any kind, express or implied. See the licence for the specific language governing permissions and limitations.</div>
            <div style="font-size:11.5px;line-height:1.6;color:#79818f;margin-top:8px">Developed for research purposes. Use responsibly: results and generated outputs are the user's responsibility and should be reviewed before being relied upon for engineering, certification or commercial decisions. The authors and Imperial College London accept no liability for any outcome of its use.</div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px">
            <span onClick="{{ openAbout }}" style="font-size:12px;font-weight:600;color:#2f6bd8;cursor:pointer">← Back to About</span>
            <button onClick="{{ closeAbout }}" style="font-family:'IBM Plex Sans';font-size:13px;font-weight:600;color:#fff;background:#2f6bd8;border:none;border-radius:7px;padding:9px 22px;cursor:pointer" style-hover="background:#255bbf">Close</button>
          </div>
        </div>
      </div>
    </div>
  </sc-if>

  <!-- SHORTCUTS MODAL -->
  <sc-if value="{{ shortcutsOpen }}" hint-placeholder-val="{{ false }}">
    <div style="position:fixed;inset:0;z-index:80;background:rgba(15,22,38,.42);display:flex;align-items:center;justify-content:center;padding:24px">
      <div style="width:460px;max-width:100%;max-height:90vh;overflow:auto;background:#fff;border-radius:12px;box-shadow:0 26px 80px rgba(15,22,38,.40);animation:omFade .14s ease both">
        <div style="height:38px;display:flex;align-items:center;justify-content:space-between;padding:0 14px;background:#f7f8fa;border-bottom:1px solid #e2e5ea;border-radius:12px 12px 0 0;position:sticky;top:0">
          <div style="display:flex;align-items:center;gap:9px">
            <div style="width:12px;height:12px;border-radius:50%;background:#b3123c;box-shadow:inset 0 0 0 2px #fff"></div>
            <span style="font-size:12.5px;font-weight:600;color:#1b2230">Keyboard shortcuts</span>
          </div>
          <span onClick="{{ closeAbout }}" style="font-size:14px;color:#79818f;cursor:pointer;line-height:1">✕</span>
        </div>
        <div style="padding:18px 20px 20px">
          <div style="font-size:10px;font-weight:600;letter-spacing:.13em;color:#9aa2b0;text-transform:uppercase;margin-bottom:4px">Open a module</div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f0f2f5"><span style="font-size:13px;color:#1b2230">Open Dataset Packaging</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#48505f;background:#eff1f4;border:1px solid #e0e3e9;border-radius:5px;padding:2px 8px">⌘D</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f0f2f5"><span style="font-size:13px;color:#1b2230">Open Method <span style="color:#9aa2b0">(when available)</span></span><span style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#48505f;background:#eff1f4;border:1px solid #e0e3e9;border-radius:5px;padding:2px 8px">⌘M</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0"><span style="font-size:13px;color:#1b2230">Open Analysis</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#48505f;background:#eff1f4;border:1px solid #e0e3e9;border-radius:5px;padding:2px 8px">⌘A</span></div>
          <div style="font-size:10px;font-weight:600;letter-spacing:.13em;color:#9aa2b0;text-transform:uppercase;margin:16px 0 4px">General</div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #f0f2f5"><span style="font-size:13px;color:#1b2230">Recent sessions</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#48505f;background:#eff1f4;border:1px solid #e0e3e9;border-radius:5px;padding:2px 8px">⌘R</span></div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0"><span style="font-size:13px;color:#1b2230">Close dialog</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#48505f;background:#eff1f4;border:1px solid #e0e3e9;border-radius:5px;padding:2px 8px">Esc</span></div>
          <div style="display:flex;justify-content:flex-end;margin-top:18px">
            <button onClick="{{ closeAbout }}" style="font-family:'IBM Plex Sans';font-size:13px;font-weight:600;color:#fff;background:#2f6bd8;border:none;border-radius:7px;padding:9px 22px;cursor:pointer" style-hover="background:#255bbf">Close</button>
          </div>
        </div>
      </div>
    </div>
  </sc-if>

  <!-- TOAST -->
  <sc-if value="{{ toast }}" hint-placeholder-val="{{ false }}">
    <div style="position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:90;background:#1b2230;color:#fff;font-size:12.5px;padding:10px 18px;border-radius:8px;box-shadow:0 10px 30px rgba(15,22,38,.30);animation:omFade .16s ease both">{{ toast }}</div>
  </sc-if>
</div>
`,d=`class Component extends DCLogic {
  state = { openMenu: null, modal: null, toast: null };

  toggle(m){ this.setState(s => ({ openMenu: s.openMenu === m ? null : m })); }
  launch(name){
    const routes = { Dataset: 'packaging', 'Dataset Packaging': 'packaging', Method: 'method-editor', Analysis: 'analysis' };
    const labels = { Dataset: 'Dataset Packaging', 'Dataset Packaging': 'Dataset Packaging', Method: 'Method Editor', Analysis: 'Method Analysis' };
    const route = routes[name];
    const label = labels[name] || name;
    this.setState({ toast: 'Opening ' + label + '…', openMenu: null });
    clearTimeout(this._t);
    if (this.props.onNavigate && route) {
      this.props.onNavigate(route);
      this._t = setTimeout(() => this.setState({ toast: null }), 160);
      return;
    }
    this._t = setTimeout(() => this.setState({ toast: null }), 2200);
  }

  renderVals(){
    const p = this.props;
    const methodReady = p.methodReady ?? false;
    return {
      showWorkflow: p.showWorkflow ?? true,
      showRecent: p.showRecent ?? true,
      methodReady: methodReady,
      methodNotReady: !methodReady,
      fileMenuOpen: this.state.openMenu === 'file',
      mtdpMenuOpen: this.state.openMenu === 'mtdp',
      helpMenuOpen: this.state.openMenu === 'help',
      anyMenuOpen: !!this.state.openMenu,
      aboutOpen: this.state.modal === 'about',
      licensingOpen: this.state.modal === 'licensing',
      shortcutsOpen: this.state.modal === 'shortcuts',
      toast: this.state.toast,
      toggleFile: () => this.toggle('file'),
      toggleMtdp: () => this.toggle('mtdp'),
      toggleHelp: () => this.toggle('help'),
      closeMenus: () => this.setState({ openMenu: null }),
      openAbout: () => this.setState({ modal: 'about', openMenu: null }),
      openLicensing: () => this.setState({ modal: 'licensing', openMenu: null }),
      openShortcuts: () => this.setState({ modal: 'shortcuts', openMenu: null }),
      closeAbout: () => this.setState({ modal: null }),
      minimizeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.minimizeWindow?.(); },
      toggleMaximizeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.toggleMaximizeWindow?.(); },
      closeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.closeWindow?.(); },
      exitApp: () => { this.setState({ openMenu: null }); (window.desktopApi?.quitApplication || window.desktopApi?.closeWindow)?.(); },
      launchDataset: () => this.launch('Dataset Packaging'),
      launchAnalysis: () => this.launch('Analysis'),
      launchMethod: () => this.launch('Method'),
    };
  }
}`,f=`
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{ box-sizing:border-box; }
  html,body{ margin:0; padding:0; }
  body{ font-family:'Inter','Segoe UI Variable','Segoe UI',system-ui,sans-serif; color:#1e242c; background:#eef0f2; }
  .mono{ font-family:'JetBrains Mono','Cascadia Code',Consolas,monospace; }
  input{ outline:none; }
  input:focus{ border-color:#3a72c4 !important; }
</style>
</helmet>

<div style="height:100vh; display:flex; flex-direction:column; background:#eef0f2; overflow:hidden;">

  <!-- ============ WINDOW TITLE BAR + MENU ============ -->
  <div style="display:flex; align-items:center; gap:12px; height:42px; padding:0 12px 0 14px; background:#f4f6f8; border-bottom:1px solid #e3e7eb; position:relative; z-index:60; flex:none;">
    <span style="width:13px; height:13px; border-radius:3px; background:#c42b1c; flex:none;"></span>
    <span style="font-size:12.5px; font-weight:700; color:#3a4250; flex:none; letter-spacing:-0.01em;">Method Editor</span>

    <!-- menu bar -->
    <div style="display:flex; align-items:center; gap:1px;">
      <sc-for list="{{ menus }}" as="mn" hint-placeholder-count="6">
      <div style="position:relative;">
        <span onClick="{{ mn.onClick }}" onMouseEnter="{{ mn.onHover }}" style="{{ mn.labelStyle }}" style-hover="background:#e9edf1;">{{ mn.label }}</span>
        <sc-if value="{{ mn.open }}" hint-placeholder-val="{{ false }}">
        <div style="position:absolute; top:calc(100% + 5px); left:0; min-width:238px; background:#fff; border:1px solid #e3e7eb; border-radius:9px; box-shadow:0 12px 32px rgba(40,35,25,0.16); padding:5px; z-index:70;">
          <sc-for list="{{ mn.items }}" as="it" hint-placeholder-count="4">
            <sc-if value="{{ it.isSep }}" hint-placeholder-val="{{ false }}">
              <div style="height:1px; background:#edf0f3; margin:5px 7px;"></div>
            </sc-if>
            <sc-if value="{{ it.isItem }}" hint-placeholder-val="{{ true }}">
              <div onClick="{{ it.onClick }}" style="{{ it.rowStyle }}" style-hover="background:#eef2f7;">
                <span>{{ it.label }}</span>
                <span class="mono" style="font-size:11px; color:{{ it.scColor }}; letter-spacing:0.02em; flex:none;">{{ it.shortcut }}</span>
              </div>
            </sc-if>
          </sc-for>
        </div>
        </sc-if>
      </div>
      </sc-for>
    </div>

    <div style="margin-left:auto; display:flex; align-items:center; gap:14px;">
      <span class="mono" style="font-size:11.5px; color:#8a93a0;">CAG-CF-Modied-ULV20.mtdp</span>
      <span onClick="{{ openShortcuts }}" title="Keyboard shortcuts" style="font-size:11px; color:#6e7a86; border:1px solid #d6dbe1; border-radius:5px; padding:2px 8px; cursor:pointer; flex:none;" style-hover="background:#e9edf1;"><span class="mono">Ctrl+/</span></span>
      <div data-window-controls="true" style="display:flex; align-items:center; gap:18px; color:#a09a8e; font-size:13px;"><span data-window-control="minimize" onClick="{{ minimizeWindow }}" style="cursor:pointer; padding:5px 3px;">—</span><span data-window-control="maximize" onClick="{{ toggleMaximizeWindow }}" style="font-size:11px; cursor:pointer; padding:5px 3px;">▢</span><span data-window-control="close" onClick="{{ closeWindow }}" style="cursor:pointer; padding:5px 3px;">✕</span></div>
    </div>
  </div>

  <!-- backdrop closes any open menu -->
  <sc-if value="{{ anyMenuOpen }}" hint-placeholder-val="{{ false }}">
  <div onClick="{{ closeMenus }}" style="position:fixed; inset:0; z-index:55;"></div>
  </sc-if>

  <!-- ============ PAGE ============ -->
  <div style="flex:1; display:flex; flex-direction:column; align-items:center; padding:12px 24px 0; min-height:0; overflow:hidden;">

    <!-- decor top -->
    <div style="width:940px; flex:none; display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
      <span style="font-size:11px; letter-spacing:0.13em; text-transform:uppercase; color:#a09a8e; font-weight:600;">Method Editor</span>
      <div style="display:flex; align-items:center; gap:7px; font-size:11.5px; color:#a09a8e;">
        <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:6px; height:6px; border-radius:50%; background:#5a7a3d;"></span>Package</span>
        <span style="color:#d6dbe1;">·</span>
        <span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:6px; height:6px; border-radius:50%; background:#5a7a3d;"></span>Method</span>
        <span style="color:#d6dbe1;">·</span>
        <span style="display:inline-flex; align-items:center; gap:5px; color:{{ accentInk }}; font-weight:600; background:{{ accentSoft }}; padding:2px 9px; border-radius:11px;"><span style="width:6px; height:6px; border-radius:50%; background:{{ accent }};"></span>Editing</span>
        <span style="color:#d6dbe1;">·</span>
        <span style="display:inline-flex; align-items:center; gap:5px; color:#a09a8e;"><span style="width:6px; height:6px; border-radius:50%; background:#c5ccd4;"></span>Generate</span>
      </div>
    </div>

    <!-- ============ SPOTLIGHT ============ -->
    <div style="width:940px; background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 8px 28px rgba(40,35,25,0.06); padding:0; overflow:visible; flex:1; min-height:0; display:flex; flex-direction:column;">

      <!-- ===== HEADER REGION (fixed) ===== -->
      <div style="padding:16px 28px 8px; flex:none;">

      <!-- METHOD MANAGER -->
      <div style="position:relative; display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <button onClick="{{ toggleMenu }}" onDoubleClick="{{ startRenameCurrent }}" title="Click to switch · double-click to rename" style="display:inline-flex; align-items:center; gap:8px; border:1px solid #c3cad2; background:#fff; color:#1e242c; font-family:inherit; font-size:13px; font-weight:600; padding:7px 12px; border-radius:6px; cursor:pointer;">
          <span style="width:7px; height:7px; border-radius:50%; background:{{ accent }};"></span>{{ methodLabel }} <span class="mono" style="font-size:11.5px; color:#5a6675; font-weight:400;">v{{ methodVersion }}</span> <span style="color:#a09a8e;">▾</span>
        </button>
        <button onClick="{{ createMethod }}" style="border:1px solid transparent; background:transparent; color:{{ accent }}; font-family:inherit; font-size:12.5px; font-weight:600; padding:7px 8px; border-radius:6px; cursor:pointer;">+ New method</button>
        <span style="font-size:11.5px; color:#a09a8e;">{{ methodCount }} in registry</span>

        <sc-if value="{{ menuOpen }}" hint-placeholder-val="{{ false }}">
        <div style="position:absolute; top:100%; left:0; margin-top:6px; min-width:340px; background:#fff; border:1px solid #e3e7eb; border-radius:8px; box-shadow:0 8px 24px rgba(40,35,25,0.13); padding:6px; z-index:50;">
          <div style="font-size:10px; letter-spacing:0.09em; text-transform:uppercase; color:#a09a8e; font-weight:600; padding:6px 10px 4px;">Methods</div>
          <sc-for list="{{ methodMenu }}" as="m" hint-placeholder-count="3">
          <div style="{{ m.rowStyle }}">
            <sc-if value="{{ m.editing }}" hint-placeholder-val="{{ false }}">
            <span style="display:flex; align-items:center; gap:9px; flex:1;">
              <span style="{{ m.dotStyle }}"></span>
              <input value="{{ nameDraft }}" onChange="{{ onNameInput }}" onKeyDown="{{ onNameKey }}" onBlur="{{ commitName }}" ref="{{ nameInputRef }}" style="{{ nameInputStyle }}"></input>
              <span style="font-size:9.5px; color:#a09a8e; flex:none; white-space:nowrap;">↵ save</span>
            </span>
            </sc-if>
            <sc-if value="{{ m.notEditing }}" hint-placeholder-val="{{ true }}">
            <span onClick="{{ m.onSelect }}" style="display:flex; align-items:center; gap:9px; flex:1; cursor:pointer;">
              <span style="{{ m.dotStyle }}"></span>
              <span style="font-size:12.5px; font-weight:600; color:#1e242c;">{{ m.label }}</span>
              <span class="mono" style="font-size:10.5px; color:#a09a8e;">v{{ m.version }}</span>
            </span>
            <span onClick="{{ m.onStartRename }}" title="Rename method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
            </span>
            <sc-if value="{{ m.canDel }}" hint-placeholder-val="{{ true }}">
            <span onClick="{{ m.onDelete }}" title="Delete method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a8412a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m1 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path></svg>
            </span>
            </sc-if>
            </sc-if>
          </div>
          </sc-for>
          <div style="font-size:10px; color:#a9b1bb; padding:5px 10px 2px;">Double-click a method, or use ✎, to rename.</div>
          <div onClick="{{ createMethod }}" style="display:flex; align-items:center; gap:8px; padding:9px 10px; margin-top:4px; border-top:1px solid #edf0f3; color:{{ accent }}; font-size:12.5px; font-weight:600; cursor:pointer;">+ New method</div>
        </div>
        </sc-if>
      </div>

      <!-- headline -->
      <div style="font-size:17px; font-weight:600; letter-spacing:-0.01em;">Tune an analysis setting, then generate a new version</div>
      <div style="font-size:11.5px; color:#5a6675; margin-bottom:12px; margin-top:3px;">7 runs on this package · editing from <span class="mono" style="font-size:12px;">v{{ methodVersion }}</span> → draft <span class="mono" style="font-size:12px;">v0.1.1</span> · <span style="color:{{ accentInk }}; font-weight:600;">{{ changeCount }} change(s) staged</span></div>

      <!-- ===== PIPELINE (collapsible · expands on hover/focus) ===== -->
      <div onMouseEnter="{{ pipeOn }}" onMouseLeave="{{ pipeOff }}" onFocus="{{ pipeOn }}" tabindex="0" style="position:relative; outline:none;">

        <!-- compact resting strip -->
        <div style="display:flex; align-items:center; gap:9px; padding:8px 13px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc;">
          <span style="font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:700; flex:none;">Pipeline</span>
          <span style="font-size:12px; color:#6e7a86;">Data entry</span>
          <span style="color:#c5ccd4;">›</span>
          <span onClick="{{ editTestRange }}" style="{{ trChip }}"><span style="{{ trStatusDot }}"></span>Test range</span>
          <span style="color:#c5ccd4;">›</span>
          <span style="font-size:12px; color:#6e7a86;">Stress–strain</span>
          <span style="color:#c5ccd4;">→</span>
          <span style="font-size:12px; color:#6e7a86;">Strength</span>
          <span onClick="{{ editModulus }}" style="{{ modChip }}"><span style="{{ modStatusDot }}"></span>Modulus</span>
          <span onClick="{{ editBending }}" style="{{ bnChip }}"><span style="{{ bnStatusDot }}"></span>Bending</span>
          <span style="margin-left:auto; display:inline-flex; align-items:center; gap:9px; font-size:10.5px; color:#a9b1bb;"><span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:7px; height:7px; border-radius:50%; background:{{ accent }};"></span>edited</span><span style="display:inline-flex; align-items:center; gap:5px;"><span style="width:7px; height:7px; border-radius:50%; background:#c5ccd4;"></span>unchanged</span><span style="color:#d6dbe1;">·</span>hover for full map</span>
        </div>

        <!-- expanded overlay diagram -->
        <sc-if value="{{ pipeExpanded }}" hint-placeholder-val="{{ false }}">
        <div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); z-index:40; background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 16px 44px rgba(40,35,25,0.17); padding:16px 22px 20px;">
          <div style="font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:600; margin-bottom:12px;">Analysis pipeline — how the data is processed, in order · click an editable box</div>
          <div style="width:884px;">
        <div style="display:flex; align-items:stretch;">
          <div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 13px;">
            <div style="font-size:12.5px; font-weight:600;">Data entry point</div>
            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">load · strain · geometry → area · mean strain</div>
          </div>
          <div style="flex:0 0 28px; display:flex; align-items:center; justify-content:center;">
            <svg width="28" height="14" viewBox="0 0 28 14"><line x1="0" y1="7" x2="20" y2="7" stroke="{{ accent }}" stroke-width="2"></line><path d="M19,2 L27,7 L19,12 Z" fill="{{ accent }}"></path></svg>
          </div>
          <div onClick="{{ editTestRange }}" style="{{ trBoxStyle }}">
            <div style="display:flex; align-items:center; justify-content:space-between;">
              <div style="font-size:13px; font-weight:600;">Test range</div>
              <span style="display:flex; gap:5px;">
                <sc-if value="{{ trDeactShow }}" hint-placeholder-val="{{ false }}"><span style="font-size:8.5px; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; color:#6b7480; background:#dfe3e8; padding:2px 6px; border-radius:9px;">Off · bypassed</span></sc-if>
                <sc-if value="{{ trEditShow }}" hint-placeholder-val="{{ true }}"><span style="font-size:8.5px; font-weight:600; letter-spacing:0.07em; text-transform:uppercase; color:#fff; background:{{ accent }}; padding:2px 6px; border-radius:9px;">Editing</span></sc-if>
                <sc-if value="{{ trErrShow }}" hint-placeholder-val="{{ false }}"><span style="font-size:8.5px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#fff; background:#a8412a; padding:2px 6px; border-radius:9px;">! check</span></sc-if>
              </span>
            </div>
            <div style="font-size:11px; color:#5a6675; margin-top:2px;">{{ trSubText }}</div>
          </div>
          <div style="flex:0 0 28px; display:flex; align-items:center; justify-content:center;">
            <svg width="28" height="14" viewBox="0 0 28 14"><line x1="0" y1="7" x2="20" y2="7" stroke="{{ accent }}" stroke-width="2"></line><path d="M19,2 L27,7 L19,12 Z" fill="{{ accent }}"></path></svg>
          </div>
          <div style="flex:0 0 276px; border:1.5px solid #c3cad2; border-radius:8px; background:#fff; padding:8px 13px;">
            <div style="font-size:12.5px; font-weight:600;">Stress–strain</div>
            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">bounded curve</div>
          </div>
        </div>

        <div style="position:relative; height:46px;">
          <svg viewBox="0 0 884 46" width="884" height="46" style="position:absolute; inset:0;">
            <defs>
              <marker id="hd_a" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="{{ accent }}"></path></marker>
              <marker id="hd_g" markerWidth="8" markerHeight="8" refX="5.5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#bfc6ce"></path></marker>
            </defs>
            <path d="M746,2 C746,26 138,18 138,44" fill="none" stroke="{{ strengthLeg }}" stroke-width="2" marker-end="url(#{{ strengthMk }})"></path>
            <path d="M746,2 C746,28 442,28 442,44" fill="none" stroke="{{ modulusLeg }}" stroke-width="3" marker-end="url(#{{ modulusMk }})"></path>
            <path d="M746,2 L746,44" fill="none" stroke="{{ bendingLeg }}" stroke-width="2" marker-end="url(#{{ bendingMk }})"></path>
            <circle cx="746" cy="3" r="3.5" fill="{{ accent }}"></circle>
          </svg>
        </div>

        <div style="display:flex; align-items:stretch;">
          <div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 14px;">
            <div style="font-size:12.5px; font-weight:600; color:#5a6675;">Strength</div>
            <div style="font-size:10.5px; color:#a09a8e; margin-top:2px;">max load → strength → failure strain</div>
          </div>
          <div style="flex:0 0 28px;"></div>
          <div onClick="{{ editModulus }}" style="{{ modCardStyle }}">
            <div style="display:flex; align-items:center; justify-content:space-between;">
              <span style="font-size:13px; font-weight:700; color:#1e242c;">Modulus</span>
              <span style="display:flex; gap:5px;">
                <sc-if value="{{ modEditShow }}" hint-placeholder-val="{{ true }}"><span style="font-size:9.5px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#fff; background:{{ accent }}; padding:2px 7px; border-radius:10px;">Editing</span></sc-if>
                <sc-if value="{{ modErrShow }}" hint-placeholder-val="{{ false }}"><span style="font-size:9.5px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#fff; background:#a8412a; padding:2px 7px; border-radius:10px;">! check</span></sc-if>
              </span>
            </div>
            <div style="font-size:11px; color:{{ modSubColor }}; margin-top:3px;">chord slope · 0.0005–0.0025 strain</div>
          </div>
          <div style="flex:0 0 28px;"></div>
          <div onClick="{{ editBending }}" style="{{ bnCardStyle }}">
            <div style="display:flex; align-items:center; justify-content:space-between;">
              <span style="font-size:13px; font-weight:700; color:#1e242c;">Bending</span>
              <sc-if value="{{ bnEditShow }}" hint-placeholder-val="{{ false }}"><span style="font-size:9.5px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#fff; background:{{ accent }}; padding:2px 7px; border-radius:10px;">Editing</span></sc-if>
            </div>
            <div style="font-size:11px; color:{{ bnSubColor }}; margin-top:3px;">{{ bnSubText }}</div>
          </div>
        </div>
          </div>
        </div>
        </sc-if>
      </div>

      </div>
      <!-- ===== /HEADER REGION ===== -->

      <!-- ===== EDIT PANEL (scrolls internally) ===== -->
      <div style="flex:1; min-height:0; overflow-y:auto; padding:10px 28px 12px;">

      <!-- ===== MODULUS EDIT CARD ===== -->
      <sc-if value="{{ mo }}" hint-placeholder-val="{{ true }}">
      <div style="margin:2px 0 8px; border:1px solid #e3e7eb; border-radius:8px; background:#fff; overflow:hidden;">
        <div style="display:flex; align-items:center; gap:11px; padding:14px 18px; border-bottom:1px solid #edf0f3;">
          <span style="font-size:9.5px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:{{ accentInk }}; background:{{ accentSoft }}; padding:3px 8px; border-radius:5px;">Branch · 1 result</span>
          <span style="font-size:15px; font-weight:600;">Compressive modulus</span>
          <span style="font-size:12px; color:#a09a8e;">stiffness from the slope of the bounded stress–strain curve</span>
        </div>
        <div style="padding:18px;">
          <div style="display:flex; gap:22px; align-items:stretch;">

            <!-- concept diagram -->
            <div style="flex:0 0 286px; border:1px solid #edf0f3; border-radius:8px; background:#fbfcfd; padding:13px 15px;">
              <div style="font-size:10px; letter-spacing:0.09em; text-transform:uppercase; color:#a09a8e; font-weight:700; margin-bottom:8px;">What this setting does</div>
              <svg viewBox="0 0 256 158" width="100%" style="display:block;">
                <line x1="30" y1="134" x2="246" y2="134" stroke="#e3e7eb" stroke-width="1.5"></line>
                <line x1="30" y1="134" x2="30" y2="16" stroke="#e3e7eb" stroke-width="1.5"></line>
                <text x="240" y="150" text-anchor="end" font-size="9" fill="#a09a8e" font-family="Inter,sans-serif">strain</text>
                <text x="34" y="22" font-size="9" fill="#a09a8e" font-family="Inter,sans-serif">stress</text>
                <path d="{{ moCurve }}" fill="none" stroke="#bfc6ce" stroke-width="2.5"></path>
                <line x1="{{ mo_x1 }}" y1="134" x2="{{ mo_x1 }}" y2="{{ mo_y1 }}" stroke="#a09a8e" stroke-width="1" stroke-dasharray="3 3"></line>
                <line x1="{{ mo_x2 }}" y1="134" x2="{{ mo_x2 }}" y2="{{ mo_y2 }}" stroke="#a09a8e" stroke-width="1" stroke-dasharray="3 3"></line>
                <line x1="{{ mo_x1 }}" y1="{{ mo_y1 }}" x2="{{ mo_x2 }}" y2="{{ mo_y2 }}" stroke="{{ accent }}" stroke-width="3"></line>
                <circle cx="{{ mo_x1 }}" cy="{{ mo_y1 }}" r="4.5" fill="{{ accent }}"></circle>
                <circle cx="{{ mo_x2 }}" cy="{{ mo_y2 }}" r="4.5" fill="{{ accent }}"></circle>
                <text x="{{ mo_startLabelX }}" y="149" text-anchor="middle" font-size="9.5" fill="{{ accentInk }}" font-weight="600" font-family="Inter,sans-serif">ε start</text>
                <text x="{{ mo_endLabelX }}" y="149" text-anchor="middle" font-size="9.5" fill="{{ accentInk }}" font-weight="600" font-family="Inter,sans-serif">ε end</text>
                <sc-if value="{{ moSlopeShow }}" hint-placeholder-val="{{ true }}"><text x="{{ mo_x2 }}" y="{{ mo_y2 }}" dx="8" dy="-3" font-size="9.5" fill="{{ accentInk }}" font-weight="700" font-family="Inter,sans-serif">slope = E</text></sc-if>
              </svg>
              <div style="font-size:10px; color:{{ accentInk }}; margin-top:3px; display:flex; align-items:center; gap:6px;"><span style="width:14px; height:2.5px; background:{{ accent }}; border-radius:2px; flex:none;"></span>live — the chord follows the values you type below</div>
              <div style="font-size:11px; color:#5a6675; line-height:1.5; margin-top:6px;">Modulus is the <b style="color:#1e242c;">slope of the straight chord</b> between the two strains you set. Place them on the linear part of the curve.</div>
            </div>

            <!-- controls -->
            <div style="flex:1; display:flex; flex-direction:column;">
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
                <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">1</span>
                <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Chord strain bounds</span>
                <span style="font-size:11.5px; color:#a09a8e;">the window the straight-line fit is taken over</span>
              </div>
              <div style="display:flex; gap:16px;">
                <div style="flex:1; display:flex; flex-direction:column; gap:7px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">Start strain for fit</span><span title="Lower strain bound of the chord. Decimal strain between 0 and 0.05, below the end strain. Typical: 0.0005." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span>
                    <span class="mono" style="font-size:10.5px; color:#a09a8e;">strain · 0 – 0.05</span>
                  </div>
                  <input value="{{ fStart.value }}" onChange="{{ fStart.onInput }}" style="{{ fStart.style }}"></input>
                  <span style="font-size:11.5px; color:{{ fStart.msgColor }}; display:block; text-align:right;">{{ fStart.msg }}</span>
                </div>
                <div style="flex:1; display:flex; flex-direction:column; gap:7px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:700;">End strain for fit</span><span title="Upper strain bound of the chord. Decimal strain between 0 and 0.05, above the start strain. Was 0.0025 in v0.1.0." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span>
                    <span class="mono" style="font-size:10.5px; color:#a09a8e;">strain · 0 – 0.05</span>
                  </div>
                  <input value="{{ fEnd.value }}" onChange="{{ fEnd.onInput }}" style="{{ fEnd.style }}"></input>
                  <span style="font-size:11.5px; color:{{ fEnd.msgColor }}; display:block; text-align:right;">{{ fEnd.msg }}</span>
                </div>
              </div>
              <div style="margin-top:14px; font-size:12px; color:#5a6675; background:#f4f7f9; border:1px solid #edf0f3; border-radius:6px; padding:10px 12px; line-height:1.5;"><b style="color:#1e242c;">In words:</b> fit a straight line from <span class="mono" style="font-size:11px; color:{{ accentInk }};">ε {{ moStartEcho }}</span> to <span class="mono" style="font-size:11px; color:{{ accentInk }};">ε {{ moEndEcho }}</span> on the bounded curve and report its slope.</div>
            </div>
          </div>
          <div style="margin-top:16px; padding-top:14px; border-top:1px solid #edf0f3; font-size:12px; color:#5a6675;"><b style="color:#1e242c;">Affects →</b> reported <span class="mono" style="font-size:11px;">compressive_modulus_MPa</span> &amp; the modulus guide line in the audit evidence view.</div>
        </div>
      </div>
      </sc-if>

      <!-- ===== TEST RANGE EDIT CARD ===== -->
      <sc-if value="{{ tr }}" hint-placeholder-val="{{ false }}">
      <div style="margin:2px 0 8px; border:1px solid #e3e7eb; border-radius:8px; background:#fff; overflow:hidden;">
        <div style="display:flex; align-items:center; gap:11px; padding:14px 18px; border-bottom:1px solid #edf0f3;">
          <span style="font-size:9.5px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:{{ accentInk }}; background:{{ accentSoft }}; padding:3px 8px; border-radius:5px;">Trunk · all 3 results</span>
          <span style="font-size:15px; font-weight:600;">Test range — the valid analysis interval</span>
          <span style="font-size:12px; color:#a09a8e;">where the analysed curve begins and ends · every result is computed inside it</span>
        </div>

        <div style="padding:18px;">

          <!-- HERO BOUNDARY DIAGRAM -->
          <div style="border:1px solid #edf0f3; border-radius:8px; background:#fbfcfd; padding:13px 16px 9px; margin-bottom:22px;">
            <div style="font-size:10px; letter-spacing:0.09em; text-transform:uppercase; color:#a09a8e; font-weight:700; margin-bottom:6px;">The three steps below carve this interval out of the raw curve</div>
            <svg viewBox="0 0 848 150" width="100%" style="display:block;">
              <rect x="40" y="14" width="80" height="104" fill="#e8ecf0"></rect>
              <rect x="120" y="14" width="{{ tr_intW }}" height="104" rx="2" fill="{{ accentSoft }}"></rect>
              <rect x="{{ tr_endX }}" y="14" width="{{ tr_tailW }}" height="104" fill="#e8ecf0"></rect>
              <line x1="40" y1="118" x2="808" y2="118" stroke="#d6dbe1" stroke-width="1.5"></line>
              <path d="M40,114 L120,110 C260,102 410,50 620,30 C690,42 752,82 808,104" fill="none" stroke="#6e7a86" stroke-width="2.5"></path>
              <line x1="120" y1="14" x2="120" y2="118" stroke="{{ accent }}" stroke-width="1.5" stroke-dasharray="4 3"></line>
              <line x1="{{ tr_endX }}" y1="14" x2="{{ tr_endX }}" y2="118" stroke="{{ accent }}" stroke-width="1.5" stroke-dasharray="4 3"></line>
              <circle cx="120" cy="110" r="5.5" fill="{{ accent }}"></circle>
              <circle cx="{{ tr_endX }}" cy="30" r="5.5" fill="{{ accent }}"></circle>
              <text x="80" y="31" text-anchor="middle" font-size="9.5" fill="#a09a8e" font-family="Inter,sans-serif">pre-load</text>
              <text x="370" y="31" text-anchor="middle" font-size="10.5" fill="{{ accentInk }}" font-weight="700" font-family="Inter,sans-serif">analysis interval</text>
              <text x="714" y="31" text-anchor="middle" font-size="9.5" fill="#a09a8e" font-family="Inter,sans-serif">post-peak tail</text>
              <text x="120" y="136" text-anchor="middle" font-size="10.5" fill="{{ accentInk }}" font-weight="600" font-family="Inter,sans-serif">start · first point</text>
              <text x="{{ tr_endX }}" y="136" text-anchor="middle" font-size="10.5" fill="{{ accentInk }}" font-weight="600" font-family="Inter,sans-serif">end</text>
            </svg>
            <div style="font-size:11px; color:{{ accentInk }}; margin-top:2px; display:flex; align-items:center; gap:6px;"><span style="width:14px; height:2.5px; background:{{ accent }}; border-radius:2px; flex:none;"></span>live — the end boundary moves as you tune the decline drop and truncation below.</div>
          </div>

          <!-- STEP 1 · CLEAN THE SIGNAL -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">1</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Clean the signal</span>
            <span title="Classifies a conservative coherent window before end detection and routes blunt invalid scans for review — raw rows are always kept for audit. Turn the gate off to analyse the full raw series." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span>
            <span style="font-size:11.5px; color:#a09a8e;">drop blunt, incoherent rows before the boundaries are found</span>
            <span style="margin-left:auto; display:inline-flex; align-items:center; gap:8px;"><span class="mono" style="font-size:10px; color:#a09a8e;">resolve.gate_experiment_signal</span><span style="font-size:11px; font-weight:600; color:{{ gateLabelColor }};">{{ gateLabel }}</span><div onClick="{{ toggleGate }}" style="{{ gateTrack }}"><span style="{{ gateKnob }}"></span></div></span>
          </div>

          <div style="{{ gateBodyStyle }}; padding-left:32px;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
              <span style="display:inline-flex; align-items:center; gap:6px; border:1px solid #e3e7eb; background:#eff1f4; color:#5a6675; border-radius:5px; padding:5px 10px; font-size:11px; font-weight:600;">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2"><rect x="5" y="11" width="14" height="9" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path></svg>
                Coherent window · always on
              </span>
              <span style="font-size:11px; color:#a09a8e;">the basis every downstream check needs — it cannot be disabled</span>
            </div>

            <div style="margin-bottom:18px;">
              <div style="display:inline-flex; align-items:center; gap:7px; margin-bottom:4px;"><span style="font-size:12.5px; font-weight:600;">Exclude blunt tail evidence</span><span title="Each rule is independent. Excluded rows are dropped from the analysis window but always retained in the raw record for audit." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></div>
              <div style="font-size:11.5px; color:#5a6675; margin-bottom:6px; max-width:620px; line-height:1.5;">Each rule drops one class of incoherent rows. Toggle a rule on or off, and edit the highlighted threshold that defines it. Excluded rows stay in the raw record for audit.</div>

              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exLowload.toggle }}" style="{{ exLowload.track }}"><span style="{{ exLowload.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,32 C12,16 18,12 24,13 C29,14 32,30 38,35" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="38" y1="36" x2="84" y2="36" stroke="{{ accent }}" stroke-width="1.3" stroke-dasharray="3 2"></line>
                  <circle cx="46" cy="36" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="56" cy="36" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="66" cy="36" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="76" cy="36" r="2.1" fill="{{ accent }}"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Persistent low-load tails</span>
                <span style="{{ exLowload.txtStyle }}">load stays below <input value="{{ exLowload.lowloadFracV }}" onChange="{{ exLowload.lowloadFracOn }}" style="{{ exLowload.pStyle }}"></input>% of peak for <input value="{{ exLowload.lowloadPtsV }}" onChange="{{ exLowload.lowloadPtsOn }}" style="{{ exLowload.pStyle }}"></input>+ points</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exJumps.toggle }}" style="{{ exJumps.track }}"><span style="{{ exJumps.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <circle cx="18" cy="34" r="2.1" fill="#6e7a86"></circle>
                  <circle cx="30" cy="33" r="2.1" fill="#6e7a86"></circle>
                  <line x1="44" y1="33" x2="44" y2="11" stroke="{{ accent }}" stroke-width="1.6"></line>
                  <path d="M41.5,14 L44,10.5 L46.5,14" fill="none" stroke="{{ accent }}" stroke-width="1.2"></path>
                  <circle cx="44" cy="10" r="2.8" fill="{{ accent }}"></circle>
                  <circle cx="58" cy="33" r="2.1" fill="#6e7a86"></circle>
                  <circle cx="70" cy="34" r="2.1" fill="#6e7a86"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Implausible jumps</span>
                <span style="{{ exJumps.txtStyle }}">one step jumps more than <input value="{{ exJumps.jumpsMultV }}" onChange="{{ exJumps.jumpsMultOn }}" style="{{ exJumps.pStyle }}"></input>× the peak load</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exPlateau.toggle }}" style="{{ exPlateau.track }}"><span style="{{ exPlateau.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,34 C12,30 16,24 22,24" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="22" y1="24" x2="70" y2="24" stroke="{{ accent }}" stroke-width="1.5"></line>
                  <circle cx="22" cy="24" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="34" cy="24" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="46" cy="24" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="58" cy="24" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="70" cy="24" r="2.1" fill="{{ accent }}"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Artificial plateaus</span>
                <span style="{{ exPlateau.txtStyle }}"><input value="{{ exPlateau.plateauPtsV }}" onChange="{{ exPlateau.plateauPtsOn }}" style="{{ exPlateau.pStyle }}"></input>+ identical readings repeat in a row</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exReset.toggle }}" style="{{ exReset.track }}"><span style="{{ exReset.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <circle cx="16" cy="32" r="2.1" fill="#6e7a86"></circle>
                  <circle cx="28" cy="26" r="2.1" fill="#6e7a86"></circle>
                  <circle cx="40" cy="20" r="2.1" fill="#6e7a86"></circle>
                  <path d="M40,14 C30,10 22,11 16,14" fill="none" stroke="{{ accent }}" stroke-width="1.4" stroke-dasharray="3 2"></path>
                  <path d="M18.5,11 L15,14 L18.5,17" fill="none" stroke="{{ accent }}" stroke-width="1.2"></path>
                  <circle cx="52" cy="26" r="2.1" fill="#6e7a86"></circle>
                  <circle cx="64" cy="20" r="2.1" fill="#6e7a86"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Domain resets</span>
                <span style="{{ exReset.txtStyle }}">the time / strain axis steps backward, or jumps <input value="{{ exReset.resetMultV }}" onChange="{{ exReset.resetMultOn }}" style="{{ exReset.pStyle }}"></input>× its normal step</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exNonnum.toggle }}" style="{{ exNonnum.track }}"><span style="{{ exNonnum.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <circle cx="16" cy="30" r="2.1" fill="#6e7a86"></circle>
                  <rect x="34" y="16" width="13" height="13" rx="1.5" fill="#fdf2ee" stroke="#c0392b" stroke-width="1"></rect>
                  <rect x="49" y="16" width="13" height="13" rx="1.5" fill="#fdf2ee" stroke="#c0392b" stroke-width="1"></rect>
                  <line x1="37" y1="19" x2="44" y2="26" stroke="#c0392b" stroke-width="1"></line>
                  <line x1="44" y1="19" x2="37" y2="26" stroke="#c0392b" stroke-width="1"></line>
                  <line x1="52" y1="19" x2="59" y2="26" stroke="#c0392b" stroke-width="1"></line>
                  <line x1="59" y1="19" x2="52" y2="26" stroke="#c0392b" stroke-width="1"></line>
                  <circle cx="74" cy="30" r="2.1" fill="#6e7a86"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Non-numeric clusters</span>
                <span style="{{ exNonnum.txtStyle }}"><input value="{{ exNonnum.nonnumPtsV }}" onChange="{{ exNonnum.nonnumPtsOn }}" style="{{ exNonnum.pStyle }}"></input>+ non-numeric cells sit next to each other</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exFragments.toggle }}" style="{{ exFragments.track }}"><span style="{{ exFragments.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,36 C20,35 36,34 52,34 C64,34 74,35 86,35" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="6" y1="16" x2="86" y2="16" stroke="#c5ccd4" stroke-width="1" stroke-dasharray="3 2"></line>
                  <circle cx="34" cy="14" r="2.4" fill="{{ accent }}"></circle>
                  <circle cx="50" cy="12" r="2.4" fill="{{ accent }}"></circle>
                  <circle cx="64" cy="15" r="2.4" fill="{{ accent }}"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Disconnected high-load fragments</span>
                <span style="{{ exFragments.txtStyle }}"><input value="{{ exFragments.fragPtsV }}" onChange="{{ exFragments.fragPtsOn }}" style="{{ exFragments.pStyle }}"></input>+ isolated points appear above <input value="{{ exFragments.fragFracV }}" onChange="{{ exFragments.fragFracOn }}" style="{{ exFragments.pStyle }}"></input>% of peak</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ exRestart.toggle }}" style="{{ exRestart.track }}"><span style="{{ exRestart.knob }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <circle cx="14" cy="36" r="1.8" fill="#c5ccd4"></circle>
                  <circle cx="24" cy="36" r="1.8" fill="#c5ccd4"></circle>
                  <circle cx="34" cy="36" r="1.8" fill="#c5ccd4"></circle>
                  <circle cx="44" cy="36" r="1.8" fill="#c5ccd4"></circle>
                  <path d="M52,36 L62,11" fill="none" stroke="{{ accent }}" stroke-width="1.8"></path>
                  <path d="M62,11 L72,34" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <circle cx="62" cy="10" r="2.6" fill="{{ accent }}"></circle>
                </svg>
                <span style="flex:0 0 172px; font-size:12.5px; font-weight:600;">Late restart / spikes</span>
                <span style="{{ exRestart.txtStyle }}">load jumps over <input value="{{ exRestart.restartFracV }}" onChange="{{ exRestart.restartFracOn }}" style="{{ exRestart.pStyle }}"></input>% of peak after <input value="{{ exRestart.restartPtsV }}" onChange="{{ exRestart.restartPtsOn }}" style="{{ exRestart.pStyle }}"></input> quiet points</span>
              </div>
            </div>

            <div>
              <div style="display:inline-flex; align-items:center; gap:7px; margin-bottom:3px;"><span style="font-size:12.5px; font-weight:600;">Borderline discontinuities</span><span title="A short, ambiguous dip or step in the signal — too small to confidently mark the end of the test. You decide whether it shortens the window or is merely flagged." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></div>
              <div style="font-size:11.5px; color:#5a6675; margin-bottom:11px; max-width:640px; line-height:1.75;">A dip is treated as <b style="color:#1e242c;">borderline</b> when it drops less than <input value="{{ bl.magV }}" onChange="{{ bl.magOn }}" style="{{ bl.pStyle }}"></input>% of peak <i>and</i> lasts fewer than <input value="{{ bl.ptsV }}" onChange="{{ bl.ptsOn }}" style="{{ bl.pStyle }}"></input> points. Anything larger is taken as a real end. For dips inside that band:</div>
              <div style="display:flex; gap:12px; max-width:600px;">
                <div onClick="{{ setReview }}" style="{{ blReviewCard }}">
                  <svg viewBox="0 0 200 56" width="100%" style="display:block; margin-bottom:7px;">
                    <line x1="6" y1="44" x2="194" y2="44" stroke="#e3e7eb" stroke-width="1"></line>
                    <path d="M10,38 C44,20 74,18 92,22 L100,32 L108,20 C140,14 168,11 190,9" fill="none" stroke="#6e7a86" stroke-width="2"></path>
                    <circle cx="100" cy="27" r="9" fill="none" stroke="#d98a1f" stroke-width="1.5"></circle>
                    <line x1="10" y1="51" x2="190" y2="51" stroke="{{ accent }}" stroke-width="2.5"></line>
                  </svg>
                  <div style="font-size:12px; font-weight:600;">Keep &amp; flag for review</div>
                  <div style="font-size:11px; color:#5a6675; margin-top:1px;">window unchanged · dip noted in the audit log</div>
                </div>
                <div onClick="{{ setExclude }}" style="{{ blExcludeCard }}">
                  <svg viewBox="0 0 200 56" width="100%" style="display:block; margin-bottom:7px;">
                    <line x1="6" y1="44" x2="194" y2="44" stroke="#e3e7eb" stroke-width="1"></line>
                    <path d="M10,38 C44,20 74,18 92,22 L100,32" fill="none" stroke="#6e7a86" stroke-width="2"></path>
                    <path d="M100,32 L108,20 C140,14 168,11 190,9" fill="none" stroke="#d6dbe1" stroke-width="2" stroke-dasharray="3 3"></path>
                    <circle cx="100" cy="27" r="9" fill="none" stroke="#c0392b" stroke-width="1.5"></circle>
                    <line x1="10" y1="51" x2="100" y2="51" stroke="{{ accent }}" stroke-width="2.5"></line>
                    <line x1="100" y1="51" x2="190" y2="51" stroke="#c5ccd4" stroke-width="2" stroke-dasharray="3 3"></line>
                  </svg>
                  <div style="font-size:12px; font-weight:600;">Cut the window here</div>
                  <div style="font-size:11px; color:#5a6675; margin-top:1px;">interval ends at the dip · later points dropped</div>
                </div>
              </div>
            </div>
          </div>

          <div style="height:1px; background:#edf0f3; margin:22px 0;"></div>

          <!-- STEP 2 · WHERE THE INTERVAL STARTS -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">2</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Where the interval starts</span>
            <span style="font-size:11.5px; color:#a09a8e;">the first acquired point opens the analysis</span>
            <span style="margin-left:auto; font-size:8.5px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#6b7480; background:#dfe3e8; padding:2px 7px; border-radius:9px;">Standard policy</span>
          </div>
          <div style="padding-left:32px;">
            <div style="display:flex; gap:14px; align-items:center; margin-bottom:12px;">
              <div style="flex:none; border:1px solid #edf0f3; border-radius:7px; background:#fbfcfd; padding:5px 7px;">
                <svg viewBox="0 0 96 50" width="104" style="display:block;">
                  <line x1="6" y1="44" x2="90" y2="44" stroke="#e3e7eb" stroke-width="1"></line>
                  <circle cx="12" cy="42" r="1.8" fill="#c5ccd4"></circle>
                  <circle cx="19" cy="41" r="1.8" fill="#c5ccd4"></circle>
                  <path d="M26,38 C40,32 60,16 88,8" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="26" y1="10" x2="26" y2="44" stroke="{{ accent }}" stroke-width="1" stroke-dasharray="3 2"></line>
                  <circle cx="26" cy="38" r="3" fill="{{ accent }}"></circle>
                  <text x="26" y="9" text-anchor="middle" font-size="6.5" fill="{{ accentInk }}" font-weight="700" font-family="Inter,sans-serif">start</text>
                </svg>
              </div>
              <div style="display:flex; flex-direction:column; gap:2px;">
                <span style="font-size:12.5px; color:#1e242c;"><b style="color:#1e242c;">Rule:</b> the first acquired point opens the interval.</span>
                <span class="mono" style="font-size:10px; color:#a09a8e;">resolve.experiment_boundaries · start_policy = first_point</span>
                <span style="font-size:11px; color:#a09a8e;">Alternative start policies are not enabled for this method.</span>
              </div>
            </div>
            <div style="font-size:12px; color:#5a6675; background:#f4f7f9; border:1px solid #edf0f3; border-radius:6px; padding:10px 12px; line-height:1.5; max-width:640px;"><b style="color:#1e242c;">In words:</b> the very first acquired point — raw index 0 of the coherent window — begins the interval. Machine pre-load points (settling, slack take-up) sit before it and are preserved as raw evidence only.</div>
          </div>

          <div style="height:1px; background:#edf0f3; margin:22px 0;"></div>

          <!-- STEP 3 · WHERE THE INTERVAL ENDS -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">3</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Where the interval ends</span>
            <span title="The end is not chosen from a list — it is detected by the truncation logic. Turn truncation off and no end is cut: the interval runs to the last point." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span>
            <span style="font-size:11.5px; color:#a09a8e;">detected where load declines and does not recover</span>
            <span style="margin-left:auto; display:inline-flex; align-items:center; gap:8px;"><span class="mono" style="font-size:10px; color:#a09a8e;">resolve.experiment_boundaries</span><span style="font-size:11px; font-weight:600; color:{{ truncLabelColor }};">{{ truncLabel }}</span><div onClick="{{ toggleTrunc }}" style="{{ truncTrack }}"><span style="{{ truncKnob }}"></span></div></span>
          </div>

          <div style="padding-left:32px;">
            <div style="display:flex; align-items:flex-start; gap:9px; margin-bottom:14px; padding:10px 12px; background:#f4f7f9; border:1px solid #edf0f3; border-radius:6px;">
              <span style="font-size:8.5px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:{{ accentInk }}; background:{{ accentSoft }}; padding:3px 7px; border-radius:5px; flex:none; margin-top:1px;">Rule</span>
              <div style="display:flex; flex-direction:column; gap:1px;">
                <span style="font-size:12.5px; color:#1e242c;">{{ endRule }}</span>
                <span class="mono" style="font-size:10px; color:#a09a8e;">{{ endRuleCode }}</span>
              </div>
            </div>

            <div style="{{ truncBodyStyle }}">
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                <span style="display:inline-flex; align-items:center; gap:6px; border:1px solid #e3e7eb; background:#eff1f4; color:#5a6675; border-radius:5px; padding:5px 10px; font-size:11px; font-weight:600;">
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2"><rect x="5" y="11" width="14" height="9" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path></svg>
                  Peak candidate detection · required
                </span>
                <span style="font-size:11px; color:#a09a8e;">each refinement below tunes how the end is found — none of them can break detection</span>
              </div>

              <!-- drop -->
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ tDrop.onToggle }}" style="{{ tDrop.trackStyle }}"><span style="{{ tDrop.knobStyle }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,30 C16,12 24,10 32,10 C44,10 50,26 60,32 C68,36 78,38 86,39" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="28" y1="11" x2="86" y2="11" stroke="#c5ccd4" stroke-width="1" stroke-dasharray="3 2"></line>
                  <line x1="44" y1="24" x2="86" y2="24" stroke="{{ accent }}" stroke-width="1" stroke-dasharray="3 2"></line>
                  <line x1="78" y1="12" x2="78" y2="23" stroke="{{ accent }}" stroke-width="1.4"></line>
                  <path d="M75.5,14.5 L78,11.5 L80.5,14.5" fill="none" stroke="{{ accent }}" stroke-width="1.1"></path>
                  <path d="M75.5,20.5 L78,23.5 L80.5,20.5" fill="none" stroke="{{ accent }}" stroke-width="1.1"></path>
                  <circle cx="32" cy="10" r="2.6" fill="#6e7a86"></circle>
                </svg>
                <span style="flex:0 0 180px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ tDrop.label }}</span><span title="{{ tDrop.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ tDrop.mono }}</span></span>
                <input type="range" min="{{ tDrop.min }}" max="{{ tDrop.max }}" step="{{ tDrop.step }}" value="{{ tDrop.value }}" onChange="{{ tDrop.onInput }}" style="{{ tDrop.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:{{ tDrop.readColor }};">{{ tDrop.readout }}</span>
                <span style="flex:0 0 116px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ tDrop.caption }}</span>
              </div>

              <!-- persistence -->
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ tPersist.onToggle }}" style="{{ tPersist.trackStyle }}"><span style="{{ tPersist.knobStyle }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,14 C14,16 22,28 30,30" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="30" y1="30" x2="84" y2="30" stroke="{{ accent }}" stroke-width="1.4"></line>
                  <circle cx="36" cy="30" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="46" cy="30" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="56" cy="30" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="66" cy="30" r="2.1" fill="{{ accent }}"></circle>
                  <circle cx="76" cy="30" r="2.1" fill="{{ accent }}"></circle>
                </svg>
                <span style="flex:0 0 180px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ tPersist.label }}</span><span title="{{ tPersist.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ tPersist.mono }}</span></span>
                <input type="range" min="{{ tPersist.min }}" max="{{ tPersist.max }}" step="{{ tPersist.step }}" value="{{ tPersist.value }}" onChange="{{ tPersist.onInput }}" style="{{ tPersist.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:{{ tPersist.readColor }};">{{ tPersist.readout }}</span>
                <span style="flex:0 0 116px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ tPersist.caption }}</span>
              </div>

              <!-- recovery -->
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ tRecovery.onToggle }}" style="{{ tRecovery.trackStyle }}"><span style="{{ tRecovery.knobStyle }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <path d="M6,12 C16,20 22,30 30,30 C38,30 42,22 48,24 C54,26 62,33 72,36 C78,37 82,38 86,39" fill="none" stroke="#6e7a86" stroke-width="1.8"></path>
                  <line x1="38" y1="20" x2="62" y2="20" stroke="#d98a1f" stroke-width="1" stroke-dasharray="3 2"></line>
                  <circle cx="45" cy="22" r="2.3" fill="#d98a1f"></circle>
                  <text x="62" y="17" font-size="6.5" fill="#d98a1f" font-family="Inter,sans-serif">tol</text>
                </svg>
                <span style="flex:0 0 180px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ tRecovery.label }}</span><span title="{{ tRecovery.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ tRecovery.mono }}</span></span>
                <input type="range" min="{{ tRecovery.min }}" max="{{ tRecovery.max }}" step="{{ tRecovery.step }}" value="{{ tRecovery.value }}" onChange="{{ tRecovery.onInput }}" style="{{ tRecovery.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:{{ tRecovery.readColor }};">{{ tRecovery.readout }}</span>
                <span style="flex:0 0 116px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ tRecovery.caption }}</span>
              </div>

              <!-- load floor -->
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ tFloor.onToggle }}" style="{{ tFloor.trackStyle }}"><span style="{{ tFloor.knobStyle }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <line x1="6" y1="30" x2="86" y2="30" stroke="{{ accent }}" stroke-width="1.3" stroke-dasharray="4 2"></line>
                  <circle cx="22" cy="16" r="2.4" fill="{{ accent }}"></circle>
                  <circle cx="36" cy="12" r="2.4" fill="{{ accent }}"></circle>
                  <circle cx="54" cy="35" r="2.4" fill="#c5ccd4"></circle>
                  <circle cx="68" cy="37" r="2.4" fill="#c5ccd4"></circle>
                  <text x="86" y="28" text-anchor="end" font-size="6.5" fill="{{ accentInk }}" font-family="Inter,sans-serif">floor</text>
                </svg>
                <span style="flex:0 0 180px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ tFloor.label }}</span><span title="{{ tFloor.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ tFloor.mono }}</span></span>
                <input type="range" min="{{ tFloor.min }}" max="{{ tFloor.max }}" step="{{ tFloor.step }}" value="{{ tFloor.value }}" onChange="{{ tFloor.onInput }}" style="{{ tFloor.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:{{ tFloor.readColor }};">{{ tFloor.readout }}</span>
                <span style="flex:0 0 116px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ tFloor.caption }}</span>
              </div>

              <!-- scale guard (on/off) -->
              <div style="display:flex; align-items:center; gap:12px; padding:11px 0; border-top:1px solid #f4f6f8;">
                <div onClick="{{ tGuard.onToggle }}" style="{{ tGuard.trackStyle }}"><span style="{{ tGuard.knobStyle }}"></span></div>
                <svg viewBox="0 0 92 46" width="92" style="flex:none;">
                  <line x1="6" y1="40" x2="86" y2="40" stroke="#e3e7eb" stroke-width="1"></line>
                  <rect x="18" y="10" width="11" height="30" rx="1.5" fill="#c5ccd4"></rect>
                  <rect x="42" y="28" width="11" height="12" rx="1.5" fill="{{ accent }}"></rect>
                  <rect x="64" y="33" width="11" height="7" rx="1.5" fill="#f0d9d2"></rect>
                  <line x1="64" y1="29" x2="75" y2="38" stroke="#c0392b" stroke-width="1.5"></line>
                  <line x1="75" y1="29" x2="64" y2="38" stroke="#c0392b" stroke-width="1.5"></line>
                  <text x="23.5" y="8" text-anchor="middle" font-size="6" fill="#a09a8e" font-family="Inter,sans-serif">full</text>
                </svg>
                <span style="flex:0 0 180px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ tGuard.label }}</span><span title="{{ tGuard.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ tGuard.mono }}</span></span>
                <span style="flex:1; font-size:11.5px; color:{{ tGuard.explainColor }}; line-height:1.45;">{{ tGuard.explain }}</span>
              </div>

              <div style="margin-top:13px; font-size:12px; color:#5a6675; background:#f4f7f9; border:1px solid #edf0f3; border-radius:6px; padding:10px 12px; line-height:1.55;"><b style="color:#1e242c;">In words:</b> {{ truncPlain }}</div>
            </div>
          </div>

          <sc-if value="{{ showValidation }}" hint-placeholder-val="{{ true }}">
          <div style="display:flex; gap:14px; flex-wrap:wrap; margin-top:18px; font-size:11.5px;">
            <span style="color:#3d5c1c;">✓ window ≥ 50 points</span>
            <span style="color:#3d5c1c;">✓ end after start</span>
            <span style="color:#284f7e;">ⓘ gate excluded 1 terminal tail · kept for audit</span>
          </div>
          </sc-if>

          <div style="margin-top:16px; padding-top:14px; border-top:1px solid #edf0f3; font-size:12px; color:#5a6675;"><b style="color:#1e242c;">Affects →</b> every reported result — strength, modulus &amp; bending all read this window.</div>
        </div>
      </div>
      </sc-if>

      <!-- ===== BENDING EDIT CARD ===== -->
      <sc-if value="{{ bn }}" hint-placeholder-val="{{ false }}">
      <div style="margin:2px 0 8px; border:1px solid #e3e7eb; border-radius:8px; background:#fff; overflow:hidden;">
        <div style="display:flex; align-items:center; gap:11px; padding:14px 18px; border-bottom:1px solid #edf0f3;">
          <span style="font-size:9.5px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:{{ accentInk }}; background:{{ accentSoft }}; padding:3px 8px; border-radius:5px;">Diagnostic · flags runs</span>
          <span style="font-size:15px; font-weight:600;">Bending pattern diagnostic</span>
          <span style="font-size:12px; color:#a09a8e;">opposite-face strain divergence — tune how it is detected; the verdict it outputs is fixed</span>
        </div>
        <div style="padding:18px;">

          <div style="display:flex; align-items:flex-start; gap:9px; background:{{ accentSoft }}; border:1px solid #e3e7eb; border-radius:7px; padding:11px 14px; margin-bottom:20px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{{ accentInk }}" stroke-width="2" style="flex:none; margin-top:1px;"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4M12 8h.01"></path></svg>
            <span style="font-size:11.5px; color:{{ accentInk }}; line-height:1.5;">These controls tune <b>how bending is detected and classified</b> — the window, the threshold and the routing limits. The verdict categories and the metrics recorded per run are fixed <b>outputs</b> of the method, shown here for reference only.</span>
          </div>

          <!-- STEP 1 -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">1</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Assessment window</span>
            <span style="font-size:11.5px; color:#a09a8e;">where bending % is measured along the load curve</span>
          </div>
          <div style="padding-left:32px;">
            <sc-for list="{{ bnWindowSliders }}" as="sl" hint-placeholder-count="2">
            <div style="display:flex; align-items:center; gap:13px; padding:10px 0; border-top:1px solid #f4f6f8;">
              <span style="flex:0 0 230px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ sl.label }}</span><span title="{{ sl.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ sl.mono }}</span></span>
              <input type="range" min="{{ sl.min }}" max="{{ sl.max }}" step="{{ sl.step }}" value="{{ sl.value }}" onChange="{{ sl.onChange }}" style="{{ sl.sliderStyle }}"></input>
              <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:#1e242c;">{{ sl.readout }}</span>
              <span style="flex:0 0 120px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ sl.caption }}</span>
            </div>
            </sc-for>
            <div style="font-size:11px; color:#a09a8e; margin-top:9px;">strain basis <span class="mono" style="font-size:10.5px;">compression_magnitude</span> · ISO 14126 default window is 10–90%.</div>
          </div>

          <div style="height:1px; background:#edf0f3; margin:18px 0;"></div>

          <!-- STEP 2 -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">2</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Exceedance threshold</span>
            <span style="font-size:11.5px; color:#a09a8e;">the line a point must cross to be “bent”</span>
          </div>
          <div style="padding-left:32px;">
            <div style="display:flex; align-items:center; gap:13px; padding:10px 0;">
              <span style="flex:0 0 230px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ bnThreshold.label }}</span><span title="{{ bnThreshold.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ bnThreshold.mono }}</span></span>
              <input type="range" min="{{ bnThreshold.min }}" max="{{ bnThreshold.max }}" step="{{ bnThreshold.step }}" value="{{ bnThreshold.value }}" onChange="{{ bnThreshold.onChange }}" style="{{ bnThreshold.sliderStyle }}"></input>
              <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:#1e242c;">{{ bnThreshold.readout }}</span>
              <span style="flex:0 0 120px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ bnThreshold.caption }}</span>
            </div>
            <svg viewBox="0 0 760 122" width="100%" style="display:block; margin-top:6px;">
              <line x1="24" y1="98" x2="744" y2="98" stroke="#e3e7eb" stroke-width="1"></line>
              <line x1="24" y1="{{ bnThLineY }}" x2="744" y2="{{ bnThLineY }}" stroke="#c0392b" stroke-width="1.5" stroke-dasharray="6 4"></line>
              <text x="744" y="{{ bnThLineY }}" dy="-5" text-anchor="end" font-size="10" fill="#c0392b" font-family="Inter,sans-serif">threshold {{ bnThreshold.readout }}</text>
              <path d="{{ bnPath }}" fill="none" stroke="{{ accent }}" stroke-width="2"></path>
              <sc-for list="{{ bnPoints }}" as="pt" hint-placeholder-count="15">
              <circle cx="{{ pt.cx }}" cy="{{ pt.cy }}" r="{{ pt.r }}" fill="{{ pt.fill }}"></circle>
              </sc-for>
              <text x="24" y="117" font-size="10" fill="#a09a8e" font-family="Inter,sans-serif">bending % across the window — drag the threshold and points re-flag live; red points are exceedances</text>
            </svg>
            <div style="display:flex; align-items:center; gap:11px; margin-top:10px; padding:10px 13px; border:1px solid {{ bnVerdict.bd }}; background:{{ bnVerdict.bg }}; border-radius:7px;">
              <span style="font-size:9px; letter-spacing:0.09em; text-transform:uppercase; color:#a09a8e; font-weight:700; flex:none;">Live verdict</span>
              <span style="width:9px; height:9px; border-radius:2px; background:{{ bnVerdict.color }}; flex:none;"></span>
              <span class="mono" style="font-size:13px; font-weight:700; color:{{ bnVerdict.color }};">{{ bnVerdict.key }}</span>
              <span style="font-size:11.5px; color:#5a6675;">{{ bnVerdict.note }}</span>
              <span class="mono" style="margin-left:auto; font-size:10.5px; color:#a09a8e;">{{ bnVerdict.count }} exceedances · longest run {{ bnVerdict.seg }} pt</span>
            </div>
          </div>

          <div style="height:1px; background:#edf0f3; margin:18px 0;"></div>

          <!-- STEP 3 -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">3</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Segment detection</span>
            <span style="font-size:11.5px; color:#a09a8e;">how exceedance points are grouped into runs of bending</span>
          </div>
          <div style="padding-left:32px;">
            <div style="display:flex; align-items:center; gap:13px; padding:10px 0;">
              <span style="flex:0 0 230px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ bnGap.label }}</span><span title="{{ bnGap.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ bnGap.mono }}</span></span>
              <input type="range" min="{{ bnGap.min }}" max="{{ bnGap.max }}" step="{{ bnGap.step }}" value="{{ bnGap.value }}" onChange="{{ bnGap.onChange }}" style="{{ bnGap.sliderStyle }}"></input>
              <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:#1e242c;">{{ bnGap.readout }}</span>
              <span style="flex:0 0 120px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ bnGap.caption }}</span>
            </div>
            <div style="display:flex; align-items:center; gap:13px; padding:10px 0; border-top:1px solid #f4f6f8;">
              <div onClick="{{ bnSpikeToggle }}" style="{{ bnSpikeTrack }}"><span style="{{ bnSpikeKnob }}"></span></div>
              <span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">Treat a single point as a spike</span><span title="When on, a lone exceedance point is classified as a spike rather than a one-point segment." style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span>
              <span class="mono" style="margin-left:auto; font-size:10px; color:#a09a8e;">segment_detection.classify_single_point_as_spike</span>
            </div>
          </div>

          <div style="height:1px; background:#edf0f3; margin:18px 0;"></div>

          <!-- STEP 4 -->
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <span style="width:22px; height:22px; border-radius:50%; background:{{ accentSoft }}; color:{{ accentInk }}; font-size:11px; font-weight:700; display:inline-flex; align-items:center; justify-content:center; flex:none;">4</span>
            <span style="font-size:11px; letter-spacing:0.07em; text-transform:uppercase; color:#1e242c; font-weight:700;">Routing limits → verdict</span>
            <span style="font-size:11.5px; color:#a09a8e;">the verdicts are fixed outputs — you tune the limits that route a run between them</span>
          </div>
          <div style="padding-left:32px;">
            <div style="font-size:11.5px; color:#5a6675; line-height:1.5; margin-bottom:12px; max-width:640px;">Each box names a verdict the method can <b style="color:#1e242c;">output</b>. The sliders inside set the limits that keep a run in the gentler verdict — raise a limit to tolerate more bending before it escalates.</div>
            <div style="display:flex; align-items:center; gap:9px; border:1px solid #d8e6d2; background:#f1f7ee; border-radius:7px; padding:11px 14px; margin-bottom:10px;">
              <span style="width:9px; height:9px; border-radius:2px; background:#2f8a4e; flex:none;"></span>
              <span class="mono" style="font-size:12px; font-weight:600; color:#2f6a40;">PASS</span>
              <span style="font-size:11.5px; color:#6a8a6a;">no exceedance, or below every limit set below</span>
            </div>

            <div style="border:1px solid #e3e7eb; border-radius:7px; padding:4px 14px 12px; margin-bottom:10px;">
              <div style="display:flex; align-items:center; gap:9px; padding:9px 0 2px;">
                <span style="width:9px; height:9px; border-radius:2px; background:#5aa06a; flex:none;"></span>
                <span class="mono" style="font-size:12px; font-weight:600; color:#1e242c;">PASS_WITH_SPIKES</span>
                <span style="font-size:11.5px; color:#a09a8e;">isolated one–two-point spikes tolerated</span>
              </div>
              <sc-for list="{{ bnPassSliders }}" as="sl" hint-placeholder-count="2">
              <div style="display:flex; align-items:center; gap:13px; padding:9px 0; border-top:1px solid #f4f6f8;">
                <span style="flex:0 0 224px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ sl.label }}</span><span title="{{ sl.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ sl.mono }}</span></span>
                <input type="range" min="{{ sl.min }}" max="{{ sl.max }}" step="{{ sl.step }}" value="{{ sl.value }}" onChange="{{ sl.onChange }}" style="{{ sl.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:#1e242c;">{{ sl.readout }}</span>
                <span style="flex:0 0 120px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ sl.caption }}</span>
              </div>
              </sc-for>
            </div>

            <div style="border:1px solid #efe2cf; border-radius:7px; padding:4px 14px 12px; margin-bottom:10px;">
              <div style="display:flex; align-items:center; gap:9px; padding:9px 0 2px;">
                <span style="width:9px; height:9px; border-radius:2px; background:#d98a1f; flex:none;"></span>
                <span class="mono" style="font-size:12px; font-weight:600; color:#1e242c;">WARN_TRANSIENT</span>
                <span style="font-size:11.5px; color:#a09a8e;">repeated short clusters, but no sustained region</span>
              </div>
              <sc-for list="{{ bnWarnSliders }}" as="sl" hint-placeholder-count="2">
              <div style="display:flex; align-items:center; gap:13px; padding:9px 0; border-top:1px solid #f4f6f8;">
                <span style="flex:0 0 224px; display:flex; flex-direction:column; gap:2px;"><span style="display:inline-flex; align-items:center; gap:7px;"><span style="font-size:12.5px; font-weight:600;">{{ sl.label }}</span><span title="{{ sl.info }}" style="display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; border-radius:50%; border:1px solid #c3cad2; color:#a09a8e; font-size:9px; font-weight:700; font-style:italic; cursor:help; flex:none;">i</span></span><span class="mono" style="font-size:10px; color:#a09a8e;">{{ sl.mono }}</span></span>
                <input type="range" min="{{ sl.min }}" max="{{ sl.max }}" step="{{ sl.step }}" value="{{ sl.value }}" onChange="{{ sl.onChange }}" style="{{ sl.sliderStyle }}"></input>
                <span class="mono" style="flex:0 0 56px; text-align:right; font-size:13px; font-weight:600; color:#1e242c;">{{ sl.readout }}</span>
                <span style="flex:0 0 120px; text-align:right; font-size:10.5px; color:#a09a8e;">{{ sl.caption }}</span>
              </div>
              </sc-for>
            </div>

            <div style="display:flex; align-items:center; gap:9px; border:1px solid #f0d9d2; background:#fdf2ee; border-radius:7px; padding:11px 14px;">
              <span style="width:9px; height:9px; border-radius:2px; background:#c0392b; flex:none;"></span>
              <span class="mono" style="font-size:12px; font-weight:600; color:#6e2a1a;">FAIL_SUSTAINED</span>
              <span style="font-size:11.5px; color:#8a4a39;">anything beyond the WARN limits — run routed to review at acceptance</span>
            </div>
          </div>

          <div style="margin-top:16px; padding-top:14px; border-top:1px solid #edf0f3; font-size:12px; color:#5a6675;"><b style="color:#1e242c;">Affects →</b> the bending <b>pattern verdict</b> (PASS · SPIKES · TRANSIENT · SUSTAINED) shown at acceptance and in the audit report. Diagnostic only — does not change reported strength, modulus or failure strain.</div>
        </div>
      </div>
      </sc-if>

      </div>
      <!-- ===== /EDIT PANEL ===== -->

      <!-- ===== ACTION BAR (pinned footer) ===== -->
      <div style="flex:none; padding:13px 28px; border-top:1px dashed #e3e7eb; display:flex; align-items:center; justify-content:space-between; gap:20px; background:#fff; border-radius:0 0 10px 10px;">
        <div style="display:flex; align-items:center; gap:14px;">
          <div>
            <div style="font-size:13px; font-weight:600;">Draft <span class="mono" style="font-size:12px;">v0.1.1</span> · {{ dirtyLabel }}</div>
            <div style="font-size:11.5px; color:#a09a8e;">Generate commits the {{ changeCount }} change(s) listed below · picked up by the Method Wizard on next run</div>
          </div>
          <input placeholder="reason for change…" style="border:1px solid #c3cad2; border-radius:4px; padding:7px 11px; font-size:12.5px; font-family:inherit; color:#1e242c; width:200px; background:#fff;"></input>
        </div>
        <button style="border:1px solid {{ genBorder }}; background:{{ genBg }}; color:{{ genColor }}; font-family:inherit; font-size:13px; font-weight:600; padding:9px 18px; border-radius:4px; cursor:{{ genCursor }}; display:inline-flex; align-items:center; gap:8px;">▶ Generate new method version</button>
      </div>
    </div>

    <!-- CHANGE LEDGER (Norman + Nielsen) — every diff vs v0.1.0, visible in every mode -->
    <div style="width:940px; flex:none; display:flex; align-items:center; gap:12px; margin-top:8px;">
      <span style="font-size:10px; letter-spacing:0.09em; text-transform:uppercase; color:#a09a8e; font-weight:700; flex:none;">Change ledger <span style="color:{{ accentInk }};">· {{ changeCount }}</span></span>
      <div style="display:flex; align-items:center; gap:7px; overflow-x:auto; flex:1; min-width:0; padding-bottom:2px;">
        <sc-if value="{{ noChanges }}" hint-placeholder-val="{{ false }}">
          <span style="font-size:11.5px; color:#a9b1bb; font-style:italic;">identical to v0.1.0 — nothing to generate yet</span>
        </sc-if>
        <sc-for list="{{ changes }}" as="c" hint-placeholder-count="1">
          <span style="display:inline-flex; align-items:center; gap:6px; flex:none; border:1px solid #e3e7eb; background:#fff; border-radius:999px; padding:4px 11px; font-size:11px; white-space:nowrap;">
            <span style="color:#5a6675; font-weight:600;">{{ c.lbl }}</span>
            <span class="mono" style="font-size:10px; color:#a9b1bb; text-decoration:line-through;">{{ c.base }}</span>
            <span style="color:{{ accent }};">→</span>
            <span class="mono" style="font-size:10.5px; color:{{ accentInk }}; font-weight:600;">{{ c.cur }}</span>
          </span>
        </sc-for>
      </div>
      <span style="font-size:11px; color:#a09a8e; flex:none;">Activity log · 5</span>
    </div>

  </div>

  <!-- ============ STATUS BAR ============ -->
  <div style="flex:none; display:flex; align-items:center; justify-content:space-between; height:30px; padding:0 16px; background:#f4f6f8; border-top:1px solid #e3e7eb; margin-top:8px;">
    <span style="display:inline-flex; align-items:center; gap:8px; font-size:11.5px; color:#5a6675;"><span style="width:7px; height:7px; border-radius:50%; background:{{ statusDot }};"></span>{{ statusText }}</span>
    <span style="font-size:11.5px; color:#a09a8e;">Method Editor · mtdp v0.2.0</span>
  </div>

  <!-- ============ KEYBOARD SHORTCUTS OVERLAY ============ -->
  <sc-if value="{{ shortcutsOpen }}" hint-placeholder-val="{{ false }}">
  <div onClick="{{ closeShortcuts }}" style="position:fixed; inset:0; z-index:90; background:rgba(28,34,42,0.34); display:flex; align-items:center; justify-content:center;">
    <div onClick="{{ stop }}" style="width:448px; background:#fff; border-radius:12px; box-shadow:0 24px 60px rgba(20,18,12,0.32); overflow:hidden;">
      <div style="display:flex; align-items:center; justify-content:space-between; padding:16px 20px; border-bottom:1px solid #edf0f3;">
        <span style="font-size:14px; font-weight:700; color:#1e242c;">Keyboard shortcuts</span>
        <span onClick="{{ closeShortcuts }}" style="font-size:14px; color:#a09a8e; cursor:pointer; padding:2px 6px;">✕</span>
      </div>
      <div style="padding:8px 12px 14px;">
        <sc-for list="{{ shortcutRows }}" as="r" hint-placeholder-count="8">
        <div style="display:flex; align-items:center; justify-content:space-between; gap:20px; padding:9px 8px; border-bottom:1px solid #f4f6f8;">
          <span style="font-size:12.5px; color:#28303a;">{{ r.d }}</span>
          <span class="mono" style="font-size:11.5px; color:#44505d; background:#f1f3f6; border:1px solid #e3e7eb; border-radius:5px; padding:3px 9px; white-space:nowrap; flex:none;">{{ r.k }}</span>
        </div>
        </sc-for>
      </div>
    </div>
  </div>
  </sc-if>

  <!-- ============ TOAST ============ -->
  <sc-if value="{{ hasToast }}" hint-placeholder-val="{{ false }}">
  <div style="position:fixed; left:50%; bottom:48px; transform:translateX(-50%); z-index:95; background:#1e242c; color:#fff; font-size:12.5px; padding:9px 17px; border-radius:8px; box-shadow:0 10px 30px rgba(20,18,12,0.28);">{{ toast }}</div>
  </sc-if>

</div>
`,p=`class Component extends DCLogic {
  state = {
    active: 'modulus',
    pipeExpanded: false,
    methods: [
      { id:'iso14126_2023', label:'ISO 14126 Compression', version:'0.1.0' },
      { id:'iso604',        label:'ISO 604 Compression',    version:'0.3.0' },
      { id:'astmd695',      label:'ASTM D695 Compression',  version:'0.2.0' },
    ],
    methodId: 'iso14126_2023',
    menuOpen: false,
    topMenu: null,
    shortcutsOpen: false,
    toast: null,
    newSeq: 1,
    editingNameId: null,
    nameDraft: '',
    startStrain: '0.0005',
    endStrain: '0.0030',
    gateOn: true,
    excl: { lowload:true, resets:true, nonnum:true, jumps:true, plateaus:true, fragments:false, restart:false },
    gateP: {
      lowloadFrac:'20', lowloadPts:'3', jumpsMult:'2.0', plateauPts:'3',
      resetMult:'8', nonnumPts:'2', fragFrac:'50', fragPts:'5', restartFrac:'5', restartPts:'15',
    },
    borderline: 'review',
    blMag:'1.0', blPts:'8',
    truncOn: true,
    trunc: { drop:true, persist:true, recovery:true, loadfloor:true, scaleguard:true },
    drop: '0.10', persist: '8', recovery: '0.05', loadfloor: '2.0',
    bend: {
      winLower:'10', winUpper:'90', threshold:'10',
      allowGap:'0', spikeSingle:true,
      passSegPts:'2', passFrac:'0.02', warnSegFrac:'0.05', warnFrac:'0.10',
    },
  };

  num(raw, min, max, int) {
    const t = String(raw == null ? '' : raw).trim();
    if (t === '') return { ok:false, msg:'required' };
    const re = int ? /^\\d+$/ : /^-?\\d*\\.?\\d+$/;
    if (!re.test(t)) return { ok:false, msg: int ? 'whole number expected' : 'number expected' };
    const v = parseFloat(t);
    if (v < min || v > max) return { ok:false, msg:'expected ' + min + '–' + max };
    return { ok:true, val:v, msg:'' };
  }

  componentDidMount() {
    this._onKey = (e) => {
      const meta = e.metaKey || e.ctrlKey;
      const t = e.target || {};
      const tag = (t.tagName || '').toLowerCase();
      const typing = tag === 'input' || tag === 'textarea' || t.isContentEditable;
      if (e.key === 'Escape') { this.setState({ topMenu:null, shortcutsOpen:false, menuOpen:false, editingNameId:null }); return; }
      if (meta && e.key === '/') { e.preventDefault(); this.setState(st => ({ shortcutsOpen: !st.shortcutsOpen, topMenu:null })); return; }
      if (meta && (e.key === 'n' || e.key === 'N')) { e.preventDefault(); this.createMethodNow(); return; }
      if (meta && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null })); return; }
      if (meta && (e.key === 'g' || e.key === 'G')) { e.preventDefault(); this.fireToast('Generating new method version…'); return; }
      if (meta && e.key === 'Enter') { e.preventDefault(); this.fireToast('Validating draft…'); return; }
      if (e.key === 'F2') { e.preventDefault(); this.renameCurrentNow(); return; }
      if (typing || meta) return;
      if (e.key === '1') { this.setState({ active:'testRange' }); }
      else if (e.key === '2') { this.setState({ active:'modulus' }); }
      else if (e.key === '3') { this.setState({ active:'bending' }); }
    };
    window.addEventListener('keydown', this._onKey);
  }
  componentWillUnmount() { window.removeEventListener('keydown', this._onKey); clearTimeout(this._tt); }

  createMethodNow() {
    this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label, topMenu:null }; });
  }
  renameCurrentNow() {
    this.setState(st => { const cur = st.methods.find(m => m.id === st.methodId) || st.methods[0]; return { menuOpen:true, editingNameId: cur.id, nameDraft: cur.label, topMenu:null }; });
  }
  resetAll() {
    this.setState({ startStrain:'0.0005', endStrain:'0.0025', gateOn:true, truncOn:true, borderline:'review', drop:'0.10', persist:'8', recovery:'0.05', loadfloor:'2.0', bend:{ winLower:'10', winUpper:'90', threshold:'10', allowGap:'0', spikeSingle:true, passSegPts:'2', passFrac:'0.02', warnSegFrac:'0.05', warnFrac:'0.10' }, topMenu:null });
    this.fireToast('Reset to v0.1.0');
  }
  fireToast(msg) { clearTimeout(this._tt); this.setState({ toast: msg, topMenu:null }); this._tt = setTimeout(() => this.setState({ toast:null }), 1900); }

  renderVals() {
    const a = this.props.accent ?? 'blue';
    const palettes = {
      blue:     { accent:'#3a72c4', soft:'#e8eff9', hover:'#2f5fa6', ink:'#284f7e' },
      teal:     { accent:'#0e7c86', soft:'#e2f0f1', hover:'#0b656d', ink:'#0b4f55' },
      violet:   { accent:'#5a46c9', soft:'#ece9fb', hover:'#4a39ab', ink:'#3d2f8f' },
      graphite: { accent:'#3a3a3a', soft:'#ededed', hover:'#2a2a2a', ink:'#2a2a2a' },
    };
    const p = palettes[a] || palettes.blue;
    const A = p.accent, S = p.soft, INK = p.ink;
    const s = this.state;
    const active = s.active, mo = active === 'modulus', tr = active === 'testRange', bn = active === 'bending';
    const trDeact = !s.gateOn && !s.truncOn;

    const pipeChip = (on) => on
      ? { display:'inline-flex', alignItems:'center', gap:'7px', fontSize:'12px', fontWeight:600, color:INK, background:S, border:'1px solid '+A, borderRadius:'999px', padding:'3px 11px', cursor:'pointer' }
      : { display:'inline-flex', alignItems:'center', gap:'7px', fontSize:'12px', fontWeight:500, color:'#5a6675', background:'#fff', border:'1px solid #d6dbe1', borderRadius:'999px', padding:'3px 11px', cursor:'pointer' };
    const activeLabel = tr ? 'Test range' : (mo ? 'Modulus' : 'Bending');

    const baseBox = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 13px', cursor:'pointer', position:'relative' };
    const baseRes = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 14px', cursor:'pointer', position:'relative' };
    const seg = (on) => ({ padding:'7px 14px', borderRadius:'6px', fontSize:'12.5px', cursor:'pointer', fontFamily:'inherit', background:on?S:'#fff', color:on?INK:'#5a6675', border:on?('1px solid '+A):'1px solid #e3e7eb', fontWeight:on?600:500 });
    const trk = (on) => ({ position:'relative', width:'34px', height:'20px', borderRadius:'999px', background:on?A:'#c3cad2', flex:'none', cursor:'pointer' });
    const knb = (on) => { const o = { position:'absolute', top:'2px', width:'16px', height:'16px', borderRadius:'50%', background:'#fff' }; o[on?'right':'left'] = '2px'; return o; };

    const ERRB = '#a8412a', ERRBG = '#fdf2ee', ERRINK = '#6e2a1a', OKINK = '#3d5c1c';
    const inBase = { fontFamily:"'JetBrains Mono','Cascadia Code',Consolas,monospace", border:'1px solid #c3cad2', borderRadius:'4px', padding:'8px 11px', fontSize:'14px', background:'#fff', color:'#1e242c', width:'100%', boxSizing:'border-box' };
    const inErr = { ...inBase, border:'1.5px solid '+ERRB, background:ERRBG };
    const inAcc = { ...inBase, border:'1.5px solid '+A, background:S };

    // ---- modulus fields ----
    const vS = this.num(s.startStrain, 0, 0.05, false);
    const vE = this.num(s.endStrain, 0, 0.05, false);
    const cross = (vS.ok && vE.ok) ? (parseFloat(s.startStrain) < parseFloat(s.endStrain)) : true;
    const startErr = !vS.ok || (vS.ok && vE.ok && !cross);
    const endErr   = !vE.ok || (vS.ok && vE.ok && !cross);
    const endChanged = s.endStrain.trim() !== '0.0025';
    const fStart = {
      value: s.startStrain, onInput: (e) => this.setState({ startStrain: e.target.value }),
      style: startErr ? inErr : inBase,
      msg: !vS.ok ? vS.msg : (!cross ? 'must be below end strain' : '✓ below end strain'),
      msgColor: startErr ? ERRINK : OKINK,
    };
    const fEnd = {
      value: s.endStrain, onInput: (e) => this.setState({ endStrain: e.target.value }),
      style: endErr ? inErr : (endChanged ? inAcc : inBase),
      msg: !vE.ok ? vE.msg : (!cross ? 'must be above start strain' : 'was 0.0025 · ✓ inside test range · ✓ enough points'),
      msgColor: endErr ? ERRINK : OKINK,
    };
    const modErr = startErr || endErr;

    // ---- methods ----
    const cur = s.methods.find(m => m.id === s.methodId) || s.methods[0] || { label:'—', version:'0.0.0' };
    const canDel = s.methods.length > 1;
    const methodMenu = s.methods.map(m => ({
      label: m.label, version: m.version, canDel,
      editing: s.editingNameId === m.id, notEditing: s.editingNameId !== m.id,
      onStartRename: () => this.setState({ editingNameId: m.id, nameDraft: m.label }),
      onSelect: () => this.setState({ methodId: m.id, menuOpen: false }),
      onDelete: () => this.setState(st => {
        if (st.methods.length <= 1) return {};
        const mm = st.methods.filter(x => x.id !== m.id);
        const methodId = st.methodId === m.id ? mm[0].id : st.methodId;
        return { methods: mm, methodId };
      }),
      rowStyle: { display:'flex', alignItems:'center', gap:'8px', padding:'8px 10px', borderRadius:'6px', background: m.id === s.methodId ? S : 'transparent' },
      dotStyle: { width:'7px', height:'7px', borderRadius:'50%', background: m.id === s.methodId ? A : '#c5ccd4', flex:'none' },
    }));

    // ---- method naming / renaming ----
    const commitName = () => this.setState(st => {
      if (st.editingNameId == null) return {};
      const nm = (st.nameDraft || '').trim();
      const methods = nm ? st.methods.map(x => x.id === st.editingNameId ? { ...x, label: nm } : x) : st.methods;
      return { methods, editingNameId: null };
    });
    const cancelName = () => this.setState({ editingNameId: null });
    const onNameKey = (e) => {
      if (e.key === 'Enter') { e.preventDefault(); commitName(); e.target.blur(); }
      else if (e.key === 'Escape') { e.preventDefault(); cancelName(); e.target.blur(); }
    };

    // ---- exclusion chips ----
    const exclDefs = [
      ['lowload','Persistent low-load tails'], ['resets','Domain resets'], ['nonnum','Non-numeric clusters'],
      ['jumps','Implausible jumps'], ['plateaus','Artificial plateaus'], ['fragments','Disconnected high-load fragments'], ['restart','Late restart / spikes'],
    ];
    const chip = (on) => on
      ? { display:'inline-flex', alignItems:'center', gap:'6px', border:'1px solid '+A, background:S, color:INK, borderRadius:'999px', padding:'5px 12px', fontSize:'11.5px', fontWeight:500, cursor:'pointer' }
      : { display:'inline-flex', alignItems:'center', gap:'6px', border:'1px solid #e3e7eb', background:'#fff', color:'#a09a8e', borderRadius:'999px', padding:'5px 12px', fontSize:'11.5px', fontWeight:500, cursor:'pointer' };
    const dot = (on) => on ? { width:'6px', height:'6px', borderRadius:'50%', background:A } : { width:'6px', height:'6px', borderRadius:'50%', border:'1.5px solid #c5ccd4' };
    const exclChips = exclDefs.map(([k, label]) => ({
      label, onClick: () => this.setState(st => ({ excl: { ...st.excl, [k]: !st.excl[k] } })),
      chipStyle: chip(s.excl[k]), dotStyle: dot(s.excl[k]),
    }));

    // ---- gate exclusion rules with inline tunable thresholds ----
    const gp = s.gateP;
    const setGp = (k, v) => this.setState(st => ({ gateP: { ...st.gateP, [k]: v } }));
    const pillStyle = (on) => ({ fontFamily:"'JetBrains Mono','Cascadia Code',Consolas,monospace", width:'46px', textAlign:'center', border:'1px solid '+(on?'#c3cad2':'#e3e7eb'), borderRadius:'4px', padding:'3px 3px', fontSize:'12px', color:(on?'#1e242c':'#a9b1bb'), background:(on?'#fff':'#f2f5f7'), margin:'0 2px', pointerEvents:(on?'auto':'none') });
    const mkRule = (key, params) => {
      const on = s.excl[key];
      const o = {
        toggle: () => this.setState(st => ({ excl: { ...st.excl, [key]: !st.excl[key] } })),
        track: trk(on), knob: knb(on),
        txtStyle: { fontSize:'12px', color:(on?'#5a6675':'#a9b1bb'), lineHeight:'1.9', flex:'1' },
        pStyle: pillStyle(on),
      };
      params.forEach(pk => { o[pk + 'V'] = String(gp[pk]); o[pk + 'On'] = (e) => setGp(pk, e.target.value); });
      return o;
    };
    const exLowload   = mkRule('lowload',   ['lowloadFrac','lowloadPts']);
    const exJumps     = mkRule('jumps',     ['jumpsMult']);
    const exPlateau   = mkRule('plateaus',  ['plateauPts']);
    const exReset     = mkRule('resets',    ['resetMult']);
    const exNonnum    = mkRule('nonnum',    ['nonnumPts']);
    const exFragments = mkRule('fragments', ['fragFrac','fragPts']);
    const exRestart   = mkRule('restart',   ['restartFrac','restartPts']);
    const bl = { magV:String(s.blMag), magOn:(e)=>this.setState({blMag:e.target.value}), ptsV:String(s.blPts), ptsOn:(e)=>this.setState({blPts:e.target.value}), pStyle:pillStyle(true) };

    // ---- truncation parts (bounded sliders) ----
    const sliderStyle = { flex:'1', accentColor:A, height:'18px', cursor:'pointer', minWidth:'0' };
    const partDefs = [
      { key:'drop',       valKey:'drop',     label:'Meaningful drop',           mono:'peak_decline.drop_fraction',          info:'How far load must fall below the running peak to count as a decline. Fraction of peak. Lower truncates more eagerly.', min:0, max:1,  step:0.01, unit:'',   plain:(v)=>'≥ '+Math.round(parseFloat(v)*100)+'% below peak',  hasInput:true },
      { key:'persist',    valKey:'persist',  label:'Low-state persistence',     mono:'peak_decline.persistence_points',     info:'Consecutive low-load points required to confirm the end, so transient dips are not mistaken for it.', min:1, max:500, step:1,   unit:' pt', plain:(v)=>'for '+v+' points',  hasInput:true },
      { key:'recovery',   valKey:'recovery', label:'Recovery amplitude tol.',   mono:'peak_decline.recovery_tolerance',     info:'Permitted rebound after a candidate end before it is rejected as non-terminal. Fraction of peak.', min:0, max:1,  step:0.01, unit:'',   plain:(v)=>'rebound < '+Math.round(parseFloat(v)*100)+'% ok',  hasInput:true },
      { key:'loadfloor',  valKey:'loadfloor',label:'Gated candidate load floor', mono:'peak_decline.candidate_load_floor_N', info:'Minimum load (N) for a point to be a valid end candidate inside the gate window.', min:0, max:50, step:0.5,  unit:' N',  plain:(v)=>'above '+v+' N',  hasInput:true },
      { key:'scaleguard', valKey:null,       label:'Full-run scale guard',      mono:'peak_decline.full_run_scale_guard',   info:'Rejects end candidates that conflict with the full-run load scale. No value — on or off.', hasInput:false },
    ];
    let trErr = false;
    const truncParts = partDefs.map(d => {
      const on = s.trunc[d.key];
      const enabled = s.truncOn && on;
      let value = '', slStyle = null, readout = '', caption = '', readColor = '#1e242c';
      if (d.hasInput) {
        value = String(s[d.valKey]);
        readout = value + (d.unit || '');
        caption = enabled ? d.plain(value) : 'off';
        readColor = enabled ? '#1e242c' : '#a09a8e';
        slStyle = { ...sliderStyle, opacity: enabled ? 1 : 0.5, pointerEvents: enabled ? 'auto' : 'none', cursor: enabled ? 'pointer' : 'default' };
      }
      return {
        label: d.label, info: d.info, mono: d.mono, hasInput: d.hasInput,
        trackStyle: trk(on), knobStyle: knb(on),
        onToggle: () => this.setState(st => ({ trunc: { ...st.trunc, [d.key]: !st.trunc[d.key] } })),
        value, min:String(d.min ?? 0), max:String(d.max ?? 1), step:String(d.step ?? 1),
        sliderStyle: slStyle, readout, caption, readColor,
        onInput: d.hasInput ? ((e) => this.setState({ [d.valKey]: e.target.value })) : null,
      };
    });

    const dropPct = Math.round(parseFloat(s.drop) * 100);
    const recPct = Math.round(parseFloat(s.recovery) * 100);
    let truncPlain;
    if (!s.truncOn) {
      truncPlain = 'Truncation is off — the interval runs all the way to the last acquired point.';
    } else {
      const head = [];
      if (s.trunc.drop) head.push('load falls at least ' + dropPct + '% below its running peak');
      if (s.trunc.persist) head.push('stays low for ' + s.persist + ' consecutive points');
      let txt = 'The end is called once ' + (head.length ? head.join(' and ') : 'a sustained post-peak decline is detected') + '.';
      const tail = [];
      if (s.trunc.recovery) tail.push('rebounds under ' + recPct + '% are ignored');
      if (s.trunc.loadfloor) tail.push('only points above ' + s.loadfloor + ' N qualify as candidates');
      if (s.trunc.scaleguard) tail.push('candidates conflicting with the full-run load scale are rejected');
      if (tail.length) txt += ' ' + tail.map(t => t.charAt(0).toUpperCase() + t.slice(1)).join('; ') + '.';
      truncPlain = txt;
    }

    const [tDrop, tPersist, tRecovery, tFloor, tGuard] = truncParts;
    tGuard.explain = (s.truncOn && s.trunc.scaleguard)
      ? 'On — rejects end candidates that conflict with the full-run load scale.'
      : (s.truncOn ? 'Off — candidates are not checked against the full-run scale.' : 'inactive while truncation is off');
    tGuard.explainColor = (s.truncOn && s.trunc.scaleguard) ? '#5a6675' : '#a09a8e';
    const endRule = s.truncOn
      ? 'the end is the first point where load, after reaching its peak, declines and does not recover.'
      : 'no end is cut — the interval runs all the way to the last acquired point.';
    const endRuleCode = s.truncOn ? 'end_policy = peak_decline_non_recovery' : 'end_policy = none · full series kept';

    // ---- bending diagnostic (step-wise) ----
    const b = s.bend;
    const setBend = (k, v) => this.setState(st => ({ bend: { ...st.bend, [k]: v } }));
    const bnWindowSliders = [
      { label:'Window lower bound', mono:'window.lower_percent', info:'Start of the assessment window as a % of maximum load. ISO 14126 uses 10%.', value:String(b.winLower), min:'0', max:'50', step:'1', caption:'% max load · 0–50', sliderStyle, readout:b.winLower+'%', onChange:(e)=>setBend('winLower', e.target.value) },
      { label:'Window upper bound', mono:'window.upper_percent', info:'End of the assessment window as a % of maximum load. ISO 14126 uses 90%.', value:String(b.winUpper), min:'50', max:'100', step:'1', caption:'% max load · 50–100', sliderStyle, readout:b.winUpper+'%', onChange:(e)=>setBend('winUpper', e.target.value) },
    ];
    const bnThreshold = { label:'Counts as bent above', mono:'threshold_percent', info:'A data point counts as exceeded once its bending % rises above this value.', value:String(b.threshold), min:'0', max:'30', step:'0.5', caption:'% · 0–30', sliderStyle, readout:b.threshold+'%', onChange:(e)=>setBend('threshold', e.target.value) };
    const bnGap = { label:'Allowed gap within a segment', mono:'segment_detection.allow_gap_points', info:'Points below threshold tolerated inside one contiguous exceedance segment before it is split.', value:String(b.allowGap), min:'0', max:'5', step:'1', caption:'points · 0–5', sliderStyle, readout:b.allowGap+' pt', onChange:(e)=>setBend('allowGap', e.target.value) };
    const bnSpikeTrack = trk(b.spikeSingle), bnSpikeKnob = knb(b.spikeSingle);
    const bnSpikeToggle = () => setBend('spikeSingle', !b.spikeSingle);
    const bnPassSliders = [
      { label:'Max longest segment', mono:'pass_with_spikes.max_longest_segment_points', info:'At or below this many contiguous exceedance points, isolated spikes still PASS.', value:String(b.passSegPts), min:'1', max:'10', step:'1', caption:'points · 1–10', sliderStyle, readout:b.passSegPts+' pt', onChange:(e)=>setBend('passSegPts', e.target.value) },
      { label:'Max total exceedance', mono:'pass_with_spikes.max_total_exceedance_fraction', info:'Total fraction of window points above threshold still permitted as PASS_WITH_SPIKES.', value:String(b.passFrac), min:'0', max:'0.1', step:'0.005', caption:'fraction · 0–0.10', sliderStyle, readout:b.passFrac, onChange:(e)=>setBend('passFrac', e.target.value) },
    ];
    const bnWarnSliders = [
      { label:'Max longest-segment fraction', mono:'warn_transient.max_longest_segment_fraction', info:'Longest contiguous exceedance as a fraction of the window. Beyond this it is no longer transient.', value:String(b.warnSegFrac), min:'0', max:'0.3', step:'0.005', caption:'fraction · 0–0.30', sliderStyle, readout:b.warnSegFrac, onChange:(e)=>setBend('warnSegFrac', e.target.value) },
      { label:'Max total exceedance', mono:'warn_transient.max_total_exceedance_fraction', info:'Total exceedance fraction tolerated as transient before the verdict becomes sustained.', value:String(b.warnFrac), min:'0', max:'0.5', step:'0.01', caption:'fraction · 0–0.50', sliderStyle, readout:b.warnFrac, onChange:(e)=>setBend('warnFrac', e.target.value) },
    ];
    const bnSubText = 'diagnostic · ' + b.winLower + '–' + b.winUpper + '% load window';

    // ============================================================
    // LIVE COUPLING (Victor) — diagrams driven by the actual values
    // ============================================================

    // -- modulus chord: endpoints track the typed strains, slope recomputes --
    const eMax = 0.006, xL = 30, xR = 244, yBot = 134, curveH = 108; // zoomed to the working strain range so the chord reads
    const moXof = (e) => xL + (Math.max(0, Math.min(eMax, e)) / eMax) * (xR - xL);
    const moYof = (e) => yBot - curveH * Math.pow(Math.max(0, Math.min(eMax, e)) / eMax, 0.82);
    let moCurve = '';
    for (let i = 0; i <= 26; i++) { const e = (i / 26) * eMax; moCurve += (i ? ' L' : 'M') + moXof(e).toFixed(1) + ',' + moYof(e).toFixed(1); }
    const moES = vS.ok ? parseFloat(s.startStrain) : 0.0005;
    const moEE = vE.ok ? parseFloat(s.endStrain) : 0.0025;
    const mo_x1 = moXof(moES), mo_y1 = moYof(moES), mo_x2 = moXof(moEE), mo_y2 = moYof(moEE);
    // slope of the drawn chord, normalised to an illustrative modulus index
    const moSlopeIdx = (moEE > moES) ? ((moYof(moES) - moYof(moEE)) / (moXof(moEE) - moXof(moES))) : 0;
    const moSlopeShow = !modErr;

    // -- bending: live threshold line, live point flags, live verdict --
    const bnPts = [3,5,4,8,12,9,5,4,6,13,16,8,4,3,5]; // illustrative bending % per window point
    const bnN = bnPts.length, bnX0 = 40, bnX1 = 740, bnTopPct = 30, bnYbot = 98, bnYtop = 38;
    const bnYof = (pct) => bnYbot - (Math.max(0, Math.min(bnTopPct, pct)) / bnTopPct) * (bnYbot - bnYtop);
    const bnXof = (i) => bnX0 + (i / (bnN - 1)) * (bnX1 - bnX0);
    const thr = parseFloat(b.threshold) || 0;
    const bnThLineY = bnYof(thr);
    let bnPath = '';
    const bnPoints = bnPts.map((pct, i) => {
      const cx = bnXof(i), cy = bnYof(pct), over = pct > thr;
      bnPath += (i ? ' L' : 'M') + cx.toFixed(1) + ',' + cy.toFixed(1);
      return { cx: cx.toFixed(1), cy: cy.toFixed(1), r: over ? '4' : '2.6', fill: over ? '#c0392b' : A };
    });
    // live verdict from exceedances vs the routing limits
    const allowGap = parseInt(b.allowGap) || 0;
    let exceedCount = 0, longestSeg = 0, run = 0, gap = 0;
    bnPts.forEach((pct) => {
      if (pct > thr) { run += 1 + gap; gap = 0; exceedCount++; if (run > longestSeg) longestSeg = run; }
      else { if (gap < allowGap && run > 0) { gap++; } else { run = 0; gap = 0; } }
    });
    const totalFrac = exceedCount / bnN, segFrac = longestSeg / bnN;
    const passFrac = parseFloat(b.passFrac), warnSegFrac = parseFloat(b.warnSegFrac), warnFrac = parseFloat(b.warnFrac);
    const passSegPts = parseInt(b.passSegPts);
    let bnVerdictKey;
    if (exceedCount === 0) bnVerdictKey = 'PASS';
    else if (longestSeg <= passSegPts && totalFrac <= Math.max(passFrac, 0.13)) bnVerdictKey = 'PASS_WITH_SPIKES';
    else if (segFrac <= Math.max(warnSegFrac, 0.2) && totalFrac <= Math.max(warnFrac, 0.4)) bnVerdictKey = 'WARN_TRANSIENT';
    else bnVerdictKey = 'FAIL_SUSTAINED';
    const verdictMap = {
      PASS:             { color:'#2f6a40', bg:'#f1f7ee', bd:'#d8e6d2', note:'no point crosses the threshold' },
      PASS_WITH_SPIKES: { color:'#1e242c', bg:'#f1f7ee', bd:'#d8e6d2', note:'isolated spikes only — within PASS limits' },
      WARN_TRANSIENT:   { color:'#8a5a14', bg:'#fbf3e4', bd:'#efe2cf', note:'repeated short clusters — flagged, not failed' },
      FAIL_SUSTAINED:   { color:'#6e2a1a', bg:'#fdf2ee', bd:'#f0d9d2', note:'sustained region — routed to review at acceptance' },
    };
    const bnVerdict = { key: bnVerdictKey, ...verdictMap[bnVerdictKey], count: exceedCount, seg: longestSeg };

    // -- test range: end boundary slides with the truncation drop --
    const trX0 = 40, trX1 = 808, trIntStart = 120;
    let tr_endX;
    if (!s.truncOn) tr_endX = trX1;                       // no truncation → runs to last point
    else { const dr = Math.max(0, Math.min(1, parseFloat(s.drop) || 0)); tr_endX = 540 + dr * 200; }
    const tr_intW = Math.max(0, tr_endX - trIntStart);
    const tr_tailW = Math.max(0, trX1 - tr_endX);
    const tr_peakY = 30 + (1 - Math.max(0, Math.min(1, parseFloat(s.drop) || 0))) * 0;

    // ============================================================
    // CHANGE LEDGER (Norman + Nielsen) — every diff vs v0.1.0
    // ============================================================
    const BASE = {
      startStrain:'0.0005', endStrain:'0.0025', gateOn:true, truncOn:true,
      borderline:'review', drop:'0.10', persist:'8', recovery:'0.05', loadfloor:'2.0',
      blMag:'1.0', blPts:'8',
      bend:{ winLower:'10', winUpper:'90', threshold:'10', allowGap:'0', spikeSingle:true },
    };
    const onoff = (v) => v ? 'on' : 'off';
    const ledgerSpec = [
      { lbl:'Modulus · start strain', cur:s.startStrain, base:BASE.startStrain },
      { lbl:'Modulus · end strain',   cur:s.endStrain,   base:BASE.endStrain },
      { lbl:'Signal gate',            cur:onoff(s.gateOn),  base:onoff(BASE.gateOn) },
      { lbl:'Truncation',             cur:onoff(s.truncOn), base:onoff(BASE.truncOn) },
      { lbl:'Borderline policy',      cur:s.borderline,  base:BASE.borderline },
      { lbl:'Decline drop',           cur:Math.round(parseFloat(s.drop)*100)+'%', base:Math.round(parseFloat(BASE.drop)*100)+'%' },
      { lbl:'Low-state persistence',  cur:s.persist+' pt', base:BASE.persist+' pt' },
      { lbl:'Recovery tolerance',     cur:Math.round(parseFloat(s.recovery)*100)+'%', base:Math.round(parseFloat(BASE.recovery)*100)+'%' },
      { lbl:'Candidate load floor',   cur:s.loadfloor+' N', base:BASE.loadfloor+' N' },
      { lbl:'Bending · window low',   cur:b.winLower+'%', base:BASE.bend.winLower+'%' },
      { lbl:'Bending · window high',  cur:b.winUpper+'%', base:BASE.bend.winUpper+'%' },
      { lbl:'Bending · threshold',    cur:b.threshold+'%', base:BASE.bend.threshold+'%' },
      { lbl:'Bending · segment gap',  cur:b.allowGap+' pt', base:BASE.bend.allowGap+' pt' },
    ];
    const changes = ledgerSpec.filter(c => String(c.cur) !== String(c.base))
      .map(c => ({ lbl:c.lbl, base:String(c.base), cur:String(c.cur) }));
    const changeCount = changes.length;
    const changesSummary = changeCount === 0
      ? 'no changes from v0.1.0'
      : changeCount + (changeCount === 1 ? ' setting' : ' settings') + ' changed vs v0.1.0';

    // ============================================================
    // LIVE PIPELINE STATUS (Raskin) — state visible in every mode
    // ============================================================
    const editedMod = s.startStrain !== BASE.startStrain || s.endStrain !== BASE.endStrain;
    const editedTR = onoff(s.gateOn) !== onoff(BASE.gateOn) || onoff(s.truncOn) !== onoff(BASE.truncOn)
      || s.borderline !== BASE.borderline || s.drop !== BASE.drop || s.persist !== BASE.persist
      || s.recovery !== BASE.recovery || s.loadfloor !== BASE.loadfloor;
    const editedBn = b.winLower !== BASE.bend.winLower || b.winUpper !== BASE.bend.winUpper
      || b.threshold !== BASE.bend.threshold || b.allowGap !== BASE.bend.allowGap;
    const statusDotStyle = (active, edited, err) => {
      const c = err ? '#c0392b' : (edited ? A : '#c5ccd4');
      return { width:'7px', height:'7px', borderRadius:'50%', background:c, flex:'none',
               boxShadow: active ? ('0 0 0 3px '+S) : 'none' };
    };
    const trStatusDot = statusDotStyle(tr, editedTR, trErr);
    const modStatusDot = statusDotStyle(mo, editedMod, modErr);
    const bnStatusDot = statusDotStyle(bn, editedBn, false);

    const anyErr = modErr || trErr;

    // ============================================================
    // TOP MENU BAR + KEYBOARD COMMANDS
    // ============================================================
    const tm = s.topMenu;
    const setActive = (k) => this.setState({ active:k, topMenu:null });
    const mkItem = (label, shortcut, fn, disabled) => ({
      isItem:true, isSep:false, label, shortcut: shortcut || '',
      scColor: disabled ? '#c2c8cf' : '#9aa3ad',
      onClick: () => { this.setState({ topMenu:null }); if (!disabled && fn) fn(); },
      rowStyle: { display:'flex', alignItems:'center', justifyContent:'space-between', gap:'30px', padding:'6px 10px', borderRadius:'5px', fontSize:'12.5px', color: disabled ? '#b3b9c0' : '#28303a', cursor: disabled ? 'default' : 'pointer', whiteSpace:'nowrap', background:'transparent' },
    });
    const sepItem = () => ({ isItem:false, isSep:true, label:'', shortcut:'', scColor:'#9aa3ad' });
    const mkStage = (label, sc, key, isActive) => {
      const it = mkItem(label, sc, () => setActive(key));
      it.rowStyle = { ...it.rowStyle, background: isActive ? S : 'transparent', color: isActive ? INK : '#28303a', fontWeight: isActive ? 600 : 400 };
      return it;
    };
    const menusData = [
      { id:'file', label:'File', items:[
        mkItem('New method', 'Ctrl+N', () => this.createMethodNow()),
        mkItem('Open package…', 'Ctrl+O', () => this.fireToast('Open package… (demo)')),
        sepItem(),
        mkItem('Save draft', 'Ctrl+S', () => this.fireToast('Draft saved')),
        mkItem('Export…', 'Ctrl+E', () => this.fireToast('Export… (demo)')),
        sepItem(),
        mkItem('Close', 'Ctrl+W', () => this.fireToast('Close (demo)')),
      ]},
      { id:'edit', label:'Edit', items:[
        mkItem('Undo', 'Ctrl+Z', null, true),
        mkItem('Redo', 'Ctrl+Shift+Z', null, true),
        sepItem(),
        mkItem('Rename method', 'F2', () => this.renameCurrentNow()),
        mkItem('Reset to v0.1.0', '', () => this.resetAll()),
        mkItem('Discard changes', '', () => this.resetAll()),
      ]},
      { id:'view', label:'View', items:[
        mkItem('Expand pipeline map', 'Ctrl+P', () => this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null }))),
        sepItem(),
        mkItem('Change ledger', '', () => this.fireToast(changeCount + ' change(s) staged')),
        mkItem('Validation messages', '', () => this.fireToast((this.props.showValidation ?? true) ? 'Validation is on' : 'Validation is off')),
      ]},
      { id:'stage', label:'Stage', items:[
        mkStage('Test range', '1', 'testRange', tr),
        mkStage('Modulus', '2', 'modulus', mo),
        mkStage('Bending', '3', 'bending', bn),
      ]},
      { id:'generate', label:'Generate', items:[
        mkItem('Validate draft', 'Ctrl+Enter', () => this.fireToast('Validating draft…')),
        mkItem('Generate new version', 'Ctrl+G', () => this.fireToast('Generating new method version…')),
      ]},
      { id:'help', label:'Help', items:[
        mkItem('Keyboard shortcuts', 'Ctrl+/', () => this.setState({ shortcutsOpen:true, topMenu:null })),
        mkItem('About Method Editor', '', () => this.fireToast('Method Editor · mtdp v0.2.0')),
      ]},
    ];
    const menus = menusData.map(mn => ({
      label: mn.label, open: tm === mn.id, items: mn.items,
      onClick: () => this.setState(st => ({ topMenu: st.topMenu === mn.id ? null : mn.id, menuOpen:false })),
      onHover: () => { if (this.state.topMenu && this.state.topMenu !== mn.id) this.setState({ topMenu: mn.id }); },
      labelStyle: { fontSize:'13px', color: tm === mn.id ? '#1e242c' : '#44505d', fontWeight: tm === mn.id ? 600 : 500, padding:'5px 10px', borderRadius:'6px', cursor:'pointer', background: tm === mn.id ? '#e6eaee' : 'transparent', userSelect:'none' },
    }));
    const shortcutRows = [
      { k:'Ctrl+N', d:'New method' },
      { k:'F2', d:'Rename current method' },
      { k:'1 · 2 · 3', d:'Jump to Test range · Modulus · Bending' },
      { k:'Ctrl+P', d:'Expand the pipeline map' },
      { k:'Ctrl+Enter', d:'Validate draft' },
      { k:'Ctrl+G', d:'Generate new method version' },
      { k:'Ctrl+/', d:'Show this shortcuts panel' },
      { k:'Esc', d:'Close menus and dialogs' },
    ];

    return {
      accent:A, accentSoft:S, accentInk:INK,
      active, mo, tr, bn,
      pipeExpanded: s.pipeExpanded,
      pipeOn: () => this.setState({ pipeExpanded: true }),
      pipeOff: () => this.setState({ pipeExpanded: false }),
      trChip: pipeChip(tr), modChip: pipeChip(mo), bnChip: pipeChip(bn), activeLabel,
      editTestRange: () => this.setState({ active:'testRange' }),
      editModulus: () => this.setState({ active:'modulus' }),
      editBending: () => this.setState({ active:'bending' }),
      trBoxStyle: trErr ? { ...baseBox, border:'1.5px solid #a8412a', background:'#fdf2ee' } : (trDeact ? { ...baseBox, border:'1.5px dashed #aeb6bf', background:'#eef1f4' } : (tr ? { ...baseBox, border:'1.5px solid '+A, background:S } : { ...baseBox, border:'1px solid #c3cad2', background:'#fff' })),
      trDeact, trDeactShow: trDeact,
      trSubText: trDeact ? 'deactivated · full raw series kept' : 'gate & truncation',
      modCardStyle: modErr ? { ...baseRes, border:'1.5px solid #a8412a', background:'#fdf2ee' } : (mo ? { ...baseRes, border:'1.5px solid '+A, background:S } : { ...baseRes, border:'1px solid #c3cad2', background:'#fff' }),
      modErrShow: modErr, modEditShow: mo && !modErr,
      bnCardStyle: bn ? { ...baseRes, border:'1.5px solid '+A, background:S } : { ...baseRes, border:'1px solid #c3cad2', background:'#fff' },
      bnEditShow: bn, bnSubColor: bn ? INK : '#5a6675', bnSubText,
      bnWindowSliders, bnThreshold, bnGap, bnSpikeTrack, bnSpikeKnob, bnSpikeToggle, bnPassSliders, bnWarnSliders,
      // live coupling
      moCurve, mo_x1, mo_y1, mo_x2, mo_y2, moSlopeShow,
      mo_startLabelX: mo_x1, mo_endLabelX: mo_x2,
      bnPath, bnThLineY, bnPoints, bnVerdict,
      tr_endX, tr_intW, tr_tailW,
      // ledger + live status
      changes, changeCount, changesSummary, hasChanges: changeCount > 0, noChanges: changeCount === 0,
      trStatusDot, modStatusDot, bnStatusDot,
      trErrShow: trErr, trEditShow: tr && !trErr,
      modSubColor: mo ? INK : '#5a6675',
      strengthLeg: tr ? A : '#c5ccd4', strengthMk: tr ? 'hd_a' : 'hd_g',
      modulusLeg: (tr||mo) ? A : '#c5ccd4', modulusMk: (tr||mo) ? 'hd_a' : 'hd_g',
      bendingLeg: (tr||bn) ? A : '#c5ccd4', bendingMk: (tr||bn) ? 'hd_a' : 'hd_g',
      segTrStyle: seg(tr), segModStyle: seg(mo),

      methodLabel: cur.label, methodVersion: cur.version, methodCount: s.methods.length,
      menuOpen: s.menuOpen, toggleMenu: () => this.setState(st => ({ menuOpen: !st.menuOpen })),
      createMethod: () => this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label }; }),
      methodMenu,
      nameDraft: s.nameDraft,
      onNameInput: (e) => this.setState({ nameDraft: e.target.value }),
      onNameKey, commitName, cancelName,
      nameInputRef: (el) => { if (el && this._focusedFor !== s.editingNameId) { this._focusedFor = s.editingNameId; setTimeout(() => { try { el.focus(); el.select(); } catch (_) {} }, 0); } },
      startRenameCurrent: () => this.setState({ menuOpen:true, editingNameId: cur.id, nameDraft: cur.label }),
      nameInputStyle: { flex:1, fontFamily:'inherit', fontSize:'12.5px', fontWeight:600, color:'#1e242c', border:'1px solid '+A, borderRadius:'4px', padding:'3px 7px', outline:'none', background:'#fff', minWidth:0 },

      fStart, fEnd, moStartEcho: s.startStrain, moEndEcho: s.endStrain,

      gateOn: s.gateOn, gateTrack: trk(s.gateOn), gateKnob: knb(s.gateOn),
      toggleGate: () => this.setState(st => ({ gateOn: !st.gateOn })),
      gateBodyStyle: s.gateOn ? { } : { opacity:0.42, pointerEvents:'none' },
      gateLabel: s.gateOn ? 'enabled' : 'disabled', gateLabelColor: s.gateOn ? OKINK : '#a09a8e',
      exclChips, exLowload, exJumps, exPlateau, exReset, exNonnum, exFragments, exRestart, bl,
      blReviewCard:  { flex:'1', borderRadius:'8px', padding:'11px 12px 12px', cursor:'pointer', border: s.borderline==='review'  ? '1.5px solid '+A : '1px solid #e3e7eb', background: s.borderline==='review'  ? S : '#fff' },
      blExcludeCard: { flex:'1', borderRadius:'8px', padding:'11px 12px 12px', cursor:'pointer', border: s.borderline==='exclude' ? '1.5px solid '+A : '1px solid #e3e7eb', background: s.borderline==='exclude' ? S : '#fff' },
      setReview: () => this.setState({ borderline:'review' }), setExclude: () => this.setState({ borderline:'exclude' }),

      truncOn: s.truncOn, truncTrack: trk(s.truncOn), truncKnob: knb(s.truncOn),
      toggleTrunc: () => this.setState(st => ({ truncOn: !st.truncOn })),
      truncBodyStyle: s.truncOn ? { } : { opacity:0.42, pointerEvents:'none' },
      truncLabel: s.truncOn ? 'enabled' : 'disabled', truncLabelColor: s.truncOn ? OKINK : '#a09a8e',
      tDrop, tPersist, tRecovery, tFloor, tGuard, endRule, endRuleCode, truncPlain,
      startPolicyStyle: 'border:1px solid #e3e7eb; background:#eff1f4; color:#5a6675;',
      endPolicyStyle: s.truncOn ? ('border:1px solid '+A+'; background:'+S+'; color:'+INK+';') : 'border:1px solid #e3e7eb; background:#eff1f4; color:#5a6675;',
      endPolicyText: s.truncOn ? 'end → peak_decline_non_recovery' : 'end → last point',
      endPolicyNote: s.truncOn ? 'determined by the truncation logic' : 'truncation off · full series kept',

      menus, anyMenuOpen: !!tm, closeMenus: () => this.setState({ topMenu:null }),
      openShortcuts: () => this.setState({ shortcutsOpen:true, topMenu:null }),
      shortcutsOpen: s.shortcutsOpen, closeShortcuts: () => this.setState({ shortcutsOpen:false }),
      minimizeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.minimizeWindow?.(); },
      toggleMaximizeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.toggleMaximizeWindow?.(); },
      closeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.closeWindow?.(); },
      stop: (e) => e.stopPropagation(),
      shortcutRows, toast: s.toast, hasToast: !!s.toast,

      showValidation: this.props.showValidation ?? true,
      dirtyLabel: anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' · 1 field needs attention' : changesSummary,
      genBg:     anyErr ? '#eff1f4' : A,
      genColor:  anyErr ? '#a09a8e' : '#fff',
      genBorder: anyErr ? '#e3e7eb' : A,
      genCursor: anyErr ? 'not-allowed' : 'pointer',
      statusDot: anyErr ? '#a8412a' : A,
      statusText: anyErr ? 'Fix field format to continue' : 'Draft — not saved',
    };
  }
}`;function m({onLaunch:e,onReady:t}){let[n,r]=i.useState(null),[s,c]=i.useState(null),l=i.useCallback(t=>{r(null),e?.(t)},[e]),f=i.useCallback(()=>{r(null),(window.desktopApi?.quitApplication||window.desktopApi?.closeWindow)?.()},[]),p=i.useCallback(()=>{r(null),c(null)},[]),m=i.useCallback(e=>{r(null),c(e)},[]);return i.useEffect(()=>{let e=e=>{e.key===`Escape`&&p()};return window.addEventListener(`keydown`,e),()=>window.removeEventListener(`keydown`,e)},[p]),(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(o,{name:`CompressionSuiteHome`,template:u,logic:d,methodReady:!0,showWorkflow:!0,showRecent:!1,onNavigate:e,onReady:t}),(0,a.jsxs)(`div`,{className:`launcher-hit-layer`,"aria-hidden":`false`,children:[(0,a.jsx)(`button`,{className:`launcher-menu-hit launcher-menu-hit--file`,type:`button`,"aria-label":`File`,onClick:()=>r(e=>e===`file`?null:`file`)}),(0,a.jsx)(`button`,{className:`launcher-menu-hit launcher-menu-hit--help`,type:`button`,"aria-label":`Help`,onClick:()=>r(e=>e===`help`?null:`help`)}),n&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`button`,{className:`launcher-menu-scrim`,type:`button`,"aria-label":`Close menu`,onClick:()=>r(null)}),n===`file`&&(0,a.jsxs)(`div`,{className:`launcher-menu-pop launcher-file-menu`,role:`menu`,"aria-label":`File`,children:[(0,a.jsxs)(`button`,{type:`button`,role:`menuitem`,onClick:()=>l(`packaging`),children:[(0,a.jsx)(`span`,{children:`Open Dataset Packaging...`}),(0,a.jsx)(`span`,{children:`Ctrl+D`})]}),(0,a.jsxs)(`button`,{type:`button`,role:`menuitem`,onClick:()=>l(`method-editor`),children:[(0,a.jsx)(`span`,{children:`Open Method...`}),(0,a.jsx)(`span`,{children:`Ctrl+M`})]}),(0,a.jsxs)(`button`,{type:`button`,role:`menuitem`,onClick:()=>l(`analysis`),children:[(0,a.jsx)(`span`,{children:`Open Analysis...`}),(0,a.jsx)(`span`,{children:`Ctrl+A`})]}),(0,a.jsx)(`i`,{}),(0,a.jsxs)(`button`,{type:`button`,role:`menuitem`,disabled:!0,"aria-disabled":`true`,children:[(0,a.jsx)(`span`,{children:`Recent sessions`}),(0,a.jsx)(`span`,{children:`Not available`})]}),(0,a.jsx)(`i`,{}),(0,a.jsx)(`button`,{type:`button`,role:`menuitem`,onClick:f,children:(0,a.jsx)(`span`,{children:`Exit`})})]}),n===`help`&&(0,a.jsxs)(`div`,{className:`launcher-menu-pop launcher-help-menu`,role:`menu`,"aria-label":`Help`,children:[(0,a.jsxs)(`button`,{type:`button`,role:`menuitem`,onClick:()=>m(`guide`),children:[(0,a.jsx)(`span`,{children:`User guidelines`}),(0,a.jsx)(`span`,{children:`Bundled`})]}),(0,a.jsx)(`button`,{type:`button`,role:`menuitem`,onClick:()=>m(`shortcuts`),children:(0,a.jsx)(`span`,{children:`Keyboard shortcuts`})}),(0,a.jsx)(`button`,{type:`button`,role:`menuitem`,onClick:()=>m(`licensing`),children:(0,a.jsx)(`span`,{children:`Licensing & notices...`})}),(0,a.jsx)(`i`,{}),(0,a.jsx)(`button`,{type:`button`,role:`menuitem`,onClick:()=>m(`about`),children:(0,a.jsx)(`span`,{children:`About this suite...`})})]})]}),s&&(0,a.jsx)(h,{modal:s,setModal:c,closeOverlay:p}),(0,a.jsx)(`button`,{className:`launcher-row-hit launcher-row-hit--dataset`,type:`button`,"aria-label":`Open Dataset Packaging`,"data-launcher-hit":`dataset-packaging`,onClick:()=>l(`packaging`)}),(0,a.jsx)(`button`,{className:`launcher-row-hit launcher-row-hit--method`,type:`button`,"aria-label":`Open Method`,"data-launcher-hit":`method-editor`,onClick:()=>l(`method-editor`)}),(0,a.jsx)(`button`,{className:`launcher-row-hit launcher-row-hit--analysis`,type:`button`,"aria-label":`Open Analysis`,"data-launcher-hit":`analysis`,onClick:()=>l(`analysis`)})]})]})}function h({modal:e,setModal:t,closeOverlay:n}){return e===`guide`?(0,a.jsx)(`div`,{className:`launcher-modal-scrim`,role:`presentation`,onMouseDown:n,children:(0,a.jsxs)(`section`,{className:`launcher-modal launcher-modal--wide`,role:`dialog`,"aria-modal":`true`,"aria-labelledby":`launcher-guide-title`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsx)(g,{titleId:`launcher-guide-title`,title:`User guidelines — NextCOMP Data Reduction Suite`,onClose:n}),(0,a.jsxs)(`div`,{className:`launcher-modal-body`,children:[(0,a.jsx)(_,{title:`User guidelines`,subtitle:`Packaging, method editing, analysis, acceptance, and MTDA review.`}),(0,a.jsx)(c,{section:`suite`}),(0,a.jsxs)(`p`,{className:`launcher-guide-note`,children:[`The full screenshot walkthrough is bundled as `,(0,a.jsx)(`span`,{children:`GUIDELINES.md`}),` in the repository root.`]}),(0,a.jsxs)(`div`,{className:`launcher-modal-actions`,children:[(0,a.jsx)(`button`,{className:`launcher-link-button`,type:`button`,onClick:()=>t(`shortcuts`),children:`Keyboard shortcuts →`}),(0,a.jsx)(`button`,{className:`launcher-primary-button`,type:`button`,onClick:n,children:`Close`})]})]})]})}):e===`about`?(0,a.jsx)(`div`,{className:`launcher-modal-scrim`,role:`presentation`,onMouseDown:n,children:(0,a.jsxs)(`section`,{className:`launcher-modal launcher-modal--wide`,role:`dialog`,"aria-modal":`true`,"aria-labelledby":`launcher-about-title`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsx)(g,{titleId:`launcher-about-title`,title:`About — NextCOMP Data Reduction Suite`,onClose:n}),(0,a.jsxs)(`div`,{className:`launcher-modal-body`,children:[(0,a.jsx)(_,{title:`Data Reduction Suite`,subtitle:`Data reduction pipeline for compression testing.`}),(0,a.jsxs)(`dl`,{className:`launcher-about-grid`,children:[(0,a.jsx)(`dt`,{children:`Version`}),(0,a.jsx)(`dd`,{children:`1.1.0`}),(0,a.jsx)(`dt`,{children:`Scope`}),(0,a.jsx)(`dd`,{children:`Compression testing`}),(0,a.jsx)(`dt`,{children:`Modules`}),(0,a.jsx)(`dd`,{children:`Dataset Packaging · Method · Analysis`}),(0,a.jsx)(`dt`,{children:`Developer`}),(0,a.jsx)(`dd`,{children:`Giacomo Damilano`}),(0,a.jsx)(`dt`,{children:`Email`}),(0,a.jsx)(`dd`,{className:`launcher-link-text`,children:`giacomo.damilano@gmail.com`}),(0,a.jsx)(`dt`,{children:`Project`}),(0,a.jsx)(`dd`,{children:`NextCOMP — Next Generation Fibre-Reinforced Composites`}),(0,a.jsx)(`dt`,{children:`License`}),(0,a.jsx)(`dd`,{children:`Apache License, Version 2.0`})]}),(0,a.jsx)(`p`,{className:`launcher-funding-text`,children:`Funding: UK Engineering and Physical Sciences Research Council (EPSRC) programme Grant EP/T011653/1, Next Generation Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression, Imperial College London and the University of Bristol.`}),(0,a.jsxs)(`div`,{className:`launcher-modal-actions`,children:[(0,a.jsx)(`button`,{className:`launcher-link-button`,type:`button`,onClick:()=>t(`licensing`),children:`Licensing & notices →`}),(0,a.jsx)(`button`,{className:`launcher-primary-button`,type:`button`,onClick:n,children:`Close`})]})]})]})}):e===`licensing`?(0,a.jsx)(`div`,{className:`launcher-modal-scrim`,role:`presentation`,onMouseDown:n,children:(0,a.jsxs)(`section`,{className:`launcher-modal launcher-modal--wide`,role:`dialog`,"aria-modal":`true`,"aria-labelledby":`launcher-licensing-title`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsx)(g,{titleId:`launcher-licensing-title`,title:`Licensing & notices — NextCOMP Data Reduction Suite`,onClose:n}),(0,a.jsxs)(`div`,{className:`launcher-modal-body`,children:[(0,a.jsx)(_,{title:`Licensing & notices`,subtitle:`Apache License, Version 2.0 · © 2026 Imperial College London`}),(0,a.jsxs)(`div`,{className:`launcher-license-copy`,children:[(0,a.jsx)(`p`,{children:`© 2026 Imperial College London. This product includes software developed at Imperial College London, made available under the Apache License, Version 2.0.`}),(0,a.jsx)(`p`,{children:`Apache-2.0 permits use, modification and redistribution, including for commercial purposes and within proprietary or sold products, provided the licence text and this NOTICE are retained.`}),(0,a.jsx)(`p`,{children:`The developer, Giacomo Damilano, is expressly authorised to use, reuse, modify, sublicense and incorporate the project-authored code and documentation, including for commercial purposes and within private, proprietary or sold products, subject to the third-party boundaries set out below.`}),(0,a.jsx)(`p`,{children:`The Apache-2.0 licence does not grant rights over third-party materials, standards documents, institutional or project logos, generated outputs, or external libraries identified as separately licensed or restricted. Redistributions must retain the NOTICE file and applicable third-party notices.`}),(0,a.jsx)(`p`,{children:`Unless required by applicable law or agreed in writing, the software is provided on an "AS IS" basis, without warranties or conditions of any kind, express or implied.`}),(0,a.jsx)(`p`,{children:`Developed for research purposes. Results and generated outputs are the user's responsibility and should be reviewed before being relied upon for engineering, certification or commercial decisions.`})]}),(0,a.jsxs)(`div`,{className:`launcher-modal-actions`,children:[(0,a.jsx)(`button`,{className:`launcher-link-button`,type:`button`,onClick:()=>t(`about`),children:`← Back to About`}),(0,a.jsx)(`button`,{className:`launcher-primary-button`,type:`button`,onClick:n,children:`Close`})]})]})]})}):(0,a.jsx)(`div`,{className:`launcher-modal-scrim`,role:`presentation`,onMouseDown:n,children:(0,a.jsxs)(`section`,{className:`launcher-modal launcher-modal--shortcuts`,role:`dialog`,"aria-modal":`true`,"aria-labelledby":`launcher-shortcuts-title`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsx)(g,{titleId:`launcher-shortcuts-title`,title:`Keyboard shortcuts`,onClose:n}),(0,a.jsxs)(`div`,{className:`launcher-modal-body`,children:[(0,a.jsx)(v,{title:`Open a module`,rows:[[`Ctrl+D`,`Open Dataset Packaging`],[`Ctrl+M`,`Open Method`],[`Ctrl+A`,`Open Analysis`]]}),(0,a.jsx)(v,{title:`Window`,rows:[[`F11 / Alt+Enter`,`Maximize or restore`],[`Ctrl+Shift+M`,`Minimize window`],[`Ctrl+W`,`Close window`],[`Ctrl+Q`,`Quit application`]]}),(0,a.jsx)(v,{title:`General`,rows:[[`Esc`,`Close menus and dialogs`]]}),(0,a.jsx)(`div`,{className:`launcher-modal-actions launcher-modal-actions--end`,children:(0,a.jsx)(`button`,{className:`launcher-primary-button`,type:`button`,onClick:n,children:`Close`})})]})]})})}function g({titleId:e,title:t,onClose:n}){return(0,a.jsxs)(`header`,{className:`launcher-modal-chrome`,children:[(0,a.jsx)(`div`,{className:`launcher-modal-title-dot`}),(0,a.jsx)(`h2`,{id:e,children:t}),(0,a.jsx)(`button`,{type:`button`,className:`launcher-modal-close`,"aria-label":`Close dialog`,onClick:n,children:`×`})]})}function _({title:e,subtitle:t}){return(0,a.jsxs)(`div`,{className:`launcher-brand-panel`,children:[(0,a.jsxs)(`div`,{children:[(0,a.jsx)(`div`,{className:`launcher-brand-eyebrow`,children:`NextCOMP`}),(0,a.jsx)(`div`,{className:`launcher-brand-title`,children:e}),(0,a.jsx)(`div`,{className:`launcher-brand-subtitle`,children:t})]}),(0,a.jsx)(`img`,{src:`assets/nextcomp-logo.png`,alt:`NextCOMP`})]})}function v({title:e,rows:t}){return(0,a.jsxs)(`section`,{className:`launcher-shortcut-group`,children:[(0,a.jsx)(`h3`,{children:e}),t.map(([t,n])=>(0,a.jsxs)(`div`,{className:`launcher-shortcut-row`,children:[(0,a.jsx)(`span`,{children:n}),(0,a.jsx)(`kbd`,{children:t})]},`${e}-${t}`))]})}var y=t();function b(e){return(e||``).replaceAll(`:root`,`:host`).replace(/html\s*,\s*body\s*\{/g,`:host {`).replace(/(^|[\s,{;}])body\s*\{/g,`$1.shadow-viewport {`)}function x({css:e,children:t,className:n}){let r=i.useRef(null),[o,s]=i.useState(null);return i.useLayoutEffect(()=>{let e=r.current;e&&s(e.shadowRoot||e.attachShadow({mode:`open`}))},[]),i.useEffect(()=>{let e=r.current;if(!e)return;let t=()=>{let t=document.documentElement,n=t.getAttribute(`data-density`);n?e.setAttribute(`data-density`,n):e.removeAttribute(`data-density`);let r=t.getAttribute(`style`)||``;r&&r.split(`;`).forEach(t=>{let n=t.indexOf(`:`);if(n>0){let r=t.slice(0,n).trim(),i=t.slice(n+1).trim();r.startsWith(`--`)&&i&&e.style.setProperty(r,i)}})};t();let n=new MutationObserver(t);return n.observe(document.documentElement,{attributes:!0,attributeFilter:[`data-density`,`style`]}),()=>n.disconnect()},[]),(0,a.jsx)(`div`,{ref:r,className:[`shadow-screen-host`,n].filter(Boolean).join(` `),children:o&&(0,y.createPortal)((0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`style`,{children:`:host{display:block;width:100%;height:100%;min-height:0;contain:layout paint style;} .shadow-viewport{width:100%;height:100%;min-height:0;overflow:hidden;} ${b(e)}`}),(0,a.jsx)(`div`,{className:`shadow-viewport`,children:t})]}),o)})}function S(e){Promise.resolve(e).then(e=>{e&&typeof e==`object`&&window.__compressionSyncWindowState?.(e)}).catch(()=>{})}function C(e){let t=window.desktopApi;if(!(!t||typeof t[e]!=`function`))return t[e]()}function w({className:e=``}){let t=(e,t=!1)=>n=>{n.preventDefault(),n.stopPropagation();let r=C(e);t&&S(r)};return(0,a.jsxs)(`div`,{className:[`desktop-window-controls`,e].filter(Boolean).join(` `),"data-window-controls":`true`,"aria-label":`Window controls`,children:[(0,a.jsx)(`button`,{type:`button`,className:`desktop-window-control`,"data-window-control":`minimize`,onClick:t(`minimizeWindow`),title:`Minimize`,"aria-label":`Minimize window`,children:`-`}),(0,a.jsx)(`button`,{type:`button`,className:`desktop-window-control`,"data-window-control":`maximize`,onClick:t(`toggleMaximizeWindow`,!0),title:`Maximize window`,"aria-label":`Maximize window`,children:`▢`}),(0,a.jsx)(`button`,{type:`button`,className:`desktop-window-control desktop-window-control--close`,"data-window-control":`close`,onClick:t(`closeWindow`),title:`Close`,"aria-label":`Close window`,children:`x`})]})}var T={id:`mechanical.compression`,version:`0.3.0`,label:`Compression`,unitSystem:`mechanical_metric_mm_N`,source:`schema_library/mechanical/compression/0.3.0.yaml`},E={length:{mm:1,cm:10,m:1e3,um:.001},force:{N:1,kN:1e3},speed:{"mm/min":1,"mm/s":60},strain:{"mm/mm":1,usn:1e-6,microstrain:1e-6},stress:{MPa:1,"N/mm^2":1,kPa:.001,Pa:1e-6},time:{s:1,ms:.001,us:1e-6}};function D(e,t,n,r){let i=E[t];if(!i||i[n]==null||i[r]==null)return e;let a=parseFloat(e);if(isNaN(a))return e;let o=a*i[n]/i[r];return String(Math.round(o*1e6)/1e6)}function O(e,t,n){let r=E[e];if(!r||r[t]==null||r[n]==null)return null;let i=r[t]/r[n];return i>=1?`× `+i:`÷ `+Math.round(1/i)}var k={};function A(e){return k[e.id]=e,e.id}var ee={units:[`mm`,`cm`,`m`],stdUnit:`mm`,dim:`length`,min:0};A({id:`sample_type`,label:`Sample type`,type:`string`,hardRequired:!0,importance:`required`,pattern:/^[\w .,+/()#°-]+$/,ph:`Dataset / sample family name`,desc:`Dataset/sample family name used to identify the tested group.`}),A({id:`treatment`,label:`Treatment`,type:`string`,importance:`recommended`,ph:`Condition or environmental ageing state`,desc:`Material treatment, condition, or environmental ageing state.`}),A({id:`material_label`,label:`Material label`,type:`string`,importance:`recommended`,ph:`Label used in the formal report`}),A({id:`test_id`,label:`Test ID`,type:`string`,importance:`recommended`,ph:`Lab test / request number`}),A({id:`report_operator`,label:`Dataset operator`,type:`string`,importance:`recommended`,desc:`Person responsible for the test series.`}),A({id:`loading_method`,label:`Loading method`,type:`enum`,importance:`required`,options:[{v:`method_1_shear_loading`,label:`Shear loading (Method 1)`},{v:`method_2_combined_loading`,label:`Combined loading (Method 2)`},{v:`other_specified`,label:`Other specified`,deviation:!0}]}),A({id:`loading_method_other`,label:`Other loading method`,type:`string`,importance:`optional`,visibleWhen:{field:`loading_method`,equals:`other_specified`},requiredWhen:{field:`loading_method`,equals:`other_specified`},desc:`Required when Loading method is Other specified; reported as an ISO deviation.`}),A({id:`specimen_type`,label:`Specimen type`,type:`enum`,importance:`required`,options:[{v:`type_a`,label:`Type A`},{v:`type_b1`,label:`Type B1`},{v:`type_b2`,label:`Type B2`},{v:`other_specified`,label:`Other specified`,deviation:!0}]}),A({id:`specimen_type_other`,label:`Other specimen type`,type:`string`,importance:`optional`,visibleWhen:{field:`specimen_type`,equals:`other_specified`},requiredWhen:{field:`specimen_type`,equals:`other_specified`},desc:`Required when Specimen type is Other specified; reported as an ISO deviation.`}),A({id:`material_type`,label:`Material type`,type:`string`,importance:`recommended`}),A({id:`matrix_type`,label:`Matrix type`,type:`string`,importance:`recommended`}),A({id:`reinforcement_type`,label:`Reinforcement type`,type:`string`,importance:`recommended`}),A({id:`manufacturer`,label:`Manufacturer`,type:`string`,importance:`recommended`}),A({id:`manufacturer_code`,label:`Manufacturer code`,type:`string`,importance:`optional`}),A({id:`material_source`,label:`Source`,type:`string`,importance:`recommended`}),A({id:`material_form`,label:`Form`,type:`string`,importance:`recommended`}),A({id:`previous_history`,label:`Previous history`,type:`string`,importance:`recommended`}),A({id:`cutting_direction`,label:`Cutting direction`,type:`string`,importance:`recommended`}),A({id:`fibre_orientation`,label:`Fibre orientation`,type:`string`,importance:`recommended`}),A({id:`layup`,label:`Layup`,type:`string`,importance:`recommended`}),A({id:`preparation_method`,label:`Preparation method`,type:`string`,importance:`recommended`}),A({id:`end_tabs`,label:`End tabs`,type:`string`,importance:`optional`}),A({id:`surface_preparation`,label:`Surface preparation`,type:`string`,importance:`optional`}),A({id:`specimen_preparation_notes`,label:`Notes`,type:`string`,importance:`optional`}),A({id:`fixture_type`,label:`Fixture type`,type:`string`,importance:`recommended`}),A({id:`fixture_standard_reference`,label:`Fixture standard reference`,type:`string`,importance:`optional`}),A({id:`fixture_manufacturer_design`,label:`Manufacturer/design`,type:`string`,importance:`recommended`}),A({id:`alignment_procedure`,label:`Alignment procedure`,type:`string`,importance:`recommended`}),A({id:`fixture_notes`,label:`Notes`,type:`string`,importance:`optional`}),A({id:`conditioning_standard`,label:`Conditioning standard`,type:`string`,importance:`recommended`}),A({id:`temperature`,label:`Temperature`,type:`float`,importance:`recommended`,units:[`°C`,`°F`,`K`],stdUnit:`°C`,dim:`temperature`,unitInline:!0,ph:`e.g. 23`,desc:`Conditioning / test temperature. Enter the number; pick the unit from the list.`}),A({id:`humidity`,label:`Humidity`,type:`float`,importance:`recommended`,units:[`% RH`],stdUnit:`% RH`,dim:`humidity`,unitInline:!0,min:0,ph:`e.g. 50`,desc:`Relative humidity during conditioning. Enter the number; the unit is fixed to % RH.`}),A({id:`conditioning_time`,label:`Conditioning time`,type:`float`,importance:`recommended`,units:[`h`,`min`,`s`,`d`],stdUnit:`h`,dim:`time`,unitInline:!0,min:0,ph:`e.g. 88`,desc:`Conditioning duration. Enter the number; pick the unit from the list.`}),A({id:`test_environment`,label:`Test environment`,type:`string`,importance:`recommended`}),A({id:`speed_of_testing`,label:`Speed of testing`,type:`float`,importance:`recommended`,units:[`mm/min`,`mm/s`],stdUnit:`mm/min`,dim:`speed`,min:0,unitInline:!0,desc:`Crosshead / test speed. Enter the number; pick the unit from the list.`}),A({id:`strain_measurement_method`,label:`Strain measurement method`,type:`string`,importance:`required`}),A({id:`measurement_location`,label:`Measurement location`,type:`string`,importance:`recommended`}),A({id:`acquisition_system`,label:`Acquisition system`,type:`string`,importance:`recommended`}),A({id:`sampling_rate`,label:`Sampling rate`,type:`float`,importance:`recommended`,units:[`Hz`,`kHz`],stdUnit:`Hz`,dim:`frequency`,unitInline:!0,min:0,ph:`e.g. 100`,desc:`Data acquisition rate. Enter the number; pick the unit from the list.`}),A({id:`measurement_notes`,label:`Notes`,type:`string`,importance:`optional`}),A({id:`deviations_from_standard`,label:`Deviations from standard`,type:`string`,importance:`optional`}),A({id:`remarks`,label:`Remarks`,type:`string`,importance:`optional`}),A({id:`specimen_name`,label:`Specimen name`,type:`string`,hardRequired:!0,importance:`required`,pattern:/^[\w .,+/()#°-]+$/}),A({id:`sample_id`,label:`Sample ID`,type:`string`,importance:`optional`}),A({id:`width`,label:`Width`,type:`float`,hardRequired:!0,importance:`required`,...ee,span:1}),A({id:`thickness`,label:`Thickness`,type:`float`,hardRequired:!0,importance:`required`,...ee,span:1}),A({id:`gauge_length`,label:`Strain-measurement gauge length`,type:`float`,importance:`recommended`,...ee,desc:`Required for methods deriving strain from extension or crosshead displacement; recommended with direct strain channels.`}),A({id:`distance_between_end_tabs`,label:`Distance between end tabs / unsupported length`,type:`float`,importance:`optional`,...ee}),A({id:`tab_length`,label:`Tab length`,type:`float`,importance:`optional`,...ee,span:1}),A({id:`tab_thickness`,label:`Tab thickness`,type:`float`,importance:`optional`,...ee,span:1}),A({id:`operator`,label:`Operator`,type:`string`,importance:`recommended`}),A({id:`instrument_model`,label:`Instrument model`,type:`string`,importance:`optional`}),A({id:`instrument_id`,label:`Instrument ID / serial number`,type:`string`,importance:`recommended`}),A({id:`instrument_location`,label:`Instrument location`,type:`string`,importance:`optional`}),A({id:`load_cell`,label:`Load cell`,type:`float`,importance:`optional`,units:[`N`,`kN`],stdUnit:`kN`,dim:`force`,min:0,span:1}),A({id:`test_speed`,label:`Test speed`,type:`float`,importance:`recommended`,units:[`mm/min`],stdUnit:`mm/min`,dim:`speed`,min:0,span:1}),A({id:`test_date`,label:`Test date`,type:`date`,importance:`recommended`}),A({id:`source_software`,label:`Source software`,type:`string`,importance:`recommended`}),A({id:`run_notes`,label:`Run notes`,type:`string`,importance:`optional`}),A({id:`primary_failure_mode`,label:`Primary failure mode`,type:`enum`,importance:`required_for_accepted_runs`,default:`not_recorded`,notRecorded:`not_recorded`,options:[{v:`in_plane_shear`,label:`In-plane shear`},{v:`complex`,label:`Complex`},{v:`through_thickness_shear`,label:`Through-thickness shear`},{v:`splitting`,label:`Splitting`},{v:`delamination`,label:`Delamination`},{v:`not_recorded`,label:`Not recorded`}]}),A({id:`failure_location`,label:`Failure location`,type:`enum`,importance:`required_for_accepted_runs`,default:`not_recorded`,notRecorded:`not_recorded`,options:[{v:`within_gauge_length`,label:`Within gauge length`},{v:`at_gauge_length_end`,label:`At gauge length end`},{v:`fixture_edge_or_tab_edge`,label:`Fixture edge or tab edge`},{v:`grip_end_block`,label:`Grip/end block`},{v:`end_tab`,label:`End tab`},{v:`specimen_end`,label:`Specimen end`},{v:`outside_gauge_length`,label:`Outside gauge length`},{v:`unknown`,label:`Unknown`},{v:`not_recorded`,label:`Not recorded`}]}),A({id:`invalid_specimen_reason`,label:`Invalid specimen reason`,type:`enum`,importance:`optional`,default:`none`,options:[{v:`none`,label:`None`},{v:`bending_non_compliance`,label:`Bending non-compliance`},{v:`grip_end_block_failure`,label:`Grip/end block failure`},{v:`end_tab_failure`,label:`End tab failure`},{v:`specimen_end_failure`,label:`Specimen end failure`},{v:`operator_marked_invalid`,label:`Operator marked invalid`},{v:`data_quality_issue`,label:`Data quality issue`},{v:`other`,label:`Other`}]}),A({id:`invalid_specimen_reason_other`,label:`Other invalid specimen reason`,type:`string`,importance:`optional`,visibleWhen:{field:`invalid_specimen_reason`,equals:`other`},requiredWhen:{field:`invalid_specimen_reason`,equals:`other`},desc:`Required when Invalid specimen reason is Other.`}),A({id:`visible_buckling_or_bending_observation`,label:`Visible buckling / bending observation`,type:`enum`,importance:`optional`,default:`not_recorded`,notRecorded:`not_recorded`,options:[{v:`none_observed`,label:`None observed`},{v:`visible_bending`,label:`Visible bending`},{v:`suspected_euler_buckling`,label:`Suspected Euler buckling`},{v:`specimen_slip_or_fixture_issue`,label:`Specimen slip or fixture issue`},{v:`other`,label:`Other`},{v:`not_recorded`,label:`Not recorded`}]}),A({id:`visible_buckling_or_bending_observation_other`,label:`Other buckling / bending observation`,type:`string`,importance:`optional`,visibleWhen:{field:`visible_buckling_or_bending_observation`,equals:`other`},requiredWhen:{field:`visible_buckling_or_bending_observation`,equals:`other`}}),A({id:`failure_analysis_notes`,label:`Failure analysis notes`,type:`string`,importance:`optional`}),A({id:`failure_image_reference`,label:`Failure image reference`,type:`string`,importance:`optional`,desc:`Should link to the image-evidence failure view where available.`}),A({id:`validity`,label:`Validity`,type:`enum`,importance:`recommended`,default:`accepted`,options:[{v:`accepted`,label:`Accepted`},{v:`rejected`,label:`Rejected`},{v:`requires_review`,label:`Requires review`},{v:`unknown`,label:`Unknown`}]}),A({id:`requires_review`,label:`Requires review`,type:`bool`,importance:`optional`}),A({id:`rejection_reason`,label:`Rejection reason`,type:`string`,importance:`optional`});var te=[{id:`overview`,label:`Overview`,fields:[`sample_type`,`treatment`,`material_label`]},{id:`test_identification`,label:`Test Identification`,fields:[`test_id`,`report_operator`,`loading_method`,`loading_method_other`,`specimen_type`,`specimen_type_other`]},{id:`material_identification`,label:`Material Identification`,fields:[`material_type`,`matrix_type`,`reinforcement_type`,`manufacturer`,`manufacturer_code`,`material_source`,`material_form`,`previous_history`]},{id:`specimen_preparation`,label:`Specimen Preparation`,fields:[`cutting_direction`,`fibre_orientation`,`layup`,`preparation_method`,`end_tabs`,`surface_preparation`,`specimen_preparation_notes`]},{id:`loading_fixture`,label:`Loading Fixture`,fields:[`fixture_type`,`fixture_standard_reference`,`fixture_manufacturer_design`,`alignment_procedure`,`fixture_notes`]},{id:`test_conditions`,label:`Test Conditions`,fields:[`conditioning_standard`,`temperature`,`humidity`,`conditioning_time`,`test_environment`,`speed_of_testing`]},{id:`measurement_method`,label:`Measurement Method`,fields:[`strain_measurement_method`,`measurement_location`,`acquisition_system`,`sampling_rate`,`measurement_notes`]},{id:`deviations_remarks`,label:`Deviations / Remarks`,fields:[`deviations_from_standard`,`remarks`]}].map(e=>({...e,fields:e.fields.map(e=>k[e])})),j=[{id:`specimen_geometry`,label:`Specimen Geometry`,fields:[`specimen_name`,`sample_id`,`width`,`thickness`,`gauge_length`,`distance_between_end_tabs`,`tab_length`,`tab_thickness`]},{id:`run_acquisition_inputs`,label:`Run Acquisition Inputs`,fields:[`operator`,`instrument_model`,`instrument_id`,`instrument_location`,`load_cell`,`test_speed`,`test_date`,`source_software`]},{id:`channel_preamble_summary`,label:`Channel / Preamble Summary`,fields:[`run_notes`]},{id:`user_validity_failure_observation`,label:`User Validity / Failure Observation`,fields:[`primary_failure_mode`,`failure_location`,`invalid_specimen_reason`,`invalid_specimen_reason_other`,`visible_buckling_or_bending_observation`,`visible_buckling_or_bending_observation_other`,`failure_analysis_notes`,`failure_image_reference`,`validity`,`requires_review`,`rejection_reason`]}].map(e=>({...e,fields:e.fields.map(e=>k[e])})),M=k,N=[{id:`load`,label:`Load`,required:!0,repeatable:!1,units:[`N`,`kN`],std:`N`,dim:`force`},{id:`extension`,label:`Extension`,repeatable:!1,units:[`mm`,`cm`,`m`],std:`mm`,dim:`length`},{id:`displacement`,label:`Displacement`,repeatable:!1,units:[`mm`,`cm`,`m`],std:`mm`,dim:`length`},{id:`strain`,label:`Strain`,repeatable:!0,units:[`usn`,`microstrain`,`mm/mm`],std:`mm/mm`,dim:`strain`},{id:`stress`,label:`Stress`,repeatable:!0,units:[`MPa`,`N/mm^2`],std:`MPa`,dim:`stress`},{id:`time`,label:`Time`,repeatable:!1,units:[`s`,`ms`,`us`],std:`s`,dim:`time`},{id:`ignore`,label:`Ignore — not exported`,repeatable:!0,units:[`—`],std:`—`}],ne={};N.forEach(e=>ne[e.id]=e);var re=[{id:`front`,label:`Front image`},{id:`side`,label:`Side image`},{id:`top`,label:`Top image`},{id:`failure`,label:`Failure image`},{id:`scale_reference`,label:`Scale reference`},{id:`other`,label:`Other image`}],P=[`dataset`,`run`,`schema_mapping`,`calibration`,`equipment_evidence`,`other`];function F(e){return e!=null&&String(e).trim()!==``}function I(e,t){return F(t)&&!(e.notRecorded&&t===e.notRecorded)}function L(e,t){return e.visibleWhen?(t[e.visibleWhen.field]||``)===e.visibleWhen.equals:!0}function R(e,t){return e.hardRequired||e.requiredWhen&&(t[e.requiredWhen.field]||``)===e.requiredWhen.equals?`required`:e.importance===`required_for_accepted_runs`?(t.validity||M.validity.default)===`accepted`?`required`:`optional`:e.importance===`required`?`report`:e.importance===`recommended`?`recommended`:`optional`}function z(e,t,n){return e.filter(e=>{if(!L(e,t))return!1;let r=R(e,t);return n===`essential`?r===`required`||r===`report`:n===`core`?r!==`optional`||F(t[e.id]):!0})}var ie=[/^\d{4}-\d{2}-\d{2}$/,/^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$/];function ae(e,t){if(!F(t))return null;if(e.type===`float`){if(String(t).includes(`,`))return`Use “.” as decimal separator`;let n=Number(t);if(isNaN(n))return`Not a number`;if(e.min!==void 0&&n<e.min)return`Must be ≥ `+e.min;if(e.min===0&&n===0)return`Must be > 0`}return e.type===`date`&&!ie.some(e=>e.test(String(t).trim()))?`Unrecognized date — use yyyy-MM-dd`:e.pattern&&!oe(e.pattern,String(t).trim())?`Contains characters outside [\\w .,+/()#-]`:null}function oe(e,t){if(e.test)return e.test(t);try{return new RegExp(e).test(t)}catch{return!0}}function se(e,t){let n=0,r=0,i=0;return e.forEach(e=>{let a=t[e.id],o=R(e,t);I(e,a)&&n++,(o===`required`||o===`report`)&&(r++,I(e,a)&&!ae(e,a)&&i++)}),{filled:n,total:e.length,reqTotal:r,reqFilled:i}}function ce(e){return(e.channels||[]).filter(e=>e.status===`unmatched`||e.status===`ambiguous`)}function le(e){return(e.channels||[]).some(e=>e.family===`load`&&(e.status===`matched`||e.status===`manual`))}function B(e,t){let n=[],r=[],i=[];j.forEach(t=>t.fields.forEach(t=>{if(!L(t,e.values))return;let a=e.values[t.id],o=R(t,e.values),s=ae(t,a);s?r.push({field:t,err:s}):o===`required`&&!I(t,a)?n.push(t):o===`report`&&!I(t,a)&&i.push(t)}));let a=ce(e).length,o=le(e),s=te.every(e=>e.fields.every(e=>L(e,t.values)?R(e,t.values)!==`required`||I(e,t.values[e.id]):!0));return{missing:n,errors:r,reportGaps:i,chIssues:a,loadOk:o,datasetOk:s,ready:r.length===0&&n.length===0&&a===0&&o&&s}}function ue(e){if(e.backendValidation&&e.backendValidation.source===`backend`)return de(e.backendValidation);let t=[],n=[],r=[],i=[],a=[],o=e.dataset;te.forEach(e=>e.fields.forEach(i=>{if(!L(i,o.values))return;let a=o.values[i.id],s=R(i,o.values),c=ae(i,a),l={type:`dataset`,sectionId:e.id,fieldId:i.id};c?t.push({text:`Dataset · `+i.label+` — `+c,action:`jump`,target:l}):s===`required`&&!I(i,a)?n.push({text:`Dataset · `+i.label+` is required`,detail:i.desc,action:`jump`,target:l}):s===`report`&&!I(i,a)&&r.push({text:`Dataset · `+i.label+` — required for the report`,detail:`Export proceeds; the report will carry a gap.`,action:`jump`,target:l})}));let s=0,c=0;e.groups.forEach(e=>e.runs.forEach(r=>{c++;let i=B(r,o);i.ready&&s++,i.errors.forEach(({field:n,err:i})=>t.push({text:r.id+` · `+n.label+` — `+i,action:`jump`,target:{type:`run`,groupId:e.id,runId:r.id,sectionId:fe(n.id,`run`),fieldId:n.id}})),i.missing.forEach(t=>n.push({text:r.id+` · `+t.label+(t.importance===`required_for_accepted_runs`?` — required while validity is “Accepted”`:` is required`),action:`jump`,target:{type:`run`,groupId:e.id,runId:r.id,sectionId:fe(t.id,`run`),fieldId:t.id}})),ce(r).forEach(n=>t.push({text:r.id+` · header “`+n.header+`” `+(n.status===`ambiguous`?`is ambiguous (`+(n.candidates||[]).length+` candidates)`:`has no channel family`),action:`channels`,target:{groupId:e.id,runId:r.id}})),le(r)||t.push({text:r.id+` · no Load channel assigned — Load is the one required data column`,action:`channels`,target:{groupId:e.id,runId:r.id}})}));let l=e.groups.reduce((e,t)=>e+t.runs.filter(e=>ce(e).length===0).length,0);return i.push({text:`Schema `+T.id+` v`+T.version+` — field types, enums and value patterns`,detail:`All filled values type-check against the schema.`}),i.push({text:`Channel families on `+l+`/`+c+` runs resolve to the data_table layout`}),i.push({text:`Sidecar pairing — `+e.sourcePairs.length+`/`+e.sourcePairs.length+` CSVs paired 1:1 by base name`}),i.push({text:`Units conform to `+T.unitSystem+` accepted units; conversion rules available`}),a.push({text:`Raw CSV numeric plausibility (curve shapes, outliers)`,detail:`Out of scope for enrichment — checked downstream by the method pipeline.`}),a.push({text:`Image evidence completeness`,detail:`image_evidence.required = false in this schema.`}),{errors:t,missing:n,reportItems:r,passed:i,skipped:a,readyRuns:s,totalRuns:c}}function de(e){let t=Array.isArray(e.issues)?e.issues:[],n=e=>{let t=e.scope===`run`?`run`:`dataset`,n=e.field||e.target&&e.target.fieldId||null,r=e.target||{type:t,groupId:e.group_id,runId:e.run_id,fieldId:n};return n&&!r.sectionId&&(r.sectionId=fe(n,t)),{text:e.text||e.message||`Backend validation issue`,detail:e.detail,action:e.category===`data_table`?`channels`:`jump`,target:r}},r=[],i=[],a=[];return t.forEach(e=>{let t=n(e);e.severity===`warning`?a.push(t):e.code===`required`?i.push(t):r.push(t)}),{errors:r,missing:i,reportItems:a,passed:e.passed||[],skipped:e.skipped||[],readyRuns:e.ready_runs||0,totalRuns:e.total_runs||0}}function fe(e,t){let n=(t===`run`?j:te).find(t=>t.fields.some(t=>t.id===e));return n?n.id:null}function pe(e,t){if(!e.options)return t;let n=e.options.find(e=>e.v===t);return n?n.label:t}function me(e){return e.replace(`run_0`,`r`).replace(`run_`,`r`)}function V(e){return e&&window.FAMILY[e]&&window.FAMILY[e].label||e||null}Object.assign(window,{SCHEMA_META:T,UNIT_FACTORS:E,convertUnit:D,conversionFactorLabel:O,DATASET_SECTIONS:te,RUN_SECTIONS:j,ALL_FIELDS:M,CHANNEL_FAMILIES:N,FAMILY:ne,IMAGE_VIEWS:re,SUPPLEMENTAL_SCOPES:P,isFilled:F,isRecorded:I,isVisible:L,effLevel:R,visibleFields:z,fieldError:ae,sectionCounts:se,channelIssues:ce,hasLoadChannel:le,runReadiness:B,buildValidationReport:ue,sectionOf:fe,enumLabel:pe,runShort:me,familyLabel:V,installBackendSchemaForm:U});var he=[{id:`compression-0.3.0`,label:`Compression`,schema:`mechanical.compression`,version:`0.3.0`,conf:85,detected:!0,hint:`Preamble tokens + channel families (load, displacement, strain) match the compression data_table; sidecars declare a compressive test.`},{id:`compression-0.2.0`,label:`Compression`,schema:`mechanical.compression`,version:`0.2.0`,conf:61,hint:`Previous version of the same schema — migration path to 0.3.0 exists (compatible_prior_versions).`},{id:`flexural-0.1.0`,label:`Flexural`,schema:`mechanical.flexural`,version:`0.1.0`,conf:34,hint:`Channel layout partially compatible; no flexure-specific tokens found in preambles.`},{id:`tensile-0.1.0`,label:`Tensile`,schema:`mechanical.tensile`,version:`0.1.0`,conf:28,hint:`Load/strain channels match, but sidecar test mode contradicts tension.`},{id:`generic-0.1.0`,label:`Generic stress–strain`,schema:`mechanical.generic_stress_strain`,version:`0.1.0`,conf:22,hint:`Always-available fallback — accepts any stress/strain layout, weakest validation.`}];function H(e){return(Array.isArray(e?.schemas)?e.schemas:[]).filter(e=>e&&e.id&&e.label&&e.version).map(e=>({id:e.id,label:e.label,schema:e.schema||e.schema_id||e.id,version:e.version||e.schema_version||``,conf:Number(e.conf||0),detected:!!e.detected,hint:e.hint||`Loaded from backend schema registry.`,schemaForm:e.schemaForm||e.schema_form||null}))}function U(e){if(!e||typeof e!=`object`)return!1;let t=[...Object.values(e.fieldsById||{}),...Array.isArray(e.datasetFields)?e.datasetFields:[],...Array.isArray(e.runFields)?e.runFields:[]],n=new Map;return t.forEach(e=>{let t=ge(e);t?.id&&n.set(t.id,t)}),n.size?(Object.keys(k).forEach(e=>delete k[e]),n.forEach((e,t)=>{k[t]=e}),_e(te,e.datasetSections||e.dataset_sections,`dataset`),_e(j,e.runSections||e.run_sections,`run`),ve(e.channelFamilies||e.channel_families),ye(E,e.unitFactors||e.unit_factors||{}),Array.isArray(e.imageViews||e.image_views)&&re.splice(0,re.length,...(e.imageViews||e.image_views).map(e=>({id:e.id,label:e.label||e.id}))),Array.isArray(e.supplementalScopes||e.supplemental_scopes)&&P.splice(0,P.length,...e.supplementalScopes||e.supplemental_scopes),Object.assign(T,{id:e.schema||e.schemaId||T.id,version:e.version||T.version,label:e.label||T.label,unitSystem:e.unitSystem||e.unit_system||T.unitSystem,source:e.source||`backend schema registry`}),!0):!1}function ge(e){if(!e||typeof e!=`object`)return null;let t=e.id||e.fieldId||e.field_id;if(!t)return null;let n=e.type||`string`,r=Array.isArray(e.options)?e.options.map(e=>({v:e.v??e.value,label:e.label||String(e.v??e.value??``),deviation:!!e.deviation})):Array.isArray(e.allowedValues||e.allowed_values)?(e.allowedValues||e.allowed_values).map(t=>({v:t,label:e.displayLabels?.[t]||e.display_labels?.[t]||String(t).replace(/[_-]/g,` `),deviation:Array.isArray(e.deviationValues||e.deviation_values)&&(e.deviationValues||e.deviation_values).includes(t)})):[],i=e.units||e.acceptedUnits||e.accepted_units,a=e.visibleWhen||e.visible_when,o=e.requiredWhen||e.required_when;return{...e,id:t,label:e.label||t,type:n,hardRequired:!!(e.hardRequired??e.hard_required??e.required),importance:e.importance||e.reportImportance||e.report_importance||(e.required?`required`:`optional`),options:r,units:Array.isArray(i)&&i.length?i:void 0,stdUnit:e.stdUnit||e.standardUnit||e.standard_unit||(Array.isArray(i)?i[0]:void 0),dim:e.dim||e.unitDimension||e.unit_dimension,desc:e.desc||e.description||``,ph:e.ph||e.placeholder||``,min:e.min??e.validation?.min,max:e.max??e.validation?.max,pattern:e.pattern||e.validation?.pattern,visibleWhen:W(a),requiredWhen:W(o),unitInline:!!(e.unitInline??e.unit_inline),notRecorded:e.notRecorded||e.not_recorded}}function W(e){if(!(!e||typeof e!=`object`))return{field:e.field||e.fieldId||e.field_id,equals:e.equals??e.value}}function _e(e,t,n){let r=Array.isArray(t)?t.map(e=>{let t=Array.isArray(e.fields)?e.fields.map(e=>k[e.id||e.fieldId||e.field_id]||ge(e)).filter(Boolean):Array.isArray(e.fieldIds||e.field_ids)?(e.fieldIds||e.field_ids).map(e=>k[e]).filter(Boolean):[];return{id:e.id||e.key||e.label,label:e.label||e.id||`Metadata`,scope:e.scope||n,fields:t}}).filter(e=>e.id&&e.fields.length):[];r.length&&e.splice(0,e.length,...r)}function ve(e){if(!Array.isArray(e)||!e.length)return;let t=e.map(e=>({id:e.id||e.family,label:e.label||e.id||e.family,required:!!e.required,repeatable:!!e.repeatable,units:e.units||e.accepted_units||[],std:e.std||e.standard_unit,dim:e.dim||e.unit_dimension})).filter(e=>e.id);t.length&&(N.splice(0,N.length,...t),ye(ne,{}),N.forEach(e=>{ne[e.id]=e}))}function ye(e,t){Object.keys(e).forEach(t=>delete e[t]),Object.entries(t||{}).forEach(([t,n])=>{e[t]=n&&typeof n==`object`&&!Array.isArray(n)?{...n}:n})}Object.assign(window,{SCHEMA_CANDIDATES:he,installBackendSchemaForm:U});var{useState:be,useEffect:xe,useRef:Se}=i.default;function Ce({editor:e,density:t,runIdx:n,runCount:r,canUndo:i,canRedo:a,undoLabel:o,redoLabel:s,lastExportPath:c}){let l=e;return[{id:`file`,label:`File`,items:[{id:`open-files`,label:`Open files (drag & drop)…`,kbd:`Ctrl+O`},{id:`open-folder`,label:`Open source folder…`,kbd:`Ctrl+Shift+O`},{id:`open-package`,label:`Open MTDP package…`},{sep:!0},{id:`recent-sessions`,label:`Recent sessions (autosaved)…`},{sep:!0},{id:`export`,label:`Export MTDP package…`,kbd:`Ctrl+Shift+E`,disabled:!l},{id:`export-all-ready`,label:`Export all ready groups…`,disabled:!l},{id:`open-export-analysis`,label:`Open exported package in Analysis…`,disabled:!c},{sep:!0},{id:`close-package`,label:`Close package`,disabled:!l}]},{id:`edit`,label:`Edit`,items:[{id:`undo`,label:i&&o?`Undo `+o:`Undo`,kbd:`Ctrl+Z`,disabled:!l||!i},{id:`redo`,label:a&&s?`Redo `+s:`Redo`,kbd:`Ctrl+Shift+Z`,disabled:!l||!a},{sep:!0},{id:`copy-prev`,label:`Copy values from previous run`,kbd:`Ctrl+D`,disabled:!l||n<=0}]},{id:`view`,label:`View`,items:[{id:`density-essential`,label:`Required fields only`,check:t===`essential`,disabled:!l},{id:`density-core`,label:`Required + recommended`,check:t===`core`,disabled:!l},{id:`density-all`,label:`All fields`,check:t===`all`,disabled:!l},{sep:!0},{id:`open-grid`,label:`⊞ Grid — all runs`,disabled:!l},{id:`source-files`,label:`Source files`,disabled:!l}]},{id:`group`,label:`Group`,items:[{id:`propose-groups`,label:`Propose groups…`,disabled:!l},{id:`new-group`,label:`New group`,disabled:!l},{id:`rename-group`,label:`Rename group`,disabled:!l,kbd:`✎ or dbl-click`},{id:`delete-group`,label:`Delete group`,disabled:!l}]},{id:`run`,label:`Run`,items:[{id:`prev-run`,label:`Previous run`,kbd:`Ctrl+Up`,disabled:!l||n<=0},{id:`next-run`,label:`Next run`,kbd:`Ctrl+Down`,disabled:!l||n<0||n>=r-1},{sep:!0},{id:`channels`,label:`Channel assignments…`,disabled:!l},{id:`evidence`,label:`Manage run image evidence…`,disabled:!l}]},{id:`tools`,label:`Tools`,items:[{id:`validate`,label:`Validate — issues drawer`,kbd:`Ctrl+R`,disabled:!l},{id:`rematch-yaml`,label:`Re-match YAML sidecars…`,disabled:!l},{id:`supplemental`,label:`Manage supplemental files…`,disabled:!l},{sep:!0},{id:`change-schema`,label:`Change detected schema…`,disabled:!l}]},{id:`help`,label:`Help`,items:[{id:`schema-ref`,label:`Schema reference — Compression v0.3.0`},{id:`about`,label:`About Dataset Packaging`}]}]}function we({stage:e,bundle:t,density:n,runIdx:r,runCount:i,canUndo:o,canRedo:s,undoLabel:c,redoLabel:l,lastExportPath:u,onAction:d}){let[f,p]=be(null),m=Se(null),h=Se(!1),g=e===`editor`&&!!t,_=Ce({editor:g,density:n,runIdx:r,runCount:i,canUndo:o,canRedo:s,undoLabel:c,redoLabel:l,lastExportPath:u}),v=!!window.desktopApi;xe(()=>{if(!f)return;let e=e=>{m.current&&!m.current.contains(e.target)&&p(null)};return document.addEventListener(`mousedown`,e),()=>document.removeEventListener(`mousedown`,e)},[f]),xe(()=>{if(!f)return;let e=e=>{e.key===`Escape`&&(e.preventDefault(),p(null))};return document.addEventListener(`keydown`,e,!0),()=>document.removeEventListener(`keydown`,e,!0)},[f]);let y=e=>{p(null),d(e)};return(0,a.jsxs)(`div`,{className:`menubar menubar--desktop`,ref:m,onDoubleClick:e=>{v&&(e.preventDefault(),!e.target.closest(`button,.menu__pop,.menu__btn,.menubar__schema,.desktop-window-control`)&&window.desktopApi?.toggleMaximizeWindow?.())},children:[(0,a.jsx)(`span`,{className:`menubar__title`,"data-window-drag":`true`,children:`Dataset Packaging`}),(0,a.jsx)(`nav`,{className:`menubar__menus`,children:_.map(e=>(0,a.jsxs)(`div`,{className:`menu`,children:[(0,a.jsx)(`button`,{className:`menu__btn`+(f===e.id?` is-open`:``),onMouseDown:t=>{t.preventDefault(),t.stopPropagation(),h.current=!0,p(t=>t===e.id?null:e.id)},onClick:t=>{if(t.preventDefault(),t.stopPropagation(),h.current){h.current=!1;return}p(t=>t===e.id?null:e.id)},onMouseEnter:()=>{f&&f!==e.id&&p(e.id)},children:e.label}),f===e.id&&(0,a.jsx)(`div`,{className:`menu__pop`,onMouseDown:e=>e.stopPropagation(),onClick:e=>e.stopPropagation(),children:e.items.map((e,t)=>e.sep?(0,a.jsx)(`div`,{className:`menu__sep`},`sep`+t):(0,a.jsxs)(`button`,{className:`menu__item`,disabled:!!e.disabled,onClick:()=>y(e.id),children:[(0,a.jsx)(`span`,{className:`chk`,children:e.check?`✓`:``}),(0,a.jsx)(`span`,{className:`lab`,children:e.label}),e.kbd&&(0,a.jsx)(`span`,{className:`kbd`,children:e.kbd})]},e.id))})]},e.id))}),(0,a.jsx)(`div`,{className:`menubar__dragzone`,"data-window-drag":`true`,"aria-hidden":`true`}),g&&(0,a.jsxs)(`button`,{className:`menubar__schema`,title:`Click to change the detected schema`,onClick:()=>y(`change-schema`),children:[t.schemaOverridden?`Schema (manual): `:`Detected schema: `,(0,a.jsxs)(`b`,{children:[t.schemaLabel,` · v`,t.schemaVersion]}),t.schemaOverridden?(0,a.jsx)(`span`,{className:`menubar__override`,children:`override`}):(0,a.jsxs)(`span`,{className:`menubar__conf`,children:[t.detectConfidence,`%`]})]}),(0,a.jsx)(w,{className:`menubar__windowctrls`})]})}Object.assign(window,{MenuBar:we});var{useState:Te}=i.default;function Ee({kind:e,title:t,sub:n,width:r,children:i,foot:o,onClose:s}){return(0,a.jsx)(`div`,{className:`modalscrim`,onMouseDown:e=>{e.target===e.currentTarget&&s()},children:(0,a.jsxs)(`div`,{className:`modal modal--`+(r||`mid`),children:[(0,a.jsxs)(`div`,{className:`modal__hd`,children:[(0,a.jsxs)(`div`,{children:[(0,a.jsx)(`div`,{className:`modal__kind`,children:e}),(0,a.jsx)(`h2`,{className:`modal__title`,children:t}),n&&(0,a.jsx)(`p`,{className:`modal__sub`,children:n})]}),(0,a.jsx)(`button`,{className:`modal__x`,onClick:s,title:`Close`,children:`✕`})]}),(0,a.jsx)(`div`,{className:`modal__body`,children:i}),o&&(0,a.jsx)(`div`,{className:`modal__foot`,children:o})]})})}function De({bundle:e,groupId:t,runId:n,onAssign:r,onSelectRun:i,onClose:o}){let s=e.groups.find(e=>e.id===t)||e.groups[0],c=s.runs.find(e=>e.id===n)||s.runs[0],l=window.channelIssues(c),u=e.groups.flatMap(e=>e.runs.map(t=>({g:e,r:t}))).find(({r:e})=>e.id!==c.id&&window.channelIssues(e).length>0),d=(e,t)=>c.channels.some((n,r)=>r!==t&&n.family===e&&!window.FAMILY[e]?.repeatable),f=(e,t)=>{let n=t?window.FAMILY[t]:null,i=c.channels[e];r(s.id,c.id,e,{family:t||null,unit:n?i.unit&&n.units.includes(i.unit)?i.unit:n.std:i.unit,status:t?`manual`:i.candidates?`ambiguous`:`unmatched`})},p=(e,t)=>r(s.id,c.id,e,{unit:t});return(0,a.jsx)(Ee,{kind:`CHANNEL ASSIGNMENTS`,width:`wide`,onClose:o,title:`Parsed channels — `+c.id,sub:(0,a.jsxs)(`span`,{children:[`Headers in `,(0,a.jsx)(`span`,{className:`mono`,children:c.fileLabel}),` → schema channel families (`,(0,a.jsx)(`span`,{className:`mono`,style:{fontSize:`11px`},children:`data_table.columns`}),`). Load is required; Strain and Stress are repeatable.`]}),foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`modal__footnote `+(l.length?`modal__footnote--warn`:`modal__footnote--ok`),children:l.length?`⚠ `+l.length+` header`+(l.length>1?`s`:``)+` unresolved — this run cannot export`:window.hasLoadChannel(c)?`✓ All headers assigned — Load present`:`⚠ No Load channel — Load is required`}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[u&&(0,a.jsxs)(`button`,{className:`btn btn--sm`,onClick:()=>i(u.g.id,u.r.id),children:[`Next unresolved run · `,u.r.id,` →`]}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:o,children:`Done`})]})]}),children:(0,a.jsxs)(`table`,{className:`chtable`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`Source header`}),(0,a.jsx)(`th`,{children:`Channel family`}),(0,a.jsx)(`th`,{children:`Unit`}),(0,a.jsx)(`th`,{style:{textAlign:`right`},children:`Status`})]})}),(0,a.jsx)(`tbody`,{children:c.channels.map((e,t)=>{let n=e.status===`unmatched`||e.status===`ambiguous`,r=e.family?window.FAMILY[e.family]:null,i=e.candidates?[...e.candidates,...window.CHANNEL_FAMILIES.map(e=>e.id).filter(t=>!e.candidates.includes(t))]:window.CHANNEL_FAMILIES.map(e=>e.id);return(0,a.jsxs)(`tr`,{className:n?e.status===`ambiguous`?`is-amb`:`is-issue`:``,children:[(0,a.jsxs)(`td`,{children:[(0,a.jsx)(`span`,{className:`hdr`,children:e.header}),e.note&&(0,a.jsx)(`span`,{className:`note`,children:e.note})]}),(0,a.jsx)(`td`,{children:(0,a.jsxs)(`select`,{className:e.family?``:`is-empty`,value:e.family||``,onChange:e=>f(t,e.target.value),children:[(0,a.jsx)(`option`,{value:``,children:e.candidates?`— choose (`+e.candidates.length+` candidates) —`:`— assign family —`}),i.map(n=>{let r=window.FAMILY[n]||{id:n,label:n,required:!1},i=d(n,t)&&n!==e.family;return(0,a.jsx)(`option`,{value:n,disabled:i,children:r.label+(r.required?` (required)`:``)+(e.candidates&&e.candidates.includes(n)?` · candidate`:``)+(i?` · already assigned`:``)},n)})]})}),(0,a.jsx)(`td`,{children:(0,a.jsxs)(`select`,{className:`unitpick`+(e.unit?``:` is-empty`),value:e.unit||``,disabled:!e.family,onChange:e=>p(t,e.target.value),children:[!e.unit&&(0,a.jsx)(`option`,{value:``,children:`—`}),(r?r.units:e.unit?[e.unit]:[]).map(e=>(0,a.jsx)(`option`,{value:e,children:e},e))]})}),(0,a.jsxs)(`td`,{style:{textAlign:`right`},children:[(0,a.jsx)(`span`,{className:`chstat chstat--`+e.status,children:e.status===`ambiguous`?`? ambiguous`:e.status}),e.via&&e.status===`matched`&&(0,a.jsx)(`span`,{className:`via`,children:e.via})]})]},e.header)})})]})})}function Oe(e,t){let n=window.runReadiness(e,t),r=[];n.errors.length&&r.push({t:n.errors.length+` value error`+(n.errors.length>1?`s`:``)+` — `+n.errors.map(e=>e.field.label.toLowerCase()).join(`, `),act:`jump`,f:n.errors[0].field}),n.missing.length&&r.push({t:n.missing.length+` required missing — `+n.missing.map(e=>e.label.toLowerCase()).join(`, `),act:`jump`,f:n.missing[0]});let i=window.channelIssues(e).length;return i&&r.push({t:i+` channel header`+(i>1?`s`:``)+` unresolved`,act:`channels`}),window.hasLoadChannel(e)||r.push({t:`no Load channel`,act:`channels`}),r}function ke({bundle:e,onExport:t,onJump:n,onOpenChannels:r,onClose:i}){let[o,s]=Te(`~/Documents/MTDP exports`),[c,l]=Te(e.name+`.mtdp`),u=window.buildValidationReport(e),d=e.groups.flatMap(e=>e.runs.map(t=>({g:e,r:t}))),f=d.filter(({r:t})=>window.runReadiness(t,e.dataset).ready);return(0,a.jsxs)(Ee,{kind:`EXPORT`,width:`wide`,onClose:i,title:`Export MTDP package — run manifest`,sub:`Every run is listed. Nothing is skipped silently — non-ready runs are excluded with their reason shown.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`span`,{className:`modal__footnote`,children:[(0,a.jsxs)(`b`,{children:[f.length,` of `,d.length]}),` runs will be included`,f.length<d.length&&(0,a.jsxs)(a.Fragment,{children:[` · `,d.length-f.length,` skipped, listed above`]})]}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:i,children:`Cancel`}),(0,a.jsxs)(`button`,{className:`btn btn--primary btn--sm`,disabled:f.length===0,onClick:()=>t({initialDir:o,defaultName:c,included:f.length,total:d.length}),children:[`⬇ Export `,f.length,` of `,d.length,` runs`]})]})]}),children:[(0,a.jsxs)(`table`,{className:`mantable`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{}),(0,a.jsx)(`th`,{children:`Run`}),(0,a.jsx)(`th`,{children:`Specimen`}),(0,a.jsx)(`th`,{children:`Status`})]})}),(0,a.jsx)(`tbody`,{children:d.map(({g:t,r:i})=>{let o=window.runReadiness(i,e.dataset).ready,s=o?[]:Oe(i,e.dataset);return(0,a.jsxs)(`tr`,{className:o?``:`is-off`,children:[(0,a.jsx)(`td`,{className:`cb`,children:o?`☑`:`☐`}),(0,a.jsx)(`td`,{className:`runid mono`,children:i.id}),(0,a.jsx)(`td`,{className:`mono spec`,children:i.values.specimen_name}),(0,a.jsx)(`td`,{className:`reason`,children:o?(0,a.jsx)(`span`,{className:`okt`,children:`✓ ready`}):s.map((e,o)=>(0,a.jsxs)(`span`,{className:`skipline`,children:[(0,a.jsx)(`b`,{children:e.t}),` `,e.act===`jump`?(0,a.jsx)(`button`,{className:`go`,onClick:()=>n({type:`run`,groupId:t.id,runId:i.id,sectionId:window.sectionOf(e.f.id,`run`),fieldId:e.f.id}),children:`fix →`}):(0,a.jsx)(`button`,{className:`go`,onClick:()=>r({groupId:t.id,runId:i.id}),children:`open channels →`})]},o))})]},i.id)})})]}),u.reportItems.length>0&&(0,a.jsxs)(`div`,{className:`dlgnote dlgnote--warn`,style:{marginTop:`12px`},children:[`⚠ `,(0,a.jsxs)(`b`,{children:[u.reportItems.length,` report gap`,u.reportItems.length>1?`s`:``]}),` — `,u.reportItems.map(e=>e.text.replace(`Dataset · `,``).replace(` — required for the report`,``)).join(` · `),`. Export proceeds; the formal report will show these as missing.`]}),(0,a.jsxs)(`div`,{className:`exprow`,style:{marginTop:`14px`},children:[(0,a.jsx)(`label`,{children:`Save to`}),(0,a.jsxs)(`div`,{className:`pathrow`,children:[(0,a.jsx)(`input`,{className:`inp mono`,style:{fontSize:`12.5px`},value:o,onChange:e=>s(e.target.value)}),(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:()=>s(`~/Desktop`),children:`Choose…`})]})]}),(0,a.jsxs)(`div`,{className:`exprow`,children:[(0,a.jsx)(`label`,{children:`File name`}),(0,a.jsx)(`input`,{className:`inp mono`,style:{fontSize:`12.5px`},value:c,onChange:e=>l(e.target.value)})]})]})}function Ae({proposals:e,onApply:t,onClose:n}){let r=e&&e.length?e:[],o=r[0]?.id||``,[s,c]=Te(o);return i.useEffect(()=>{r.some(e=>e.id===s)||c(o)},[o,r,s]),(0,a.jsxs)(Ee,{kind:`GROUPING`,width:`mid`,onClose:n,title:`Proposed sample groups`,sub:`Ranked by confidence from the backend dataset_grouping engine. Applying replaces the current grouping while keeping run data attached.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`modal__footnote`,children:`You can drag runs between groups afterwards.`}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:n,children:`Cancel`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,disabled:!s,onClick:()=>t(s),children:`Apply proposal`})]})]}),children:[r.length===0&&(0,a.jsx)(`div`,{className:`dlgnote dlgnote--warn`,children:`No backend grouping proposal is available for the current session.`}),r.map(e=>{let t=Number(e.conf??e.confidence??0),n=(e.groups||[]).map(e=>e.name+` (`+(e.run_count||0)+`)`).join(` · `);return(0,a.jsxs)(`label`,{className:`proposal`+(s===e.id?` is-picked`:``),children:[(0,a.jsx)(`input`,{type:`radio`,name:`proposal`,checked:s===e.id,onChange:()=>c(e.id)}),(0,a.jsxs)(`span`,{className:`pbody`,children:[(0,a.jsxs)(`span`,{className:`t`,children:[e.title,(0,a.jsxs)(`span`,{className:`conf`,children:[(0,a.jsx)(`span`,{className:`conf__track`,children:(0,a.jsx)(`span`,{className:`conf__fill conf__fill--`+(t>=80?`ok`:`warn`),style:{width:t+`%`}})}),(0,a.jsxs)(`span`,{className:`conf__num`,children:[t,`%`]})]})]}),(0,a.jsx)(`span`,{className:`d`,children:e.description||e.desc||`Backend-authored grouping proposal.`}),n&&(0,a.jsx)(`span`,{className:`d`,children:(0,a.jsx)(`span`,{className:`mono`,style:{fontSize:`11px`},children:n})})]})]},e.id)})]})}function je({bundle:e,candidates:t,onPick:n,onClose:r}){let[i,o]=Te(e.schemaId),s=t&&t.length?t:window.SCHEMA_CANDIDATES;return(0,a.jsx)(Ee,{kind:`SCHEMA`,width:`mid`,onClose:r,title:`Change detected schema`,sub:`Candidates from the schema library. Detection used preamble tokens + channel layout. A manual override is recorded in the audit trail.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`modal__footnote`,children:`Switching schema re-derives every form from the new YAML.`}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:r,children:`Cancel`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:()=>n(i),children:`Use this schema`})]})]}),children:s.map(e=>(0,a.jsxs)(`label`,{className:`proposal`+(i===e.id?` is-picked`:``),children:[(0,a.jsx)(`input`,{type:`radio`,name:`schema`,checked:i===e.id,onChange:()=>o(e.id)}),(0,a.jsxs)(`span`,{className:`pbody`,children:[(0,a.jsxs)(`span`,{className:`t`,children:[e.label,` · v`,e.version,e.detected&&(0,a.jsx)(`span`,{className:`schemachip`,style:{cursor:`default`},children:`detected`}),(0,a.jsxs)(`span`,{className:`conf`,children:[(0,a.jsx)(`span`,{className:`conf__track`,children:(0,a.jsx)(`span`,{className:`conf__fill conf__fill--`+(e.conf>=80?`ok`:e.conf>=40?`warn`:`err`),style:{width:e.conf+`%`}})}),(0,a.jsxs)(`span`,{className:`conf__num`,children:[e.conf,`%`]})]})]}),(0,a.jsxs)(`span`,{className:`d`,children:[(0,a.jsx)(`span`,{className:`mono`,style:{fontSize:`11px`},children:e.schema}),` — `,e.hint]})]})]},e.id))})}function Me({bundle:e,groupId:t,runId:n,onAdd:r,onRemove:i,onClose:o}){let s=e.groups.find(e=>e.id===t)||e.groups[0],c=s.runs.find(e=>e.id===n)||s.runs[0],l=c.evidence||[],[u,d]=Te(`failure`);return(0,a.jsxs)(Ee,{kind:`IMAGE EVIDENCE`,width:`mid`,onClose:o,title:`Run image evidence — `+c.id,sub:`Schema views: front · side · top · failure · scale reference · other. Optional in this schema (image_evidence.required = false); embedded in the package.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`span`,{className:`modal__footnote`,children:[l.length,` image(s) attached`]}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`select`,{className:`inp`,style:{padding:`5px 8px`,fontSize:`12px`},value:u,onChange:e=>d(e.target.value),children:window.IMAGE_VIEWS.map(e=>(0,a.jsx)(`option`,{value:e.id,children:e.label},e.id))}),(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:()=>r(s.id,c.id,u),children:`＋ Add image…`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:o,children:`Done`})]})]}),children:[l.length===0&&(0,a.jsxs)(`div`,{className:`evempty`,children:[`No images attached to this run yet.`,(0,a.jsx)(`br`,{}),`Pick a view and use “Add image…”, or drop image files here.`]}),l.map((e,t)=>(0,a.jsxs)(`div`,{className:`evrow`,children:[(0,a.jsx)(`span`,{className:`ic`,children:`▣`}),(0,a.jsx)(`span`,{className:`nm`,children:e.name}),(0,a.jsx)(`span`,{className:`kind`,children:(window.IMAGE_VIEWS.find(t=>t.id===e.view)||{}).label||e.view}),(0,a.jsx)(`button`,{className:`rm`,title:`Remove`,onClick:()=>i(s.id,c.id,t),children:`✕`})]},t))]})}function Ne({bundle:e,groupId:t,runId:n,onAdd:r,onRemove:o,onClose:s}){let c=e.groups.find(e=>e.id===t)||e.groups[0],l=c&&n?c.runs.find(e=>e.id===n):null,u=[...c?.supplemental||e.supplemental||[],...l?.supplemental||[]],[d,f]=Te(`dataset`),p=window.SUPPLEMENTAL_SCOPES.filter(e=>l||e!==`run`);return i.useEffect(()=>{p.includes(d)||f(`dataset`)},[d,p]),(0,a.jsxs)(Ee,{kind:`SUPPLEMENTAL FILES`,width:`mid`,onClose:s,title:`Supplemental files`,sub:`Carried in the package, not validated against the schema. Accepted scopes: dataset · run · schema_mapping · calibration · equipment_evidence · other.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`span`,{className:`modal__footnote`,children:[u.length,` file(s) attached · preserved in package`]}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`select`,{className:`inp`,style:{padding:`5px 8px`,fontSize:`12px`},value:d,onChange:e=>f(e.target.value),children:p.map(e=>(0,a.jsx)(`option`,{value:e,children:e.replace(/_/g,` `)},e))}),(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:()=>r(c?.id,l?.id||null,d),children:`＋ Add file…`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:s,children:`Done`})]})]}),children:[u.length===0&&(0,a.jsx)(`div`,{className:`evempty`,children:`No supplemental files attached.`}),u.map((e,t)=>(0,a.jsxs)(`div`,{className:`evrow`,children:[(0,a.jsx)(`span`,{className:`ic`,children:`▤`}),(0,a.jsx)(`span`,{className:`nm`,children:e.name}),(0,a.jsx)(`span`,{className:`kind`,children:(e.scope||`other`).replace(/_/g,` `)}),(0,a.jsx)(`button`,{className:`rm`,title:`Remove`,onClick:()=>o(c?.id,l?.id||null,t),children:`✕`})]},t))]})}function G({bundle:e,summary:t,review:n,mappingRows:r,onRowsChange:i,onReviewMapping:o,onApplyMapping:s,onRematch:c,onClose:l}){let u=t?.pairs||e.sourcePairs.map(e=>({csv:e.csv,yaml:e.yaml,status:`paired · base name`,paired:!0})),d=t?.pairedCount??u.filter(e=>e.paired!==!1).length,f=t?.runCount??u.length,p=r||n?.rows||[],m=n?.fieldOptions||[],h=(e,t)=>{i(p.map((n,r)=>{if(r!==e)return n;let i={...n.mapping||{},...t},a=m.find(e=>e.id===i.target_field_id);return{...n,mapping:i,suggestedFieldId:i.target_field_id||null,suggestedFieldLabel:a?.label||``,detectedUnit:i.unit||``,action:i.action||n.action}}))};return(0,a.jsxs)(Ee,{kind:`SIDECAR PAIRING`,width:`mid`,onClose:l,title:`Review / re-match YAML sidecars`,sub:`Paired 1:1 by base name (sidecar_import.same_stem) — each .yaml describes the run of the CSV it sits next to.`,foot:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`span`,{className:`modal__footnote `+(d===f?`modal__footnote--ok`:``),children:[`✓ `,d,`/`,f,` CSVs paired`]}),(0,a.jsxs)(`div`,{className:`modal__actions`,children:[(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:c,children:`⇄ Re-run matching`}),(0,a.jsx)(`button`,{className:`btn btn--sm`,onClick:o,children:`Review mapping`}),n&&(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:()=>s(p),children:`Apply mapping profile`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:l,children:`Done`})]})]}),children:[(0,a.jsxs)(`table`,{className:`pairtable`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`CSV (run data)`}),(0,a.jsx)(`th`,{}),(0,a.jsx)(`th`,{children:`YAML sidecar (run info)`}),(0,a.jsx)(`th`,{style:{textAlign:`right`},children:`Status`})]})}),(0,a.jsx)(`tbody`,{children:u.map(e=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{children:e.csv}),(0,a.jsx)(`td`,{className:`arr`,children:`⟷`}),(0,a.jsx)(`td`,{children:e.yaml||`No same-stem YAML`}),(0,a.jsx)(`td`,{style:{textAlign:`right`},children:(0,a.jsx)(`span`,{className:`chstat `+(e.paired===!1?`chstat--unmatched`:`chstat--matched`),children:e.status||(e.paired===!1?`not paired`:`paired · base name`)})})]},e.runId||e.csv))})]}),(0,a.jsxs)(`div`,{className:`dlgnote`,style:{marginTop:`12px`},children:[`Pairing rule: `,(0,a.jsx)(`b`,{children:(0,a.jsx)(`span`,{className:`mono`,children:`<name>.csv ↔ <name>.yaml`})}),`. Unknown sidecar keys prompt for mapping (`,(0,a.jsx)(`span`,{className:`mono`,children:`unknown_keys: prompt_mapping`}),`); on conflict the sidecar wins (`,(0,a.jsx)(`span`,{className:`mono`,children:`conflict_policy: prefer_sidecar`}),`).`]}),n&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`div`,{className:`dlgnote`,style:{marginTop:`12px`},children:[`Mapping profile `,(0,a.jsx)(`b`,{children:(0,a.jsx)(`span`,{className:`mono`,children:n.profileId})}),` · `,n.summary?.mappedCount||0,`/`,n.summary?.rowCount||p.length,` suggested mappings · `,n.summary?.reviewCount||0,` require review`]}),(0,a.jsxs)(`table`,{className:`pairtable`,style:{marginTop:`10px`},children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`YAML key`}),(0,a.jsx)(`th`,{children:`Raw value`}),(0,a.jsx)(`th`,{children:`Canonical field`}),(0,a.jsx)(`th`,{children:`Unit`}),(0,a.jsx)(`th`,{children:`Action`}),(0,a.jsx)(`th`,{style:{textAlign:`right`},children:`Status`})]})}),(0,a.jsx)(`tbody`,{children:p.map((e,t)=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{children:(0,a.jsx)(`span`,{className:`mono`,children:e.sourceKey||e.mapping?.source_key})}),(0,a.jsx)(`td`,{children:e.rawText||``}),(0,a.jsx)(`td`,{children:(0,a.jsxs)(`select`,{value:e.mapping?.target_field_id||``,onChange:e=>h(t,{target_field_id:e.target.value||null,action:e.target.value?`map`:`ignore`,user_corrected:!0}),children:[(0,a.jsx)(`option`,{value:``,children:`Ignore / no field`}),m.map(e=>(0,a.jsxs)(`option`,{value:e.id,children:[e.label,` (`,e.id,`)`]},e.id))]})}),(0,a.jsx)(`td`,{children:(0,a.jsx)(`input`,{value:e.mapping?.unit||``,onChange:e=>h(t,{unit:e.target.value,user_corrected:!0}),style:{width:`72px`}})}),(0,a.jsx)(`td`,{children:(0,a.jsxs)(`select`,{value:e.mapping?.action||`map`,onChange:e=>h(t,{action:e.target.value,user_corrected:!0}),children:[(0,a.jsx)(`option`,{value:`map`,children:`Map`}),(0,a.jsx)(`option`,{value:`ignore`,children:`Ignore`}),(0,a.jsx)(`option`,{value:`defer`,children:`Defer`})]})}),(0,a.jsx)(`td`,{style:{textAlign:`right`},children:(0,a.jsx)(`span`,{className:`chstat chstat--matched`,children:e.status||e.mapping?.status})})]},e.sourceKey||e.mapping?.source_key||t))})]})]})]})}Object.assign(window,{Modal:Ee,ChannelInspector:De,ExportDialog:ke,ProposeGroupsDialog:Ae,SchemaDialog:je,EvidenceDialog:Me,SupplementalDialog:Ne,RematchYamlDialog:G});var{useState:Pe}=i.default,Fe=`mtdp:native-source-drop`;function Ie(e){if(!e||typeof e!=`string`)return``;let t=e.trim();if(!t)return``;if(t.startsWith(`file://`))try{return decodeURIComponent(new URL(t).pathname||``).replace(/^\/([A-Za-z]:\/)/,`$1`)}catch{return``}return t}function Le(e){let t=[],n=e=>{let n=Ie(e);n&&!t.includes(n)&&t.push(n)};Array.from(e?.files||[]).forEach(e=>{n(e?.path),n(e?.webkitRelativePath)});let r=typeof e?.getData==`function`?e.getData(`text/uri-list`):``;return String(r||``).split(/\r?\n/).forEach(e=>{let t=e.trim();t&&!t.startsWith(`#`)&&n(t)}),t}function K(e){let t=e?.detail||{},n=Array.isArray(t.paths)?t.paths:[],r=[];return n.forEach(e=>{let t=Ie(e);t&&!r.includes(t)&&r.push(t)}),r}function Re({onStartIngest:e,onDropSources:t,onOpenPackage:n}){let[r,i]=Pe(!1);return(0,a.jsxs)(`section`,{className:`core core--bundle`,children:[(0,a.jsxs)(`header`,{className:`bundlehd`,children:[(0,a.jsxs)(`div`,{className:`bundlehd__top`,children:[(0,a.jsx)(`span`,{className:`bundlehd__kind`,children:`SUPRA CONTAINER`}),(0,a.jsx)(`span`,{className:`schemachip schemachip--muted`,children:`no schema yet`})]}),(0,a.jsx)(`h1`,{className:`bundlehd__name bundlehd__name--muted`,children:`No package loaded`}),(0,a.jsxs)(`div`,{className:`bundlehd__meta`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`b`,{children:`0`}),` groups`]}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`b`,{children:`0`}),` runs`]})]})]}),(0,a.jsxs)(`div`,{className:`emptystart`,children:[(0,a.jsxs)(`div`,{className:`dropzone`+(r?` is-over`:``),onClick:e,onDragOver:e=>{e.preventDefault(),i(!0)},onDragLeave:()=>i(!1),onDrop:n=>{n.preventDefault(),i(!1);let r=Le(n.dataTransfer);r.length&&t?t(r):e()},children:[(0,a.jsx)(`span`,{className:`big`,children:`⇣`}),(0,a.jsx)(`b`,{children:`Drop CSV files and YAML sidecars here`}),(0,a.jsx)(`span`,{className:`sub`,children:`…or click to choose a source folder · sidecars pair by base name: name.csv ↔ name.yaml`})]}),(0,a.jsxs)(`div`,{className:`emptystart__actions`,children:[(0,a.jsxs)(`button`,{className:`btn btn--lg`,onClick:e,children:[(0,a.jsx)(`span`,{className:`ic`,children:`▣`}),` Select source folder…`]}),(0,a.jsxs)(`button`,{className:`btn btn--lg`,onClick:n,children:[(0,a.jsx)(`span`,{className:`ic`,children:`▢`}),` Open MTDP package…`]})]}),(0,a.jsx)(`p`,{className:`emptystart__hint`,children:`Files are parsed, the schema is detected, sidecars are paired and sample groups are proposed automatically. Unresolved channel headers are flagged before you start enriching. Raw files are never modified, and working state autosaves as a draft session.`})]})]})}function ze(){return(0,a.jsxs)(`section`,{className:`core core--insert`,children:[(0,a.jsx)(`header`,{className:`insrhd`,children:(0,a.jsx)(`div`,{className:`insrhd__row`,children:(0,a.jsxs)(`div`,{className:`insrhd__scope`,children:[(0,a.jsx)(`span`,{className:`scopekind scopekind--ds`,children:`NO PACKAGE`}),(0,a.jsx)(`span`,{className:`insrhd__spec`,children:`Nothing to enrich yet`})]})})}),(0,a.jsxs)(`div`,{className:`insrempty`,children:[(0,a.jsx)(`div`,{className:`insrempty__mark`,children:`⛁`}),(0,a.jsxs)(`div`,{className:`insrempty__txt`,children:[`Drop raw files to generate a package,`,(0,a.jsx)(`br`,{}),`then enrich dataset metadata and runs here.`]})]}),(0,a.jsxs)(`footer`,{className:`insrfoot`,children:[(0,a.jsxs)(`div`,{className:`legend`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--req`,children:`*`}),` Required (export)`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--rep`,children:`†`}),` Required for report`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--rec`,children:`**`}),` Recommended`]})]}),(0,a.jsxs)(`div`,{className:`insrfoot__actions`,children:[(0,a.jsx)(`button`,{className:`btn btn--ghost btn--sm`,disabled:!0,children:`✓ Validate`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,disabled:!0,children:`⬇ Export…`})]})]})]})}Object.assign(window,{EmptyBundlePanel:Re,EmptyInsertPanel:ze});var{useState:Be,useRef:Ve,useEffect:He}=i.default;function Ue(e,t){let n=window.runReadiness(e,t),r=(e.channels||[]).filter(e=>e.status===`unmatched`).length,i=(e.channels||[]).filter(e=>e.status===`ambiguous`).length;return n.errors.length?{cls:`err`,label:n.errors.length+` error`+(n.errors.length>1?`s`:``)}:r||!window.hasLoadChannel(e)?{cls:`err`,label:(r||1)+` channel`+(r>1?`s`:``)}:i?{cls:`amb`,label:i+` ambiguous`}:n.missing.length?{cls:`warn`,label:n.missing.length+` missing`}:n.ready?{cls:`ok`,label:`Ready`}:{cls:`warn`,label:`needs input`}}function We({run:e,group:t,dataset:n,selected:r,onSelect:i,onInspectChannels:o,onEvidence:s,onCopyPrev:c,runIdx:l,groups:u,onMoveRun:d,onDragStart:f}){let[p,m]=Be(!1),h=Ve(null);He(()=>{if(!p)return;let e=e=>{h.current&&!h.current.contains(e.target)&&m(!1)};return document.addEventListener(`mousedown`,e),()=>document.removeEventListener(`mousedown`,e)},[p]);let g=Ue(e,n),_=(e.channels||[]).filter(e=>e.status===`unmatched`).length,v=(e.channels||[]).filter(e=>e.status===`ambiguous`).length;return(0,a.jsxs)(`div`,{ref:h,className:`trow trow--run`+(r?` is-selected`:``),draggable:!0,title:`Double-click: channel assignments`,onDragStart:n=>f(n,e,t),onClick:()=>i({type:`run`,groupId:t.id,runId:e.id}),onDoubleClick:()=>o(t.id,e.id),children:[(0,a.jsx)(`span`,{className:`trow__grip`,"aria-hidden":!0,children:`⋮⋮`}),(0,a.jsxs)(`span`,{className:`trow__name`,children:[(0,a.jsxs)(`span`,{className:`trow__runid`,children:[e.id,_>0&&(0,a.jsxs)(`button`,{className:`chip-ch chip-ch--err`,title:`Unassigned channel header — click to resolve`,onClick:n=>{n.stopPropagation(),o(t.id,e.id)},children:[`⚠ `,_,` ch`]}),v>0&&(0,a.jsxs)(`button`,{className:`chip-ch chip-ch--amb`,title:`Ambiguous channel header — click to choose`,onClick:n=>{n.stopPropagation(),o(t.id,e.id)},children:[`? `,v,` ch`]})]}),(0,a.jsx)(`span`,{className:`trow__spec mono`,children:e.values.specimen_name||e.fileLabel})]}),(0,a.jsxs)(`span`,{className:`rstat rstat--`+g.cls,children:[(0,a.jsx)(`span`,{className:`rstat__dot`}),g.label]}),(0,a.jsxs)(`span`,{className:`trow__kebabwrap`,children:[(0,a.jsx)(`button`,{className:`kebab`,title:`Run actions`,onClick:e=>{e.stopPropagation(),m(e=>!e)},children:`⋯`}),p&&(0,a.jsxs)(`span`,{className:`rowpop`,onClick:e=>e.stopPropagation(),children:[(0,a.jsx)(`button`,{onClick:()=>{m(!1),o(t.id,e.id)},children:`⚙ Channel assignments…`}),(0,a.jsx)(`button`,{onClick:()=>{m(!1),s(t.id,e.id)},children:`▣ Image evidence…`}),l>0&&(0,a.jsxs)(`button`,{onClick:()=>{m(!1),c(t.id,e.id)},children:[`⧉ Copy values from `,t.runs[l-1].id]}),u.filter(e=>e.id!==t.id).map(n=>(0,a.jsxs)(`button`,{onClick:()=>{m(!1),d(e,t.id,n.id)},children:[`→ Move to “`,n.name,`”`]},n.id))]})]})]})}function Ge({group:e,editing:t,onStartEdit:n,onCommit:r,onCancel:i}){let o=Ve(null);return He(()=>{t&&o.current&&(o.current.focus(),o.current.select())},[t]),t?(0,a.jsx)(`input`,{ref:o,className:`renamein`,defaultValue:e.name,onClick:e=>e.stopPropagation(),onKeyDown:e=>{e.key===`Enter`&&r(e.target.value),e.key===`Escape`&&i()},onBlur:e=>r(e.target.value)}):(0,a.jsxs)(`span`,{className:`grouphd__namewrap`,children:[(0,a.jsx)(`span`,{className:`grouphd__name`,title:`Double-click to rename`,onDoubleClick:e=>{e.stopPropagation(),n()},children:e.name}),(0,a.jsx)(`button`,{className:`grouphd__pencil`,title:`Rename group`,onClick:e=>{e.stopPropagation(),n()},children:`✎`})]})}function Ke({group:e,dataset:t,selection:n,onSelect:r,onMoveRun:i,onInspectChannels:o,onEvidence:s,onCopyPrev:c,groups:l,expanded:u,onToggle:d,editing:f,onStartEdit:p,onRename:m,onCancelEdit:h,onDelete:g}){let[_,v]=Be(!1),y=e.runs.filter(e=>!window.runReadiness(e,t).ready).length,b=(n.type===`dataset`||n.type===`grid`)&&n.groupId===e.id;return(0,a.jsxs)(`div`,{className:`groupblk`+(_?` is-dragover`:``)+(e.runs.length===0?` groupblk--empty`:``),onDragOver:e=>{e.preventDefault(),v(!0)},onDragLeave:()=>v(!1),onDrop:t=>{t.preventDefault(),v(!1);let n=window.__dragRun;n&&i(n.run,n.fromGroupId,e.id)},children:[(0,a.jsxs)(`div`,{className:`grouphd`+(b?` is-selected`:``),onClick:()=>r({type:`dataset`,groupId:e.id}),children:[(0,a.jsx)(`button`,{className:`grouphd__tw`,onClick:t=>{t.stopPropagation(),d(e.id)},children:u?`▾`:`▸`}),(0,a.jsx)(`span`,{className:`grouphd__icon`,"aria-hidden":!0,children:`▦`}),(0,a.jsx)(Ge,{group:e,editing:f,onStartEdit:p,onCommit:t=>m(e.id,t),onCancel:h}),(0,a.jsxs)(`span`,{className:`grouphd__count`,children:[e.runs.length,` runs`]}),(0,a.jsx)(`span`,{className:`grouphd__ready`,children:e.runs.length===0?(0,a.jsx)(`span`,{className:`grouphd__hint`,children:`empty`}):y===0?(0,a.jsx)(`span`,{className:`rdy rdy--ok`,children:`● all ready`}):(0,a.jsxs)(`span`,{className:`rdy rdy--warn`,children:[`● `,y,` not ready`]})}),(0,a.jsx)(`button`,{className:`grouphd__bulk`,title:`Open the editing grid — type once in the ⊞ All-runs row to fill every run`,onClick:t=>{t.stopPropagation(),r({type:`grid`,groupId:e.id})},children:`⊞ grid`}),(0,a.jsx)(`button`,{className:`grouphd__del`,"data-group-action":`delete`,"data-groupid":e.id,title:`Delete group (runs move to Unassigned)`,onClick:t=>{t.stopPropagation(),g(e.id)},children:`✕`})]}),u&&e.runs.length>0&&(0,a.jsx)(`div`,{className:`grouprows`,children:e.runs.map((u,d)=>(0,a.jsx)(We,{run:u,group:e,dataset:t,runIdx:d,groups:l,selected:n.type===`run`&&n.runId===u.id,onSelect:r,onInspectChannels:o,onEvidence:s,onCopyPrev:c,onMoveRun:i,onDragStart:(e,t,n)=>{window.__dragRun={run:t,fromGroupId:n.id}}},u.id))}),u&&e.runs.length===0&&(0,a.jsx)(`div`,{className:`grouprows`,children:`drag runs here to fill this group`})]})}function qe({bundle:e,selection:t,onSelect:n,onMoveRun:r,onInspectChannels:i,onEvidence:o,onCopyPrev:s,onProposeGroups:c,onNewGroup:l,onRenameGroup:u,onDeleteGroup:d,onRematchYaml:f,editingGroupId:p,onStartRename:m,onCancelRename:h,onChangeSchema:g}){let[_,v]=Be(()=>Object.fromEntries(e.groups.map(e=>[e.id,!0]))),[y,b]=Be(!1),x=e=>v(t=>({...t,[e]:!t[e]})),S=e.groups.reduce((e,t)=>e+t.runs.length,0),C=e.groups.reduce((t,n)=>t+n.runs.filter(t=>window.runReadiness(t,e.dataset).ready).length,0),w=S?Math.round(C/S*100):0;return(0,a.jsxs)(`section`,{className:`core core--bundle`,children:[(0,a.jsxs)(`header`,{className:`bundlehd`,children:[(0,a.jsxs)(`div`,{className:`bundlehd__top`,children:[(0,a.jsx)(`span`,{className:`bundlehd__kind`,children:`SUPRA CONTAINER`}),(0,a.jsxs)(`button`,{className:`schemachip`,style:{font:`inherit`,fontSize:`11.5px`,fontWeight:600},title:`Click to change the detected schema`,onClick:g,children:[e.schemaLabel,` · v`,e.schemaVersion,e.schemaOverridden?` · manual`:``]})]}),(0,a.jsx)(`h1`,{className:`bundlehd__name`,children:e.name}),(0,a.jsxs)(`div`,{className:`bundlehd__meta`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`b`,{children:e.groups.length}),` group`,e.groups.length===1?``:`s`]}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`b`,{children:S}),` runs`]}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{className:`bundlehd__ready`,children:[C,`/`,S,` export-ready`]})]}),(0,a.jsx)(`div`,{className:`bundlebar`,children:(0,a.jsx)(`span`,{className:`bundlebar__fill`,style:{width:w+`%`}})})]}),(0,a.jsxs)(`div`,{className:`bundletools`,children:[(0,a.jsxs)(`button`,{className:`btn btn--sm`,onClick:c,children:[(0,a.jsx)(`span`,{className:`ic`,children:`⊞`}),` Propose groups…`]}),(0,a.jsxs)(`button`,{className:`btn btn--sm btn--ghost`,onClick:l,children:[(0,a.jsx)(`span`,{className:`ic`,children:`＋`}),` New group`]})]}),(0,a.jsxs)(`div`,{className:`trow trow--head`,children:[(0,a.jsx)(`span`,{className:`trow__grip`}),(0,a.jsx)(`span`,{children:`Group / run`}),(0,a.jsx)(`span`,{children:`Status`}),(0,a.jsx)(`span`,{})]}),(0,a.jsxs)(`div`,{className:`bundletree`,children:[e.groups.map(c=>(0,a.jsx)(Ke,{group:c,dataset:e.dataset,groups:e.groups,selection:t,onSelect:n,onMoveRun:r,onInspectChannels:i,onEvidence:o,onCopyPrev:s,expanded:_[c.id]!==!1,onToggle:x,editing:p===c.id,onStartEdit:()=>m(c.id),onRename:u,onCancelEdit:h,onDelete:d},c.id)),(0,a.jsxs)(`div`,{className:`groupblk groupblk--unassigned`,onDragOver:e=>e.preventDefault(),onDrop:e=>{e.preventDefault();let t=window.__dragRun;t&&r(t.run,t.fromGroupId,`__unassigned`)},children:[(0,a.jsxs)(`div`,{className:`grouphd grouphd--muted`,children:[(0,a.jsx)(`span`,{className:`grouphd__tw`}),(0,a.jsx)(`span`,{className:`grouphd__icon`,"aria-hidden":!0,children:`○`}),(0,a.jsx)(`span`,{className:`grouphd__name`,children:`Unassigned`}),(0,a.jsxs)(`span`,{className:`grouphd__count`,children:[e.unassigned.length,` runs`]}),(0,a.jsx)(`span`,{className:`grouphd__hint`,children:`drag here to remove from a group`})]}),e.unassigned.length>0&&(0,a.jsx)(`div`,{className:`grouprows`,children:e.unassigned.map(c=>(0,a.jsx)(We,{run:c,group:{id:`__unassigned`,runs:e.unassigned},dataset:e.dataset,runIdx:-1,groups:e.groups,selected:t.runId===c.id,onSelect:n,onInspectChannels:i,onEvidence:o,onCopyPrev:s,onMoveRun:r,onDragStart:(e,t)=>{window.__dragRun={run:t,fromGroupId:`__unassigned`}}},c.id))})]})]}),(0,a.jsxs)(`div`,{className:`filesdrawer`,children:[(0,a.jsxs)(`button`,{className:`filesdrawer__hd`,onClick:()=>b(e=>!e),children:[(0,a.jsxs)(`span`,{children:[y?`▾`:`▸`,` Source files`]}),(0,a.jsxs)(`span`,{className:`filesdrawer__count`,children:[e.sourcePairs.length,` CSV + `,e.sourcePairs.length,` YAML`]}),(0,a.jsx)(`span`,{className:`filesdrawer__rematch`,onClick:e=>{e.stopPropagation(),f()},children:`review pairing ›`})]}),y&&(0,a.jsx)(`ul`,{className:`filesdrawer__list`,children:e.sourcePairs.map(e=>(0,a.jsxs)(`li`,{children:[(0,a.jsx)(`span`,{className:`ic`,children:`▢`}),e.csv,` `,(0,a.jsxs)(`span`,{className:`pair`,children:[`⟷ `,e.yaml]})]},e.csv))})]})]})}Object.assign(window,{BundlePanel:qe,runStatusInfo:Ue});var{useState:Je,useRef:Ye,useMemo:Xe}=i.default;function Ze(e,t){let n=[];return window.RUN_SECTIONS.forEach(r=>{let i=r.fields.filter(n=>{if(!e.runs.some(e=>window.isVisible(n,e.values)))return!1;let r=n.hardRequired?`required`:n.importance===`required`?`report`:n.importance===`required_for_accepted_runs`?`required`:n.importance;return t===`essential`?r===`required`||r===`report`:t===`core`?r!==`optional`||e.runs.some(e=>window.isFilled(e.values[n.id])):!0});i.length&&n.push({sec:r,fields:i})}),n}function Qe({f:e,value:t,run:n,onChange:r,onCommit:i,cellRef:o,onKeyDown:s,onPaste:c,cls:l}){if(e.type===`enum`||e.type===`bool`){let c=e.type===`bool`?[{v:`true`,label:`Yes`},{v:`false`,label:`No`}]:e.options;return(0,a.jsx)(`td`,{className:l,children:(0,a.jsxs)(`select`,{ref:o,"data-runid":n.id,"data-fkey":e.id,value:t||``,onKeyDown:s,onChange:e=>{r(e.target.value),i(e.target.value)},children:[(0,a.jsx)(`option`,{value:``,children:`—`}),c.map(e=>(0,a.jsx)(`option`,{value:e.v,children:e.label},e.v))]})})}return(0,a.jsx)(`td`,{className:l,title:l.includes(`is-err`)?window.fieldError(e,t):``,children:(0,a.jsx)(`input`,{ref:o,value:t||``,placeholder:`—`,"data-runid":n.id,"data-fkey":e.id,onKeyDown:s,onPaste:c,onChange:e=>r(e.target.value),onBlur:e=>i(e.target.value)})})}function $e({f:e,group:t,onBulkSet:n,cellRef:r,onKeyDown:i}){let o=new Set(t.runs.map(t=>t.values[e.id]==null?``:String(t.values[e.id]))),s=o.size===1?[...o][0]:null,c=o.size;if(e.type===`enum`||e.type===`bool`){let t=e.type===`bool`?[{v:`true`,label:`Yes`},{v:`false`,label:`No`}]:e.options;return(0,a.jsx)(`td`,{className:`is-all`,children:(0,a.jsxs)(`select`,{ref:r,"data-grid-all":e.id,value:s||``,onKeyDown:i,onChange:t=>{t.target.value&&n(e.id,t.target.value)},children:[(0,a.jsx)(`option`,{value:``,children:s===null?`mixed · `+c:`—`}),t.map(e=>(0,a.jsx)(`option`,{value:e.v,children:e.label},e.v))]})})}return(0,a.jsx)(`td`,{className:`is-all`,children:(0,a.jsx)(`input`,{ref:r,"data-grid-all":e.id,defaultValue:s||``,placeholder:s===null?`mixed · `+c:`type once ↵`,onKeyDown:t=>{t.key===`Enter`&&t.target.value.trim()&&t.target.value!==s?n(e.id,t.target.value.trim()):i(t)},onBlur:t=>{t.target.value.trim()&&t.target.value!==s&&n(e.id,t.target.value.trim())}},s===null?`mixed`+c:`u`+s)})}function et({bundle:e,group:t,selection:n,density:r,onCellSet:i,onCellCommit:o,onCellBatchCommit:s,onBulkSet:c}){let l=Xe(()=>Ze(t,r),[t,r]),u=l.flatMap(e=>e.fields),d=Ye({}),f=(e,t)=>e+`:`+t,p=(e,t)=>n=>{let r=(e,t)=>{let r=d.current[f(e,t)];r&&(n.preventDefault(),r.focus(),r.select&&r.select())};n.key===`ArrowDown`||n.key===`Enter`&&n.target.tagName===`INPUT`?r(e+1,t):n.key===`ArrowUp`?r(e-1,t):n.key===`ArrowLeft`&&(n.target.selectionStart===0||n.target.tagName===`SELECT`)?r(e,t-1):n.key===`ArrowRight`&&(n.target.tagName===`SELECT`||n.target.selectionStart===(n.target.value||``).length)&&r(e,t+1)},m=(e,n)=>r=>{let a=r.clipboardData.getData(`text`);if(!a||!a.includes(`	`)&&!a.includes(`
`))return;r.preventDefault();let o=a.split(/\r?\n/).filter(e=>e.length),c=t.runs.findIndex(t=>t.id===e.id),l=[];o.forEach((e,r)=>{let a=t.runs[c+r];a&&e.split(`	`).forEach((e,t)=>{let r=u[n+t];if(r&&r.type!==`enum`&&r.type!==`bool`){let t=e.trim();i(a.id,r.id,t),l.push({run_id:a.id,patch:{[r.id]:t}})}})}),l.length&&s(l)};return(0,a.jsxs)(`div`,{className:`gridview`,children:[(0,a.jsxs)(`div`,{className:`gridview__hint`,children:[`All `,t.runs.length,` runs · type once in the `,(0,a.jsx)(`b`,{className:`allink`,children:`⊞ All runs`}),` row to fill every run · paste a block from Excel into any cell · `,(0,a.jsx)(`span`,{className:`mono`,style:{fontSize:`11px`},children:`↑↓←→`}),` move · `,(0,a.jsx)(`span`,{className:`mono`,style:{fontSize:`11px`},children:`↵`}),` next run`]}),(0,a.jsx)(`div`,{className:`gridscroll`,children:(0,a.jsxs)(`table`,{className:`gtable`,children:[(0,a.jsxs)(`thead`,{children:[(0,a.jsxs)(`tr`,{className:`gtable__secs`,children:[(0,a.jsx)(`th`,{className:`gtable__rowhd`}),l.map(e=>(0,a.jsx)(`th`,{colSpan:e.fields.length,children:e.sec.label},e.sec.id))]}),(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{className:`gtable__rowhd`,children:`Run`}),u.map(e=>(0,a.jsxs)(`th`,{title:e.desc||e.label,children:[e.label,e.hardRequired&&(0,a.jsx)(`span`,{className:`mk mk--req`,children:`*`}),e.importance===`required_for_accepted_runs`&&(0,a.jsx)(`span`,{className:`mk mk--req`,title:`Required while validity is Accepted`,children:`*ᵃ`}),e.units&&(0,a.jsx)(`span`,{className:`gtable__unit`,children:t.units[e.id]||e.stdUnit})]},e.id))]})]}),(0,a.jsxs)(`tbody`,{children:[(0,a.jsxs)(`tr`,{className:`gtable__all`,children:[(0,a.jsx)(`th`,{className:`gtable__rowhd`,children:`⊞ All runs`}),u.map((e,n)=>(0,a.jsx)($e,{f:e,group:t,onBulkSet:c,cellRef:e=>d.current[f(0,n)]=e,onKeyDown:p(0,n)},e.id))]}),t.runs.map((t,r)=>{let s=window.runStatusInfo(t,e.dataset);return(0,a.jsxs)(`tr`,{className:n.type===`run`&&n.runId===t.id?`is-selected`:``,children:[(0,a.jsxs)(`th`,{className:`gtable__rowhd`,children:[(0,a.jsx)(`span`,{className:`tdot tdot--`+s.cls,title:s.label}),t.id]}),u.map((e,n)=>{if(!window.isVisible(e,t.values))return(0,a.jsx)(`td`,{className:`is-na`,children:`·`},e.id);let s=t.values[e.id],c=window.isFilled(s)&&window.fieldError(e,s),l=window.effLevel(e,t.values)===`required`&&!window.isRecorded(e,s);return(0,a.jsx)(Qe,{f:e,value:s,run:t,cls:c?`is-err`:l?`is-req`:``,onChange:n=>i(t.id,e.id,n),onCommit:n=>o(t.id,e.id,n),cellRef:e=>d.current[f(r+1,n)]=e,onKeyDown:p(r+1,n),onPaste:m(t,n)},e.id)})]},t.id)})]})]})})]})}Object.assign(window,{GridView:et});var{useState:tt,useMemo:nt,useRef:rt,useEffect:it}=i.default,at=(0,a.jsxs)(`span`,{className:`kbdhint`,children:[(0,a.jsx)(`b`,{children:`Tab`}),` next · `,(0,a.jsx)(`b`,{children:`Alt+Enter`}),` next empty required · `,(0,a.jsx)(`b`,{children:`Ctrl+Enter`}),` next run`]});function ot(e){return e===`required`?(0,a.jsx)(`span`,{className:`mk mk--req`,title:`Required for export`,children:`*`}):e===`report`?(0,a.jsx)(`span`,{className:`mk mk--rep`,title:`Required for the report (export proceeds)`,children:`†`}):e===`recommended`?(0,a.jsx)(`span`,{className:`mk mk--rec`,title:`Recommended`,children:`**`}):null}function st(e){return e.type===`float`?`number`:e.type===`date`?`date`:e.type===`enum`?`choice`:e.type===`bool`?`yes / no`:`text`}function q(e){return e.type===`float`?`number`+(e.min===0?` > 0`:e.min===void 0?``:` ≥ `+e.min):e.type===`date`?`date · yyyy-MM-dd`:e.type===`enum`?e.options.length+` choices`:e.type===`bool`?`yes / no`:(e.pattern,`text`)}function ct({f:e,group:t,onUseForAll:n}){let r=new Map;t.runs.forEach(t=>{let n=t.values[e.id]==null?``:String(t.values[e.id]);r.has(n)||r.set(n,[]),r.get(n).push(t.id)});let i=[...r.entries()].sort((e,t)=>t[1].length-e[1].length);return(0,a.jsxs)(`div`,{className:`mixpop`,onMouseDown:e=>e.preventDefault(),children:[(0,a.jsxs)(`div`,{className:`mixpop__t`,children:[`Values across `,t.runs.length,` runs`]}),(0,a.jsx)(`table`,{children:(0,a.jsx)(`tbody`,{children:i.map(([t,r],i)=>(0,a.jsxs)(`tr`,{className:i>0&&r.length===1?`is-outlier`:``,children:[(0,a.jsx)(`td`,{className:`r`,children:r.length>3?r.length+` runs`:r.map(window.runShort).join(`, `)}),(0,a.jsx)(`td`,{className:`v`,children:t===``?`—`:e.options?window.enumLabel(e,t):t}),(0,a.jsx)(`td`,{className:`a`,children:t!==``&&(0,a.jsx)(`button`,{onClick:()=>n(t),children:`use for all`})})]},i))})}),(0,a.jsx)(`div`,{className:`mixpop__f`,children:`Typing a value replaces all of these — undo with Ctrl+Z.`})]})}function lt({f:e,from:t,to:n,count:r,onApply:i,onCancel:o}){let s=window.conversionFactorLabel(e.dim,t,n);return(0,a.jsxs)(`div`,{className:`unitconfirm`,children:[(0,a.jsxs)(`span`,{className:`unitconfirm__q`,children:[(0,a.jsxs)(`b`,{children:[t,` → `,n]}),` on `,r,` runs:`]}),(0,a.jsxs)(`button`,{className:`unitconfirm__btn unitconfirm__btn--pri`,onClick:()=>i(!0),children:[`Convert values `,s&&`(`+s+`)`]}),(0,a.jsx)(`button`,{className:`unitconfirm__btn`,onClick:()=>i(!1),children:`Relabel only`}),(0,a.jsx)(`button`,{className:`unitconfirm__x`,onClick:o,children:`✕`})]})}function ut({f:e,value:t,ctx:n,unitValue:r,scope:i,group:o,focused:s,touched:c,validated:l,onChange:u,onFocus:d,onBlur:f,onUnitPick:p,onUnitInline:m,pendingUnit:h,onUnitApply:g,onUnitCancel:_,onCommit:v,onApplyAll:y,sharedCount:b,mixed:x}){let S=window.effLevel(e,n),C=window.isFilled(t)?window.fieldError(e,t):null,w=!window.isRecorded(e,t),T=!!x&&w,E=e.type===`enum`||e.type===`bool`,D=C?`err`:!w&&!T?`ok`:null,O=S===`required`&&w&&!T&&(c||l),k=[`field`,e.span===1?`field--half`:``,T?`is-mixed`:``,O?`is-required`:``,C?`is-error`:``,window.isFilled(t)?`is-filled`:``].join(` `),A=i===`run`?`✎ this run only`:i===`shared-run`?`⊞ writes to all `+b+` runs`:`◈ shared — applies to every run`;return(0,a.jsxs)(`div`,{className:k,children:[(0,a.jsxs)(`label`,{className:`field__label`,children:[e.label,ot(S)]}),(0,a.jsxs)(`div`,{className:`field__control`,children:[(0,a.jsxs)(`div`,{className:`field__inputwrap`,children:[(0,a.jsxs)(`div`,{className:`inpfield`+(E?` inpfield--select`:``),children:[E?(0,a.jsxs)(`select`,{className:`inp`,"data-fkey":e.id,"data-req":+(S===`required`),value:t||``,onChange:e=>u(e.target.value),onFocus:d,onBlur:t=>f(e.id,t.target.value),children:[(0,a.jsx)(`option`,{value:``,children:T?`— mixed (`+x+`) —`:`—`}),(e.type===`bool`?[{v:`true`,label:`Yes`},{v:`false`,label:`No`}]:e.options).map(e=>(0,a.jsxs)(`option`,{value:e.v,children:[e.label,e.deviation?` ⚠ ISO deviation`:``]},e.v))]}):(0,a.jsx)(`input`,{className:`inp`,"data-fkey":e.id,"data-req":+(S===`required`),type:`text`,inputMode:e.type===`float`?`decimal`:void 0,placeholder:T?`Mixed · `+x+` values`:e.ph||(e.type===`float`?`0.00`:e.type===`date`?`yyyy-MM-dd`:``),value:t||``,onChange:e=>u(e.target.value),onFocus:d,onBlur:t=>f(e.id,t.target.value)}),D&&(0,a.jsx)(`span`,{className:`vchk vchk--`+D,title:D===`ok`?`Valid `+st(e):`Invalid `+st(e),children:D===`ok`?`✓`:`!`})]}),e.units&&(0,a.jsx)(`select`,{className:`unit`,"data-unit-fkey":e.id,value:r||e.stdUnit,onChange:t=>{e.unitInline?(m(e,t.target.value),v&&v(e.id+`__unit`,t.target.value)):p(e,r||e.stdUnit,t.target.value)},children:e.units.map(e=>(0,a.jsx)(`option`,{value:e,children:e},e))})]}),h&&h.fieldId===e.id&&(0,a.jsx)(lt,{f:e,from:h.from,to:h.to,count:b,onApply:t=>g(e,h.to,t),onCancel:_}),T&&s&&(0,a.jsx)(ct,{f:e,group:o,onUseForAll:e=>u(e)}),(0,a.jsxs)(`div`,{className:`field__under`,children:[C&&(0,a.jsxs)(`span`,{className:`msg msg--err`,children:[`⚠ `,C]}),!C&&O&&(0,a.jsx)(`span`,{className:`msg msg--req`,children:`Required for export`}),!C&&!O&&S===`report`&&w&&(0,a.jsx)(`span`,{className:`msg msg--rep`,children:`Required for the report`}),!C&&T&&!s&&(0,a.jsx)(`span`,{className:`msg msg--mixed`,children:`differs across runs — focus to see values`}),s&&!C&&(0,a.jsxs)(`span`,{className:`focusinfo`,children:[(0,a.jsx)(`span`,{className:`typehint`,title:`Expected value type`,children:q(e)}),(0,a.jsx)(`span`,{className:`blast blast--`+i,children:A}),at]}),y&&window.isFilled(t)&&!C&&!s&&(0,a.jsxs)(`button`,{className:`applyall`,onClick:()=>y(e.id),children:[`⊞ apply to all `,b]})]})]})]})}function dt({sec:e,values:t,ctxValues:n,density:r,scope:i,scopeTag:o,group:s,sharedCount:c,mixedMap:l,focusKey:u,setFocusKey:d,touchedKeys:f,markTouched:p,validated:m,onField:h,unitFor:g,onUnitPick:_,pendingUnit:v,onUnitApply:y,onUnitCancel:b,onCommit:x,onApplyAll:S,innerRef:C,children:w}){let T=n||t,E=window.visibleFields(e.fields,T,r);if(E.length===0&&!w)return null;let D=window.sectionCounts(E,t);return(0,a.jsxs)(`section`,{className:`formsec formsec--`+i,ref:C,"data-sec":e.id,children:[(0,a.jsxs)(`div`,{className:`formsec__hd`,children:[(0,a.jsx)(`h3`,{className:`formsec__title`,children:e.label}),o&&(0,a.jsx)(`span`,{className:`formsec__scope formsec__scope--`+i,children:o}),(0,a.jsxs)(`span`,{className:`formsec__count`,children:[D.filled,`/`,E.length]})]}),(0,a.jsx)(`div`,{className:`formgrid`,children:E.map(n=>(0,a.jsx)(ut,{f:n,value:t[n.id],ctx:T,scope:i,group:s,unitValue:n.unitInline?t[n.id+`__unit`]||n.stdUnit:g?g(n):null,focused:u===e.id+`:`+n.id,touched:f[n.id]||!1,validated:m,mixed:l?l[n.id]:0,sharedCount:c,onChange:e=>h(n.id,e),onFocus:()=>d(e.id+`:`+n.id),onBlur:(e,t)=>{d(null),p(e),x&&x(e,t)},onUnitPick:_,onUnitInline:(e,t)=>h(e.id+`__unit`,t),pendingUnit:v,onUnitApply:y,onUnitCancel:b,onCommit:x,onApplyAll:S},n.id))}),w]})}function ft({rows:e}){return(0,a.jsx)(`div`,{className:`chanlist`,children:e.map(e=>(0,a.jsxs)(`div`,{className:`chanrow`+(e.cls?` chanrow--`+e.cls:``),children:[(0,a.jsx)(`span`,{className:`hdr`,children:e.header}),(0,a.jsx)(`span`,{className:`dim`+(e.fam?``:` dim--none`),children:e.fam||`no family assigned`}),(0,a.jsx)(`span`,{className:`un`,children:e.unit||`—`}),(0,a.jsx)(`span`,{className:`chstat chstat--`+e.status,children:e.statusLabel})]},e.header))})}function pt({run:e,onInspect:t}){let n=window.channelIssues(e);return(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(ft,{rows:e.channels.map(e=>({header:e.header,fam:e.family?window.familyLabel(e.family):null,unit:e.unit,status:e.status,statusLabel:e.status===`ambiguous`?`? ambiguous`:e.status,cls:e.status===`ambiguous`?`amb`:e.status===`unmatched`?`issue`:null}))}),(0,a.jsx)(`div`,{className:`chanblock__foot`,children:(0,a.jsxs)(`button`,{className:`rowbtn`,onClick:t,children:[(0,a.jsx)(`span`,{children:`⚙`}),` Review & reassign channel headers…`,n.length>0&&(0,a.jsxs)(`span`,{className:`cnt`,style:{color:`var(--warn)`},children:[n.length,` unresolved`]})]})})]})}function mt(e){let t=new Map;return e.runs.forEach(e=>(e.channels||[]).forEach(n=>{let r=t.get(n.header)||{header:n.header,fams:new Set,units:new Set,issues:[],count:0};r.count++,n.family&&r.fams.add(window.familyLabel(n.family)),n.unit&&r.units.add(n.unit),(n.status===`unmatched`||n.status===`ambiguous`)&&r.issues.push(e.id),t.set(n.header,r)})),[...t.values()]}function ht({group:e,onInspect:t,innerRef:n}){let r=mt(e),i=[...new Set(r.flatMap(e=>e.issues))],o=r.filter(e=>e.issues.length===0).length,s=r.map(t=>({header:t.header,fam:t.fams.size===1?[...t.fams][0]:t.fams.size===0?null:`differs across runs`,unit:t.units.size===1?[...t.units][0]:t.units.size===0?`—`:`mixed`,status:t.issues.length===0?`matched`:`unmatched`,statusLabel:t.issues.length===0?t.count===e.runs.length?`ok · all runs`:`ok · `+t.count+`/`+e.runs.length+` runs`:`unresolved · `+t.issues.map(window.runShort).join(`, `),cls:t.issues.length?`issue`:null}));return(0,a.jsxs)(`section`,{className:`formsec formsec--shared-run`,ref:n,"data-sec":`channels-shared`,children:[(0,a.jsxs)(`div`,{className:`formsec__hd`,children:[(0,a.jsx)(`h3`,{className:`formsec__title`,children:`Parsed channels`}),(0,a.jsxs)(`span`,{className:`formsec__scope formsec__scope--shared-run`,children:[`across `,e.runs.length,` runs`]}),(0,a.jsxs)(`span`,{className:`formsec__count`,children:[o,`/`,r.length]})]}),(0,a.jsx)(ft,{rows:s}),(0,a.jsx)(`div`,{className:`chanblock__foot`,children:(0,a.jsxs)(`button`,{className:`rowbtn`,onClick:()=>t(i[0]||e.runs[0].id),children:[(0,a.jsx)(`span`,{children:`⚙`}),` Review & reassign channel headers…`,i.length>0&&(0,a.jsxs)(`span`,{className:`cnt`,style:{color:`var(--warn)`},children:[i.length,` run`,i.length>1?`s`:``,` unresolved`]})]})})]})}function gt({bundle:e,onJump:t,onOpenChannels:n,onClose:r}){let i=window.buildValidationReport(e),o=[...i.errors.map(e=>({...e,mark:`✕`,mcls:`e`})),...i.missing.map(e=>({...e,mark:`⚠`,mcls:`w`})),...i.reportItems.map(e=>({...e,mark:`†`,mcls:`r`}))],[s,c]=tt(0),l=Math.min(s,Math.max(0,o.length-1)),u=e=>{e&&(e.action===`channels`?n(e.target):t(e.target))};return(0,a.jsxs)(`div`,{className:`issuesdrawer`,children:[(0,a.jsxs)(`div`,{className:`issuesdrawer__bar`,children:[(0,a.jsx)(`b`,{children:`Issues`}),(0,a.jsxs)(`span`,{className:`cnt-e`,children:[`✕ `,i.errors.length,` error`,i.errors.length===1?``:`s`]}),(0,a.jsxs)(`span`,{className:`cnt-w`,children:[`⚠ `,i.missing.length,` missing`]}),(0,a.jsxs)(`span`,{className:`cnt-r`,children:[`† `,i.reportItems.length,` report gap`,i.reportItems.length===1?``:`s`]}),(0,a.jsxs)(`span`,{className:`cnt-ok`,children:[`✓ `,i.passed.length,` checks passed · `,i.skipped.length,` out of scope`]}),(0,a.jsxs)(`span`,{className:`issuesdrawer__nav`,children:[o.length>0&&(0,a.jsx)(`button`,{className:`fixnext`,onClick:()=>{let e=o[l];u(e),c(e=>Math.min(e+1,o.length-1))},children:`Fix next →`}),(0,a.jsx)(`button`,{className:`dclose`,title:`Close`,onClick:r,children:`✕`})]})]}),o.length===0?(0,a.jsxs)(`div`,{className:`issuesdrawer__clear`,children:[`✓ Nothing blocking — `,i.readyRuns,`/`,i.totalRuns,` runs export-ready.`,` `,`Checked: `,i.passed.map(e=>e.text.split(` — `)[0]).join(` · `),`. Not validated: `,i.skipped.map(e=>e.text).join(` · `),`.`]}):(0,a.jsx)(`ul`,{className:`issuesdrawer__list`,children:o.map((e,t)=>(0,a.jsxs)(`li`,{className:t===l?`is-cur`:``,onClick:()=>{c(t),u(e)},children:[(0,a.jsx)(`span`,{className:`m `+e.mcls,children:e.mark}),(0,a.jsxs)(`span`,{className:`txt`,children:[e.text,e.detail&&(0,a.jsx)(`span`,{className:`detail`,children:e.detail})]}),(0,a.jsx)(`span`,{className:`go`,children:e.action===`channels`?`open channels →`:`go to field →`})]},t))})]})}function _t(e){let t={},n={};return window.RUN_SECTIONS.forEach(r=>r.fields.forEach(r=>{let i=new Set(e.runs.map(e=>e.values[r.id]==null?``:String(e.values[r.id])));i.size===1?t[r.id]=[...i][0]:(t[r.id]=``,n[r.id]=i.size)})),{vals:t,mixed:n}}function vt({groups:e,active:t,onJump:n}){return(0,a.jsx)(`nav`,{className:`rail`,children:e.map(e=>(0,a.jsxs)(`div`,{className:`rail__grp`,children:[(0,a.jsx)(`div`,{className:`rail__hd`,children:e.title}),e.sections.map(e=>{let r=e.counts,i=r.reqTotal>0?r.reqFilled===r.reqTotal&&r.filled>0:r.filled===r.total&&r.total>0;return(0,a.jsxs)(`button`,{className:`railitem`+(t===e.id?` is-active`:``),onClick:()=>n(e.id),children:[(0,a.jsx)(`span`,{className:`railitem__dot`+(i?` is-done`:r.filled?` is-partial`:``)}),(0,a.jsx)(`span`,{className:`railitem__label`,children:e.label}),r.total>0&&(0,a.jsxs)(`span`,{className:`railitem__count`,children:[r.filled,`/`,r.total]})]},e.id)})]},e.key))})}function yt({bundle:e,selection:t,onSelect:n,density:r,onDensity:i,onEditDataset:o,onEditRun:s,onBulkSet:c,onUnitPolicy:l,onCopyPrev:u,onCommitDataset:d,onCommitRun:f,onCommitBulkRun:p,onCommitRunMatrix:m,onInspectChannels:h,onEvidence:g,onSupplemental:_,issuesOpen:v,onToggleIssues:y,onValidate:b,hasValidated:x,onExport:S,onJump:C,focusSection:w,toast:T}){let E=e.groups.find(e=>e.id===t.groupId)||e.groups[0],D=t.type===`run`,O=t.type===`grid`,k=D?E.runs.find(e=>e.id===t.runId)||E.runs[0]:null,A=k?E.runs.indexOf(k):-1,[ee,te]=tt(null),[j,M]=tt(null),[N,ne]=tt({}),[re,P]=tt(null),F=rt(null),I=rt({}),L=rt(null),R=e=>ne(t=>t[e]?t:{...t,[e]:!0}),z=nt(()=>_t(E),[E]),ie=e.dataset.values,ae=window.DATASET_SECTIONS.map(e=>({...e,counts:window.sectionCounts(window.visibleFields(e.fields,ie,r),ie)})),oe=D?window.RUN_SECTIONS.map(e=>({...e,counts:window.sectionCounts(window.visibleFields(e.fields,k.values,r),k.values)})):[],se=t.type===`dataset`?window.RUN_SECTIONS.map(e=>({...e,counts:window.sectionCounts(window.visibleFields(e.fields,z.vals,r),z.vals)})):[],ce=t.type===`dataset`?mt(E):null,le=ce?{id:`channels-shared`,label:`Parsed channels`,counts:(()=>{let e=ce.filter(e=>e.issues.length===0).length;return{filled:e,total:ce.length,reqTotal:ce.length,reqFilled:e}})()}:null,B=D?[{key:`run`,title:`RUN — `+k.id,sections:oe},{key:`ds`,title:`DATASET — shared · `+E.runs.length+` runs`,sections:ae}]:[{key:`ds`,title:`DATASET — shared across `+E.runs.length+` runs`,sections:ae},{key:`runshared`,title:`RUNS — SHARED`,sections:[...se,le].filter(Boolean)}],ue=B.flatMap(e=>e.sections),de=e=>{te(e);let t=I.current[e],n=F.current;t&&n&&(n.scrollTop=t.offsetTop-8)},fe=()=>{let e=F.current;if(!e)return;let t=null;ue.forEach(n=>{let r=I.current[n.id];r&&r.offsetTop-16<=e.scrollTop&&(t=n.id)}),t&&t!==ee&&te(t)};it(()=>{if(te(ue[0]&&ue[0].id),F.current&&(F.current.scrollTop=0),P(null),L.current&&F.current){let e=L.current;L.current=null,requestAnimationFrame(()=>{let t=F.current&&F.current.querySelector(`[data-fkey="`+e+`"]`);t&&(t.focus(),t.select&&t.select(),t.scrollIntoViewIfNeeded&&t.scrollIntoViewIfNeeded())})}},[t.type,t.runId,t.groupId]),it(()=>{w&&w.sectionId&&requestAnimationFrame(()=>{if(de(w.sectionId),w.fieldId&&F.current){let e=F.current.querySelector(`[data-fkey="`+w.fieldId+`"]`);e&&(e.focus(),e.select&&e.select())}})},[w]);let pe=e=>{if(e.key===`Enter`){if(e.altKey){e.preventDefault();let t=[...F.current.querySelectorAll(`[data-req="1"]`)],n=t.indexOf(document.activeElement),r=[...t.slice(n+1),...t.slice(0,n+1)].find(e=>!e.value);r&&(r.focus(),r.select&&r.select())}else if((e.metaKey||e.ctrlKey)&&D&&A<E.runs.length-1){e.preventDefault();let t=document.activeElement&&document.activeElement.getAttribute(`data-fkey`);t&&(L.current=t),n({type:`run`,groupId:E.id,runId:E.runs[A+1].id})}}},me=(e,t,n)=>{t!==n&&P({fieldId:e.id,from:t,to:n})},V=(e,t,n)=>{P(null),l(E.id,e,t,n)},he=D?window.runReadiness(k,e.dataset):null,H=nt(()=>{let e=0,t=0,n=0,r=0;return window.DATASET_SECTIONS.forEach(i=>i.fields.forEach(i=>{if(!window.isVisible(i,ie))return;let a=window.effLevel(i,ie),o=window.isRecorded(i,ie[i.id])&&!window.fieldError(i,ie[i.id]);a===`required`&&(e++,o&&t++),a===`report`&&(n++,o&&r++)})),{req:e,ok:t,rep:n,repOk:r}},[e.dataset]),U=nt(()=>window.buildValidationReport(e),[e]),ge=U.errors.length+U.missing.length,W=e=>D&&e===`channel_preamble_summary`?(0,a.jsx)(pt,{run:k,onInspect:()=>h(E.id,k.id)}):null;return(0,a.jsxs)(`section`,{className:`core core--insert`,children:[(0,a.jsxs)(`header`,{className:`insrhd`,children:[(0,a.jsxs)(`div`,{className:`insrhd__row`,children:[(0,a.jsxs)(`div`,{className:`insrhd__scope`,children:[D?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`scopekind scopekind--run`,children:`RUN`}),(0,a.jsxs)(`div`,{className:`stepper`,children:[(0,a.jsx)(`button`,{className:`stepper__btn`,disabled:A<=0,onClick:()=>n({type:`run`,groupId:E.id,runId:E.runs[A-1].id}),children:`‹`}),(0,a.jsxs)(`span`,{className:`stepper__label`,children:[(0,a.jsx)(`b`,{className:`mono`,children:k.id}),(0,a.jsxs)(`span`,{className:`stepper__of`,children:[A+1,` of `,E.runs.length]})]}),(0,a.jsx)(`button`,{className:`stepper__btn`,disabled:A>=E.runs.length-1,onClick:()=>n({type:`run`,groupId:E.id,runId:E.runs[A+1].id}),children:`›`})]}),(0,a.jsx)(`span`,{className:`insrhd__spec mono`,children:k.values.specimen_name||k.fileLabel})]}):(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`scopekind `+(O?`scopekind--bulk`:`scopekind--ds`),children:O?`GRID`:`DATASET`}),(0,a.jsx)(`span`,{className:`insrhd__title`,children:E.name})]}),(0,a.jsxs)(`div`,{className:`scopepills`,children:[(0,a.jsx)(`button`,{className:t.type===`dataset`?`is-active`:``,onClick:()=>n({type:`dataset`,groupId:E.id}),children:`Shared metadata`}),(0,a.jsx)(`button`,{className:O?`is-active`:``,onClick:()=>n({type:`grid`,groupId:E.id}),children:`⊞ Grid · all runs`})]})]}),(0,a.jsx)(`div`,{className:`insrhd__controls`,children:(0,a.jsxs)(`label`,{className:`density`,title:`Field visibility`,children:[(0,a.jsx)(`span`,{className:`density__ic`,children:`☰`}),(0,a.jsxs)(`select`,{value:r,onChange:e=>i(e.target.value),children:[(0,a.jsx)(`option`,{value:`essential`,children:`Required only`}),(0,a.jsx)(`option`,{value:`core`,children:`Required + recommended`}),(0,a.jsx)(`option`,{value:`all`,children:`All fields`})]})]})})]}),(0,a.jsxs)(`div`,{className:`insrprog`,children:[D&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`div`,{className:`insrprog__bar`,children:(0,a.jsx)(`span`,{className:`insrprog__fill`,style:{width:(he.missing.length+he.errors.length===0?100:Math.max(8,100-(he.missing.length+he.errors.length)*22))+`%`}})}),(0,a.jsx)(`span`,{className:`insrprog__txt`,children:he.ready?(0,a.jsx)(`span`,{className:`insrprog__ok`,children:`✓ run is export-ready`}):(0,a.jsxs)(a.Fragment,{children:[he.missing.length>0&&(0,a.jsxs)(`span`,{className:`insrprog__warn`,children:[he.missing.length,` required missing`]}),he.errors.length>0&&(0,a.jsxs)(`span`,{className:`insrprog__err`,children:[` · `,he.errors.length,` error`,he.errors.length>1?`s`:``]}),he.chIssues>0&&(0,a.jsxs)(`span`,{className:`insrprog__err`,children:[` · `,he.chIssues,` channel`,he.chIssues>1?`s`:``]}),!he.datasetOk&&(0,a.jsx)(`span`,{className:`insrprog__warn`,children:` · dataset incomplete`})]})}),A>0&&(0,a.jsxs)(`button`,{className:`linkbtn`,title:`Fill empty fields from the previous run`,onClick:()=>u(E.id,k.id),children:[`⧉ copy from `,E.runs[A-1].id]})]}),t.type===`dataset`&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`div`,{className:`insrprog__bar`,children:(0,a.jsx)(`span`,{className:`insrprog__fill`,style:{width:(H.req?H.ok/H.req*100:100)+`%`}})}),(0,a.jsxs)(`span`,{className:`insrprog__txt`,children:[(0,a.jsxs)(`b`,{children:[H.ok,`/`,H.req]}),` required · `,(0,a.jsxs)(`b`,{children:[H.repOk,`/`,H.rep]}),` report-required · applies to all `,E.runs.length,` runs`]})]}),O&&(0,a.jsxs)(`span`,{className:`bulknote`,children:[`One grid for everything: the `,(0,a.jsx)(`b`,{className:`bulknote__mix`,children:`⊞ All runs`}),` row fills every run; cells edit single runs; Excel paste works anywhere. `,(0,a.jsxs)(`b`,{children:[U.readyRuns,`/`,U.totalRuns]}),` runs ready.`]})]})]}),O?(0,a.jsx)(et,{bundle:e,group:E,selection:t,density:r,onCellSet:(e,t,n)=>s(E.id,e,t,n),onCellCommit:(e,t,n)=>f&&f(E.id,e,t,n),onCellBatchCommit:e=>m&&m(E.id,e),onBulkSet:(e,t)=>{c(E.id,e,t),p&&p(E.id,e,t)}}):(0,a.jsxs)(`div`,{className:`insrbody`,children:[(0,a.jsx)(vt,{groups:B,active:ee,onJump:de}),(0,a.jsxs)(`div`,{className:`formscroll`,ref:F,onScroll:fe,onKeyDown:pe,children:[t.type===`dataset`&&ae.map(e=>(0,a.jsx)(dt,{sec:e,values:ie,density:r,scope:`dataset`,scopeTag:`shared · all runs`,group:E,sharedCount:E.runs.length,focusKey:j,setFocusKey:M,touchedKeys:N,markTouched:R,validated:x,innerRef:t=>I.current[e.id]=t,onField:(e,t)=>o(e,t),onCommit:(e,t)=>d&&d(E.id,e,t),onUnitPick:me,pendingUnit:re,onUnitApply:V,onUnitCancel:()=>P(null)},e.id)),t.type===`dataset`&&(0,a.jsx)(`div`,{className:`scopedivider scopedivider--bulk`,children:(0,a.jsxs)(`span`,{children:[`Runs — shared · identical on every run · typing here fills all `,E.runs.length]})}),t.type===`dataset`&&se.map(e=>(0,a.jsx)(dt,{sec:e,values:z.vals,ctxValues:z.vals,density:r,scope:`shared-run`,scopeTag:`runs · shared`,group:E,mixedMap:z.mixed,sharedCount:E.runs.length,focusKey:j,setFocusKey:M,touchedKeys:N,markTouched:R,validated:x,unitFor:e=>E.units[e.id],innerRef:t=>I.current[e.id]=t,onField:(e,t)=>c(E.id,e,t,!0),onCommit:(e,t)=>p&&p(E.id,e,t),onUnitPick:me,pendingUnit:re,onUnitApply:V,onUnitCancel:()=>P(null)},e.id)),t.type===`dataset`&&(0,a.jsx)(ht,{group:E,innerRef:e=>I.current[`channels-shared`]=e,onInspect:e=>h(E.id,e)}),t.type===`dataset`&&(0,a.jsx)(`div`,{className:`formfoot`,children:(0,a.jsxs)(`button`,{className:`rowbtn`,onClick:_,children:[(0,a.jsx)(`span`,{children:`▤`}),` Manage supplemental files…`,(0,a.jsxs)(`span`,{className:`cnt`,children:[(e.supplemental||[]).length,` files`]})]})}),D&&oe.map(e=>(0,a.jsx)(dt,{sec:e,values:k.values,density:r,scope:`run`,group:E,sharedCount:E.runs.length,focusKey:j,setFocusKey:M,touchedKeys:N,markTouched:R,validated:x,unitFor:e=>E.units[e.id],innerRef:t=>I.current[e.id]=t,onField:(e,t)=>s(E.id,k.id,e,t),onCommit:(e,t)=>f&&f(E.id,k.id,e,t),onUnitPick:me,pendingUnit:re,onUnitApply:V,onUnitCancel:()=>P(null),onApplyAll:e=>{c(E.id,e,k.values[e]),p&&p(E.id,e,k.values[e])},children:W(e.id)},e.id)),D&&(0,a.jsx)(`div`,{className:`formfoot`,style:{marginTop:`14px`},children:(0,a.jsxs)(`button`,{className:`rowbtn`,onClick:()=>g(E.id,k.id),children:[(0,a.jsx)(`span`,{children:`▣`}),` Manage run image evidence…`,(0,a.jsxs)(`span`,{className:`cnt`,children:[(k.evidence||[]).length,` images`]})]})}),D&&(0,a.jsx)(`div`,{className:`scopedivider`,children:(0,a.jsxs)(`span`,{children:[`Shared dataset metadata — edited once, applied to all `,E.runs.length,` runs`]})}),D&&ae.map(e=>(0,a.jsx)(dt,{sec:e,values:ie,density:r,scope:`dataset`,scopeTag:`shared`,group:E,sharedCount:E.runs.length,focusKey:j,setFocusKey:M,touchedKeys:N,markTouched:R,validated:x,innerRef:t=>I.current[e.id]=t,onField:(e,t)=>o(e,t),onCommit:(e,t)=>d&&d(E.id,e,t),onUnitPick:me,pendingUnit:re,onUnitApply:V,onUnitCancel:()=>P(null)},e.id))]})]}),v&&(0,a.jsx)(gt,{bundle:e,onJump:C,onOpenChannels:e=>h(e.groupId,e.runId),onClose:y}),(0,a.jsxs)(`footer`,{className:`insrfoot`,children:[(0,a.jsxs)(`div`,{className:`legend`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--req`,children:`*`}),` Required (export)`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--rep`,children:`†`}),` Required for report`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`span`,{className:`mk mk--rec`,children:`**`}),` Recommended`]})]}),(0,a.jsxs)(`div`,{className:`insrfoot__actions`,children:[x?(0,a.jsx)(`button`,{className:`issuechip`+(ge?` has-issues`:``),onClick:y,title:`Toggle the issues drawer`,children:ge?`⚠ `+ge+` issue`+(ge>1?`s`:``):`✓ no issues`}):(0,a.jsx)(`button`,{className:`btn btn--ghost btn--sm`,onClick:b,children:`✓ Validate`}),(0,a.jsx)(`button`,{className:`btn btn--primary btn--sm`,onClick:S,children:`⬇ Export…`})]})]}),T&&(0,a.jsxs)(`div`,{className:`toast`,children:[(0,a.jsx)(`span`,{children:T.msg}),T.undo&&(0,a.jsx)(`button`,{className:`toast__undo`,onClick:T.undo,children:`Undo`})]})]})}Object.assign(window,{InsertPanel:yt});var{useState:J,useEffect:bt,useRef:xt}=i.default;function St(){let[e,t]=J(`empty`),[n,r]=J(null),[i,o]=J({type:`dataset`,groupId:`g1`}),[s,c]=J(`core`),[u,d]=J(null),[f,p]=J(null),[m,h]=J(null),[g,_]=J(null),[v,y]=J(!1),[b,x]=J(!1),[S,C]=J(null),[w,T]=J(null),[E,D]=J(null),[O,k]=J(window.SCHEMA_CANDIDATES),[A,ee]=J([]),[te,j]=J(null),[M,N]=J(null),[ne,re]=J([]),[P,F]=J(null),[,I]=J(0),L=xt(null),R=xt([]),z=xt([]),ie=xt(null),ae=xt(null),oe=xt(null),se=e=>{L.current=e,r(e)},ce=e=>{U(e?.bundle?.schemaForm||e?.bundle?.schema_form||e?.schemaForm||e?.schema_form||e?.schema?.form);let t=H(e);t.length&&(k(t),window.SCHEMA_CANDIDATES=t)},le=(e,n)=>{if(!e?.bundle){let e=`Backend package did not return a displayable bundle.`;return D(e),B(e),!1}return R.current=[],z.current=[],ie.current=null,I(0),U(e.bundle.schemaForm||e.bundle.schema_form||e.schemaForm||e.schema_form||e.schema?.form),T(e),ce(e),ee([]),j(null),N(null),re([]),F(null),D(null),se(e.bundle),t(`editor`),o({type:`dataset`,groupId:e.bundle.groups?.[0]?.id||null}),y(!1),x(!1),C(null),d(null),n&&B(n),!0},B=(e,t)=>{_({msg:e,undo:t||null}),clearTimeout(ae.current),ae.current=setTimeout(()=>_(null),t?4200:2600)},ue=(e,t,n)=>{let r=L.current;if(!r)return;let i=t(r);if(!i||i===r)return;let a=n&&n.coalesce||null;a&&ie.current===a&&R.current.length||(R.current.push({bundle:r,label:e}),R.current.length>80&&R.current.shift(),z.current=[]),ie.current=a,se(i),I(R.current.length)},de=()=>{let e=R.current.pop();!e||!L.current||(z.current.push({bundle:L.current,label:e.label}),ie.current=null,se(e.bundle),I(R.current.length),B(`↩ Undid `+e.label))},fe=()=>{let e=z.current.pop();!e||!L.current||(R.current.push({bundle:L.current,label:e.label}),ie.current=null,se(e.bundle),I(R.current.length),B(`↪ Redid `+e.label))},pe=xt();pe.current=de;let me=xt();me.current=fe,bt(()=>{let e=e=>{(e.metaKey||e.ctrlKey)&&(e.key===`z`||e.key===`Z`)&&(e.preventDefault(),e.shiftKey?me.current():pe.current())};return document.addEventListener(`keydown`,e),()=>document.removeEventListener(`keydown`,e)},[]),bt(()=>{let e=!0,t=window.desktopApi?.packaging;return t?.createSession&&t.createSession().then(t=>{if(e){if(t?.status===`ok`){T(t.data),ce(t.data),D(null);return}window.desktopApi?.host&&D(t?.message||`Backend packaging session unavailable.`)}}).catch(t=>{e&&window.desktopApi?.host&&D(t?.message||`Backend packaging session unavailable.`)}),()=>{e=!1}},[]);let V=async()=>{if(w?.session_id)return w;let e=window.desktopApi?.packaging;if(!e?.createSession)throw Error(`Desktop backend bridge is not available.`);let t=await e.createSession();if(t?.status!==`ok`)throw Error(t?.message||`Backend packaging session unavailable.`);return T(t.data),ce(t.data),ee([]),D(null),t.data},he=async()=>{let e=window.desktopApi?.packaging;if(!e?.openPackageDialog){let e=`Open MTDP package requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),n=await e.openPackageDialog({session_id:t.session_id});if(n?.status===`ok`){let e=n.data?.source_summary?.package_path,t=e?e.split(/[\\/]/).pop():`package`;le(n.data,`Opened MTDP package: `+t);return}if(n?.error_type===`Cancelled`)return;let r=n?.message||`Could not open MTDP package.`;D(r),B(`Could not open MTDP package: `+r)}catch(e){let t=e?.message||`Could not open MTDP package.`;D(t),B(`Could not open MTDP package: `+t)}},ge=async(e=`folder`)=>{let t=window.desktopApi?.packaging;if(!t?.openSourcesDialog){let e=`Open source files requires the desktop backend bridge.`;D(e),B(e);return}try{let n=await V(),r=await t.openSourcesDialog({session_id:n.session_id,kind:e});if(r?.status===`ok`){let t=Number(r.data?.source_summary?.source_count||0),n=e===`files`?`source files`:`source folder`,i=t?` (`+t+` source file`+(t===1?``:`s`)+`)`:``;le(r.data,`Loaded `+n+i);return}if(r?.error_type===`Cancelled`)return;let i=r?.message||`Could not open source files.`;D(i),B(`Could not open source files: `+i)}catch(e){let t=e?.message||`Could not open source files.`;D(t),B(`Could not open source files: `+t)}},W=async e=>{let t=window.desktopApi?.packaging;if(!t?.loadSources){let e=`Dropped source files require the desktop backend bridge.`;D(e),B(e);return}try{let n=await V(),r=await t.loadSources({session_id:n.session_id,paths:e});if(r?.status===`ok`){let t=Number(r.data?.source_summary?.source_count||e.length||0),n=t?` (`+t+` source file`+(t===1?``:`s`)+`)`:``;le(r.data,`Loaded dropped source paths`+n);return}let i=r?.message||`Could not load dropped source files.`;D(i),B(`Could not load dropped source files: `+i)}catch(e){let t=e?.message||`Could not load dropped source files.`;D(t),B(`Could not load dropped source files: `+t)}};bt(()=>{let e=e=>{let t=K(e);t.length&&W(t)};return window.addEventListener(Fe,e),()=>window.removeEventListener(Fe,e)},[w]),bt(()=>{if(!(e!==`editor`||!n))return clearTimeout(oe.current),oe.current=setTimeout(()=>{let e=new Date;C(String(e.getHours()).padStart(2,`0`)+`:`+String(e.getMinutes()).padStart(2,`0`))},600),()=>clearTimeout(oe.current)},[n,e]);let _e=e=>{if(e&&e.endsWith(`__unit`)){let t=window.ALL_FIELDS[e.slice(0,-6)];return(t?t.label:e)+` unit`}let t=window.ALL_FIELDS[e];return t?t.label:e},ve=e=>e&&e.backendValidation?{...e,backendValidation:null}:e,ye=(e,t)=>{x(!1),ue(`edit “`+_e(e)+`”`,n=>({...ve(n),dataset:{...n.dataset,values:{...n.dataset.values,[e]:t}}}),{coalesce:`ds:`+e})},be=(e,t,n,r)=>{x(!1),ue(`edit `+t+` · `+_e(n),i=>({...ve(i),groups:i.groups.map(i=>i.id===e?{...i,runs:i.runs.map(e=>e.id===t?{...e,values:{...e.values,[n]:r}}:e)}:i)}),{coalesce:`run:`+t+`:`+n})},xe=e=>{if(e?.status!==`ok`){let t=e?.message||`Could not synchronize metadata edit.`;return D(t),B(`Could not synchronize metadata edit: `+t),!1}return T(e.data),ce(e.data),ee([]),D(null),!0},Se=(e,t)=>{if(e?.status!==`ok`){let t=e?.message||`Could not synchronize backend mutation.`;return D(t),B(`Could not synchronize backend mutation: `+t),!1}return T(e.data),ce(e.data),ee([]),D(null),x(!1),U(e.data?.bundle?.schemaForm||e.data?.bundle?.schema_form||e.data?.schemaForm||e.data?.schema_form||e.data?.schema?.form),e.data?.bundle&&se(e.data.bundle),t&&B(t),!0},Ce=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.updateDatasetFields){if(window.desktopApi?.host){let e=`Dataset metadata edits require the desktop backend bridge.`;D(e),B(e)}return}try{let i=await V();xe(await r.updateDatasetFields({session_id:i.session_id,group_id:e,patch:{[t]:n}}))}catch(e){let t=e?.message||`Could not synchronize dataset metadata edit.`;D(t),B(`Could not synchronize dataset metadata edit: `+t)}},Te=async(e,t,n,r)=>{let i=window.desktopApi?.packaging;if(!i?.updateRunFields){if(window.desktopApi?.host){let e=`Run metadata edits require the desktop backend bridge.`;D(e),B(e)}return}try{let a=await V();xe(await i.updateRunFields({session_id:a.session_id,group_id:e,run_id:t,patch:{[n]:r}}))}catch(e){let t=e?.message||`Could not synchronize run metadata edit.`;D(t),B(`Could not synchronize run metadata edit: `+t)}},Ee=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.updateGroupRunFields){if(window.desktopApi?.host){let e=`Bulk run metadata edits require the desktop backend bridge.`;D(e),B(e)}return}try{let i=await V();Se(await r.updateGroupRunFields({session_id:i.session_id,group_id:e,patch:{[t]:n}}))}catch(e){let t=e?.message||`Could not synchronize bulk run metadata edit.`;D(t),B(`Could not synchronize bulk run metadata edit: `+t)}},Oe=async(e,t)=>{let n=window.desktopApi?.packaging;if(!(!t||t.length===0)){if(!n?.updateRunFieldMatrix){if(window.desktopApi?.host){let e=`Grid paste metadata edits require the desktop backend bridge.`;D(e),B(e)}return}try{let r=await V();Se(await n.updateRunFieldMatrix({session_id:r.session_id,group_id:e,updates:t}))}catch(e){let t=e?.message||`Could not synchronize pasted grid metadata.`;D(t),B(`Could not synchronize pasted grid metadata: `+t)}}},Pe=(e,t,n,r)=>{if(x(!1),ue(`⊞ “`+_e(t)+`” → all runs`,r=>({...ve(r),groups:r.groups.map(r=>r.id===e?{...r,runs:r.runs.map(e=>({...e,values:{...e.values,[t]:n}}))}:r)}),r?{coalesce:`bulk:`+e+`:`+t}:void 0),!r){let r=L.current.groups.find(t=>t.id===e);B(`⊞ “`+_e(t)+`” = `+n+` applied to all `+(r?r.runs.length:``)+` runs`,()=>pe.current())}},Ie=async(e,t,n,r)=>{let i=L.current.groups.find(t=>t.id===e),a=i&&i.units[t.id]||t.stdUnit;if(a===n)return;let o=window.desktopApi?.packaging;if(!o?.setGroupRunUnit){if(window.desktopApi?.host){let e=`Group unit policy changes require the desktop backend bridge.`;D(e),B(e)}return}try{let i=await V();Se(await o.setGroupRunUnit({session_id:i.session_id,group_id:e,field_id:t.id,unit:n,convert:r}),(r?`Converted “`:`Relabelled “`)+t.label+`” `+a+` → `+n+` on all runs`)}catch(e){let t=e?.message||`Could not synchronize group unit policy.`;D(t),B(`Could not synchronize group unit policy: `+t)}},Le=(e,t)=>{let n=L.current.groups.find(t=>t.id===e),r=n?n.runs.findIndex(e=>e.id===t):-1;if(!n||r<=0)return;let i=n.runs[r-1],a={specimen_name:1,sample_id:1,failure_image_reference:1},o=0;ue(`copy from `+i.id+` → `+t,n=>({...n,groups:n.groups.map(n=>n.id===e?{...n,runs:n.runs.map(e=>{if(e.id!==t)return e;let n={...e.values};return Object.keys(i.values).forEach(e=>{a[e]||!window.isFilled(n[e])&&window.isFilled(i.values[e])&&(n[e]=i.values[e],o++)}),{...e,values:n}})}:n)})),B(o?`⧉ Copied `+o+` value`+(o>1?`s`:``)+` from `+i.id+` into `+t:`Nothing to copy — no empty fields with a value on `+i.id,o?()=>pe.current():null)},Be=async(e,t,n)=>{if(t===n)return;let r=window.desktopApi?.packaging;if(!r?.moveRun){if(window.desktopApi?.host){let e=`Moving runs requires the desktop backend bridge.`;D(e),B(e)}return}try{let i=await V(),a=await r.moveRun({session_id:i.session_id,run_id:e.id,from_group_id:t,target_group_id:n});if(Se(a)){let t=n===`__unassigned`?`Unassigned`:(a.data?.bundle?.groups||[]).find(e=>e.id===n)?.name;o({type:n===`__unassigned`?`dataset`:`run`,groupId:n===`__unassigned`?a.data?.bundle?.groups?.[0]?.id||null:n,runId:e.id}),B(e.id+` → `+(t||n))}}catch(e){let t=e?.message||`Could not move run.`;D(t),B(`Could not move run: `+t)}},Ve=async(e,t)=>{p(null);let n=(t||``).trim();if(!n)return;let r=window.desktopApi?.packaging;if(!r?.renameGroup){if(window.desktopApi?.host){let e=`Renaming groups requires the desktop backend bridge.`;D(e),B(e)}return}try{let t=await V();Se(await r.renameGroup({session_id:t.session_id,group_id:e,name:n}),`Group renamed`)}catch(e){let t=e?.message||`Could not rename group.`;D(t),B(`Could not rename group: `+t)}},He=async()=>{let e=window.desktopApi?.packaging;if(!e?.createGroup){if(window.desktopApi?.host){let e=`Creating groups requires the desktop backend bridge.`;D(e),B(e)}return}try{let t=await V(),n=await e.createGroup({session_id:t.session_id,name:`New group`});if(Se(n,`Group created — name it, then drag runs in`)){let e=n.data?.bundle?.groups||[],t=e[e.length-1];t&&(p(t.id),o({type:`dataset`,groupId:t.id}))}}catch(e){let t=e?.message||`Could not create group.`;D(t),B(`Could not create group: `+t)}},Ue=async e=>{let t=n.groups.find(t=>t.id===e);if(!t)return;let r=window.desktopApi?.packaging;if(!r?.deleteGroup){if(window.desktopApi?.host){let e=`Deleting groups requires the desktop backend bridge.`;D(e),B(e)}return}try{let n=await V(),a=await r.deleteGroup({session_id:n.session_id,group_id:e});if(!Se(a))return;if(i.groupId===e){let e=a.data?.bundle?.groups?.[0];o({type:`dataset`,groupId:e?e.id:null})}let s=t.runs.length;B(s===0?`Group deleted`:`Group deleted — `+s+` run`+(s===1?``:`s`)+` moved to Unassigned`)}catch(e){let t=e?.message||`Could not delete group.`;D(t),B(`Could not delete group: `+t)}f===e&&p(null)},We=(e,t,n,r)=>ue(`channel assignment · `+t,i=>({...i,groups:i.groups.map(i=>i.id===e?{...i,runs:i.runs.map(e=>e.id===t?{...e,channels:e.channels.map((e,t)=>t===n?{...e,...r}:e)}:e)}:i)}),{coalesce:`ch:`+t+`:`+n}),Ge=async()=>{let e=window.desktopApi?.packaging;if(!e?.proposeGroups){let e=`Proposing groups requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),n=await e.proposeGroups({session_id:t.session_id});if(n?.status===`ok`){let e=n.data?.proposals||[];ee(e),D(null),d({kind:`propose`,proposals:e}),e.length===0&&B(`No backend grouping proposals are available.`);return}let r=n?.message||`Could not propose groups.`;D(r),B(`Could not propose groups: `+r)}catch(e){let t=e?.message||`Could not propose groups.`;D(t),B(`Could not propose groups: `+t)}},Ke=async e=>{let t=window.desktopApi?.packaging;if(!t?.applyGroupingProposal){let e=`Applying grouping proposals requires the desktop backend bridge.`;D(e),B(e);return}try{let n=await V(),r=await t.applyGroupingProposal({session_id:n.session_id,proposal_id:e});if(!Se(r))return;let i=r.data?.bundle?.groups?.[0];o({type:`dataset`,groupId:i?i.id:null}),d(null),B(`Applied backend grouping proposal`)}catch(e){let t=e?.message||`Could not apply grouping proposal.`;D(t),B(`Could not apply grouping proposal: `+t)}},Je=async e=>{d(null);let t=O.find(t=>t.id===e);if(!t)return;let n=window.desktopApi?.packaging;if(!n?.setSchema){let e=`Changing schema requires the desktop backend bridge.`;D(e),B(e);return}try{let e=await V(),r=await n.setSchema({session_id:e.session_id,schema_id:t.id});if(r?.status===`ok`){le(r.data,t.detected?`Schema reset to detected: `+t.label:`Schema manually set to `+t.label+` v`+t.version+` — recorded in backend session`);return}let i=r?.message||`Could not change schema.`;D(i),B(`Could not change schema: `+i)}catch(e){let t=e?.message||`Could not change schema.`;D(t),B(`Could not change schema: `+t)}},Ye=async()=>{let e=window.desktopApi?.packaging;if(!e?.validateGroup){let e=`Validation requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),n=L.current?.groups?.find(e=>e.id===i.groupId)||L.current?.groups?.[0],r=await e.validateGroup({session_id:t.session_id,group_id:n?.id});if(r?.status===`ok`){le(r.data),y(!0),x(!0);let e=r.data?.bundle?.backendValidation,t=Number(e?.error_count||0);B(t?`Validation found `+t+` blocking issue`+(t===1?``:`s`):`Validation passed — group is export-ready`);return}let a=r?.message||`Could not validate package.`;D(a),B(`Could not validate package: `+a)}catch(e){let t=e?.message||`Could not validate package.`;D(t),B(`Could not validate package: `+t)}},Xe=async({initialDir:e,defaultName:t}={})=>{let n=window.desktopApi?.packaging;if(!n?.exportGroup){let e=`Export requires the desktop backend bridge.`;D(e),B(e);return}try{let r=await V(),a=L.current?.groups?.find(e=>e.id===i.groupId)||L.current?.groups?.[0],o=await n.exportGroup({session_id:r.session_id,group_id:a?.id,initial_dir:e,default_name:t});if(o?.error_type===`Cancelled`)return;if(o?.status!==`ok`){let e=o?.message||`Could not export package.`;D(e),B(`Could not export package: `+e);return}le(o.data);let s=o.data?.export;s?.path&&F(s.path),D(null),d(null),B(`✓ Exported `+(s?.fileName||`MTDP package`))}catch(e){let t=e?.message||`Could not export package.`;D(t),B(`Could not export package: `+t)}},Ze=async()=>{let e=window.desktopApi?.packaging;if(!e?.exportAllReady){let e=`Export all ready groups requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),n=await e.exportAllReady({session_id:t.session_id,initial_dir:`~/Documents/MTDP exports`});if(n?.error_type===`Cancelled`)return;if(n?.status!==`ok`){let e=n?.message||`Could not export ready groups.`;D(e),B(`Could not export ready groups: `+e);return}le(n.data);let r=n.data?.exportAll||n.data?.export_all||{},i=Number(r.exportedCount||0),a=Number(r.skippedCount||0),o=Array.isArray(r.exports)?r.exports.find(e=>e?.path):null;o?.path&&F(o.path),D(null),B(`✓ Exported `+i+` ready group`+(i===1?``:`s`)+(a?` · skipped `+a:``))}catch(e){let t=e?.message||`Could not export ready groups.`;D(t),B(`Could not export ready groups: `+t)}},Qe=async()=>{if(!P){B(`Export a package before opening Analysis.`);return}let e=window.__compressionSuiteOpenChild;if(typeof e!=`function`){let e=`Analysis handoff requires the desktop child-window shell.`;D(e),B(e);return}try{await e({screen:`analysis`,initial_package_path:P}),D(null),B(`Opened exported package in Analysis.`)}catch(e){let t=e?.message||`Could not open Analysis.`;D(t),B(`Could not open Analysis: `+t)}},$e=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.addImageEvidence){let e=`Adding image evidence requires the desktop backend bridge.`;D(e),B(e);return}try{let i=await V(),a=await r.addImageEvidence({session_id:i.session_id,group_id:e,run_id:t,view:n});if(a?.error_type===`Cancelled`)return;Se(a)}catch(e){let t=e?.message||`Could not add image evidence.`;D(t),B(`Could not add image evidence: `+t)}},et=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.removeImageEvidence){let e=`Removing image evidence requires the desktop backend bridge.`;D(e),B(e);return}try{let i=await V();Se(await r.removeImageEvidence({session_id:i.session_id,group_id:e,run_id:t,index:n}))}catch(e){let t=e?.message||`Could not remove image evidence.`;D(t),B(`Could not remove image evidence: `+t)}},tt=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.addSupplementalFiles){let e=`Adding supplemental files requires the desktop backend bridge.`;D(e),B(e);return}try{let i=await V(),a=await r.addSupplementalFiles({session_id:i.session_id,group_id:e,run_id:n===`run`?t:null,scope:n});if(a?.error_type===`Cancelled`)return;Se(a)}catch(e){let t=e?.message||`Could not add supplemental file.`;D(t),B(`Could not add supplemental file: `+t)}},nt=async(e,t,n)=>{let r=window.desktopApi?.packaging;if(!r?.removeSupplementalFile){let e=`Removing supplemental files requires the desktop backend bridge.`;D(e),B(e);return}try{let i=await V();Se(await r.removeSupplementalFile({session_id:i.session_id,group_id:e,run_id:t,index:n}))}catch(e){let t=e?.message||`Could not remove supplemental file.`;D(t),B(`Could not remove supplemental file: `+t)}},rt=async()=>{let e=window.desktopApi?.packaging;if(!e?.rematchYamlSidecars){let e=`YAML sidecar rematch requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),n=L.current?.groups?.find(e=>e.id===i.groupId)||L.current?.groups?.[0],r=await e.rematchYamlSidecars({session_id:t.session_id,group_id:n?.id,apply_all:!0});if(Se(r)){let e=r.data?.yamlRematch||r.data?.yaml_rematch||null;j(e),N(null),re([]),e&&B(`Re-matched YAML sidecars: `+e.pairedCount+`/`+e.runCount+` paired`)}}catch(e){let t=e?.message||`Could not re-match YAML sidecars.`;D(t),B(`Could not re-match YAML sidecars: `+t)}},it=()=>{let e=L.current?.groups?.find(e=>e.id===i.groupId)||L.current?.groups?.[0];return{activeGroup:e,yamlRun:(i.type===`run`?e?.runs?.find(e=>e.id===i.runId):null)||e?.runs?.find(e=>e.sidecarStatus&&e.sidecarStatus!==`No YAML`)}},at=async()=>{let e=window.desktopApi?.packaging;if(!e?.reviewYamlMapping){let e=`YAML mapping review requires the desktop backend bridge.`;D(e),B(e);return}try{let t=await V(),{activeGroup:n,yamlRun:r}=it(),i=await e.reviewYamlMapping({session_id:t.session_id,group_id:n?.id,run_id:r?.id});if(i?.status!==`ok`){let e=i?.message||`Could not review YAML mapping.`;D(e),B(`Could not review YAML mapping: `+e);return}let a=i.data?.yamlMappingReview||i.data?.yaml_mapping_review||null;N(a),re(a?.rows||[]),D(null),a&&B(`Loaded YAML mapping review for `+a.runId+`.`)}catch(e){let t=e?.message||`Could not review YAML mapping.`;D(t),B(`Could not review YAML mapping: `+t)}},ot=async e=>{let t=window.desktopApi?.packaging;if(!t?.applyYamlMappingProfile){let e=`Applying YAML mapping profiles requires the desktop backend bridge.`;D(e),B(e);return}if(!M){B(`Review YAML mapping before applying a profile.`);return}try{let n=await V(),r=await t.applyYamlMappingProfile({session_id:n.session_id,group_id:M.groupId,run_id:M.runId,profile_id:M.profileId,apply_all:M.applyAllDefault!==!1,mappings:(e||[]).map(e=>e.mapping||e)});if(Se(r)){let e=r.data?.yamlMapping||r.data?.yaml_mapping||null;N(null),re([]),e?(j({runCount:e.appliedCount,pairedCount:e.appliedCount,pairs:(e.runs||[]).map(t=>({runId:t.runId,csv:t.runId,yaml:t.yamlPath||e.profileId,status:t.status,paired:!0}))}),B(`Applied YAML mapping profile to `+e.appliedCount+` run`+(e.appliedCount===1?``:`s`)+`.`)):j(null)}}catch(e){let t=e?.message||`Could not apply YAML mapping profile.`;D(t),B(`Could not apply YAML mapping profile: `+t)}},st=e=>{d(null),e.type===`dataset`?o(e=>({type:`dataset`,groupId:e.groupId||`g1`})):o({type:`run`,groupId:e.groupId,runId:e.runId}),h({sectionId:e.sectionId,fieldId:e.fieldId,t:Date.now()})},q=n&&(n.groups.find(e=>e.id===i.groupId)||n.groups[0]),ct=n&&i.type===`run`&&q?q.runs.findIndex(e=>e.id===i.runId):-1,lt=r=>{let a=q&&q.runs[0],s=i.type===`run`?i.runId:a&&a.id;switch(r){case`open-files`:e===`empty`?ge(`files`):B(`Already open — close the package first (File ▸ Close package)`);break;case`open-folder`:e===`empty`?ge(`folder`):B(`Already open — close the package first (File ▸ Close package)`);break;case`open-package`:he();break;case`recent-sessions`:B(e===`editor`?`1 draft session — “`+n.name+`”, autosaved `+(S||`just now`):`No draft sessions yet — sessions autosave while you work`);break;case`export`:d({kind:`export`});break;case`export-all-ready`:Ze();break;case`open-export-analysis`:Qe();break;case`close-package`:t(`empty`),se(null),C(null),F(null),j(null),N(null),re([]),R.current=[],z.current=[],I(0),ee([]),y(!1),x(!1);break;case`undo`:de();break;case`redo`:fe();break;case`copy-prev`:q&&s&&Le(q.id,s);break;case`density-essential`:c(`essential`);break;case`density-core`:c(`core`);break;case`density-all`:c(`all`);break;case`open-grid`:q&&o({type:`grid`,groupId:q.id});break;case`source-files`:B(`Source files drawer is at the bottom of the left panel`);break;case`propose-groups`:Ge();break;case`new-group`:He();break;case`rename-group`:q&&p(q.id);break;case`delete-group`:q&&Ue(q.id);break;case`prev-run`:ct>0&&o({type:`run`,groupId:q.id,runId:q.runs[ct-1].id});break;case`next-run`:ct>=0&&ct<q.runs.length-1?o({type:`run`,groupId:q.id,runId:q.runs[ct+1].id}):ct<0&&a&&o({type:`run`,groupId:q.id,runId:a.id});break;case`channels`:q&&s&&d({kind:`channels`,groupId:q.id,runId:s});break;case`evidence`:q&&s&&d({kind:`evidence`,groupId:q.id,runId:s});break;case`validate`:Ye();break;case`rematch-yaml`:j(null),N(null),re([]),d({kind:`rematch`});break;case`supplemental`:d({kind:`supplemental`,groupId:q?.id||null,runId:i.type===`run`?i.runId:null});break;case`change-schema`:d({kind:`schema`});break;case`schema-ref`:{let e=O.find(e=>e.id===n?.schemaId)||O[0];B(e?`Schema reference: `+e.schema+` v`+e.version+` — field catalogue from backend registry`:`Schema reference unavailable — backend registry did not return candidates`);break}case`about`:d({kind:`section-guide`});break;default:break}},ut=e===`editor`&&n,dt=R.current[R.current.length-1],ft=z.current[z.current.length-1];return(0,a.jsxs)(`div`,{className:`appwin`,"data-screen-label":`Dataset Packaging app`,children:[(0,a.jsx)(we,{stage:e,bundle:n,density:s,runIdx:ct,runCount:q?q.runs.length:0,canUndo:R.current.length>0,canRedo:z.current.length>0,undoLabel:dt&&dt.label,redoLabel:ft&&ft.label,lastExportPath:P,onAction:lt}),(0,a.jsxs)(`div`,{className:`cores`,children:[ut?(0,a.jsx)(qe,{bundle:n,selection:i,onSelect:o,onMoveRun:Be,onInspectChannels:(e,t)=>d({kind:`channels`,groupId:e,runId:t}),onEvidence:(e,t)=>d({kind:`evidence`,groupId:e,runId:t}),onCopyPrev:Le,onProposeGroups:Ge,onNewGroup:He,onRenameGroup:Ve,onDeleteGroup:Ue,onRematchYaml:()=>{j(null),N(null),re([]),d({kind:`rematch`})},editingGroupId:f,onStartRename:p,onCancelRename:()=>p(null),onChangeSchema:()=>d({kind:`schema`})}):(0,a.jsx)(Re,{onStartIngest:()=>ge(`folder`),onDropSources:W,onOpenPackage:he}),ut&&n.groups.length>0?(0,a.jsx)(yt,{bundle:n,selection:i,onSelect:o,density:s,onDensity:c,onEditDataset:ye,onEditRun:be,onBulkSet:Pe,onCommitDataset:Ce,onCommitRun:Te,onCommitBulkRun:Ee,onCommitRunMatrix:Oe,onUnitPolicy:Ie,onCopyPrev:Le,onInspectChannels:(e,t)=>d({kind:`channels`,groupId:e,runId:t}),onEvidence:(e,t)=>d({kind:`evidence`,groupId:e,runId:t}),onSupplemental:()=>d({kind:`supplemental`,groupId:q?.id||null,runId:i.type===`run`?i.runId:null}),issuesOpen:v,onToggleIssues:()=>y(e=>!e),onValidate:Ye,hasValidated:b,onExport:()=>d({kind:`export`}),onJump:st,focusSection:m,toast:g}):(0,a.jsx)(ze,{}),ut&&u&&u.kind===`channels`&&(0,a.jsx)(De,{bundle:n,groupId:u.groupId,runId:u.runId,onAssign:We,onSelectRun:(e,t)=>d({kind:`channels`,groupId:e,runId:t}),onClose:()=>d(null)}),ut&&u&&u.kind===`export`&&(0,a.jsx)(ke,{bundle:n,onExport:Xe,onJump:st,onOpenChannels:e=>d({kind:`channels`,groupId:e.groupId,runId:e.runId}),onClose:()=>d(null)}),ut&&u&&u.kind===`propose`&&(0,a.jsx)(Ae,{proposals:u.proposals||A,onApply:Ke,onClose:()=>d(null)}),ut&&u&&u.kind===`schema`&&(0,a.jsx)(je,{bundle:n,candidates:O,onPick:Je,onClose:()=>d(null)}),ut&&u&&u.kind===`evidence`&&(0,a.jsx)(Me,{bundle:n,groupId:u.groupId,runId:u.runId,onAdd:$e,onRemove:et,onClose:()=>d(null)}),ut&&u&&u.kind===`supplemental`&&(0,a.jsx)(Ne,{bundle:n,groupId:u.groupId,runId:u.runId,onAdd:tt,onRemove:nt,onClose:()=>d(null)}),ut&&u&&u.kind===`rematch`&&(0,a.jsx)(G,{bundle:n,summary:te,review:M,mappingRows:ne,onRowsChange:re,onReviewMapping:at,onApplyMapping:ot,onRematch:rt,onClose:()=>d(null)}),u&&u.kind===`section-guide`&&(0,a.jsx)(l,{section:`dataset`,onClose:()=>d(null)})]}),(0,a.jsxs)(`div`,{className:`statusbar`,children:[(0,a.jsx)(`span`,{children:ut?`Package: `+n.name:`No package loaded`}),E&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{children:[`Backend unavailable: `,E]})]}),ut&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{children:[n.schemaLabel,` v`,n.schemaVersion,n.schemaOverridden?` (manual)`:``]})]}),(0,a.jsx)(`span`,{className:`statusbar__sp`}),ut&&S&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`span`,{className:`statusbar__save`,children:[`✓ saved `,S]}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsxs)(`span`,{children:[`draft “`,n.name,`”`]}),(0,a.jsx)(`span`,{className:`dot`,children:`·`})]}),ut&&(0,a.jsx)(`span`,{children:`raw files untouched`})]})]})}var Ct=`:root{
  --bg:#e9ebef; --doc:#f4f5f7;
  --panel:#ffffff; --panel-2:#f7f8fa; --panel-3:#eff1f4;
  --line:#e4e7ec; --line-2:#d6dae1; --line-3:#c4cad3;
  --ink:#1b2230; --ink-2:#48505f; --muted:#79818f; --faint:#9aa2b0;
  --accent:#2f6bd8; --accent-ink:#1f4fa8; --accent-wash:#eaf1fd;
  --ok:#1f9d57; --ok-wash:#e7f5ec; --warn:#c9820a; --warn-wash:#fcf3e2; --err:#d33b3b; --err-wash:#fcecec;
  --bulk:#5b3fae; --bulk-wash:#efeafc; --bulk-line:#d9cef2;
  --ds:#5b6b52; --ds-wash:#eef0ea; --ds-line:#cdd5c4;
  --r1:5px; --r2:7px; --r3:10px;
  --sh-1:0 1px 2px rgba(20,28,45,.06); --sh-2:0 6px 24px rgba(20,28,45,.10); --sh-3:0 18px 60px rgba(20,28,45,.16);
  --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
}
*{box-sizing:border-box;}
html,body{margin:0;}
body{font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--doc);color:var(--ink);-webkit-font-smoothing:antialiased;line-height:1.5;}

/* =========================== ANALYSIS (top) =========================== */
.analysis{max-width:1180px;margin:0 auto;padding:52px 32px 26px;}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent-ink);font-weight:600;}
.analysis h1{font-size:32px;line-height:1.14;margin:12px 0 10px;letter-spacing:-.02em;font-weight:700;}
.analysis .lede{font-size:16.5px;color:var(--ink-2);max-width:840px;margin:0 0 8px;text-wrap:pretty;}
.analysis .lede b{color:var(--ink);font-weight:600;}
.fixwrap{margin-top:26px;border:1px solid var(--line-2);border-radius:10px;overflow:hidden;background:var(--panel);box-shadow:var(--sh-1);}
.fixtable{border-collapse:collapse;width:100%;font-size:13px;}
.fixtable th{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);text-align:left;padding:9px 14px;background:var(--panel-2);border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;}
.fixtable td{padding:7px 14px;border-bottom:1px solid var(--line);vertical-align:top;}
.fixtable tr:last-child td{border-bottom:none;}
.fixtable .fid{font-family:var(--mono);font-size:11.5px;color:var(--accent-ink);white-space:nowrap;font-weight:500;}
.fixtable .what{font-weight:600;color:var(--ink);white-space:nowrap;}
.fixtable .how{color:var(--ink-2);font-size:12.5px;}
.fixtable .how .mono{font-family:var(--mono);font-size:11px;}
.fixtable .theme-td{color:var(--muted);font-size:11.5px;white-space:nowrap;}

.protolead{max-width:1180px;margin:38px auto 0;padding:0 32px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;}
.protolead .eyebrow{margin:0;}
.protolead .hint{color:var(--muted);font-size:13.5px;}
.protolead .hint b{color:var(--ink-2);font-weight:600;}

/* =========================== PROTOTYPE FRAME =========================== */
.stage{padding:18px 32px 70px;}
.appwin{max-width:1640px;margin:0 auto;height:880px;min-width:1180px;background:var(--bg);border:1px solid var(--line-3);
  border-radius:12px;overflow:hidden;display:flex;flex-direction:column;box-shadow:var(--sh-3);position:relative;}
@media (max-width:1240px){.stage{overflow-x:auto;}}

/* menu bar */
.menubar{height:30px;flex:0 0 auto;background:#fff;border-bottom:1px solid #e1e4e8;
  display:flex;align-items:center;gap:8px;padding:0 0 0 10px;font-size:12px;position:relative;z-index:70;user-select:none;-webkit-user-select:none;}
.menubar__title{font-weight:700;font-size:12px;letter-spacing:0;color:#1b1e23;white-space:nowrap;flex:0 0 auto;padding:0 4px;margin-right:0;}
.menubar__menus{display:flex;align-items:center;gap:2px;}
.menu{position:relative;}
.menu__btn{border:none;background:none;font:inherit;font-size:12px;color:#5a626c;padding:5px 9px;border-radius:4px;cursor:pointer;white-space:nowrap;}
.menu__btn:hover{background:#eef0f3;color:#1b1e23;}
.menu__btn.is-open{background:#eef0f3;color:#1b1e23;}
.menu__pop{position:absolute;top:28px;left:0;min-width:262px;background:#fff;border:1px solid #cbd0d6;border-radius:6px;box-shadow:0 8px 28px rgba(20,24,31,.16),0 2px 8px rgba(20,24,31,.10);padding:5px;z-index:90;}
.menu__item{display:flex;align-items:center;gap:8px;width:100%;border:none;background:none;font:inherit;text-align:left;font-size:13px;color:#1b1e23;padding:7px 9px;border-radius:4px;cursor:pointer;white-space:nowrap;}
.menu__item:hover:not(:disabled){background:#e7f1fb;color:#0a4d8c;}
.menu__item:disabled{color:var(--faint);cursor:default;}
.menu__item .chk{width:13px;flex:0 0 auto;color:#0f6cbd;font-size:11px;}
.menu__item .lab{flex:1 1 auto;overflow:hidden;text-overflow:ellipsis;max-width:300px;}
.menu__item .kbd{color:#8b929c;font-size:12px;font-family:var(--mono);}
.menu__sep{height:1px;background:#e1e4e8;margin:5px 4px;}
.menubar__schema{margin-left:0;border:none;background:none;font:inherit;color:#8b929c;font-size:12px;cursor:pointer;padding:5px 8px;border-radius:4px;white-space:nowrap;}
.menubar__schema b{color:#5a626c;font-weight:600;}
.menubar__schema:hover{background:#eef0f3;}
.menubar__schema:hover b{text-decoration:underline;}
.menubar__conf{color:#38591f;font-weight:600;margin-left:4px;}
.menubar__override{color:var(--bulk);font-weight:600;margin-left:4px;}

/* two cores */
.cores{flex:1 1 auto;display:grid;grid-template-columns:minmax(360px,1fr) minmax(760px,2.1fr);min-height:0;position:relative;}
.core{min-height:0;display:flex;flex-direction:column;background:var(--panel);}
.core--bundle{border-right:1px solid var(--line-2);background:var(--panel-2);}

/* ---------- BUNDLE header ---------- */
.bundlehd{flex:0 0 auto;padding:16px 18px 14px;border-bottom:1px solid var(--line);background:var(--panel);}
.bundlehd__top{display:flex;align-items:center;justify-content:space-between;gap:10px;}
.bundlehd__kind{font-size:10.5px;letter-spacing:.16em;font-weight:700;color:var(--faint);}
.schemachip{font-size:11.5px;font-weight:600;color:var(--accent-ink);background:var(--accent-wash);border:1px solid #d6e3fa;padding:3px 9px;border-radius:20px;cursor:pointer;}
.schemachip:hover{border-color:var(--accent);}
.bundlehd__name{font-size:21px;font-weight:700;letter-spacing:-.015em;margin:7px 0 6px;}
.bundlehd__meta{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);}
.bundlehd__meta b{color:var(--ink);font-weight:600;}
.bundlehd__meta .dot{color:var(--line-3);}
.bundlehd__ready{color:var(--accent-ink);font-weight:600;}
.bundlebar{height:5px;border-radius:4px;background:var(--panel-3);margin-top:11px;overflow:hidden;}
.bundlebar__fill{display:block;height:100%;background:linear-gradient(90deg,var(--accent),#3f86ec);border-radius:4px;transition:width .35s;}

/* toolbar */
.bundletools{flex:0 0 auto;display:flex;gap:8px;padding:11px 16px;border-bottom:1px solid var(--line);background:var(--panel-2);}
.btn{font:inherit;font-size:13px;font-weight:500;border:1px solid var(--line-2);background:#fff;color:var(--ink-2);border-radius:var(--r1);
  padding:7px 12px;cursor:pointer;display:inline-flex;align-items:center;gap:7px;transition:all .12s;white-space:nowrap;}
.btn:hover{border-color:var(--line-3);background:#fbfcfd;color:var(--ink);}
.btn .ic{font-size:13px;color:var(--accent);}
.btn--sm{padding:6px 11px;font-size:12.5px;}
.btn--ghost{background:transparent;}
.btn--primary{background:var(--accent);border-color:var(--accent);color:#fff;}
.btn--primary:hover{background:var(--accent-ink);border-color:var(--accent-ink);color:#fff;}
.btn--primary .ic{color:#fff;}
.btn:disabled{opacity:.45;cursor:default;}
.btn--lg{padding:11px 18px;font-size:14px;}

/* tree rows — v3: 4 columns (grip · name · status · kebab), F11-A */
.trow{display:grid;grid-template-columns:18px minmax(0,1fr) auto 30px;align-items:center;gap:8px;padding:0 12px 0 16px;font-size:13px;}
.trow--head{height:30px;flex:0 0 auto;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);border-bottom:1px solid var(--line);background:var(--panel-2);font-weight:600;}
.trow__grip{color:var(--line-3);font-size:10px;cursor:grab;user-select:none;}
.bundletree{flex:1 1 auto;overflow-y:auto;}
.groupblk{border-bottom:1px solid var(--line);}
.groupblk.is-dragover{background:var(--accent-wash);box-shadow:inset 0 0 0 2px #bcd2f6;}
.grouphd{display:grid;grid-template-columns:18px 18px minmax(0,1fr) auto auto auto auto;align-items:center;gap:8px;padding:10px 16px;cursor:pointer;background:var(--panel);transition:background .12s;}
.grouphd__bulk{border:none;background:none;font:inherit;font-size:11.5px;font-weight:600;color:#7a5bc7;cursor:pointer;opacity:0;white-space:nowrap;padding:0;}
.grouphd:hover .grouphd__bulk,.grouphd.is-selected .grouphd__bulk{opacity:1;}
.grouphd__bulk:hover{text-decoration:underline;}
.grouphd__del{border:none;background:none;font-size:12px;color:var(--faint);cursor:pointer;padding:1px 4px;border-radius:4px;opacity:0;white-space:nowrap;}
.grouphd:hover .grouphd__del,.grouphd.is-selected .grouphd__del{opacity:1;}
.grouphd__del:hover{color:#b5463f;background:#fdeceb;}
.grouphd:hover{background:#fafbfc;}
.grouphd.is-selected{background:var(--accent-wash);box-shadow:inset 3px 0 0 var(--accent);}
.grouphd__tw{border:none;background:none;font-size:11px;color:var(--muted);cursor:pointer;padding:0;width:18px;}
.grouphd__icon{color:var(--accent);font-size:13px;}
.grouphd__namewrap{display:flex;align-items:center;gap:5px;min-width:0;}
.grouphd__name{font-weight:600;font-size:14px;cursor:text;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.grouphd__pencil{border:none;background:none;font-size:11px;color:var(--faint);cursor:pointer;padding:1px 3px;border-radius:4px;opacity:0;flex:0 0 auto;}
.grouphd:hover .grouphd__pencil{opacity:1;}
.grouphd__pencil:hover{color:var(--accent);background:var(--accent-wash);}
.renamein{font:inherit;font-size:13.5px;font-weight:600;border:1px solid var(--accent);border-radius:4px;padding:1px 6px;width:100%;min-width:140px;box-shadow:0 0 0 3px var(--accent-wash);outline:none;}
.grouphd__count{font-size:12px;color:var(--muted);background:var(--panel-3);padding:2px 8px;border-radius:20px;white-space:nowrap;}
.grouphd__ready{font-size:12px;margin-left:2px;white-space:nowrap;}
.rdy--ok{color:var(--ok);font-weight:500;}
.rdy--warn{color:var(--warn);font-weight:500;}
.grouphd--muted{cursor:default;color:var(--muted);}
.grouphd--muted .grouphd__name{font-weight:500;color:var(--muted);cursor:default;}
.grouphd__hint{font-size:11.5px;color:var(--faint);font-style:italic;white-space:nowrap;}

.grouprows{background:var(--panel);}
.groupblk--empty .grouprows{padding:12px 16px;font-size:12px;color:var(--faint);font-style:italic;}
.trow--run{height:42px;cursor:pointer;border-top:1px solid #f1f3f6;transition:background .1s;}
.trow--run:hover{background:#f8fafc;}
.trow--run.is-selected{background:var(--accent-wash);box-shadow:inset 3px 0 0 var(--accent);}
.trow__name{display:flex;flex-direction:column;gap:0;min-width:0;}
.trow__runid{font-family:var(--mono);font-size:12.5px;color:var(--ink);font-weight:500;line-height:1.3;display:flex;align-items:center;gap:7px;}
.trow__spec{font-size:11.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1.25;}
.mono{font-family:var(--mono);}

/* F11-A: one consolidated status cell */
.rstat{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:500;white-space:nowrap;justify-self:end;}
.rstat__dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto;}
.rstat--ok{color:#177544;} .rstat--ok .rstat__dot{background:var(--ok);}
.rstat--warn{color:#9a6206;} .rstat--warn .rstat__dot{background:var(--warn);}
.rstat--err{color:#b32b2b;} .rstat--err .rstat__dot{background:var(--err);}
.rstat--amb{color:var(--accent-ink);} .rstat--amb .rstat__dot{background:var(--accent);}

/* F10-A: clickable channel chips + hover kebab */
.chip-ch{font:inherit;font-size:10px;font-weight:600;padding:1px 7px;border-radius:9px;white-space:nowrap;cursor:pointer;border:1px solid transparent;}
.chip-ch--err{background:var(--err-wash);color:#b32b2b;}
.chip-ch--err:hover{border-color:#e6b4b4;text-decoration:underline;}
.chip-ch--amb{background:var(--accent-wash);color:var(--accent-ink);}
.chip-ch--amb:hover{border-color:#bcd2f6;text-decoration:underline;}
.trow__kebabwrap{position:relative;justify-self:end;}
.kebab{border:1px solid var(--line-2);background:#fff;border-radius:5px;width:24px;height:22px;font-size:12px;color:var(--ink-2);line-height:1;cursor:pointer;visibility:hidden;}
.trow--run:hover .kebab,.kebab:focus{visibility:visible;}
.kebab:hover{border-color:var(--line-3);color:var(--ink);}
.rowpop{position:absolute;right:0;top:26px;background:#fff;border:1px solid var(--line-2);border-radius:8px;box-shadow:var(--sh-2);padding:4px;z-index:40;width:236px;display:flex;flex-direction:column;}
.rowpop button{display:flex;align-items:center;width:100%;border:none;background:none;font:inherit;font-size:12px;color:var(--ink);padding:6px 9px;border-radius:4px;text-align:left;gap:8px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.rowpop button:hover{background:var(--accent-wash);}

/* source files drawer */
.filesdrawer{flex:0 0 auto;border-top:1px solid var(--line);background:var(--panel-2);}
.filesdrawer__hd{width:100%;border:none;background:none;font:inherit;font-size:12.5px;font-weight:600;color:var(--ink-2);
  padding:10px 16px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;gap:8px;}
.filesdrawer__count{background:var(--panel-3);color:var(--muted);padding:1px 8px;border-radius:20px;font-size:11px;}
.filesdrawer__rematch{margin-left:auto;border:none;background:none;font:inherit;font-size:11.5px;color:var(--accent);cursor:pointer;}
.filesdrawer__rematch:hover{text-decoration:underline;}
.filesdrawer__list{list-style:none;margin:0;padding:0 16px 12px;display:flex;flex-direction:column;gap:5px;max-height:170px;overflow:auto;}
.filesdrawer__list li{font-size:11.5px;color:var(--ink-2);display:flex;gap:8px;align-items:center;font-family:var(--mono);}
.filesdrawer__list .ic{color:var(--faint);flex:0 0 auto;}
.filesdrawer__list .pair{color:var(--faint);}

/* ---------- INSERT panel ---------- */
.core--insert{background:var(--panel);}
.insrhd{flex:0 0 auto;padding:13px 20px 11px;border-bottom:1px solid var(--line);background:var(--panel);}
.insrhd__row{display:flex;align-items:center;justify-content:space-between;gap:14px;}
.insrhd__scope{display:flex;align-items:center;gap:12px;min-width:0;}
.scopekind{font-size:10.5px;letter-spacing:.12em;font-weight:700;padding:3px 8px;border-radius:5px;white-space:nowrap;}
.scopekind--run{background:var(--accent-wash);color:var(--accent-ink);}
.scopekind--ds{background:var(--ds-wash);color:var(--ds);}
.scopekind--bulk{background:var(--bulk-wash);color:var(--bulk);}
.stepper{display:flex;align-items:center;gap:2px;background:var(--panel-2);border:1px solid var(--line-2);border-radius:var(--r1);padding:2px;}
.stepper__btn{border:none;background:none;font-size:16px;line-height:1;color:var(--ink-2);cursor:pointer;width:26px;height:24px;border-radius:4px;}
.stepper__btn:hover:not(:disabled){background:#fff;color:var(--accent);}
.stepper__btn:disabled{color:var(--line-3);cursor:default;}
.stepper__label{display:flex;flex-direction:column;align-items:center;line-height:1.05;padding:0 4px;}
.stepper__label b{font-size:13px;}
.stepper__of{font-size:10px;color:var(--muted);}
.insrhd__spec{font-size:12.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.insrhd__title{font-size:16px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.scopepills{display:inline-flex;gap:2px;background:var(--panel-3);border:1px solid var(--line-2);border-radius:var(--r1);padding:2px;}
.scopepills button{border:none;background:none;font:inherit;font-size:12.5px;color:var(--ink-2);padding:5px 11px;border-radius:4px;cursor:pointer;white-space:nowrap;}
.scopepills button:hover{color:var(--ink);}
.scopepills button.is-active{background:#fff;color:var(--ink);font-weight:600;box-shadow:var(--sh-1);}
.insrhd__controls{display:flex;align-items:center;gap:10px;flex:0 0 auto;}
.density{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line-2);background:var(--panel-2);border-radius:var(--r1);padding:0 4px 0 9px;}
.density__ic{font-size:12px;color:var(--muted);}
.density select{border:none;background:none;font:inherit;font-size:12.5px;color:var(--ink-2);padding:6px 4px;cursor:pointer;}

.insrprog{display:flex;align-items:center;gap:12px;margin-top:11px;}
.insrprog__bar{flex:0 0 200px;height:6px;border-radius:4px;background:var(--panel-3);overflow:hidden;}
.insrprog__fill{display:block;height:100%;background:linear-gradient(90deg,var(--accent),#3f86ec);transition:width .3s;}
.insrprog__txt{font-size:12.5px;color:var(--ink-2);}
.insrprog__txt b{color:var(--ink);font-variant-numeric:tabular-nums;}
.insrprog__err{color:var(--err);font-weight:500;}
.insrprog__warn{color:var(--warn);font-weight:500;}
.insrprog__ok{color:var(--ok);font-weight:600;}
.linkbtn{margin-left:auto;border:none;background:none;font:inherit;font-size:12px;color:var(--accent);cursor:pointer;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;flex:0 0 auto;}
.linkbtn:hover:not(:disabled){text-decoration:underline;}
.linkbtn:disabled{color:var(--faint);cursor:default;}
.bulknote{font-size:12.5px;color:var(--ink-2);}
.bulknote b{color:var(--ink);}
.bulknote__mix{color:var(--bulk);font-weight:600;}

/* body: rail + form */
.insrbody{flex:1 1 auto;display:grid;grid-template-columns:232px 1fr;min-height:0;}
.rail{border-right:1px solid var(--line);background:var(--panel-2);overflow-y:auto;padding:8px 0;}
.rail__grp{margin-bottom:8px;}
.rail__hd{font-size:10px;letter-spacing:.07em;font-weight:700;color:var(--faint);padding:8px 16px 5px;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.railitem{width:100%;border:none;background:none;font:inherit;display:flex;align-items:center;gap:9px;padding:7px 14px 7px 16px;cursor:pointer;text-align:left;border-left:2px solid transparent;}
.railitem:hover{background:#eef1f4;}
.railitem.is-active{background:#fff;border-left-color:var(--accent);}
.railitem.is-active .railitem__label{color:var(--ink);font-weight:600;}
.railitem__dot{width:8px;height:8px;border-radius:50%;border:1.5px solid var(--line-3);flex:0 0 auto;}
.railitem__dot.is-partial{background:var(--warn);border-color:var(--warn);}
.railitem__dot.is-done{background:var(--ok);border-color:var(--ok);}
.railitem__label{flex:1 1 auto;font-size:12.5px;color:var(--ink-2);line-height:1.25;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.railitem__count{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;}

.formscroll{overflow-y:auto;padding:6px 26px 30px;position:relative;}

/* F9-A: persistent scope tinting — continuous left border + wash per scope */
.formsec{padding:18px 14px 6px 16px;border-bottom:1px solid var(--line);border-left:3px solid transparent;margin:0 -14px 0 -16px;padding-left:16px;}
.formsec--run{border-left-color:#bcd2f6;}
.formsec--dataset{border-left-color:var(--ds-line);background:linear-gradient(90deg,#f7f8f4,rgba(247,248,244,0) 320px);}
.formsec--shared-run{border-left-color:var(--bulk-line);background:linear-gradient(90deg,#faf8ff,rgba(250,248,255,0) 320px);}
.formsec__hd{display:flex;align-items:center;gap:10px;margin-bottom:14px;}
.formsec__title{font-size:14px;font-weight:600;margin:0;}
.formsec__scope{font-size:10.5px;font-weight:600;letter-spacing:.04em;padding:2px 7px;border-radius:5px;text-transform:uppercase;}
.formsec__scope--dataset{color:var(--ds);background:var(--ds-wash);}
.formsec__scope--shared-run{color:var(--bulk);background:var(--bulk-wash);}
.formsec__scope--run{color:var(--accent-ink);background:var(--accent-wash);}
.formsec__count{margin-left:auto;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums;background:var(--panel-2);border:1px solid var(--line);padding:2px 9px;border-radius:20px;}

.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:13px 20px;}
.field{display:flex;flex-direction:column;gap:5px;grid-column:span 2;}
.field--half{grid-column:span 1;}
.field__label{font-size:12.5px;color:var(--ink-2);font-weight:500;display:flex;align-items:center;gap:4px;}
.mk{font-weight:700;font-size:11px;}
.mk--req{color:var(--err);}
.mk--rep{color:#9a6206;}
.mk--rec{color:var(--warn);}
.field__control{display:flex;flex-direction:column;gap:3px;position:relative;}
.field__inputwrap{display:flex;gap:7px;}
.inpfield{position:relative;flex:1 1 auto;display:flex;min-width:0;}
.inpfield .inp{padding-right:30px;}
.vchk{position:absolute;top:50%;transform:translateY(-50%);right:9px;width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;pointer-events:none;}
.inpfield--select .vchk{right:28px;}
.vchk--ok{background:var(--ok-wash);color:#177544;}
.vchk--err{background:var(--err-wash);color:#b32b2b;}
.typehint{font-size:10px;color:var(--muted);background:var(--panel-2);border:1px solid var(--line);border-radius:3px;padding:1px 5px;font-family:var(--mono);white-space:nowrap;}
.inp{flex:1 1 auto;font:inherit;font-size:13.5px;color:var(--ink);background:#fff;border:1px solid var(--line-2);border-radius:var(--r1);padding:8px 10px;min-width:0;transition:border .12s,box-shadow .12s;}
.inp:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-wash);}
select.inp{cursor:pointer;}
.unit{flex:0 0 76px;font:inherit;font-size:13px;color:var(--ink-2);background:var(--panel-2);border:1px solid var(--line-2);border-radius:var(--r1);padding:8px 6px;cursor:pointer;}
.field.is-required .inp{border-color:#e8d3a6;background:#fffdf8;}
.field.is-error .inp{border-color:#e6b4b4;background:#fffafa;}
.field.is-filled .field__label{color:var(--ink);}
.field__under{display:flex;align-items:center;gap:10px;min-height:17px;flex-wrap:wrap;row-gap:3px;}
.msg{font-size:11.5px;}
.msg--err{color:var(--err);}
.msg--req{color:var(--warn);}
.msg--rep{color:#9a6206;}
.msg--mixed{color:#7a5bc7;}
.field.is-mixed .inp{border-color:var(--bulk-line);background:#faf8ff;}
.field.is-mixed .inp::placeholder{color:#9a86d6;font-style:italic;}
.field.is-mixed .field__label{color:var(--bulk);}
.applyall{margin-left:auto;border:none;background:none;font:inherit;font-size:11px;color:var(--accent);cursor:pointer;opacity:0;transition:opacity .12s;}
.field:hover .applyall{opacity:1;}
.applyall:hover{text-decoration:underline;}

/* F2-A: blast-radius microcopy + self-teaching shortcut hints */
.focusinfo{display:flex;align-items:center;gap:10px;flex:1 1 auto;min-width:0;}
.blast{font-size:10.5px;font-weight:600;padding:1px 7px;border-radius:9px;white-space:nowrap;}
.blast--run{background:var(--accent-wash);color:var(--accent-ink);}
.blast--shared-run{background:var(--bulk-wash);color:var(--bulk);}
.blast--dataset{background:var(--ds-wash);color:var(--ds);}
.kbdhint{margin-left:auto;color:var(--faint);font-size:10.5px;display:inline-flex;gap:7px;align-items:center;white-space:nowrap;}
.kbdhint b{font-family:var(--mono);font-weight:500;color:var(--muted);background:var(--panel-2);border:1px solid var(--line);border-radius:3px;padding:0 4px;font-size:10px;}

/* F3-A: mixed-value breakdown popover */
.mixpop{position:absolute;top:calc(100% - 12px);left:0;z-index:55;background:#fff;border:1px solid var(--line-2);border-radius:8px;box-shadow:var(--sh-2);padding:10px 12px;width:min(360px,100%);}
.mixpop__t{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);font-weight:700;margin-bottom:6px;}
.mixpop table{border-collapse:collapse;width:100%;font-size:11.5px;}
.mixpop td{padding:3px 4px;border-bottom:1px solid #f1f3f6;}
.mixpop tr:last-child td{border-bottom:none;}
.mixpop .r{color:var(--muted);font-family:var(--mono);font-size:11px;}
.mixpop .v{text-align:right;color:var(--ink);font-family:var(--mono);}
.mixpop tr.is-outlier .v{color:#b32b2b;font-weight:600;}
.mixpop .a{text-align:right;width:70px;}
.mixpop .a button{border:none;background:none;font:inherit;font-size:10.5px;color:var(--accent);cursor:pointer;white-space:nowrap;}
.mixpop .a button:hover{text-decoration:underline;}
.mixpop__f{font-size:10.5px;color:var(--faint);margin-top:7px;}

/* F4-A: unit policy confirm */
.unitconfirm{display:flex;align-items:center;gap:8px;background:var(--warn-wash);border:1px solid #ecd9ae;border-radius:6px;padding:6px 10px;font-size:12px;margin-top:5px;flex-wrap:wrap;}
.unitconfirm__q{color:#7a5b10;}
.unitconfirm__q b{font-family:var(--mono);font-size:11.5px;}
.unitconfirm__btn{font:inherit;font-size:11.5px;font-weight:600;border:1px solid var(--line-2);background:#fff;color:var(--ink-2);border-radius:5px;padding:4px 10px;cursor:pointer;}
.unitconfirm__btn:hover{border-color:var(--line-3);color:var(--ink);}
.unitconfirm__btn--pri{background:var(--accent);border-color:var(--accent);color:#fff;}
.unitconfirm__btn--pri:hover{background:var(--accent-ink);color:#fff;}
.unitconfirm__x{border:none;background:none;color:var(--faint);cursor:pointer;font-size:12px;margin-left:auto;}

.scopedivider{display:flex;align-items:center;gap:12px;margin:26px 0 4px;color:var(--muted);font-size:11.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;}
.scopedivider::before,.scopedivider::after{content:"";flex:1 1 auto;height:1px;background:var(--line-2);}
.scopedivider--bulk{color:var(--bulk);}
.scopedivider--bulk::before,.scopedivider--bulk::after{background:var(--bulk-line);}

.formfoot{display:flex;flex-direction:column;gap:8px;margin-top:22px;}
.rowbtn{text-align:left;font:inherit;font-size:13px;color:var(--ink-2);background:var(--panel-2);border:1px solid var(--line-2);border-radius:var(--r2);padding:11px 14px;cursor:pointer;transition:all .12s;display:flex;align-items:center;gap:9px;}
.rowbtn:hover{border-color:var(--line-3);background:#fff;color:var(--accent-ink);}
.rowbtn .cnt{margin-left:auto;font-size:11px;color:var(--muted);background:#fff;border:1px solid var(--line);padding:1px 8px;border-radius:10px;}

/* parsed channels block */
.chanlist{border:1px solid var(--line);border-radius:var(--r2);overflow:hidden;background:#fff;}
.chanrow{display:grid;grid-template-columns:minmax(110px,.9fr) 1.3fr 56px auto;gap:10px;align-items:center;padding:7px 12px;font-size:12.5px;border-bottom:1px solid #f1f3f6;}
.chanrow:last-child{border-bottom:none;}
.chanrow--issue{background:#fffdf6;}
.chanrow--amb{background:#f6f9ff;}
.chanrow .hdr{font-family:var(--mono);font-size:12px;font-weight:500;}
.chanrow .dim{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.chanrow .dim--none{color:var(--warn);font-style:italic;}
.chanrow .un{color:var(--muted);font-size:12px;}
.chanblock__foot{margin-top:9px;}
.chstat{font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:10px;white-space:nowrap;justify-self:end;}
.chstat--matched{background:var(--ok-wash);color:#177544;}
.chstat--manual{background:var(--accent-wash);color:var(--accent-ink);}
.chstat--unmatched{background:var(--err-wash);color:#b32b2b;}
/* F14-A: ambiguous = parser uncertainty = blue, not amber */
.chstat--ambiguous{background:var(--accent-wash);color:var(--accent-ink);}

/* ============ unified GRID (F1-A) ============ */
.gridview{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}
.gridview__hint{flex:0 0 auto;font-size:12.5px;color:var(--muted);padding:10px 20px;border-bottom:1px solid var(--line);background:var(--panel-2);}
.gridview__hint b{color:var(--ink-2);}
.allink{color:var(--bulk);}
.gridscroll{flex:1 1 auto;overflow:auto;}
.gtable{border-collapse:separate;border-spacing:0;font-size:12.5px;min-width:100%;}
.gtable th,.gtable td{border-bottom:1px solid var(--line);border-right:1px solid var(--line);padding:0;white-space:nowrap;}
.gtable thead th{position:sticky;background:var(--panel-2);z-index:2;padding:7px 10px;text-align:left;font-weight:600;color:var(--ink-2);font-size:11.5px;vertical-align:bottom;}
.gtable__secs th{top:0;height:26px;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);border-bottom:1px solid var(--line-2);padding:5px 10px;}
.gtable thead tr:nth-child(2) th{top:26px;border-bottom:1px solid var(--line-2);}
.gtable__unit{display:block;font-weight:400;color:var(--faint);font-size:10px;margin-top:2px;}
.gtable__rowhd{position:sticky;left:0;background:var(--panel-2);z-index:1;padding:7px 12px !important;font-family:var(--mono);font-size:11.5px;font-weight:500;border-right:1px solid var(--line-2) !important;min-width:104px;text-align:left;}
.gtable thead .gtable__rowhd{z-index:3;}
.tdot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle;}
.tdot--ok{background:var(--ok);}.tdot--warn{background:var(--warn);}.tdot--err{background:var(--err);}.tdot--amb{background:var(--accent);}
.gtable td input,.gtable td select{width:100%;min-width:120px;border:none;background:none;font:inherit;font-size:12.5px;padding:7px 10px;color:var(--ink);}
.gtable td input:focus,.gtable td select:focus{outline:2px solid var(--accent);outline-offset:-2px;background:var(--accent-wash);}
.gtable td.is-err{background:var(--err-wash);}
.gtable td.is-req{background:#fffdf6;}
.gtable td.is-na{color:var(--faint);text-align:center;background:#fcfcfd;}
.gtable tbody tr:hover td{background:#f8fafc;}
.gtable tbody tr:hover td.is-err{background:var(--err-wash);}
.gtable tbody tr.is-selected .gtable__rowhd{background:var(--accent-wash);color:var(--accent-ink);}
/* the pinned purple ⊞ All-runs row */
.gtable__all th,.gtable__all td{background:#faf8ff !important;border-bottom:2px solid var(--bulk-line);}
.gtable__all .gtable__rowhd{color:var(--bulk);font-family:'IBM Plex Sans',sans-serif;font-weight:700;font-size:11.5px;}
.gtable__all td input::placeholder{color:#9a86d6;font-style:italic;font-size:11.5px;}
.gtable__all td input:focus,.gtable__all td select:focus{outline-color:var(--bulk);background:var(--bulk-wash);}
.gtable__all td select{color:var(--bulk);}

/* ============ docked issues drawer (F7-A) ============ */
.issuesdrawer{flex:0 0 auto;border-top:1px solid var(--line-2);background:#fff;box-shadow:0 -6px 18px rgba(20,28,45,.07);display:flex;flex-direction:column;max-height:218px;}
.issuesdrawer__bar{flex:0 0 auto;display:flex;align-items:center;gap:13px;padding:8px 16px;background:var(--panel-2);border-bottom:1px solid var(--line);font-size:12.5px;}
.issuesdrawer__bar b{font-weight:700;}
.cnt-e{color:#b32b2b;font-weight:500;}
.cnt-w{color:#9a6206;font-weight:500;}
.cnt-r{color:var(--muted);}
.cnt-ok{color:var(--ok);}
.issuesdrawer__nav{margin-left:auto;display:flex;gap:6px;align-items:center;}
.fixnext{font:inherit;font-size:11.5px;font-weight:600;background:var(--accent);color:#fff;border:1px solid var(--accent);border-radius:5px;padding:3px 11px;cursor:pointer;}
.fixnext:hover{background:var(--accent-ink);}
.dclose{border:1px solid var(--line-2);background:#fff;border-radius:5px;font:inherit;font-size:11px;padding:3px 8px;color:var(--ink-2);cursor:pointer;}
.dclose:hover{color:var(--ink);}
.issuesdrawer__list{list-style:none;margin:0;padding:3px 0;overflow-y:auto;}
.issuesdrawer__list li{display:flex;gap:9px;align-items:baseline;font-size:12.5px;padding:6px 16px;color:var(--ink-2);cursor:pointer;}
.issuesdrawer__list li:hover{background:#f8fafc;}
.issuesdrawer__list li.is-cur{background:var(--accent-wash);box-shadow:inset 3px 0 0 var(--accent);}
.issuesdrawer__list .m{width:13px;flex:0 0 auto;font-size:11px;}
.issuesdrawer__list .m.e{color:var(--err);} .issuesdrawer__list .m.w{color:var(--warn);} .issuesdrawer__list .m.r{color:var(--muted);}
.issuesdrawer__list .txt{flex:1 1 auto;}
.issuesdrawer__list .detail{display:block;font-size:11px;color:var(--faint);margin-top:1px;}
.issuesdrawer__list .go{font-size:11px;color:var(--accent);white-space:nowrap;flex:0 0 auto;opacity:0;}
.issuesdrawer__list li:hover .go,.issuesdrawer__list li.is-cur .go{opacity:1;}
.issuesdrawer__clear{padding:12px 16px;font-size:12.5px;color:var(--ink-2);line-height:1.6;}
.issuechip{font:inherit;font-size:12.5px;font-weight:600;border:1px solid var(--line-2);background:#fff;border-radius:20px;padding:6px 13px;cursor:pointer;color:var(--ok);}
.issuechip.has-issues{color:#9a6206;border-color:#ecd9ae;background:var(--warn-wash);}
.issuechip:hover{border-color:var(--line-3);}

/* footer */
.insrfoot{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:11px 20px;border-top:1px solid var(--line);background:var(--panel-2);}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);}
.legend span{display:inline-flex;align-items:center;gap:5px;}
.insrfoot__actions{display:flex;gap:8px;align-items:center;}

/* toast — F5-A: actionable, with Undo */
.toast{position:absolute;bottom:64px;left:50%;transform:translateX(-50%);background:var(--ink);color:#fff;font-size:13px;font-weight:500;
  padding:9px 10px 9px 18px;border-radius:8px;box-shadow:var(--sh-2);z-index:95;animation:tin .2s ease;max-width:74%;display:flex;align-items:center;gap:14px;}
@keyframes tin{from{opacity:0;transform:translate(-50%,6px);}to{opacity:1;transform:translate(-50%,0);}}
.toast__undo{background:rgba(255,255,255,.14);border:none;color:#9ec1f7;font:inherit;font-size:12px;font-weight:600;padding:4px 13px;border-radius:5px;cursor:pointer;flex:0 0 auto;}
.toast__undo:hover{background:rgba(255,255,255,.22);color:#c3daff;}

/* status bar — F8-A: autosave readout, aligned with Method Run */
.statusbar{height:26px;flex:0 0 auto;display:flex;align-items:center;gap:9px;padding:0 14px 0 12px;font-size:12px;color:#fff;
  background:#0f6cbd;border-top:0;}
.statusbar .dot{color:rgba(255,255,255,.62);}
.statusbar__sp{flex:1 1 auto;}
.statusbar__save{color:#fff;font-weight:600;}

/* empty states */
.bundlehd__name--muted{color:var(--muted);}
.schemachip--muted{background:var(--panel-3);color:var(--muted);border-color:var(--line-2);cursor:default;}
.emptystart{flex:1 1 auto;display:flex;flex-direction:column;padding:26px 22px;gap:16px;overflow:auto;}
.emptystart__actions{display:flex;gap:10px;flex-wrap:wrap;}
.emptystart__hint{font-size:13.5px;color:var(--muted);line-height:1.55;max-width:520px;margin:0;}
.dropzone{border:1.5px dashed var(--line-3);border-radius:10px;padding:30px 20px;text-align:center;color:var(--muted);background:var(--panel-2);font-size:13px;transition:all .15s;cursor:pointer;}
.dropzone b{color:var(--ink-2);}
.dropzone .big{font-size:26px;opacity:.45;display:block;margin-bottom:6px;}
.dropzone.is-over{border-color:var(--accent);background:var(--accent-wash);color:var(--accent-ink);}
.dropzone .sub{display:block;font-size:11.5px;color:var(--faint);margin-top:5px;}
.insrempty{flex:1 1 auto;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;}
.insrempty__mark{font-size:34px;opacity:.4;}
.insrempty__txt{font-size:14px;text-align:center;line-height:1.6;color:var(--muted);}

/* ============ modal shell ============ */
.modalscrim{position:absolute;inset:0;background:rgba(20,28,45,.34);display:flex;align-items:center;justify-content:center;z-index:60;}
.modal{background:#fff;border:1px solid var(--line-2);border-radius:12px;box-shadow:var(--sh-3);max-width:94%;max-height:90%;display:flex;flex-direction:column;overflow:hidden;}
.modal--sm{width:470px;}
.modal--mid{width:620px;}
.modal--wide{width:860px;}
.modal__hd{padding:16px 20px 13px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex:0 0 auto;}
.modal__kind{font-size:10.5px;letter-spacing:.14em;font-weight:700;color:var(--accent);}
.modal__title{font-size:17px;font-weight:700;margin:4px 0 0;letter-spacing:-.01em;}
.modal__sub{font-size:12.5px;color:var(--muted);margin:3px 0 0;}
.modal__sub .mono{font-size:11.5px;}
.modal__x{border:none;background:var(--panel-2);width:26px;height:26px;border-radius:6px;cursor:pointer;color:var(--muted);font-size:13px;flex:0 0 auto;}
.modal__x:hover{background:var(--panel-3);color:var(--ink);}
.modal__body{padding:15px 20px;overflow:auto;}
.modal__foot{padding:12px 20px;border-top:1px solid var(--line);background:var(--panel-2);display:flex;justify-content:space-between;align-items:center;gap:10px;flex:0 0 auto;}
.modal__footnote{font-size:12px;color:var(--muted);}
.modal__footnote b{color:var(--ink);}
.modal__footnote--warn{color:var(--warn);font-weight:500;}
.modal__footnote--ok{color:var(--ok);font-weight:500;}
.modal__actions{display:flex;gap:8px;margin-left:auto;align-items:center;}

/* channel inspector table */
.chtable{border-collapse:collapse;width:100%;font-size:12.5px;}
.chtable th{font-size:10.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);text-align:left;padding:7px 10px;border-bottom:1px solid var(--line-2);font-weight:600;white-space:nowrap;}
.chtable td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:middle;}
.chtable tr:last-child td{border-bottom:none;}
.chtable tr.is-issue td{background:#fffdf6;}
.chtable tr.is-amb td{background:#f6f9ff;}
.chtable .hdr{font-family:var(--mono);font-size:12px;font-weight:500;white-space:nowrap;}
.chtable .via{font-size:10.5px;color:var(--faint);display:block;margin-top:1px;}
.chtable .note{font-size:11px;color:var(--warn);display:block;margin-top:2px;max-width:200px;line-height:1.35;}
.chtable select{font:inherit;font-size:12px;border:1px solid var(--line-2);border-radius:5px;padding:4px 6px;background:#fff;max-width:210px;color:var(--ink);cursor:pointer;}
.chtable select.is-empty{border-color:#e8d3a6;background:#fffdf8;color:#9a6206;}
.chtable select.unitpick{max-width:84px;}

/* export run manifest (F6-A) */
.mantable{border-collapse:collapse;width:100%;font-size:12.5px;}
.mantable th{font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);text-align:left;padding:6px 10px;border-bottom:1px solid var(--line-2);font-weight:600;}
.mantable td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;}
.mantable tr:last-child td{border-bottom:none;}
.mantable .cb{font-size:14px;width:26px;}
.mantable .runid{font-size:12px;font-weight:500;white-space:nowrap;}
.mantable .spec{font-size:11.5px;color:var(--muted);white-space:nowrap;}
.mantable .reason{font-size:11.5px;color:var(--muted);}
.mantable .okt{color:#177544;font-weight:500;}
.mantable tr.is-off td{background:#fcfcfd;color:var(--faint);}
.mantable tr.is-off .runid{color:var(--faint);text-decoration:line-through;text-decoration-color:var(--line-3);}
.skipline{display:block;line-height:1.5;}
.skipline b{color:#9a6206;font-weight:600;}
.mantable .go,.skipline .go{border:none;background:none;font:inherit;font-size:11px;color:var(--accent);cursor:pointer;padding:0;white-space:nowrap;}
.mantable .go:hover{text-decoration:underline;}

/* export rows / notes */
.exprow{display:flex;flex-direction:column;gap:5px;margin-bottom:13px;}
.exprow > label{font-size:12.5px;font-weight:500;color:var(--ink-2);}
.pathrow{display:flex;gap:8px;}
.dlgnote{font-size:12px;color:var(--muted);background:var(--panel-2);border:1px solid var(--line);border-radius:6px;padding:9px 11px;line-height:1.5;}
.dlgnote b{color:var(--ink-2);}
.dlgnote--warn{background:var(--warn-wash);border-color:#ecd9ae;color:#7a5b10;}
.dlgnote--warn b{color:#7a5b10;}

/* proposal / schema picker */
.proposal{display:flex;gap:11px;border:1px solid var(--line-2);border-radius:8px;padding:12px 14px;cursor:pointer;margin-bottom:9px;align-items:flex-start;background:#fff;}
.proposal:hover{border-color:var(--line-3);}
.proposal.is-picked{border-color:var(--accent);background:var(--accent-wash);box-shadow:0 0 0 1px var(--accent);}
.proposal input{margin-top:3px;accent-color:var(--accent);}
.proposal .pbody{flex:1 1 auto;}
.proposal .t{font-weight:600;font-size:13.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.proposal .d{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.5;}
.proposal .d .mono{font-size:11px;}
.conf{display:inline-flex;align-items:center;gap:6px;}
.conf__track{width:42px;height:5px;border-radius:3px;background:var(--panel-3);overflow:hidden;}
.conf__fill{display:block;height:100%;border-radius:3px;}
.conf__fill--ok{background:var(--ok);}.conf__fill--warn{background:var(--warn);}.conf__fill--err{background:var(--err);}
.conf__num{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;}

/* evidence / supplemental */
.evrow{display:flex;align-items:center;gap:10px;padding:8px 12px;border:1px solid var(--line);border-radius:7px;font-size:12.5px;margin-bottom:7px;background:#fff;}
.evrow .ic{color:var(--faint);}
.evrow .nm{font-family:var(--mono);font-size:12px;}
.evrow .kind{margin-left:auto;font-size:11px;background:var(--panel-3);padding:2px 8px;border-radius:10px;color:var(--ink-2);white-space:nowrap;}
.evrow .rm{border:none;background:none;color:var(--faint);cursor:pointer;font-size:13px;padding:2px;}
.evrow .rm:hover{color:var(--err);}
.evempty{font-size:12.5px;color:var(--muted);padding:20px;text-align:center;border:1.5px dashed var(--line-2);border-radius:8px;margin-bottom:10px;line-height:1.55;}

/* rematch yaml table */
.pairtable{border-collapse:collapse;width:100%;font-size:12px;}
.pairtable th{font-size:10.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);text-align:left;padding:6px 10px;border-bottom:1px solid var(--line-2);font-weight:600;}
.pairtable td{padding:7px 10px;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:11.5px;}
.pairtable tr:last-child td{border-bottom:none;}
.pairtable .arr{color:var(--faint);text-align:center;}
.pairtable .chstat{font-family:'IBM Plex Sans',sans-serif;}

::-webkit-scrollbar{width:11px;height:11px;}
::-webkit-scrollbar-thumb{background:#c9cdd5;border-radius:6px;border:3px solid transparent;background-clip:content-box;}
::-webkit-scrollbar-thumb:hover{background:#b2b7c1;background-clip:content-box;}

/* =================================================================
   ITERATION 4 — ADVERSARIAL POLISH PASS (overrides; later rules win)
   Scope: type · density · colour · micro-interaction. Structure unchanged.
   ================================================================= */

/* ---- panel + debate write-up (analysis only) ---- */
.panel-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:28px;}
@media(max-width:980px){.panel-grid{grid-template-columns:repeat(2,1fr);}}
.pcard{border:1px solid var(--line-2);border-radius:10px;padding:14px 14px 15px;background:var(--panel);box-shadow:var(--sh-1);}
.pcard__name{font-size:14px;font-weight:700;letter-spacing:-.01em;color:var(--ink);}
.pcard__role{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent-ink);font-weight:600;margin-top:5px;}
.pcard__lens{font-size:12px;color:var(--ink-2);margin-top:9px;line-height:1.5;text-wrap:pretty;}
.rounds{margin-top:30px;display:flex;flex-direction:column;gap:18px;}
.round{border:1px solid var(--line-2);border-radius:12px;overflow:hidden;background:var(--panel);box-shadow:var(--sh-1);}
.round__hd{display:flex;align-items:baseline;gap:13px;padding:13px 20px;border-bottom:1px solid var(--line);background:var(--panel-2);}
.round__no{font-family:var(--mono);font-size:11.5px;color:var(--accent-ink);font-weight:600;letter-spacing:.04em;}
.round__topic{font-size:15px;font-weight:700;letter-spacing:-.01em;color:var(--ink);}
.xchgs{padding:6px 20px 12px;}
.xchg{display:grid;grid-template-columns:132px 1fr;gap:16px;padding:11px 0;border-bottom:1px solid var(--line);}
.xchg:last-child{border-bottom:none;}
.xchg--rebut{padding-left:26px;}
.xchg--rebut .xchg__who{grid-column:1;}
.xchg__who{font-size:12.5px;font-weight:700;color:var(--ink);}
.xchg__who small{display:block;font-weight:500;color:var(--muted);font-size:10.5px;margin-top:3px;letter-spacing:.02em;}
.xchg__txt{font-size:13.5px;color:var(--ink-2);line-height:1.58;text-wrap:pretty;}
.xchg__txt b{color:var(--ink);font-weight:600;}
.xchg__txt .mono{font-family:var(--mono);font-size:12px;}
.verdict{display:flex;gap:12px;align-items:flex-start;margin:2px 20px 16px;padding:12px 15px;border-radius:9px;background:var(--accent-wash);border:1px solid #d6e3fa;}
.verdict__tag{font-size:10px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:var(--accent-ink);background:#fff;border:1px solid #d6e3fa;padding:4px 9px;border-radius:20px;white-space:nowrap;flex:0 0 auto;margin-top:1px;font-family:var(--mono);}
.verdict__txt{font-size:13px;color:var(--ink-2);line-height:1.58;text-wrap:pretty;}
.verdict__txt b{color:var(--ink);font-weight:600;}
.verdict__txt .mono{font-family:var(--mono);font-size:12px;}
.conv-hd{margin:38px 0 0;display:flex;flex-direction:column;gap:6px;}
.conv-hd .eyebrow{margin:0;}
.conv-hd__sub{font-size:13.5px;color:var(--ink-2);max-width:760px;text-wrap:pretty;}
.fixtable .by{color:var(--muted);font-size:11.5px;white-space:nowrap;font-weight:500;}
.fixtable .where{color:var(--ink-2);font-size:12px;}
.fixtable th,.fixtable td{vertical-align:top;}

/* ---- R6 · contrast floor: meaning-bearing greys darkened ---- */
:root{
  --muted:#646b79;          /* was #79818f — now ~4.7:1 on white */
  --faint:#737b8a;          /* was #9aa2b0 — now ~3.7:1 on white */
  /* R1 · dataset scope leaves the green family for a neutral stone */
  --ds:#5a5d69; --ds-wash:#f1f1f4; --ds-line:#cdcfd8;
  /* R7 · motion tokens */
  --t-fast:120ms; --t-base:200ms; --t-ease:cubic-bezier(.2,.7,.2,1);
}

/* ---- R5 · tabular figures wherever digits sit in columns / steppers ---- */
.trow__runid,.grouphd__count,.railitem__count,.insrprog__txt b,.stepper__label b,.stepper__of,
.gtable,.gtable td input,.gtable__rowhd,.mantable,.mantable .runid,.conf__num,.bundlehd__meta,
.filesdrawer__count,.formsec__count,.statusbar,.menubar__schema,.issuesdrawer__bar,.chanrow{font-variant-numeric:tabular-nums;}

/* ---- R4 · type ramp: lift the in-app floor to 11px ---- */
.bundlehd__kind,.formsec__scope,.scopekind,.modal__kind,.rail__hd,
.chip-ch,.formsec__scope--dataset,.formsec__scope--shared-run,.formsec__scope--run{font-size:11px;}
.gtable__secs th,.gtable__unit{font-size:10.5px;}
.kbdhint,.kbdhint b{font-size:10.5px;}

/* ---- R1/R3 · stone dataset scope + flattened washes (rule carries scope) ---- */
.formsec--dataset{background:var(--ds-wash);}
.formsec--shared-run{background:#faf8ff;}

/* ---- R2 · parser-uncertainty: blue kept, fill dropped for a dashed "?" ---- */
.chstat--ambiguous{background:transparent;border:1px dashed var(--accent);color:var(--accent-ink);}
.chip-ch--amb{background:transparent;border:1px dashed var(--accent);color:var(--accent-ink);}
.chip-ch--amb:hover{border-color:var(--accent-ink);text-decoration:none;background:var(--accent-wash);}
.chtable tr.is-amb td{background:transparent;box-shadow:inset 2px 0 0 var(--accent);}
.tdot--amb{background:var(--panel);box-shadow:inset 0 0 0 2px var(--accent);}

/* ---- R7 · unify motion: one fast token for affordances, one base for bars/toasts ---- */
.btn,.menu__btn,.menu__item,.railitem,.grouphd,.trow--run,.applyall,.grouphd__pencil,
.grouphd__bulk,.grouphd__del,.linkbtn,.scopepills button,.stepper__btn,.issuechip,
.schemachip,.rowbtn,.proposal,.dclose,.kebab{
  transition:background var(--t-fast) var(--t-ease),border-color var(--t-fast) var(--t-ease),
             color var(--t-fast) var(--t-ease),opacity var(--t-fast) var(--t-ease),box-shadow var(--t-fast) var(--t-ease);}
.bundlebar__fill,.insrprog__fill,.conf__fill{transition:width var(--t-base) var(--t-ease);}
.inp{transition:border-color var(--t-fast) var(--t-ease),box-shadow var(--t-fast) var(--t-ease);}

/* ---- R9 · honest reveals: hover actions fade in place (no visibility pop) ---- */
.kebab{visibility:visible;opacity:0;}
.trow--run:hover .kebab,.kebab:focus,.kebab:focus-visible{opacity:1;}

/* ---- R8 · one focus ring across every control ---- */
.btn:focus-visible,.menu__btn:focus-visible,.railitem:focus-visible,.scopepills button:focus-visible,
.stepper__btn:focus-visible,.kebab:focus-visible,.linkbtn:focus-visible,.issuechip:focus-visible,
.schemachip:focus-visible,.rowbtn:focus-visible,.filesdrawer__hd:focus-visible,.dclose:focus-visible,
.fixnext:focus-visible,.toast__undo:focus-visible,.density select:focus-visible{
  outline:2px solid var(--accent);outline-offset:1px;border-radius:var(--r1);}


/* ======================== PySide6 desktop chrome + rounded window ======================== */
:root{
  --desktop-menubar-h: 30px;
  --desktop-window-radius: 16px;
  --desktop-window-border: #c4cad3;
}
html,body,#root{width:100%;height:100%;overflow:hidden;border-radius:var(--desktop-window-radius);}
body{background:transparent;text-rendering:geometricPrecision;}
.stage--desktop{width:100vw;height:100vh;padding:0;overflow:hidden;background:transparent;border-radius:var(--desktop-window-radius);}
.stage--desktop .appwin{
  width:100vw;
  height:100vh;
  max-width:none;
  min-width:0;
  margin:0;
  border:1px solid var(--desktop-window-border);
  border-radius:var(--desktop-window-radius);
  box-shadow:none;
  overflow:hidden;
}
.menubar--desktop{height:var(--desktop-menubar-h);padding-right:0;user-select:none;-webkit-user-select:none;}
.menubar--desktop .menubar__title{height:100%;display:inline-flex;align-items:center;padding:0 4px;}
.menubar__dragzone{flex:1 1 auto;height:100%;min-width:24px;}
.menubar--desktop .menubar__schema{margin-left:0;}
.menubar__windowctrls{margin-left:0;}
.stage--desktop .cores{height:calc(100vh - var(--desktop-menubar-h) - 26px);}
.stage--desktop .modal{filter:none;}
@media(max-width:1240px){.stage--desktop{overflow:hidden;}.stage--desktop .appwin{min-width:0;}}
`,wt=`:root {
  --desktop-chrome-surface: #ffffff;
  --desktop-chrome-border: #e1e4e8;
  --desktop-chrome-hover: #eef0f3;
  --desktop-chrome-ink: #1b1e23;
  --desktop-chrome-muted: #5a626c;
  --desktop-chrome-danger: #c4392a;
}

.desktop-window-controls,
[data-window-controls="true"] {
  height: 100% !important;
  display: flex !important;
  align-items: stretch !important;
  gap: 0 !important;
  margin-left: 0 !important;
  border-left: 1px solid var(--desktop-chrome-border) !important;
}

.desktop-window-control,
[data-window-control],
[data-window-action="maximize"],
[data-window-action="toggle-maximize"] {
  width: 44px !important;
  height: 100% !important;
  min-width: 44px !important;
  min-height: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
  background: transparent !important;
  color: var(--desktop-chrome-muted) !important;
  font: inherit !important;
  font-size: 12px !important;
  line-height: 1 !important;
  text-decoration: none !important;
  cursor: pointer !important;
  user-select: none !important;
  -webkit-user-select: none !important;
}

.desktop-window-control:hover,
[data-window-control]:hover,
[data-window-action="maximize"]:hover,
[data-window-action="toggle-maximize"]:hover {
  background: var(--desktop-chrome-hover) !important;
  color: var(--desktop-chrome-ink) !important;
}

.desktop-window-control--close:hover,
[data-window-control="close"]:hover {
  background: var(--desktop-chrome-danger) !important;
  color: #ffffff !important;
}

[data-window-control="maximize"][data-window-state-synced="true"]::before {
  content: "" !important;
}

html[data-window-resizing="true"] *,
html[data-window-resizing="true"] *::before,
html[data-window-resizing="true"] *::after,
[data-window-resizing="true"] *,
[data-window-resizing="true"] *::before,
[data-window-resizing="true"] *::after {
  transition-duration: 0s !important;
  animation-duration: 0s !important;
  animation-delay: 0s !important;
  scroll-behavior: auto !important;
}

:host([data-window-resizing="true"]) *,
:host([data-window-resizing="true"]) *::before,
:host([data-window-resizing="true"]) *::after {
  transition-duration: 0s !important;
  animation-duration: 0s !important;
  animation-delay: 0s !important;
  scroll-behavior: auto !important;
}
`,Tt=`.section-guide-scrim {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 22, 38, .42);
  color: #1b2230;
  font-family: "IBM Plex Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.section-guide-dialog {
  width: min(780px, 100%);
  max-height: min(88vh, 760px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #d8dde5;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 26px 80px rgba(15, 22, 38, .38);
}

.section-guide-dialog__chrome {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 14px;
  border-bottom: 1px solid #e2e5ea;
  background: #f7f8fa;
}

.section-guide-dialog__dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  flex: none;
  background: #1f7a44;
  box-shadow: inset 0 0 0 2px #fff;
}

.section-guide-dialog__chrome h2 {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1b2230;
}

.section-guide-dialog__close {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #79818f;
  font: inherit;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.section-guide-dialog__close:hover {
  background: #eef1f5;
  color: #1b2230;
}

.section-guide-dialog__body {
  overflow: auto;
  padding: 16px;
}

.section-guide {
  display: grid;
  gap: 13px;
}

.section-guide__lead,
.section-guide section {
  border: 1px solid #e4e7ec;
  border-radius: 9px;
  background: #fff;
  padding: 15px 17px;
}

.section-guide__lead {
  border-color: #dbe8df;
  background: #f6faf7;
}

.section-guide__eyebrow,
.section-guide h4 {
  margin: 0 0 7px;
  color: #79818f;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.section-guide h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  color: #1b2230;
}

.section-guide p,
.section-guide li {
  color: #48505f;
  font-size: 12.5px;
  line-height: 1.55;
}

.section-guide p {
  margin: 6px 0 0;
}

.section-guide ol,
.section-guide ul {
  margin: 0;
  padding-left: 21px;
}

.section-guide li + li {
  margin-top: 5px;
}

.section-guide-dialog__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 15px;
  color: #79818f;
  font-size: 12px;
}

.section-guide-dialog__actions button {
  border: 1px solid #0f6cbd;
  border-radius: 7px;
  background: #0f6cbd;
  color: #fff;
  padding: 8px 15px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.section-guide-dialog__actions button:hover {
  background: #0d5fa8;
}
`,Et=`
.stage, .stage--desktop{
  padding:0 !important;
  width:100%;
  height:100%;
  display:flex;
  align-items:stretch;
  justify-content:stretch;
  overflow:hidden;
}
.appwin{
  width:100% !important;
  height:100% !important;
  min-width:0 !important;
  max-width:none !important;
  margin:0 !important;
  border:0 !important;
  border-radius:0 !important;
  box-shadow:none !important;
}
`;function Dt(){return(0,a.jsx)(x,{css:Ct+Et+wt+Tt,className:`packaging-shadow`,children:(0,a.jsx)(`div`,{className:`stage stage--desktop`,children:(0,a.jsx)(St,{})})})}function Ot(e,t){let n=0,r=0;for(;(r=e.indexOf(t,r))!==-1;)n+=1,r+=t.length;return n}function kt(e,t,n,r){let i=Ot(e,t);if(i!==r)throw Error(`Method Editor generated source drifted: expected ${r} match(es), found ${i}.`);return e.split(t).join(n)}function At(e,t,n,r){let i=t.reduce((t,n)=>t+Ot(e,n),0);if(i!==r)throw Error(`Method Editor generated source drifted: expected ${r} match(es), found ${i}.`);return t.reduce((e,t)=>e.split(t).join(n),e)}function Y(e,t,n){return kt(e,t,n,1)}var jt=`  createMethodNow() {
    this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label, topMenu:null }; });
  }`,Mt=`  createLocalMethodNow() {
    this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label, topMenu:null }; });
  }
  async createMethodNow() {
    const api = this.methodEditorApi();
    if (!api?.createDraft) { this.createLocalMethodNow(); return; }
    if (!api?.generateVersion || !api?.registerGeneratedMethod) { await this.createBackendDraftNow(); return; }
    const label = 'New method ' + this.state.newSeq;
    const generated = await this.generateVersionNow({ defaultLabel:label });
    if (generated) {
      this.setState(st => ({ newSeq:st.newSeq + 1, menuOpen:true, editingNameId:generated.method_id, nameDraft:label }));
    }
  }`,Nt=`  renameCurrentNow() {
    this.setState(st => { const cur = st.methods.find(m => m.id === st.methodId) || st.methods[0]; return { menuOpen:true, editingNameId: cur.id, nameDraft: cur.label, topMenu:null }; });
  }`,Pt=`  renameCurrentNow() {
    const cur = this.currentMethodOption();
    if (!cur) return;
    this.startRenameMethod(cur);
  }`,Ft=`
  methodEditorApi() {
    return this.props.methodEditorApi || window.desktopApi?.methodEditor || null;
  }
  apiData(response, action) {
    if (response && response.status === 'ok') return response.data || {};
    if (response && response.status === undefined) return response;
    const message = response?.message || response?.error || response?.error_type || (action + ' failed');
    throw new Error(message);
  }
  backendUnavailable() {
    return 'Method Editor backend unavailable';
  }
  displayMethodLabel(label) {
    const raw = String(label || '').trim();
    return raw.replace(/\\s*\\(generated\\s+v?[0-9]+(?:\\.[0-9]+){2}\\)\\s*$/i, '').trim() || raw;
  }
  handleBackendError(error, fallback) {
    const message = error?.message || fallback;
    this.setState({ backendBusy:false, backendStatusText: message });
    this.fireToast(message);
    return null;
  }
  hasUnsavedMethodEdits() {
    return !!this.state.methodDirty;
  }
  markMethodDirty(update) {
    if (typeof update === 'function') {
      this.setState(st => {
        const patch = update(st) || {};
        return { ...patch, methodDirty:true, backendStatusText:'Unsaved method edits' };
      });
      return;
    }
    this.setState({ ...(update || {}), methodDirty:true, backendStatusText:'Unsaved method edits' });
  }
  clearMethodDirty(statusText) {
    this.setState({ methodDirty:false, backendStatusText: statusText || this.state.backendStatusText });
  }
  saveMethodIfDirtyNow() {
    if (!this.hasUnsavedMethodEdits()) {
      this.fireToast('No method edits to save');
      return null;
    }
    return this.generateVersionNow();
  }
  confirmDiscardUnsavedEdits() {
    if (!this.hasUnsavedMethodEdits()) return true;
    return window.confirm('You have unsaved method edits. Close Method Editor and discard them?');
  }
  requestCloseWindow(e) {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    if (!this.confirmDiscardUnsavedEdits()) return;
    window.desktopApi?.closeWindow?.();
  }
  methodOptionFromBackend(item) {
    const method = item?.method || item || {};
    const id = item?.method_id || item?.methodId || item?.id || method.method_id || method.methodId || method.id;
    const version = item?.version || method.version || '0.0.0';
    const rawLabel = item?.label || item?.method_name || item?.name || method.label || method.method_name || method.name || id;
    const label = this.displayMethodLabel(rawLabel);
    const generated = !!(item?.generated || item?.source === 'method_editor_generated' || item?.source_draft_id || method.generated);
    return id ? {
      ...item,
      id,
      method_id:id,
      label,
      version,
      generated,
      canonical:item?.canonical ?? !generated,
      editable:item?.editable ?? generated,
      deletable:item?.deletable ?? generated,
    } : null;
  }
  methodPathForOption(method) {
    return method?.method_path || method?.methodPath || method?.method?.method_path || method?.method?.methodPath || '';
  }
  currentMethodOption() {
    return this.state.methods.find(m => m.id === this.state.methodId) || this.state.methods[0] || null;
  }
  async loadBackendMethods() {
    const api = this.methodEditorApi();
    if (!api?.listMethods) return;
    this.setState({ backendMode:true, backendBusy:true, backendStatusText:'Loading method registry...' });
    try {
      const data = this.apiData(await api.listMethods({}), 'List methods');
      const methods = (Array.isArray(data.methods) ? data.methods : [])
        .map(item => this.methodOptionFromBackend(item))
        .filter(Boolean);
      if (!methods.length) {
        this.setState({ backendBusy:false, backendStatusText:'No backend methods registered' });
        return;
      }
      const selected = methods.find(m => m.id === this.state.methodId) || methods[0];
      this.setState({ methods, methodId:selected.id, backendMode:true, backendBusy:false, backendDraft:null, backendGeneratedMethod:null, backendStatusText:'Method registry loaded', methodDirty:false });
      await this.loadBackendMethod(selected.id);
    } catch (error) {
      this.handleBackendError(error, 'Method registry unavailable');
    }
  }
  async loadBackendMethod(methodId) {
    const api = this.methodEditorApi();
    if (!api?.loadMethod || !methodId) return null;
    try {
      const data = this.apiData(await api.loadMethod({ methodId }), 'Load method');
      this.setState({ backendBaseMethod:data.method || null, backendDraft:null, backendGeneratedMethod:null, methodDirty:false });
      return data.method || null;
    } catch (error) {
      this.handleBackendError(error, 'Method load failed');
      return null;
    }
  }
  selectMethodNow(method) {
    const id = method?.id || method?.method_id;
    if (!id) return;
    if (!this.confirmDiscardUnsavedEdits()) return;
    this.setState({ methodId:id, menuOpen:false, editingNameId:null, backendDraft:null, backendGeneratedMethod:null, backendStatusText:'Method selected', methodDirty:false });
    this.loadBackendMethod(id);
  }
  startRenameMethod(method) {
    if (!method?.id) return;
    if (this.state.backendMode && !(method.editable || method.generated)) { this.fireToast('ISO reference methods are read-only'); return; }
    this.setState({ menuOpen:true, editingNameId: method.id, nameDraft: method.label });
  }
  async commitMethodNameNow() {
    const editingId = this.state.editingNameId;
    if (editingId == null) return;
    const label = String(this.state.nameDraft || '').trim();
    const method = this.state.methods.find(item => item.id === editingId);
    if (!label) {
      this.setState({ editingNameId:null });
      return;
    }
    if (this.state.backendMode && method && !(method.editable || method.generated)) {
      this.setState({ editingNameId:null });
      this.fireToast('ISO reference methods are read-only');
      return;
    }
    this.setState(st => ({
      methods: st.methods.map(item => item.id === editingId ? { ...item, label } : item),
      editingNameId:null,
      backendStatusText:'Renamed ' + label,
    }));
    const api = this.methodEditorApi();
    if (!this.state.backendMode || !api?.renameMethod || !method) {
      return;
    }
    try {
      const data = this.apiData(await api.renameMethod({
        method_id: method.method_id || method.id,
        method_path: this.methodPathForOption(method),
        label,
      }), 'Rename method');
      const option = this.methodOptionFromBackend(data.method || data.registry_entry || data);
      if (option) {
        this.setState(st => ({
          methods: st.methods.map(item => item.id === editingId ? { ...item, ...option, label } : item),
          backendStatusText:'Renamed ' + label,
        }));
      }
    } catch (error) {
      this.handleBackendError(error, 'Method rename failed');
    }
  }
  async createBackendDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.createDraft) return null;
    const method = this.currentMethodOption();
    const methodId = this.state.methodId || method?.id;
    if (!methodId) return this.handleBackendError(new Error('No method selected'), 'Draft creation failed');
    this.setState({ backendBusy:true, backendStatusText:'Creating draft...', topMenu:null });
    try {
      const data = this.apiData(await api.createDraft({ methodId, draftLabel:(method?.label || methodId) + ' draft' }), 'Create draft');
      const draft = data.draft;
      if (!draft?.draft_id && !draft?.draft_path) throw new Error('Draft response missing draft reference');
      this.setState({
        backendMode:true,
        backendBusy:false,
        backendDraft:draft,
        backendGeneratedMethod:null,
        backendStatusText:'Draft ready',
        menuOpen:false,
        editingNameId:null,
        methodId:draft.base_method_id || draft.method?.method_id || methodId,
      });
      this.fireToast('Draft ready');
      return draft;
    } catch (error) {
      return this.handleBackendError(error, 'Draft creation failed');
    }
  }
  async ensureBackendDraft() {
    const draft = this.state.backendDraft;
    const methodId = this.state.methodId;
    if (draft && (draft.base_method_id === methodId || draft.method?.method_id === methodId || !draft.base_method_id)) return draft;
    const created = await this.createBackendDraftNow();
    if (!created) throw new Error('Draft not available');
    return created;
  }
  controlledModulusValues() {
    const start = Number.parseFloat(this.state.startStrain);
    const end = Number.parseFloat(this.state.endStrain);
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
      throw new Error('Fix field format to continue');
    }
    return { start_strain:start, end_strain:end };
  }
  async saveControlledModulusDraft() {
    const api = this.methodEditorApi();
    if (!api?.updateDraft) throw new Error(this.backendUnavailable());
    const draft = await this.ensureBackendDraft();
    this.setState({ backendBusy:true, backendStatusText:'Saving draft...', topMenu:null });
    const data = this.apiData(await api.updateDraft({
      draft_id:draft.draft_id,
      draft_path:draft.draft_path,
      patch:{
        parameter_group:'modulus_chord_strain_window',
        values:this.controlledModulusValues(),
        reason:'Method Editor UI controlled modulus update',
      },
    }), 'Save draft');
    const updatedDraft = data.draft || draft;
    this.setState({ backendBusy:false, backendDraft:updatedDraft, backendValidation:data.validation || null, backendStatusText:'Draft saved' });
    return updatedDraft;
  }
  async saveDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.updateDraft) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      const draft = await this.saveControlledModulusDraft();
      this.fireToast('Draft saved');
      return draft;
    } catch (error) {
      return this.handleBackendError(error, 'Draft save failed');
    }
  }
  async validateDraftNow() {
    const api = this.methodEditorApi();
    if (!api?.validateDraft) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      this.setState({ backendBusy:true, backendStatusText:'Validating draft...', topMenu:null });
      const draft = await this.saveControlledModulusDraft();
      const data = this.apiData(await api.validateDraft({ draft_id:draft.draft_id, draft_path:draft.draft_path }), 'Validate draft');
      const validation = data.validation || {};
      const valid = validation.status === 'valid' || validation.loadable === true;
      this.setState({
        backendBusy:false,
        backendDraft:data.draft || draft,
        backendValidation:validation,
        backendStatusText:valid ? 'Draft valid' : 'Draft checked',
      });
      this.fireToast(valid ? 'Draft valid' : 'Draft checked');
      return { draft:data.draft || draft, validation };
    } catch (error) {
      return this.handleBackendError(error, 'Draft validation failed');
    }
  }
  nextTargetVersion() {
    const method = this.currentMethodOption();
    const raw = String(method?.version || this.state.backendBaseMethod?.version || '0.1.0').replace(/^v/i, '');
    const parts = raw.split('.').map(part => Number.parseInt(part, 10));
    if (parts.length !== 3 || parts.some(part => !Number.isFinite(part) || part < 0)) return '0.1.1';
    parts[2] += 1;
    return parts.join('.');
  }
  async generateVersionNow(options = {}) {
    const api = this.methodEditorApi();
    if (!api?.generateVersion || !api?.registerGeneratedMethod) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      if (!options.defaultLabel && !this.hasUnsavedMethodEdits()) {
        this.fireToast('No method edits to save');
        return null;
      }
      this.setState({ backendBusy:true, backendStatusText:'Saving method...', topMenu:null });
      const draft = await this.saveControlledModulusDraft();
      let validation = null;
      if (api.validateDraft) {
        const validationData = this.apiData(await api.validateDraft({ draft_id:draft.draft_id, draft_path:draft.draft_path }), 'Validate draft');
        validation = validationData.validation || null;
        if (validation && validation.loadable === false) throw new Error('Draft validation failed');
      }
      const targetVersion = this.nextTargetVersion();
      const generatedData = this.apiData(await api.generateVersion({ draft_id:draft.draft_id, draft_path:draft.draft_path, targetVersion }), 'Generate version');
      const generated = generatedData.generated_method;
      if (!generated?.method_path) throw new Error('Generated method response missing method path');
      const registerData = this.apiData(await api.registerGeneratedMethod({ method_path:generated.method_path }), 'Register generated method');
      const option = this.methodOptionFromBackend(generated);
      if (!option) throw new Error('Generated method response missing method id');
      if (options.defaultLabel) option.label = options.defaultLabel;
      option.generated = true;
      option.canonical = false;
      option.editable = true;
      option.deletable = true;
      if (options.defaultLabel && api.renameMethod) {
        try {
          const renameData = this.apiData(await api.renameMethod({
            method_id: option.method_id || option.id,
            method_path: generated.method_path,
            label: options.defaultLabel,
          }), 'Rename method');
          const renamedOption = this.methodOptionFromBackend(renameData.method || renameData.registry_entry || renameData);
          if (renamedOption?.label) option.label = renamedOption.label;
        } catch (renameError) {
          this.fireToast(renameError?.message || 'Method saved; rename failed');
        }
      }
      this.setState(st => {
        const methods = [...st.methods.filter(m => m.id !== option.id), option];
        return {
          methods,
          methodId:option.id,
          backendMode:true,
          backendBusy:false,
          backendDraft:null,
          backendGeneratedMethod:generated,
          backendRegistered:registerData.registry_entry || null,
          backendValidation:generatedData.validation || validation,
          backendStatusText:'Saved method v' + option.version,
          methodDirty:false,
          menuOpen:false,
          topMenu:null,
        };
      });
      this.fireToast('Saved method v' + option.version);
      return generated;
    } catch (error) {
      return this.handleBackendError(error, 'Generate version failed');
    }
  }
  async exportGeneratedMethodNow() {
    const api = this.methodEditorApi();
    if (!api?.exportMethodPackage) { this.fireToast(this.backendUnavailable()); return null; }
    const method = this.currentMethodOption();
    const methodPath = this.state.backendGeneratedMethod?.method_path || this.methodPathForOption(method);
    if (!methodPath) { this.fireToast('Generate a method before export'); return null; }
    try {
      this.setState({ backendBusy:true, backendStatusText:'Exporting method package...', topMenu:null });
      const defaultName = ((method?.method_id || method?.id || 'method_package') + '.zip').replace(/[^A-Za-z0-9_.-]+/g, '_');
      const data = this.apiData(await api.exportMethodPackage({ method_path:methodPath, default_name:defaultName }), 'Export method package');
      const exported = data.export || {};
      const exportName = exported.export_name || exported.archive_name || 'method package';
      const target = exported.export_path || exportName;
      this.setState({ backendBusy:false, backendExport:exported, backendStatusText:'Exported to ' + target });
      this.fireToast('Exported to ' + target);
      return exported;
    } catch (error) {
      return this.handleBackendError(error, 'Method package export failed');
    }
  }
  async openMethodPackageNow() {
    const api = this.methodEditorApi();
    if (!api?.openMethodPackage) { this.fireToast(this.backendUnavailable()); return null; }
    try {
      this.setState({ backendMode:true, backendBusy:true, backendStatusText:'Opening method package...', topMenu:null });
      const data = this.apiData(await api.openMethodPackage({ register:true }), 'Open method package');
      const generated = data.generated_method || data.method || data.imported_method;
      const option = this.methodOptionFromBackend(generated);
      if (!option) throw new Error('Opened method package response missing method id');
      option.generated = true;
      option.canonical = false;
      option.editable = true;
      option.deletable = true;
      this.setState(st => ({
        methods:[...st.methods.filter(m => m.id !== option.id), option],
        methodId:option.id,
        backendMode:true,
        backendBusy:false,
        backendDraft:null,
        backendGeneratedMethod:generated,
        backendRegistered:data.registry?.registry_entry || null,
        backendStatusText:'Opened ' + (option.label || option.id),
        menuOpen:false,
        topMenu:null,
      }));
      this.fireToast('Opened ' + (option.label || option.id));
      return generated;
    } catch (error) {
      return this.handleBackendError(error, 'Method package open failed');
    }
  }
  deleteLocalMethodNow(method) {
    this.setState(st => {
      if (st.methods.length <= 1) return {};
      const mm = st.methods.filter(x => x.id !== method.id);
      const methodId = st.methodId === method.id ? mm[0].id : st.methodId;
      return { methods:mm, methodId };
    });
  }
  async deleteMethodNow(method) {
    const api = this.methodEditorApi();
    if (!this.state.backendMode || !api?.deleteMethod) { this.deleteLocalMethodNow(method); return null; }
    if (!(method?.deletable || method?.generated)) { this.fireToast('Reference methods cannot be deleted'); return null; }
    const methodPath = method.method_path || method.method?.method_path;
    try {
      this.setState({ backendBusy:true, backendStatusText:'Deleting method...', topMenu:null });
      const data = this.apiData(await api.deleteMethod({ method_id:method.method_id || method.id, method_path:methodPath }), 'Delete method');
      let nextId = null;
      this.setState(st => {
        const methods = st.methods.filter(item => item.id !== method.id);
        nextId = st.methodId === method.id ? methods[0]?.id || null : st.methodId;
        return {
          methods,
          methodId:nextId,
          backendBusy:false,
          backendDraft:null,
          backendGeneratedMethod:st.backendGeneratedMethod?.method_id === method.id ? null : st.backendGeneratedMethod,
          backendStatusText:'Deleted ' + (data.method_id || method.label || 'method'),
          menuOpen:false,
        };
      });
      if (nextId) await this.loadBackendMethod(nextId);
      this.fireToast('Deleted ' + (data.method_id || method.label || 'method'));
      return data;
    } catch (error) {
      return this.handleBackendError(error, 'Method delete failed');
    }
  }
`,It=`            <span onClick="{{ m.onStartRename }}" title="Rename method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
            </span>`,Lt=`            <sc-if value="{{ m.canRename }}" hint-placeholder-val="{{ true }}">
            <span onClick="{{ m.onStartRename }}" title="Rename method" style="display:inline-flex; align-items:center; padding:4px; border-radius:4px; cursor:pointer;">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#a09a8e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"></path></svg>
            </span>
            </sc-if>`;function Rt(e){let t=Y(e,`<button style="border:1px solid {{ genBorder }}; background:{{ genBg }}; color:{{ genColor }}; font-family:inherit; font-size:13px; font-weight:600; padding:9px 18px; border-radius:4px; cursor:{{ genCursor }}; display:inline-flex; align-items:center; gap:8px;">▶ Generate new method version</button>`,`<button onClick="{{ saveMethod }}" aria-disabled="{{ saveDisabled }}" title="{{ saveTitle }}" style="border:1px solid {{ genBorder }}; background:{{ genBg }}; color:{{ genColor }}; font-family:inherit; font-size:13px; font-weight:600; padding:9px 18px; border-radius:4px; cursor:{{ genCursor }}; pointer-events:{{ savePointerEvents }}; display:inline-flex; align-items:center; gap:8px;">✓ Save method</button>`);return t=Y(t,`<span class="mono" style="font-size:11.5px; color:#8a93a0;">CAG-CF-Modied-ULV20.mtdp</span>`,``),t=Y(t,`<button onClick="{{ toggleMenu }}" onDoubleClick="{{ startRenameCurrent }}" title="Click to switch · double-click to rename"`,`<button onClick="{{ toggleMenu }}" onDoubleClick="{{ renameCurrentFromSelector }}" title="Click to switch · double-click to rename"`),t=Y(t,`<span onClick="{{ m.onSelect }}" style="display:flex; align-items:center; gap:9px; flex:1; cursor:pointer;">`,`<span onClick="{{ m.onSelect }}" onDoubleClick="{{ m.onStartRename }}" title="{{ m.title }}" style="display:flex; align-items:center; gap:9px; flex:1; cursor:pointer;">`),t=Y(t,`<span style="font-size:12px; color:#6e7a86;">Stress–strain</span>`,`<span title="Stress–strain is derived from the source data and is not edited here" style="font-size:12px; color:#8f98a3; background:#eef1f4; border:1px solid #d8dde3; border-radius:999px; padding:3px 10px; cursor:not-allowed;">Stress–strain</span>`),t=Y(t,`<div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); z-index:40; background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 16px 44px rgba(40,35,25,0.17); padding:16px 22px 20px;">`,`<div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); z-index:40; width:min(884px, calc(100vw - 96px)); max-width:calc(100vw - 96px); background:#fff; border:1px solid #e3e7eb; border-radius:10px; box-shadow:0 16px 44px rgba(40,35,25,0.17); padding:12px 16px 16px; overflow:hidden;">`),t=Y(t,`<div style="font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:600; margin-bottom:12px;">Analysis pipeline — how the data is processed, in order · click an editable box</div>
          <div style="width:884px;">`,`<div style="font-size:9px; letter-spacing:0.1em; text-transform:uppercase; color:#a09a8e; font-weight:700; margin-bottom:10px;">Pipeline map · editable boxes match the compact strip</div>
          <div style="width:100%; min-width:0;">`),t=Y(t,`<div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 13px;">
            <div style="font-size:12.5px; font-weight:600;">Data entry point</div>
            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">load · strain · geometry → area · mean strain</div>
          </div>`,`<div style="flex:1 1 0; min-width:0; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 13px;">
            <div style="font-size:12.5px; font-weight:600;">Data entry point</div>
            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">load · strain · geometry → area · mean strain</div>
          </div>`),t=Y(t,`<div style="flex:0 0 276px; border:1.5px solid #c3cad2; border-radius:8px; background:#fff; padding:8px 13px;">
            <div style="font-size:12.5px; font-weight:600;">Stress–strain</div>
            <div style="font-size:10.5px; color:#5a6675; margin-top:1px;">bounded curve</div>
          </div>`,`<div title="Stress–strain is derived from the source data and is not editable here" style="flex:1 1 0; min-width:0; border:1px solid #d8dde3; border-radius:8px; background:#eef1f4; padding:8px 13px; cursor:not-allowed;">
            <div style="font-size:12.5px; font-weight:600; color:#8f98a3;">Stress–strain</div>
            <div style="font-size:10.5px; color:#9aa3ad; margin-top:1px;">derived curve · read-only</div>
          </div>`),t=Y(t,`<svg viewBox="0 0 884 46" width="884" height="46" style="position:absolute; inset:0;">`,`<svg viewBox="0 0 884 46" width="100%" height="46" preserveAspectRatio="none" style="position:absolute; inset:0;">`),t=Y(t,`<div style="flex:0 0 276px; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 14px;">
            <div style="font-size:12.5px; font-weight:600; color:#5a6675;">Strength</div>
            <div style="font-size:10.5px; color:#a09a8e; margin-top:2px;">max load → strength → failure strain</div>
          </div>`,`<div style="flex:1 1 0; min-width:0; border:1px solid #e3e7eb; border-radius:8px; background:#fafbfc; padding:8px 14px;">
            <div style="font-size:12.5px; font-weight:600; color:#5a6675;">Strength</div>
            <div style="font-size:10.5px; color:#a09a8e; margin-top:2px;">max load → strength → failure strain</div>
          </div>`),t=Y(t,`Tune an analysis setting, then generate a new version`,`Tune an analysis setting, then save a method version`),t=Y(t,`Generate commits the {{ changeCount }} change(s) listed below · picked up by the Method Wizard on next run`,`Save commits the {{ changeCount }} change(s) listed below · picked up by Method Analysis on next run`),t=Y(t,`identical to v0.1.0 — nothing to generate yet`,`identical to v0.1.0 — nothing to save yet`),t=Y(t,It,Lt),t=Y(t,`Double-click a method, or use ✎, to rename.`,`Double-click an editable method, or use ✎, to rename. ISO reference stays read-only.`),t}function zt(e){let t=e;return t=Y(t,`  componentDidMount() {
    this._onKey = (e) => {`,`  componentDidMount() {
    this.loadBackendMethods();
    this._onKey = (e) => {`),t=Y(t,`    nameDraft: '',`,`    nameDraft: '',
    methodDirty: false,`),t=Y(t,`      if (meta && (e.key === 'n' || e.key === 'N')) { e.preventDefault(); this.createMethodNow(); return; }
      if (meta && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null })); return; }`,`      if (meta && (e.key === 'n' || e.key === 'N')) { e.preventDefault(); this.createMethodNow(); return; }
      if (meta && (e.key === 's' || e.key === 'S')) { e.preventDefault(); this.saveMethodIfDirtyNow(); return; }
      if (meta && (e.key === 'w' || e.key === 'W')) { e.preventDefault(); this.requestCloseWindow(e); return; }
      if (meta && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); this.setState(st => ({ pipeExpanded: !st.pipeExpanded, topMenu:null })); return; }`),t=At(t,[`this.fireToast('Generating new method version…')`,`this.fireToast('Generating new method version\\u2026')`],`this.generateVersionNow()`,2),t=At(t,[`this.fireToast('Validating draft…')`,`this.fireToast('Validating draft\\u2026')`],`this.validateDraftNow()`,2),t=Y(t,jt,Mt),t=Y(t,Nt,Pt),t=Y(t,`
  fireToast(msg) { clearTimeout(this._tt); this.setState({ toast: msg, topMenu:null }); this._tt = setTimeout(() => this.setState({ toast:null }), 1900); }

  renderVals() {`,`\n  fireToast(msg) { clearTimeout(this._tt); this.setState({ toast: msg, topMenu:null }); this._tt = setTimeout(() => this.setState({ toast:null }), 1900); }\n${Ft}\n  renderVals() {`),t=Y(t,`const canDel = s.methods.length > 1;`,`const canDel = s.methods.length > 1;`),t=Y(t,`label: m.label, version: m.version, canDel,`,`label: m.label, version: m.version, canDel: s.backendMode ? !!(m.deletable || m.generated) : canDel, canRename: s.backendMode ? !!(m.editable || m.generated) : true, title: (s.backendMode && !(m.editable || m.generated)) ? 'Reference method is read-only' : 'Double-click to rename editable method',`),t=Y(t,`onStartRename: () => this.setState({ editingNameId: m.id, nameDraft: m.label }),`,`onStartRename: (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); this.startRenameMethod(m); },`),t=Y(t,`startRenameCurrent: () => this.setState({ menuOpen:true, editingNameId: cur.id, nameDraft: cur.label }),`,`startRenameCurrent: () => this.startRenameMethod(cur),`),t=Y(t,`onSelect: () => this.setState({ methodId: m.id, menuOpen: false }),`,`onSelect: (e) => { e?.stopPropagation?.(); this.selectMethodNow(m); },`),t=Y(t,`onDelete: () => this.setState(st => {
        if (st.methods.length <= 1) return {};
        const mm = st.methods.filter(x => x.id !== m.id);
        const methodId = st.methodId === m.id ? mm[0].id : st.methodId;
        return { methods: mm, methodId };
      }),`,`onDelete: () => this.deleteMethodNow(m),`),t=Y(t,`mkItem('Open package…', 'Ctrl+O', () => this.fireToast('Open package… (demo)')),`,`mkItem('Import package…', 'Ctrl+O', () => this.openMethodPackageNow()),`),t=Y(t,`mkItem('Save draft', 'Ctrl+S', () => this.fireToast('Draft saved')),`,`mkItem('Save method', 'Ctrl+S', () => this.saveMethodIfDirtyNow(), !this.hasUnsavedMethodEdits()),`),t=Y(t,`mkItem('Export…', 'Ctrl+E', () => this.fireToast('Export… (demo)')),`,`mkItem('Export…', 'Ctrl+E', () => this.exportGeneratedMethodNow()),`),t=Y(t,`mkItem('Close', 'Ctrl+W', () => this.fireToast('Close (demo)')),`,`mkItem('Close', 'Ctrl+W', () => this.requestCloseWindow()),`),t=Y(t,`createMethod: () => this.setState(st => { const n = st.newSeq; const id = 'draft_' + n; const label = 'New method ' + n; return { methods:[...st.methods, { id, label, version:'0.1.0' }], methodId:id, newSeq:n+1, menuOpen:true, editingNameId:id, nameDraft:label }; }),`,`createMethod: () => this.createMethodNow(),`),t=Y(t,`      menus, anyMenuOpen: !!tm, closeMenus: () => this.setState({ topMenu:null }),`,`      menus, saveMethod: () => this.saveMethodIfDirtyNow(), saveDisabled: !this.hasUnsavedMethodEdits(), saveTitle: this.hasUnsavedMethodEdits() ? 'Save method edits' : 'No method edits to save', savePointerEvents: this.hasUnsavedMethodEdits() ? 'auto' : 'none', anyMenuOpen: !!tm, closeMenus: () => this.setState({ topMenu:null }),`),t=Y(t,`const baseBox = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 13px', cursor:'pointer', position:'relative' };`,`const baseBox = { flex:'1 1 0', minWidth:'0', borderRadius:'8px', padding:'8px 13px', cursor:'pointer', position:'relative' };`),t=Y(t,`const baseRes = { flex:'0 0 276px', borderRadius:'8px', padding:'8px 14px', cursor:'pointer', position:'relative' };`,`const baseRes = { flex:'1 1 0', minWidth:'0', borderRadius:'8px', padding:'8px 14px', cursor:'pointer', position:'relative' };`),t=Y(t,`      { id:'generate', label:'Generate', items:[
        mkItem('Validate draft', 'Ctrl+Enter', () => this.validateDraftNow()),
        mkItem('Generate new version', 'Ctrl+G', () => this.generateVersionNow()),
      ]},`,`      { id:'generate', label:'Save', items:[
        mkItem('Validate draft', 'Ctrl+Enter', () => this.validateDraftNow()),
        mkItem('Save method', 'Ctrl+S', () => this.saveMethodIfDirtyNow(), !this.hasUnsavedMethodEdits()),
      ]},`),t=Y(t,`mkItem('About Method Editor', '', () => this.fireToast('Method Editor · mtdp v0.2.0')),`,`mkItem('About Method Editor', '', () => { this.setState({ topMenu:null }); window.__openMethodGuidelines?.(); }),`),t=Y(t,`      { k:'Ctrl+Enter', d:'Validate draft' },
      { k:'Ctrl+G', d:'Generate new method version' },`,`      { k:'Ctrl+Enter', d:'Validate draft' },
      { k:'Ctrl+S', d:'Save method' },`),t=Y(t,`    const commitName = () => this.setState(st => {
      if (st.editingNameId == null) return {};
      const nm = (st.nameDraft || '').trim();
      const methods = nm ? st.methods.map(x => x.id === st.editingNameId ? { ...x, label: nm } : x) : st.methods;
      return { methods, editingNameId: null };
    });`,`    const commitName = () => this.commitMethodNameNow();`),t=Y(t,`value: s.startStrain, onInput: (e) => this.setState({ startStrain: e.target.value }),`,`value: s.startStrain, onInput: (e) => this.markMethodDirty({ startStrain: e.target.value }),`),t=Y(t,`value: s.endStrain, onInput: (e) => this.setState({ endStrain: e.target.value }),`,`value: s.endStrain, onInput: (e) => this.markMethodDirty({ endStrain: e.target.value }),`),t=Y(t,`label, onClick: () => this.setState(st => ({ excl: { ...st.excl, [k]: !st.excl[k] } })),`,`label, onClick: () => this.markMethodDirty(st => ({ excl: { ...st.excl, [k]: !st.excl[k] } })),`),t=Y(t,`const setGp = (k, v) => this.setState(st => ({ gateP: { ...st.gateP, [k]: v } }));`,`const setGp = (k, v) => this.markMethodDirty(st => ({ gateP: { ...st.gateP, [k]: v } }));`),t=Y(t,`toggle: () => this.setState(st => ({ excl: { ...st.excl, [key]: !st.excl[key] } })),`,`toggle: () => this.markMethodDirty(st => ({ excl: { ...st.excl, [key]: !st.excl[key] } })),`),t=Y(t,`const bl = { magV:String(s.blMag), magOn:(e)=>this.setState({blMag:e.target.value}), ptsV:String(s.blPts), ptsOn:(e)=>this.setState({blPts:e.target.value}), pStyle:pillStyle(true) };`,`const bl = { magV:String(s.blMag), magOn:(e)=>this.markMethodDirty({blMag:e.target.value}), ptsV:String(s.blPts), ptsOn:(e)=>this.markMethodDirty({blPts:e.target.value}), pStyle:pillStyle(true) };`),t=Y(t,`onToggle: () => this.setState(st => ({ trunc: { ...st.trunc, [d.key]: !st.trunc[d.key] } })),`,`onToggle: () => this.markMethodDirty(st => ({ trunc: { ...st.trunc, [d.key]: !st.trunc[d.key] } })),`),t=Y(t,`onInput: d.hasInput ? ((e) => this.setState({ [d.valKey]: e.target.value })) : null,`,`onInput: d.hasInput ? ((e) => this.markMethodDirty({ [d.valKey]: e.target.value })) : null,`),t=Y(t,`const setBend = (k, v) => this.setState(st => ({ bend: { ...st.bend, [k]: v } }));`,`const setBend = (k, v) => this.markMethodDirty(st => ({ bend: { ...st.bend, [k]: v } }));`),t=Y(t,`toggleGate: () => this.setState(st => ({ gateOn: !st.gateOn })),`,`toggleGate: () => this.markMethodDirty(st => ({ gateOn: !st.gateOn })),`),t=Y(t,`setReview: () => this.setState({ borderline:'review' }), setExclude: () => this.setState({ borderline:'exclude' }),`,`setReview: () => this.markMethodDirty({ borderline:'review' }), setExclude: () => this.markMethodDirty({ borderline:'exclude' }),`),t=Y(t,`toggleTrunc: () => this.setState(st => ({ truncOn: !st.truncOn })),`,`toggleTrunc: () => this.markMethodDirty(st => ({ truncOn: !st.truncOn })),`),t=Y(t,`closeWindow: (e) => { e?.stopPropagation?.(); window.desktopApi?.closeWindow?.(); },`,`closeWindow: (e) => this.requestCloseWindow(e),`),t=Y(t,`      startRenameCurrent: () => this.startRenameMethod(cur),`,`      startRenameCurrent: () => this.startRenameMethod(cur),
      renameCurrentFromSelector: (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); this.renameCurrentNow(); },`),t=Y(t,`dirtyLabel: anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' · 1 field needs attention' : changesSummary,`,`dirtyLabel: s.methodDirty ? (anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' · unsaved · 1 field needs attention' : changesSummary + ' · unsaved') : (s.backendDirtyLabel || (anyErr ? changeCount + ' change' + (changeCount===1?'':'s') + ' · 1 field needs attention' : changesSummary)),`),t=Y(t,`genBg:     anyErr ? '#eff1f4' : A,
      genColor:  anyErr ? '#a09a8e' : '#fff',
      genBorder: anyErr ? '#e3e7eb' : A,
      genCursor: anyErr ? 'not-allowed' : 'pointer',`,`genBg:     (anyErr || !s.methodDirty) ? '#eff1f4' : A,
      genColor:  (anyErr || !s.methodDirty) ? '#a09a8e' : '#fff',
      genBorder: (anyErr || !s.methodDirty) ? '#e3e7eb' : A,
      genCursor: (anyErr || !s.methodDirty) ? 'not-allowed' : 'pointer',`),t=Y(t,`statusText: anyErr ? 'Fix field format to continue' : 'Draft — not saved',`,`statusText: s.backendStatusText || (anyErr ? 'Fix field format to continue' : (s.methodDirty ? 'Draft — unsaved edits' : 'No unsaved edits')),`),t}var Bt=Rt(f),Vt=zt(p);function Ht({onReady:e}){let[t,n]=i.useState(!1);return i.useEffect(()=>{let e=()=>n(!0);return window.__openMethodGuidelines=e,()=>{window.__openMethodGuidelines===e&&delete window.__openMethodGuidelines}},[]),(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(o,{name:`AnalysisMethodEditorHiFiV2`,template:Bt,logic:Vt,methodEditorApi:window.desktopApi?.methodEditor,showValidation:!0,onReady:e}),t&&(0,a.jsx)(l,{section:`method`,onClose:()=>n(!1)})]})}window.WIZ=(function(){let e={channel:[`load_N`,`front_strain`,`rear_strain`,`transverse_strain`,`crosshead_mm`,`time_s`,`strain_2`,`strain_axial_2`],field:[`specimen.width`,`specimen.thickness`,`specimen.gauge_length`,`fixture.free_length`,`fixture.type`],metadata:[`fields.Operator Name`,`fields.Test Engineer`,`fields.Fixture`,`fields.Conditioning`,`fields.Environment`,`fields.Test Speed`,`fields.Lab Reference`]},t={name:`CAG-CF-Modied-ULV20.mtdp`,family:`mechanical.compression`,runs:7,schema:`Compression · v0.3.0`,path:`…\\datasets\\Compression\\CAG-CF-Modied-ULV20.mtdp`,channels:[`load_N`,`front_strain`,`rear_strain`,`crosshead_mm`,`time_s`]},n={id:`iso14126_2023`,short:`ISO 14126 Compression — v0.1.0`,title:`BS EN ISO 14126:2023 compression properties`,version:`v0.1.0`,standard:`ISO 14126`,summary:`Determines compressive strength, modulus and failure mode for fibre-reinforced plastic laminates.`,registry:`3 in registry`},r=[`channel.load → load_N`,`channel.strain → strain_axial`,`geometry.width → specimen.width_mm`,`geometry.thickness → specimen.thickness_mm`,`failure_mode → failure_mode_iso`],i=[{field:`report.operator`,example:`G. Macori`,level:`required`,sources:[`fields.Operator Name`,`fields.Test Engineer`]},{field:`report.fixture_description`,example:`4-pt CLC fixture`,level:`required`,sources:[`fields.Fixture`]},{field:`report.conditioning`,example:`23 °C / 50 % RH`,level:`recommended`,sources:[`fields.Conditioning`,`fields.Environment`]},{field:`report.testing_speed`,example:`1 mm/min`,level:`recommended`,sources:[`fields.Test Speed`]},{field:`report.strain_measurement_method`,example:`video extensometer`,level:`recommended`,sources:[]},{field:`report.specimen_type`,example:`rectangular bar`,level:`recommended`,sources:[]},{field:`report.loading_method`,example:`end-loaded`,level:`recommended`,sources:[]}],a={"report.strain_measurement_method":[`video extensometer`,`clip-on extensometer`,`strain gauge`,`DIC`],"report.specimen_type":[`rectangular bar`,`waisted (necked)`,`tabbed`],"report.loading_method":[`end-loaded`,`shear-loaded`,`mixed (combined)`]},o={missing:`Not recorded in source package`,report_override:`Report-only amendment`,source_mtdp_dataset:`Source package dataset metadata`,source_mtdp_run:`Source package run metadata`,mtda_method_output:`Computed method output`},s={required:`Required for complete report`,recommended:`Recommended report field`,optional:`Optional report field`},c=[{id:`channel.load`,input:`channel.load`,desc:`Compressive load channel`,req:`required`,kind:`channel`,status:`matched`,binding:`load_N`,coverage:`7/7 runs`,unit:`N`,via:`header token “Kraft” + unit N`,candidates:[{source:`load_N`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.96,example:`0 … 41 200 N`,reason:`Name + unit exact match`,via:`header token “Kraft” + unit N`}]},{id:`channel.front_strain`,input:`channel.front_strain`,desc:`Front-face strain gauge`,req:`required`,kind:`channel`,status:`matched`,binding:`front_strain`,coverage:`7/7 runs`,unit:`µε`,via:`role + gauge position`,candidates:[{source:`front_strain`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.93,example:`0 … 11 800 µε`,reason:`Role + position match`,via:`role + gauge position`},{source:`rear_strain`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.41,example:`0 … 11 200 µε`,reason:`Same kind, opposite face`}]},{id:`channel.rear_strain`,input:`channel.rear_strain`,desc:`Rear-face strain gauge`,req:`required`,kind:`channel`,status:`matched`,binding:`rear_strain`,coverage:`7/7 runs`,unit:`µε`,via:`role + gauge position`,candidates:[{source:`rear_strain`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.93,example:`0 … 11 200 µε`,reason:`Role + position match`,via:`role + gauge position`},{source:`front_strain`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.41,example:`0 … 11 800 µε`,reason:`Same kind, opposite face`}]},{id:`channel.transverse_strain`,input:`channel.transverse_strain`,desc:`Transverse strain (Poisson)`,req:`recommended`,kind:`channel`,status:`ambiguous`,binding:``,coverage:`7/7 runs`,unit:`µε`,note:`two strain dimensions plausible for header “Dehnung 2”`,candidates:[{source:`strain_2`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.58,example:`0 … 3 900 µε`,reason:`Header “Dehnung 2” — transverse gauge`,via:`parser found 2 plausible families`},{source:`strain_axial_2`,kind:`channel`,scope:`package`,coverage:`7/7 runs`,confidence:.54,example:`0 … 10 400 µε`,reason:`Header “Dehnung 2” — second axial gauge`,via:`parser found 2 plausible families`}]},{id:`specimen.gauge_length_mm`,input:`specimen.gauge_length_mm`,desc:`Gauge length`,req:`required`,kind:`field`,status:`matched`,binding:`specimen.gauge_length`,coverage:`7/7 runs`,unit:`mm`,via:`token alias`,candidates:[{source:`specimen.gauge_length`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.88,example:`10.0 mm`,reason:`Token alias match`,via:`token alias`},{source:`fixture.free_length`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.52,example:`12.5 mm`,reason:`Related length field`}]},{id:`specimen.width_mm`,input:`specimen.width_mm`,desc:`Specimen width`,req:`required`,kind:`field`,status:`matched`,binding:`specimen.width`,coverage:`7/7 runs`,unit:`mm`,via:`exact token`,candidates:[{source:`specimen.width`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.91,example:`25.0 mm`,reason:`Exact token match`,via:`exact token`}]},{id:`specimen.thickness_mm`,input:`specimen.thickness_mm`,desc:`Specimen thickness`,req:`required`,kind:`field`,status:`matched`,binding:`specimen.thickness`,coverage:`7/7 runs`,unit:`mm`,via:`exact token`,candidates:[{source:`specimen.thickness`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.91,example:`2.0 mm`,reason:`Exact token match`,via:`exact token`}]},{id:`report.operator`,input:`report.operator`,desc:`Operator / analyst name`,req:`recommended`,kind:`field`,status:`unmapped`,binding:``,coverage:`—`,unit:``,candidates:[{source:`fields.Operator Name`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.74,example:`G. Macori`,reason:`Label similarity to ‘operator’`},{source:`fields.Test Engineer`,kind:`field`,scope:`package metadata`,coverage:`5/7 runs`,confidence:.55,example:`G. Macori`,reason:`Partial label match`}]},{id:`report.fixture_description`,input:`report.fixture_description`,desc:`Test fixture description`,req:`recommended`,kind:`field`,status:`unmapped`,binding:``,coverage:`—`,unit:``,candidates:[{source:`fields.Fixture`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.68,example:`4-pt CLC fixture`,reason:`Label similarity`}]},{id:`report.conditioning`,input:`report.conditioning`,desc:`Conditioning environment`,req:`recommended`,kind:`field`,status:`unmapped`,binding:``,coverage:`—`,unit:``,candidates:[{source:`fields.Conditioning`,kind:`field`,scope:`package metadata`,coverage:`6/7 runs`,confidence:.62,example:`23 °C / 50 % RH`,reason:`Label similarity`},{source:`fields.Environment`,kind:`field`,scope:`package metadata`,coverage:`7/7 runs`,confidence:.49,example:`Lab ambient`,reason:`Related label`}]}],l=[`Input`,`Method`,`Mapping`,`Ready`,`Resolve`,`Reduce`,`Validate`,`Accept`,`Write`,`Report`,`Done`],u=[{pct:100,stage:`Done`,level:`info`,msg:`No backend execution trace is available.`}],d=[];function f(e,t,n=46){let r=[];for(let i=0;i<n;i++){let a=i/(n-1),o=t*a**.85*(1-.18*Math.sin(a*7+e));r.push(Math.max(0,o+Math.sin(i*1.7+e)*t*.015))}return r}function p(e,t,n=40){let r=[];for(let i=0;i<n;i++){let a=i/(n-1);r.push({x:a*1.05,y:t*(1-Math.exp(-3.1*a))*(1+.04*Math.sin(e+a*5))})}return r}p(0,1);function m({peak:e,threshold:t,pointsAbove:n,assessed:r,longest:i,call:a,action:o,window:s}){let c=r?n/r:0;return{kind:`bending`,tab:`Bending`,title:`Bending defect`,series:f(e*30,e),threshold:t,peak:e,window:s,segments:n>0?[[.52,.52+Math.min(.34,c+.06)]]:[],cards:[{key:`bending.classification`,label:`Bending call`,value:a,sub:`pattern in 10–90 % Fmax window`,level:`warn`},{key:`bending.max_percent`,label:`Peak imbalance`,value:e.toFixed(3)+`%`,sub:`max opposite-face strain imbalance`,level:`warn`},{key:`bending.threshold_percent`,label:`Review limit`,value:t.toFixed(2)+`%`,sub:`configured ISO 14126 bending threshold`,level:`info`},{key:`bending.points_above_threshold`,label:`Persistence`,value:String(n),sub:`${n} of ${r} assessed points above limit`,level:`warn`},{key:`bending.fraction_above_threshold`,label:`Window share`,value:(c*100).toFixed(1)+`%`,sub:`share of assessed load window`,level:`warn`},{key:`bending.longest_exceedance_segment`,label:`Longest segment`,value:i,sub:`contiguous exceedance evidence`,level:`info`},{key:`selection.consequence_summary`,label:`Scientist action`,value:o,sub:`final report consequence`,level:`info`}]}}return{APP_VERSION:`v0.6.0`,PACKAGE:t,METHOD:n,AVAILABLE_SOURCES:e,BOUND_CRITICAL_COUNT:35,BOUND_EXAMPLES:r,REPORT_BIND_FIELDS:i,REPORT_FIELD_OPTIONS:a,METADATA_BLANK_COUNT:38,SOURCE_TYPE_LABEL:o,IMPORTANCE_LABEL:s,BINDINGS:c,STAGES:l,TRACE_SCRIPT:u,RUN_TABLE:d,FLAGGED:[{run:`demo_run_001`,defaultCall:`Remove`,excluded:!1,defects:[`Bending`],reason:`Demo acceptance finding`,flags:[{severity:`review`,category:`bending`,message:`Demo bending review`}],narrative:`Demo-only acceptance evidence. Production review rows are loaded from the analysed dataset.`,cockpits:[m({peak:.12,threshold:.1,pointsAbove:3,assessed:40,longest:`3 points`,call:`Demo review`,action:`Excluded from final report unless kept with justification`,window:[.1,.9]})]}],OUTPUT:{mtda:`CAG-CF-Modied-ULV20.mtda`,path:`…\\datasets\\Compression\\CAG-CF-Modied-ULV20.mtda`,archiveMembers:47,requiredMissing:2,recommendedMissing:5,amendments:0,reviewerNotes:0,mtdaVersion:`v1.0.0`,sourceVersion:`draft`,artifacts:[{id:`test_report`,title:`Test Report`,role:`Formal ISO 14126 results & report-ready tables`,icon:`report`,status:`warn`,statusLabel:`Has warnings`},{id:`audit_report`,title:`Audit Report`,role:`Process-verification evidence for gates & execution`,icon:`audit`,status:`ok`,statusLabel:`Available`},{id:`browser`,title:`MTDA Browser`,role:`Browsable overview that links every artifact in the archive`,icon:`book`,status:`ok`,statusLabel:`Available`},{id:`folder`,title:`Output folder`,role:`Browse the MTDA archive on disk`,icon:`folder`,status:`ok`,statusLabel:`47 members`},{id:`open_mtda`,title:`Open MTDA`,role:`Open extracted archive browser`,icon:`package`,status:`ok`,statusLabel:`draft`}]},REPORT_FIELDS:[{field:`report.operator`,label:`Operator`,section:`Test Identification`,example:`G. Macori`,level:`required`,source:`missing`,value:``,type:`string`},{field:`report.test_date`,label:`Test date`,section:`Test Identification`,example:`2026-04-18`,level:`recommended`,source:`missing`,value:``,type:`date`},{field:`report.fixture_description`,label:`Fixture`,section:`Loading Fixture`,example:`4-pt CLC fixture`,level:`required`,source:`missing`,value:``,type:`enum`,choices:[`CLC (combined loading)`,`4-pt CLC fixture`,`end-loaded block`,`shear-loaded (IITRI)`]},{field:`report.conditioning`,label:`Conditioning`,section:`Test Conditions`,example:`23 °C / 50 % RH`,level:`recommended`,source:`missing`,value:``,type:`enum`,choices:[`23 °C / 50 % RH`,`dry (as received)`,`85 °C / 85 % RH`,`not recorded`]},{field:`report.testing_speed`,label:`Test speed`,section:`Test Conditions`,example:`1.0`,level:`recommended`,source:`missing`,value:``,type:`float`,unit:`mm/min`,units:[`mm/min`,`in/min`],min:0},{field:`report.strain_measurement_method`,label:`Strain method`,section:`Measurement Method`,example:`video extensometer`,level:`recommended`,source:`missing`,value:``,type:`enum`,choices:[`video extensometer`,`clip-on extensometer`,`strain gauge`,`DIC`]},{field:`report.specimen_type`,label:`Specimen type`,section:`Overview`,example:`rectangular bar`,level:`recommended`,source:`missing`,value:``,type:`enum`,choices:[`rectangular bar`,`waisted (necked)`,`tabbed`]},{field:`report.loading_method`,label:`Loading method`,section:`Overview`,example:`end-loaded`,level:`recommended`,source:`missing`,value:``,type:`enum`,choices:[`end-loaded`,`shear-loaded`,`mixed (combined)`]},{field:`report.tabbed`,label:`Tabbed specimen`,section:`Overview`,example:`yes`,level:`recommended`,source:`missing`,value:``,type:`bool`}],TYPE_HINT:{string:`text`,float:`number > 0`,date:`date · yyyy-MM-dd`,enum:`choices`,bool:`yes / no`},FINAL_CHECKS:{passed:[`Execution completed for all 7 runs`,`Output deviation & tolerance checks within limits`,`Acceptance policy applied · every flagged run reviewed`,`35/35 critical method inputs bound`,`MTDA archive written · 47 members`],outOfScope:[`Raw-data plausibility (operator responsibility)`,`Image-evidence completeness (not gated at finalize)`],issues:[{level:`error`,label:`2 required report fields missing — operator, fixture`,jump:`report`},{level:`report`,label:`5 recommended report fields blank`,jump:`report`}]},FINAL_REASON_KINDS:[[`review_decisions`,`Acceptance / review decisions`],[`report_completion`,`Report-completion amendments`],[`mapping_repair`,`Mapping repair`],[`other`,`Other (describe in note)`]]}})();var X=window.WIZ,Ut=`Included in final report unless removed by operator`,Wt=`Excluded from final report unless kept with justification`,{useState:Z,useEffect:Gt,useRef:Kt,useMemo:qt,useCallback:Jt}=i.default;function Q({name:e,className:t}){let n={fill:`none`,stroke:`currentColor`,strokeWidth:1.6,strokeLinecap:`round`,strokeLinejoin:`round`};return(0,a.jsx)(`svg`,{className:t,viewBox:`0 0 18 18`,width:`18`,height:`18`,"aria-hidden":`true`,children:{package:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M3 6.5 9 3l6 3.5v5L9 15l-6-3.5z`}),(0,a.jsx)(`path`,{...n,d:`M3 6.5 9 10l6-3.5M9 10v5`})]}),method:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`rect`,{...n,x:`3.5`,y:`3`,width:`11`,height:`12`,rx:`1.5`}),(0,a.jsx)(`path`,{...n,d:`M6 6.5h6M6 9h6M6 11.5h3.5`})]}),mapping:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`circle`,{...n,cx:`5`,cy:`5`,r:`1.8`}),(0,a.jsx)(`circle`,{...n,cx:`13`,cy:`13`,r:`1.8`}),(0,a.jsx)(`path`,{...n,d:`M6.7 5h3.3a2 2 0 0 1 2 2v4.3`})]}),report:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M5 2.5h5L14 6v9.5H5z`}),(0,a.jsx)(`path`,{...n,d:`M9.5 2.5V6H14M7 9h5M7 11.5h5M7 6.5h2`})]}),audit:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`rect`,{...n,x:`3`,y:`3`,width:`12`,height:`12`,rx:`1.5`}),(0,a.jsx)(`path`,{...n,d:`M6 11l2-2.5 2 1.5 3-4`})]}),workbench:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M3.5 14.5 9 3l5.5 11.5z`}),(0,a.jsx)(`path`,{...n,d:`M6 11h6`})]}),folder:(0,a.jsx)(a.Fragment,{children:(0,a.jsx)(`path`,{...n,d:`M2.5 5.5A1 1 0 0 1 3.5 4.5H7l1.3 1.4h6.2a1 1 0 0 1 1 1V13a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1z`})}),copy:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`rect`,{...n,x:`5.5`,y:`5.5`,width:`8`,height:`9`,rx:`1.2`}),(0,a.jsx)(`path`,{...n,d:`M3.5 10.5V3.5a1 1 0 0 1 1-1h6`})]}),check:(0,a.jsx)(`path`,{...n,d:`M3.5 9.5 7 13l7-8`}),warn:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M9 2.8 16 14.5H2z`}),(0,a.jsx)(`path`,{...n,d:`M9 7v3.4M9 12.4v.1`})]}),info:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`circle`,{...n,cx:`9`,cy:`9`,r:`6.5`}),(0,a.jsx)(`path`,{...n,d:`M9 8.2v4M9 5.9v.1`})]}),x:(0,a.jsx)(`path`,{...n,d:`M4 4l10 10M14 4 4 14`}),chevron:(0,a.jsx)(`path`,{...n,d:`M4 7l5 5 5-5`}),arrowR:(0,a.jsx)(`path`,{...n,d:`M3.5 9h11M10 4.5 14.5 9 10 13.5`}),play:(0,a.jsx)(`path`,{...n,d:`M5 3.5 14 9l-9 5.5z`,fill:`currentColor`}),pulse:(0,a.jsx)(`path`,{...n,d:`M2 9h3l2-5 4 10 2-5h3`}),save:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M3.5 3.5h8L15 7v7.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z`}),(0,a.jsx)(`path`,{...n,d:`M6 3.5v3.5h5M6 15v-4h6v4`})]}),edit:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M11.5 3.5 14.5 6.5 6 15H3v-3z`}),(0,a.jsx)(`path`,{...n,d:`M10 5 13 8`})]}),link:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M7.5 10.5 10.5 7.5`}),(0,a.jsx)(`path`,{...n,d:`M8 5.5 9.8 3.7a2.6 2.6 0 0 1 3.7 3.7l-1.8 1.8M10 12.5l-1.8 1.8a2.6 2.6 0 0 1-3.7-3.7L6.3 8.6`})]}),plus:(0,a.jsx)(`path`,{...n,d:`M9 4v10M4 9h10`}),trash:(0,a.jsx)(a.Fragment,{children:(0,a.jsx)(`path`,{...n,d:`M3.5 5h11M7 5V3.5h4V5M5 5l.7 9.5h6.6L13 5`})}),filter:(0,a.jsx)(`path`,{...n,d:`M3 4h12l-4.5 5.5V14L7.5 12.5V9.5z`}),book:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M3 4.2C4.8 3 7 3 9 4.2 11 3 13.2 3 15 4.2V14c-1.8-1.2-4-1.2-6 0-2-1.2-4.2-1.2-6 0z`}),(0,a.jsx)(`path`,{...n,d:`M9 4.2V14`})]}),undo:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`path`,{...n,d:`M5 7H10.5a3.5 3.5 0 0 1 0 7H6`}),(0,a.jsx)(`path`,{...n,d:`M7 4 4 7l3 3`})]}),users:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`circle`,{...n,cx:`7`,cy:`6.5`,r:`2.4`}),(0,a.jsx)(`path`,{...n,d:`M2.5 14.5a4.5 4.5 0 0 1 9 0`}),(0,a.jsx)(`path`,{...n,d:`M12 4.4a2.4 2.4 0 0 1 0 4.6M13 14.5a4.5 4.5 0 0 0-2-3.6`})]})}[e]||null})}function Yt({tone:e=`idle`,children:t,dot:n=!0}){return(0,a.jsxs)(`span`,{className:`chip`,"data-tone":e,children:[n&&(0,a.jsx)(`span`,{className:`cdot`}),t]})}function Xt({value:e}){let t=Math.round(e*100),n=e>=.8?`ok`:e>=.55?`warn`:`err`,r=e>=.8?`high`:e>=.55?`medium`:`low`,i=n===`ok`?`var(--ok-accent)`:n===`warn`?`var(--warn-accent)`:`var(--danger)`;return(0,a.jsxs)(`div`,{className:`conf`,title:`Match confidence ${t}%`,children:[(0,a.jsx)(`div`,{className:`conf-bars`,children:[0,1,2,3,4].map(t=>(0,a.jsx)(`span`,{style:{background:t<Math.round(e*5)?i:`var(--surface-3)`}},t))}),(0,a.jsxs)(`span`,{className:`conf-label`,style:{color:i},children:[r,` · `,t,`%`]})]})}function Zt({series:e,threshold:t,peak:n,window:r,segments:i,width:o=250,height:s=96}){let c=Array.isArray(e)?e.map(Number).filter(Number.isFinite):[],l=Number.isFinite(Number(t))?Number(t):0,u=Number.isFinite(Number(n))?Number(n):Math.max(l,...c,0),d=c.length;if(d<2)return(0,a.jsx)(_n,{message:`Evidence gap: missing plot.bending_curve.`});let f=Math.max(u*1.15,l*1.3,...c,.01),p=e=>e/(d-1)*(o-8)+4,m=e=>e*(o-8)+4,h=e=>s-10-e/f*(s-20),g=c.map((e,t)=>`${t===0?`M`:`L`}${p(t).toFixed(1)} ${h(e).toFixed(1)}`).join(` `),_=`${g} L${p(d-1).toFixed(1)} ${s-10} L${p(0).toFixed(1)} ${s-10} Z`,v=h(l),y=u>l?`var(--warn-accent)`:`var(--ok-accent)`,b=r||null;return(0,a.jsxs)(`div`,{className:`spark`,children:[(0,a.jsx)(`div`,{className:`spark-cap label-caps`,children:`bending % vs load · 10–90 % window`}),(0,a.jsxs)(`svg`,{width:o,height:s,className:`spark-svg`,children:[(0,a.jsx)(`defs`,{children:(0,a.jsxs)(`linearGradient`,{id:`g-${l}-${u}`,x1:`0`,y1:`0`,x2:`0`,y2:`1`,children:[(0,a.jsx)(`stop`,{offset:`0%`,stopColor:y,stopOpacity:`0.22`}),(0,a.jsx)(`stop`,{offset:`100%`,stopColor:y,stopOpacity:`0`})]})}),b&&(0,a.jsx)(`rect`,{x:m(b[0]),y:`2`,width:m(b[1])-m(b[0]),height:s-12,fill:`var(--info-accent)`,opacity:`0.06`}),b&&[b[0],b[1]].map((e,t)=>(0,a.jsx)(`line`,{x1:m(e),y1:`2`,x2:m(e),y2:s-10,stroke:`var(--info-accent)`,strokeWidth:`1`,strokeDasharray:`2 2`,opacity:`0.5`},t)),(i||[]).map((e,t)=>(0,a.jsx)(`rect`,{x:m(e[0]),y:`2`,width:m(e[1])-m(e[0]),height:s-12,fill:`var(--warn-accent)`,opacity:`0.14`},t)),(0,a.jsx)(`line`,{x1:`4`,y1:v,x2:o-4,y2:v,stroke:`var(--danger)`,strokeWidth:`1`,strokeDasharray:`3 3`,opacity:`0.7`}),(0,a.jsxs)(`text`,{x:o-6,y:v-4,textAnchor:`end`,fontSize:`9`,fill:`var(--danger)`,fontFamily:`var(--mono)`,children:[`thr `,Ln(l)]}),(0,a.jsx)(`path`,{d:_,fill:`url(#g-${l}-${u})`}),(0,a.jsx)(`path`,{d:g,fill:`none`,stroke:y,strokeWidth:`1.8`,strokeLinejoin:`round`})]})]})}function Qt({k:e,v:t,sub:n,tone:r}){return(0,a.jsxs)(`div`,{className:`metric`,"data-tone":r||``,children:[(0,a.jsx)(`div`,{className:`metric-k label-caps`,children:e}),(0,a.jsx)(`div`,{className:`metric-v`,children:t}),(0,a.jsx)(`div`,{className:`metric-sub`,children:n})]})}function $({variant:e,size:t,icon:n,children:r,className:i,...o}){return(0,a.jsxs)(`button`,{className:[`btn`,e,t,i].filter(Boolean).join(` `),...o,children:[n&&(0,a.jsx)(Q,{name:n,className:`ic`}),r]})}Object.assign(window,{Icon:Q,Chip:Yt,Confidence:Xt,Sparkline:Zt,Metric:Qt,Btn:$,useState:Z,useEffect:Gt,useRef:Kt,useMemo:qt,useCallback:Jt});function $t({badge:e,badgeTone:t,title:n,why:r,defaultOpen:i=!0,collapsible:o=!0,children:s,right:c}){let[l,u]=Z(i);return(0,a.jsxs)(`div`,{className:`task`,children:[(0,a.jsxs)(`div`,{className:`task-head`+(l?``:` bare`),onClick:()=>o&&u(e=>!e),style:{cursor:o?`pointer`:`default`},children:[(0,a.jsx)(`span`,{className:`task-flag`,"data-tone":t,children:e}),(0,a.jsxs)(`div`,{className:`col`,style:{gap:1,minWidth:0},children:[(0,a.jsx)(`span`,{className:`task-title`,children:n}),r&&(0,a.jsx)(`span`,{className:`taskWhy`,children:r})]}),(0,a.jsx)(`span`,{className:`spacer`}),c,o&&(0,a.jsx)(Q,{name:`chevron`,className:`task-chev`,style:{width:15,height:15,transform:l?`none`:`rotate(-90deg)`,color:`var(--ink-3)`}})]}),l&&(0,a.jsx)(`div`,{className:`task-body fade-in`,children:s})]})}function en({level:e}){return e===`required`?(0,a.jsx)(`span`,{className:`reqmark req`,title:`Required for complete report`,children:`*`}):e===`report`?(0,a.jsx)(`span`,{className:`reqmark rep`,title:`Required for report`,children:`†`}):(0,a.jsx)(`span`,{className:`reqmark rec`,title:`Recommended report field`,children:`**`})}function tn({pkg:e,method:t,mappingState:n,mappingSummary:r,methodCount:i,onChangePackage:o,onChangeMethod:s,onEditMapping:c}){let l=t?[t.version,t.standard].filter(Boolean).join(` · `):e?`${i||1} implemented method${(i||1)===1?``:`s`} available`:`selected after package`,u=t?r?.label||(r?`${r.bound_count||0}/${r.critical_total||0} critical bound`:`selected from method default`):`selected after method`;return(0,a.jsx)(`div`,{className:`inputs-row`,children:[{k:`PACKAGE`,v:e?e.name:`not selected`,sub:e?`${e.runs} runs · ${e.family}`:`required`,state:e?`ok`:`pending`,action:e?`Change package`:`Choose package`,on:o,enabled:!0},{k:`METHOD`,v:t?t.title:`not selected`,sub:l,state:t?`ok`:`pending`,action:t?`Change method`:`Choose method`,on:s,enabled:!!e},{k:`MAPPING`,v:t?r?.mapping_name||`default mapping`:`not selected`,sub:u,state:t?n:`pending`,action:`Review mapping`,on:c,enabled:!!t}].map(e=>(0,a.jsxs)(`div`,{className:`input-tile`,"data-state":e.state,children:[(0,a.jsxs)(`div`,{className:`tile-k`,children:[(0,a.jsx)(`span`,{className:`tile-dot`}),e.k]}),(0,a.jsx)(`div`,{className:`tile-v`,title:e.v,children:e.v}),(0,a.jsx)(`div`,{className:`tile-meta`,children:e.sub}),e.enabled&&(0,a.jsx)(`div`,{className:`tile-link`,onClick:e.on,children:e.action})]},e.k))})}function nn(e){let{pkg:t,method:n,pkgSel:r,setPkgSel:i,onChoosePackage:o,methodEntry:s,onConfirmMethod:c,mappingResolved:l,metadataResolved:u,onSaveBindings:d,onSkipBindings:f,onEditMapping:p,onOpenMetadata:m,onAcceptMetadata:h,onChangePackage:g,onChangeMethod:_,backendPackageError:v,analysisSession:y,methodOptions:b=[],selectedMethodId:x,onSelectMethodId:S,mappingSummary:C,recentPackages:w=[],recentPackageLoading:T,recentPackageError:E,onOpenPackageDialog:D,runEnabled:O,readinessStatus:k}=e,A=X.REPORT_BIND_FIELDS,ee=A.filter(e=>e.level===`required`).length,te=t&&n&&l&&u,j=b.length?b:[s||X.METHOD],M=x||j[0]?.id||``,N=j.find(e=>e.id===M)||j[0]||X.METHOD,ne=N?.id||``,re=`${j.length} method${j.length===1?``:`s`} match${j.length===1?`es`:``} ${t?.family||`the package`}`,P=C||n?.mappingSummary||N?.mappingSummary,F=P?`${P.bound_count||0}/${P.critical_total||0} critical inputs bound`:`mapping selected from method default`,I=ti(y,O),L=k||$r(y)||(O?`WORKFLOW_READY`:`NOT_CHECKED`);return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:te?`Ready to run`:t&&n?`2 things to decide first`:`Choose workflow inputs`}),(0,a.jsxs)(`div`,{className:`sub`,children:[`ISO 14126 on `,(0,a.jsx)(`b`,{children:t?t.name:`no package selected`}),` · `,t?`${t.runs} runs · mechanical.compression`:`readiness not checked`]})]}),y?.package&&(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`info`,style:{marginBottom:12},children:[(0,a.jsx)(Q,{name:`package`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsx)(`b`,{children:`Loaded from Dataset Packaging.`}),` `,y.package.package_path]})]}),v&&(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`warn`,style:{marginBottom:12},children:[(0,a.jsx)(Q,{name:`warn`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsx)(`b`,{children:`Package handoff failed.`}),` `,v]})]}),y?.readiness&&(0,a.jsxs)(`div`,{className:`banner`,"data-tone":I?`ok`:`warn`,style:{marginBottom:12},children:[(0,a.jsx)(Q,{name:I?`check`:`warn`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsxs)(`b`,{children:[`Readiness `,y.readiness.status,`.`]}),` `,y.readiness.summary?.execution_critical_passed??0,`/`,y.readiness.summary?.execution_critical_total??0,` critical inputs · `,y.readiness.summary?.report_missing_total??0,` report gaps`]})]}),(0,a.jsx)(tn,{pkg:t,method:n,mappingState:P?.critical_missing_count?`warn`:`ok`,mappingSummary:P,methodCount:j.length,onChangePackage:g,onChangeMethod:_,onEditMapping:p}),!t&&(0,a.jsx)($t,{badge:`needs you`,badgeTone:`warn`,title:`Choose an MTDP package`,collapsible:!1,right:(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:`var(--t-xs)`},children:T?`loading recent packages`:`${w.length} recent package${w.length===1?``:`s`}`}),children:(0,a.jsx)(`div`,{className:`card`,style:{overflow:`hidden`,marginBottom:12},children:w.length>0?(0,a.jsx)(`div`,{className:`pick-list`,children:w.map(e=>(0,a.jsxs)(`div`,{className:`pick`+(r===e.path?` sel`:``),onClick:()=>{i(e.path),o(e)},children:[(0,a.jsx)(`div`,{className:`p-ic`,children:(0,a.jsx)(Q,{name:`package`})}),(0,a.jsxs)(`div`,{className:`p-main`,children:[(0,a.jsx)(`div`,{className:`p-name`,children:e.name}),(0,a.jsxs)(`div`,{className:`p-meta`,children:[e.note,` · `,e.mtime||`recent`]})]}),(0,a.jsx)(`div`,{className:`p-runs`,children:e.runs?`${e.runs} runs`:e.family}),(0,a.jsx)(`div`,{className:`p-check`,children:(0,a.jsx)(Q,{name:`arrowR`})})]},e.path))}):(0,a.jsxs)(`div`,{className:`empty`,style:{padding:18},children:[(0,a.jsx)(`div`,{className:`empty-title`,children:T?`Loading recent packages...`:`No recent packages found`}),(0,a.jsx)(`div`,{className:`muted`,style:{marginTop:4},children:E||`Open a package from a folder to add it to this list.`}),(0,a.jsx)(`div`,{className:`row`,style:{marginTop:12},children:(0,a.jsx)($,{variant:`primary`,icon:`package`,onClick:D,children:`Choose package...`})})]})})}),t&&!n&&(0,a.jsxs)($t,{badge:`needs you`,badgeTone:`warn`,title:`Choose an implemented method`,collapsible:!1,right:(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:`var(--t-xs)`},children:re}),children:[(0,a.jsxs)(`div`,{className:`method-pick-row`,children:[(0,a.jsx)(`span`,{className:`label-caps`,style:{flex:`none`},children:`Method`}),(0,a.jsx)(`select`,{className:`field-input`,style:{maxWidth:360},value:ne,onChange:e=>S?.(e.target.value),children:j.map(e=>(0,a.jsx)(`option`,{value:e.id,children:e.short||e.title},e.id))}),(0,a.jsxs)(`span`,{className:`chip`,"data-tone":P?.critical_missing_count?`warn`:`ok`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:12,height:12}}),F]})]}),(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`info`,style:{marginTop:12},children:[(0,a.jsx)(Q,{name:`info`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsxs)(`b`,{children:[N.title,`.`]}),` `,N.summary]})]}),(0,a.jsxs)(`div`,{className:`row`,style:{marginTop:12,gap:8},children:[(0,a.jsx)($,{variant:`primary`,icon:`arrowR`,onClick:c,children:`Confirm method`}),(0,a.jsx)($,{onClick:g,children:`Choose package…`})]})]}),t&&n&&!te&&(0,a.jsxs)(a.Fragment,{children:[!l&&(0,a.jsxs)($t,{badge:`needs you`,badgeTone:`warn`,title:`Bind ${A.length} report fields, or accept the warnings`,why:`${ee} of ${A.length} required · method runs either way.`,children:[(0,a.jsxs)(`details`,{className:`bound-summary`,children:[(0,a.jsxs)(`summary`,{children:[(0,a.jsx)(`span`,{className:`bs-dot`}),(0,a.jsx)(`b`,{children:X.BOUND_CRITICAL_COUNT}),` critical inputs bound automatically`]}),(0,a.jsxs)(`div`,{className:`bound-chips`,style:{marginTop:10},children:[X.BOUND_EXAMPLES.map(e=>(0,a.jsxs)(`span`,{className:`chip`,"data-tone":`ok`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:12,height:12}}),e]},e)),(0,a.jsx)(`span`,{className:`chip-link`,onClick:p,children:`open mapping editor →`})]})]}),(0,a.jsxs)(`div`,{className:`label-caps`,style:{color:`var(--warn-ink)`,margin:`14px 0 8px`},children:[`Unbound report fields · `,A.length,` `,(0,a.jsx)(`span`,{className:`muted-3`,style:{textTransform:`none`,letterSpacing:0},children:`(not in the source package)`})]}),(0,a.jsx)(`div`,{className:`card`,style:{overflow:`hidden`},children:(0,a.jsxs)(`table`,{className:`tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{style:{width:`34%`},children:`Field`}),(0,a.jsx)(`th`,{children:`Example value`}),(0,a.jsx)(`th`,{style:{width:`38%`},children:`Resolution`})]})}),(0,a.jsx)(`tbody`,{children:A.map(e=>{let t=X.REPORT_FIELD_OPTIONS[e.field];return(0,a.jsxs)(`tr`,{children:[(0,a.jsxs)(`td`,{className:`mono`,children:[e.field,` `,(0,a.jsx)(en,{level:e.level})]}),(0,a.jsx)(`td`,{className:`muted`,children:e.example}),(0,a.jsx)(`td`,{children:(0,a.jsxs)(`select`,{className:`field-input`,defaultValue:``,style:{padding:`5px 9px`},children:[(0,a.jsx)(`option`,{value:``,children:`Leave blank — accept warning`}),e.sources&&e.sources.length>0&&(0,a.jsx)(`optgroup`,{label:`Bind to package source`,children:e.sources.map(e=>(0,a.jsx)(`option`,{value:`src:`+e,children:e},e))}),t&&t.length>0&&(0,a.jsx)(`optgroup`,{label:`Set value`,children:t.map(e=>(0,a.jsx)(`option`,{value:`val:`+e,children:e},e))}),(0,a.jsx)(`option`,{value:`manual`,children:`Enter manually…`})]})})]},e.field)})})]})}),(0,a.jsxs)(`div`,{className:`row`,style:{marginTop:13,gap:8},children:[(0,a.jsx)($,{variant:`primary`,icon:`save`,onClick:d,children:`Save bindings`}),(0,a.jsx)($,{onClick:f,children:`Skip — accept warnings`}),(0,a.jsx)($,{icon:`edit`,onClick:p,children:`Edit mapping profile…`}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:`var(--t-xs)`},children:`Method runs either way.`})]})]}),!u&&(0,a.jsx)($t,{badge:`optional`,badgeTone:`info`,title:`${X.METADATA_BLANK_COUNT} recommended report fields blank`,why:`Report-only — they don't affect the calculation.`,defaultOpen:l,children:(0,a.jsxs)(`div`,{className:`row`,style:{gap:8},children:[(0,a.jsx)($,{variant:`primary`,icon:`report`,onClick:m,children:`Complete report fields`}),(0,a.jsx)($,{onClick:h,children:`Leave blank — accept warnings`})]})})]}),te&&(0,a.jsxs)(`div`,{className:`setup-empty fade-in`,children:[(0,a.jsx)(`div`,{className:`se-ic`,children:(0,a.jsx)(Q,{name:`check`})}),(0,a.jsx)(`div`,{className:`se-t`,children:`All decisions resolved`}),(0,a.jsxs)(`div`,{className:`se-s`,children:[`Readiness `,(0,a.jsx)(`span`,{className:`mono`,children:L}),` · run is `,O?`enabled`:`not enabled`,`. Use `,(0,a.jsx)(`b`,{children:`Run method`}),` below.`]})]})]})}Object.assign(window,{SetupSpotlight:nn,TaskCard:$t,InputTiles:tn,ReqMark:en});function rn(e){return e.status===`matched`||e.status===`manual`}function an({initial:e=[],mappingSummary:t,onClose:n,onSave:r,onBrowse:i,onSaveAs:o,onDirtyChange:s}){function c(e){return(e||[]).map(e=>({...e,candidates:Array.isArray(e.candidates)?e.candidates:[]}))}let[l,u]=Z(()=>c(e)),[d,f]=Z(()=>{let t=e.find(e=>!rn(e));return t?t.id:e[0]?.id||``}),[p,m]=Z(`repair`),[h,g]=Z(!0),[_,v]=Z(!0),[y,b]=Z(!1),x=_||y,[S,C]=Z(`field`),[w,T]=Z(``),[E,D]=Z(!1);Gt(()=>{s?.(E)},[E,s]);let O=l.find(e=>e.id===d),k=t?.path||t?.mapping_name||`Backend mapping profile`,A=e=>{f(e),v(!1),b(!1)};function ee(e){let t=c(e);u(t),f(e=>{if(t.some(t=>t.id===e))return e;let n=t.find(e=>!rn(e));return n?n.id:t[0]?.id||``}),D(!1)}async function te(){if(!i)return;let e=await i({bindings:l,dirty:E});Array.isArray(e)&&ee(e)}async function j(){if(!o)return;let e=await o(l,E);Array.isArray(e)&&ee(e)}let M=qt(()=>{let e=l.filter(e=>e.req===`required`),t=e.filter(rn).length,n=l.filter(e=>e.req===`recommended`),r=n.filter(rn).length,i=e.filter(e=>!rn(e)).length,a=l.filter(e=>e.status===`ambiguous`).length,o=n.filter(e=>e.status===`unmapped`).length;return{critTotal:e.length,critBound:t,repTotal:n.length,repBound:r,blockers:i,ambiguous:a,reportGaps:o}},[l]),N=qt(()=>({attention:l.filter(e=>!rn(e)),resolved:l.filter(rn)}),[l]);function ne(e){u(t=>t.map(t=>t.id===d?{...t,status:`manual`,binding:e.source,coverage:e.coverage===`—`?`7/7 runs`:e.coverage,_custom:!1}:t)),D(!0)}function re(){u(e=>e.map(e=>e.id===d?{...e,status:`unmapped`,binding:``,coverage:`—`,_custom:!1}:e)),D(!0)}function P(){w.trim()&&(u(e=>e.map(e=>e.id===d?{...e,status:`manual`,binding:w.trim(),coverage:`custom`,kind:S,_custom:!0}:e)),T(``),D(!0))}let F=M.blockers?`err`:M.ambiguous||M.reportGaps?`warn`:`ok`;return(0,a.jsx)(`div`,{className:`scrim no-flicker-overlay`,onMouseDown:e=>e.target===e.currentTarget&&n(),children:(0,a.jsxs)(`div`,{className:`dialog`,style:{width:`min(1120px, 95vw)`,height:`auto`,maxHeight:`min(740px, 92%)`},onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsxs)(`div`,{className:`dialog-head`,children:[(0,a.jsx)(Q,{name:`mapping`}),(0,a.jsx)(`div`,{className:`col`,style:{gap:1},children:(0,a.jsx)(`h2`,{children:`Method mapping`})}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsxs)(`div`,{className:`path-field`,style:{maxWidth:300},title:k,children:[(0,a.jsx)(Q,{name:`mapping`,style:{width:14,height:14,flex:`none`,opacity:.6}}),(0,a.jsx)(`span`,{children:t?.mapping_name||k})]}),(0,a.jsx)($,{size:`sm`,icon:`folder`,disabled:!i,onClick:te,title:`Choose a mapping profile through the desktop backend.`,children:`Browse…`})]}),(0,a.jsxs)(`div`,{className:`dialog-body`,style:{display:`flex`,flexDirection:`column`,gap:12,paddingBottom:0},children:[(0,a.jsxs)(`div`,{className:`map-readout`,"data-tone":F,children:[(0,a.jsx)(Q,{name:M.blockers?`warn`:M.ambiguous||M.reportGaps?`info`:`check`,className:`mr-ic`}),(0,a.jsx)(`div`,{className:`mr-text`,children:M.blockers?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`b`,{children:[`Map `,M.blockers,` required input`,M.blockers>1?`s`:``]}),` to make this package runnable.`]}):M.ambiguous?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`b`,{children:[`Disambiguate `,M.ambiguous,` binding`,M.ambiguous>1?`s`:``]}),`, or leave the report field blank — critical inputs are already bound.`]}):M.reportGaps?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`b`,{children:[`Optionally map `,M.reportGaps,` report field`,M.reportGaps>1?`s`:``]}),` — or resolve them at finalization.`]}):(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`b`,{children:`Every method input has a confident source.`}),` Save to use this profile.`]})}),(0,a.jsxs)(`div`,{className:`mr-stats`,children:[(0,a.jsxs)(`span`,{className:`mr-stat`,children:[(0,a.jsxs)(`b`,{children:[M.critBound,`/`,M.critTotal]}),` critical`]}),(0,a.jsxs)(`span`,{className:`mr-stat`,children:[(0,a.jsxs)(`b`,{children:[M.repBound,`/`,M.repTotal]}),` report`]}),M.ambiguous>0&&(0,a.jsxs)(`span`,{className:`mr-stat amb`,children:[(0,a.jsx)(`b`,{children:M.ambiguous}),` ambiguous`]})]})]}),(0,a.jsx)(`div`,{className:`map-tabs`,children:[[`repair`,`Repair bindings`],[`all`,`All candidates`],[`report`,`Resolution report`]].map(([e,t])=>(0,a.jsx)(`div`,{className:`map-tab`+(p===e?` on`:``),onClick:()=>m(e),children:t},e))}),p===`repair`&&(0,a.jsxs)(`div`,{className:`map-repair`+(x?` rail-is-open`:``),children:[(0,a.jsxs)(`div`,{className:`rail-float`+(x?` open`:``),onMouseEnter:()=>b(!0),onMouseLeave:()=>b(!1),children:[(0,a.jsxs)(`button`,{className:`rail-strip`,onClick:()=>v(!0),title:`Show bindings`,children:[(0,a.jsx)(Q,{name:`chevron`,className:`rail-strip-hint`,style:{width:13,height:13,transform:`rotate(-90deg)`}}),(0,a.jsx)(`span`,{className:`rail-strip-label`,children:`Bindings`}),(0,a.jsx)(`span`,{className:`rail-strip-cap`,"data-tone":N.attention.length?`warn`:`ok`,children:N.attention.length>0?N.attention.length:(0,a.jsx)(Q,{name:`check`,style:{width:12,height:12}})})]}),(0,a.jsxs)(`div`,{className:`rail-panel card`,children:[(0,a.jsxs)(`div`,{className:`bind-rail-head`,children:[N.attention.length>0?(0,a.jsxs)(`span`,{className:`brh-t`,"data-tone":`warn`,children:[`Needs attention `,(0,a.jsx)(`span`,{className:`gcount`,children:N.attention.length})]}):(0,a.jsxs)(`span`,{className:`brh-t`,"data-tone":`ok`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:13,height:13}}),`All resolved`]}),(0,a.jsx)(`button`,{className:`brh-close`,title:`Collapse`,onClick:()=>{v(!1),b(!1)},children:(0,a.jsx)(Q,{name:`chevron`,style:{width:13,height:13,transform:`rotate(90deg)`}})})]}),(0,a.jsxs)(`div`,{className:`bind-list`,children:[N.attention.length>0?N.attention.map(e=>(0,a.jsx)(cn,{b:e,sel:e.id===d,onClick:()=>A(e.id)},e.id)):(0,a.jsxs)(`div`,{className:`bind-allclear`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:16,height:16}}),`Every input is resolved`]}),(0,a.jsxs)(`button`,{className:`bind-group-toggle`,onClick:()=>g(e=>!e),children:[(0,a.jsx)(Q,{name:`chevron`,style:{width:12,height:12,transform:h?`none`:`rotate(-90deg)`}}),`Resolved `,(0,a.jsx)(`span`,{className:`gcount`,children:N.resolved.length}),(0,a.jsx)(`span`,{className:`muted-3`,style:{marginLeft:`auto`,fontSize:11,fontWeight:500},children:h?`hide`:`show`})]}),h&&N.resolved.map(e=>(0,a.jsx)(cn,{b:e,sel:e.id===d,onClick:()=>A(e.id)},e.id))]})]})]}),(0,a.jsx)(`div`,{className:`card resolve workspace-full`,children:O&&(0,a.jsx)(ln,{b:O,onApply:ne,onClear:re,customKind:S,setCustomKind:C,customSrc:w,setCustomSrc:T,onApplyCustom:P},O.id)})]}),p===`all`&&(0,a.jsx)(un,{bindings:l}),p===`report`&&(0,a.jsx)(dn,{bindings:l,summary:M})]}),(0,a.jsxs)(`div`,{className:`dialog-foot`,children:[(0,a.jsx)($,{icon:`save`,disabled:!o,onClick:j,title:`Save the edited mapping profile through the desktop backend.`,children:`Save profile as…`}),(0,a.jsx)(`span`,{className:`spacer`}),E&&(0,a.jsxs)(`span`,{className:`muted`,style:{fontSize:`var(--t-xs)`},children:[`Unsaved edits → `,(0,a.jsx)(`span`,{className:`mono`,children:`iso14126_manual_wizard_edit.json`})]}),(0,a.jsx)($,{onClick:n,children:`Close`}),(0,a.jsx)($,{variant:`primary`,icon:`check`,disabled:M.blockers>0,onClick:()=>r(l,E),title:M.blockers?`Map all execution-critical inputs first`:`Save edits and use this profile`,children:E?`Save edits & use profile`:`Use this profile`})]})]})})}function on({b:e}){let t=e.status;return t===`unmapped`&&(t=e.req===`required`?`blocker`:`gap`),(0,a.jsx)(`span`,{className:`b-state`,"data-s":t,title:t})}function sn(e){return e.status===`matched`?(0,a.jsx)(Yt,{tone:`ok`,dot:!1,children:`auto`}):e.status===`manual`?(0,a.jsx)(Yt,{tone:`info`,dot:!1,children:`manual`}):e.status===`ambiguous`?(0,a.jsx)(Yt,{tone:`info`,dot:!1,children:`ambiguous`}):(0,a.jsx)(Yt,{tone:e.req===`required`?`err`:`warn`,dot:!1,children:e.req===`required`?`blocker`:`unmapped`})}function cn({b:e,sel:t,onClick:n}){return(0,a.jsxs)(`div`,{className:`bind`+(t?` sel`:``),onClick:n,children:[(0,a.jsx)(on,{b:e}),(0,a.jsxs)(`div`,{className:`b-main`,children:[(0,a.jsx)(`span`,{className:`b-input`,children:e.input}),(0,a.jsx)(`span`,{className:`b-bind`,children:e.binding?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`span`,{className:`arrow`,children:`→`}),(0,a.jsx)(`span`,{className:`val`,children:e.binding})]}):e.status===`ambiguous`?(0,a.jsxs)(`span`,{className:`amb`,children:[e.candidates.length,` plausible sources — choose one`]}):(0,a.jsx)(`span`,{className:`none`,children:`no source bound`})})]}),(0,a.jsxs)(`div`,{className:`b-right`,children:[sn(e),(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:11,fontFamily:`var(--mono)`},children:e.coverage})]})]})}function ln({b:e,onApply:t,onClear:n,customKind:r,setCustomKind:i,customSrc:o,setCustomSrc:s,onApplyCustom:c}){let l=e.status===`ambiguous`,u=e.note&&e.note.match(/“(.+)”/)?.[1]||null,d=rn(e)?`ok`:l?`info`:e.req===`required`?`err`:`warn`,f=new Set(e.candidates.map(e=>e.source));return(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`div`,{className:`resolve-head`,"data-tone":d,children:[(0,a.jsxs)(`div`,{className:`rh-line`,children:[(0,a.jsx)(`span`,{className:`r-input`,children:e.input}),sn(e),(0,a.jsx)(`span`,{className:`rh-req`,"data-req":e.req,children:e.req})]}),(0,a.jsxs)(`div`,{className:`r-desc`,children:[e.desc,` · expects `,(0,a.jsx)(`b`,{children:e.kind}),e.unit?(0,a.jsxs)(a.Fragment,{children:[` in `,(0,a.jsx)(`span`,{className:`mono`,children:e.unit})]}):``,` · `,e.coverage]}),(0,a.jsx)(`div`,{className:`rh-state`,children:rn(e)?(0,a.jsxs)(a.Fragment,{children:[`Bound to `,(0,a.jsx)(`span`,{className:`rh-bound mono`,children:e.binding}),e.status===`matched`&&e.via?(0,a.jsxs)(`span`,{className:`rh-via`,children:[` · auto · `,e.via]}):(0,a.jsx)(`span`,{className:`rh-via`,children:` · manual`})]}):l?(0,a.jsxs)(a.Fragment,{children:[`Parser found `,(0,a.jsx)(`b`,{children:e.candidates.length}),` plausible sources`,u?(0,a.jsxs)(a.Fragment,{children:[` for header `,(0,a.jsxs)(`span`,{className:`mono`,children:[`“`,u,`”`]})]}):null,` — choose one`]}):(0,a.jsx)(`span`,{style:{color:e.req===`required`?`var(--err-ink)`:`var(--warn-ink)`},children:e.req===`required`?`Unmapped — blocks readiness`:`Unmapped — report field will be blank`})})]}),(0,a.jsxs)(`div`,{className:`resolve-body`,children:[(0,a.jsxs)(`div`,{className:`label-caps`,children:[l?`Choose the correct source`:`Suggested sources`,` · `,e.candidates.length]}),e.candidates.map(n=>{let r=e.binding===n.source;return(0,a.jsxs)(`div`,{className:`cand`+(r?` applied`:``),onClick:()=>!r&&t(n),children:[(0,a.jsxs)(`div`,{className:`cand-top`,children:[(0,a.jsxs)(`div`,{style:{flex:1,minWidth:0},children:[(0,a.jsxs)(`div`,{className:`c-src`,children:[n.kind,`:`,n.source]}),(0,a.jsxs)(`div`,{className:`cand-meta`,children:[(0,a.jsx)(`span`,{className:`cm-cov`,children:n.coverage}),(0,a.jsx)(`span`,{className:`cm-sep`,children:`·`}),(0,a.jsx)(`span`,{className:`ex mono`,children:n.example})]})]}),(0,a.jsx)(Xt,{value:n.confidence})]}),(0,a.jsxs)(`div`,{className:`cand-foot`,children:[(0,a.jsx)(`span`,{className:`cand-reason`,children:n.reason}),r?(0,a.jsxs)(`span`,{className:`cand-applied`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:13,height:13}}),`Applied`]}):(0,a.jsxs)(`span`,{className:`cand-cta`,children:[l?`Use this`:`Use source`,(0,a.jsx)(Q,{name:`arrowR`,style:{width:13,height:13}})]})]})]},n.source)}),(0,a.jsxs)(`details`,{className:`custom-details`,children:[(0,a.jsx)(`summary`,{children:`Bind to another variable in the package…`}),(0,a.jsxs)(`div`,{className:`custom-row`,style:{marginTop:10},children:[(0,a.jsxs)(`select`,{className:`field-input`,value:o?`${r}:${o}`:``,onChange:e=>{let t=e.target.value;if(!t){s(``);return}let[n,...r]=t.split(`:`);i(n),s(r.join(`:`))},children:[(0,a.jsx)(`option`,{value:``,children:`Choose a source variable…`}),Object.entries(X.AVAILABLE_SOURCES).map(([e,t])=>(0,a.jsx)(`optgroup`,{label:e===`metadata`?`Metadata fields`:e===`field`?`Specimen / fixture fields`:`Channels`,children:t.filter(e=>!f.has(e)).map(t=>(0,a.jsx)(`option`,{value:`${e}:${t}`,children:t},t))},e))]}),(0,a.jsx)($,{size:`sm`,icon:`link`,disabled:!o.trim(),onClick:c,children:`Bind`})]}),(0,a.jsx)(`div`,{className:`custom-hint`,children:`Only variables present in this package are listed — bindings are validated on save.`})]}),e.binding&&(0,a.jsxs)(`button`,{className:`clear-link`,onClick:n,children:[`Clear binding`,e.req===`required`?` — will block readiness`:``]})]})]})}function un({bindings:e}){let t=e.flatMap(e=>e.candidates.map(t=>({...t,input:e.input,req:e.req,applied:e.binding===t.source})));return(0,a.jsx)(`div`,{className:`card`,style:{overflow:`auto`,marginBottom:16},children:(0,a.jsxs)(`table`,{className:`tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`Method input`}),(0,a.jsx)(`th`,{children:`Source`}),(0,a.jsx)(`th`,{children:`Kind`}),(0,a.jsx)(`th`,{children:`Coverage`}),(0,a.jsx)(`th`,{children:`Confidence`}),(0,a.jsx)(`th`,{children:`Provenance`}),(0,a.jsx)(`th`,{})]})}),(0,a.jsx)(`tbody`,{children:t.map((e,t)=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{className:`mono`,children:e.input}),(0,a.jsx)(`td`,{className:`mono`,children:e.source}),(0,a.jsx)(`td`,{className:`muted`,children:e.kind}),(0,a.jsx)(`td`,{className:`muted`,children:e.coverage}),(0,a.jsx)(`td`,{children:(0,a.jsx)(Xt,{value:e.confidence})}),(0,a.jsx)(`td`,{className:`muted`,style:{fontSize:`var(--t-xs)`},children:e.via||e.reason}),(0,a.jsx)(`td`,{children:e.applied&&(0,a.jsxs)(Yt,{tone:`ok`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:11,height:11}}),`applied`]})})]},t))})]})})}function dn({bindings:e,summary:t}){let n=e=>rn(e)?e.status===`matched`?`auto-matched`:`manual`:e.status===`ambiguous`?`ambiguous`:e.req===`required`?`missing`:`unmapped`,r=e=>rn(e)?`ok`:e.status===`ambiguous`?`info`:e.req===`required`?`err`:`warn`;return(0,a.jsxs)(`div`,{className:`fade-in`,style:{marginBottom:16,display:`flex`,flexDirection:`column`,gap:12},children:[(0,a.jsxs)(`div`,{className:`rr-stats`,children:[(0,a.jsxs)(`div`,{className:`rr-stat`,"data-tone":t.blockers?`err`:`ok`,children:[(0,a.jsxs)(`div`,{className:`rr-v`,children:[t.critBound,(0,a.jsxs)(`span`,{className:`rr-tot`,children:[`/`,t.critTotal]})]}),(0,a.jsx)(`div`,{className:`rr-k`,children:`critical inputs bound`})]}),(0,a.jsxs)(`div`,{className:`rr-stat`,"data-tone":t.repBound<t.repTotal?`warn`:`ok`,children:[(0,a.jsxs)(`div`,{className:`rr-v`,children:[t.repBound,(0,a.jsxs)(`span`,{className:`rr-tot`,children:[`/`,t.repTotal]})]}),(0,a.jsx)(`div`,{className:`rr-k`,children:`report fields bound`})]}),(0,a.jsxs)(`div`,{className:`rr-stat`,"data-tone":t.ambiguous?`info`:`idle`,children:[(0,a.jsx)(`div`,{className:`rr-v`,children:t.ambiguous}),(0,a.jsx)(`div`,{className:`rr-k`,children:`ambiguous resolutions`})]})]}),(0,a.jsx)(`div`,{className:`card`,style:{overflow:`hidden`},children:(0,a.jsxs)(`table`,{className:`tbl rr-tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`Method input`}),(0,a.jsx)(`th`,{children:`Req.`}),(0,a.jsx)(`th`,{children:`Resolution`}),(0,a.jsx)(`th`,{children:`Bound source`}),(0,a.jsx)(`th`,{children:`Provenance`}),(0,a.jsx)(`th`,{children:`Coverage`})]})}),(0,a.jsx)(`tbody`,{children:e.map(e=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{className:`mono`,children:e.input}),(0,a.jsx)(`td`,{children:e.req===`required`?(0,a.jsx)(`span`,{className:`reqmark req`,title:`Required`,children:`*`}):(0,a.jsx)(`span`,{className:`reqmark rec`,title:`Recommended`,children:`**`})}),(0,a.jsx)(`td`,{children:(0,a.jsx)(Yt,{tone:r(e),dot:!1,children:n(e)})}),(0,a.jsx)(`td`,{className:`mono muted`,children:e.binding?`${e.kind}:${e.binding}`:`—`}),(0,a.jsx)(`td`,{className:`muted`,style:{fontSize:`var(--t-xs)`},children:e.status===`matched`?e.via||`auto`:e.status===`manual`?`user-assigned`:`—`}),(0,a.jsx)(`td`,{className:`muted mono`,style:{fontSize:`var(--t-xs)`},children:e.coverage})]},e.id))})]})})]})}Object.assign(window,{MappingEditor:an});function fn({onComplete:e,onCancel:t,pushLog:n,backendRun:r=null,backendMode:i=!1,demoMode:o=!1}){if(r?.run_id||r?.status)return(0,a.jsx)(pn,{backendRun:r,onComplete:e});if(i)return(0,a.jsx)(pn,{backendRun:{status:`running`,phase:`queued`,progress_percent:0,message:`Starting backend method run.`,events:[],run_status:{}},onComplete:e});if(!o)return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:`Running method`}),(0,a.jsx)(`div`,{className:`sub`,children:`No analysed backend run is available for this method execution.`})]}),(0,a.jsx)(`div`,{className:`card card-pad`,children:(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`warn`,children:[(0,a.jsx)(Q,{name:`warn`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsx)(`b`,{children:`Backend analysis session required.`}),` Start the method through the desktop bridge or open a dataset package first.`]})]})})]});let[s,c]=Z(0),[l,u]=Z(0),[d,f]=Z([]),p=Kt(null),m=X.TRACE_SCRIPT,h=m[Math.min(s,m.length-1)],g=qt(()=>{let e=[`run_001`,`run_002`,`run_003`,`run_004`,`run_005`,`run_006`,`run_007`];return X.RUN_TABLE.map((t,n)=>{let r=29/e.length,i=42+n*r,a=`queued`;return l>=i+r?a=t.status===`flagged`?`flagged`:`complete`:l>=i&&l<75&&(a=`running`),l>=90&&(a=t.status===`flagged`?`flagged`:`complete`),{...t,liveStatus:a}})},[l]);Gt(()=>{if(s>=m.length){let t=setTimeout(e,900);return()=>clearTimeout(t)}let t=m[s],r=setTimeout(()=>{u(t.pct),f(e=>[...e,{...t,ts:hn(s)}]),n&&n({level:t.level,msg:t.msg}),c(e=>e+1)},s===0?350:620);return()=>clearTimeout(r)},[s]),Gt(()=>{p.current&&(p.current.scrollTop=p.current.scrollHeight)},[d]);let _=e=>{let t=X.STAGES.indexOf(h.stage),n=X.STAGES.indexOf(e);return n<t?`done`:n===t?l>=100?`done`:`active`:`todo`},v=l<100,y=g.filter(e=>!0),b={complete:g.filter(e=>e.liveStatus===`complete`).length,running:g.filter(e=>e.liveStatus===`running`).length,queued:g.filter(e=>e.liveStatus===`queued`).length,flagged:g.filter(e=>e.liveStatus===`flagged`).length};return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:`Running method`}),(0,a.jsxs)(`div`,{className:`sub`,children:[`ISO 14126 on `,(0,a.jsx)(`b`,{children:X.PACKAGE.name}),` · `,v?`writing MTDA output`:`execution complete`]})]}),(0,a.jsxs)(`div`,{className:`card card-pad`,style:{display:`flex`,flexDirection:`column`,gap:14},children:[(0,a.jsxs)(`div`,{className:`run-head`,children:[(0,a.jsxs)(`div`,{className:`rh-main`,children:[(0,a.jsx)(`div`,{className:`run-phase`,children:mn(h.stage,l)}),(0,a.jsxs)(`div`,{className:`run-meta`,children:[`started 14:22 · output → `,X.OUTPUT.mtda,` · `,d.length,` log events`]})]}),(0,a.jsxs)(`div`,{className:`run-pct`,children:[l,`%`]})]}),(0,a.jsx)(`div`,{className:`progress`,children:(0,a.jsx)(`div`,{style:{width:l+`%`}})}),(0,a.jsx)(`div`,{className:`stage-strip`,children:X.STAGES.map(e=>(0,a.jsx)(`div`,{className:`stagebox`,"data-s":_(e),children:e},e))}),(0,a.jsxs)(`div`,{className:`run-stats`,children:[(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Active stage`}),(0,a.jsx)(`div`,{className:`v`,children:h.stage})]}),(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Run rows`}),(0,a.jsxs)(`div`,{className:`v`,children:[b.running,` running · `,b.queued,` queued · `,b.complete+b.flagged,` done`]})]}),(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Latest event`}),(0,a.jsx)(`div`,{className:`v`,style:{fontSize:`var(--t-sm)`,fontWeight:500},children:h.msg})]})]})]}),(0,a.jsxs)(`div`,{className:`card card-pad`,style:{display:`flex`,flexDirection:`column`,gap:9},children:[(0,a.jsx)(`div`,{className:`label-caps`,children:`Live analysis trace`}),(0,a.jsxs)(`div`,{className:`trace`,ref:p,children:[d.map((e,t)=>(0,a.jsxs)(`div`,{className:`trace-line`,"data-l":e.level,children:[(0,a.jsx)(`span`,{className:`t-ts`,children:e.ts}),(0,a.jsxs)(`span`,{className:`t-pct`,children:[e.pct,`%`]}),(0,a.jsxs)(`span`,{className:`t-msg`,children:[e.stage,` · `,e.msg]})]},t)),v&&(0,a.jsxs)(`div`,{className:`trace-line`,children:[(0,a.jsx)(`span`,{className:`t-ts`,children:hn(s)}),(0,a.jsxs)(`span`,{className:`t-pct`,children:[l,`%`]}),(0,a.jsx)(`span`,{className:`t-msg`,style:{color:`#6f7783`},children:`▍`})]})]})]}),(0,a.jsxs)(`div`,{className:`card`,style:{overflow:`hidden`},children:[(0,a.jsx)(`div`,{style:{padding:`11px 16px`,borderBottom:`1px solid var(--border)`},children:(0,a.jsx)(`span`,{className:`label-caps`,children:`Per-run status`})}),(0,a.jsx)(`div`,{style:{maxHeight:220,overflow:`auto`},children:(0,a.jsxs)(`table`,{className:`tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{style:{width:110},children:`Run`}),(0,a.jsx)(`th`,{style:{width:120},children:`Status`}),(0,a.jsx)(`th`,{children:`Notes`})]})}),(0,a.jsx)(`tbody`,{children:y.map(e=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{className:`mono`,style:{fontWeight:600},children:e.run}),(0,a.jsx)(`td`,{children:(0,a.jsx)(`span`,{className:`run-status-pill`,"data-s":e.liveStatus,children:e.liveStatus===`running`?`● running`:e.liveStatus})}),(0,a.jsx)(`td`,{className:`muted`,children:e.liveStatus===`queued`?`—`:e.liveStatus===`running`?`Computing compression properties…`:e.note})]},e.run))})]})})]})]})}function pn({backendRun:e,onComplete:t}){let n=e?.status||`running`,r=Number(e?.progress_percent??0),i=e?.phase||`queued`,o=e?.message||`Method run queued.`,s=e?.events||[],c=e?.result||{},l=Kt(null),u=e?.run_status||{},d=Object.keys(u).length?Object.entries(u).map(([e,t])=>({run:e,liveStatus:t,note:t})):[],f={complete:d.filter(e=>e.liveStatus===`complete`||e.liveStatus===`completed`).length,running:d.filter(e=>e.liveStatus===`running`).length,queued:d.filter(e=>e.liveStatus===`queued`).length,flagged:d.filter(e=>e.liveStatus===`flagged`).length};Gt(()=>{if(n===`completed`){let e=setTimeout(t,250);return()=>clearTimeout(e)}},[n,t]),Gt(()=>{l.current&&(l.current.scrollTop=l.current.scrollHeight)},[s.length]);let p=e=>{let t=i.toLowerCase();return e.toLowerCase().includes(t.split(`_`)[0])?`active`:r>=100?`done`:`todo`};return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:n===`completed`?`Method run complete`:n===`failed`?`Method run failed`:`Running method`}),(0,a.jsxs)(`div`,{className:`sub`,children:[mn(i,r),` · output `,(0,a.jsx)(`b`,{children:c.output_path||e?.output_path||X.OUTPUT.mtda})]})]}),(0,a.jsxs)(`div`,{className:`card card-pad`,style:{display:`flex`,flexDirection:`column`,gap:14},children:[(0,a.jsxs)(`div`,{className:`run-head`,children:[(0,a.jsxs)(`div`,{className:`rh-main`,children:[(0,a.jsx)(`div`,{className:`run-phase`,children:o}),(0,a.jsxs)(`div`,{className:`run-meta`,children:[n,` · `,s.length,` backend event`,s.length===1?``:`s`]})]}),(0,a.jsxs)(`div`,{className:`run-pct`,children:[r,`%`]})]}),(0,a.jsx)(`div`,{className:`progress`,children:(0,a.jsx)(`div`,{style:{width:r+`%`}})}),(0,a.jsx)(`div`,{className:`stage-strip`,children:X.STAGES.map(e=>(0,a.jsx)(`div`,{className:`stagebox`,"data-s":p(e),children:e},e))}),(0,a.jsxs)(`div`,{className:`run-stats`,children:[(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Backend phase`}),(0,a.jsx)(`div`,{className:`v`,children:i})]}),(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Run rows`}),(0,a.jsxs)(`div`,{className:`v`,children:[f.running,` running · `,f.queued,` queued · `,f.complete+f.flagged,` done`]})]}),(0,a.jsxs)(`div`,{className:`run-stat`,children:[(0,a.jsx)(`div`,{className:`k`,children:`Latest event`}),(0,a.jsx)(`div`,{className:`v`,style:{fontSize:`var(--t-sm)`,fontWeight:500},children:o})]})]})]}),(0,a.jsxs)(`div`,{className:`card card-pad`,style:{display:`flex`,flexDirection:`column`,gap:9},children:[(0,a.jsx)(`div`,{className:`label-caps`,children:`Backend analysis trace`}),(0,a.jsxs)(`div`,{className:`trace`,ref:l,children:[s.map((e,t)=>{let n=e.data||{};return(0,a.jsxs)(`div`,{className:`trace-line`,"data-l":n.status===`failed`?`err`:n.status===`completed`?`ok`:`info`,children:[(0,a.jsx)(`span`,{className:`t-ts`,children:hn(t)}),(0,a.jsxs)(`span`,{className:`t-pct`,children:[n.progress_percent??r,`%`]}),(0,a.jsxs)(`span`,{className:`t-msg`,children:[n.phase||e.event,` · `,n.message||e.event]})]},e.event_id||t)}),n===`running`&&(0,a.jsxs)(`div`,{className:`trace-line`,children:[(0,a.jsx)(`span`,{className:`t-ts`,children:hn(s.length)}),(0,a.jsxs)(`span`,{className:`t-pct`,children:[r,`%`]}),(0,a.jsx)(`span`,{className:`t-msg`,style:{color:`#6f7783`},children:`waiting for backend event`})]})]})]}),(0,a.jsxs)(`div`,{className:`card`,style:{overflow:`hidden`},children:[(0,a.jsx)(`div`,{style:{padding:`11px 16px`,borderBottom:`1px solid var(--border)`},children:(0,a.jsx)(`span`,{className:`label-caps`,children:`Per-run status`})}),(0,a.jsx)(`div`,{style:{maxHeight:220,overflow:`auto`},children:(0,a.jsxs)(`table`,{className:`tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{style:{width:110},children:`Run`}),(0,a.jsx)(`th`,{style:{width:120},children:`Status`}),(0,a.jsx)(`th`,{children:`Notes`})]})}),(0,a.jsx)(`tbody`,{children:d.length?d.map(e=>(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`td`,{className:`mono`,style:{fontWeight:600},children:e.run}),(0,a.jsx)(`td`,{children:(0,a.jsx)(`span`,{className:`run-status-pill`,"data-s":e.liveStatus,children:e.liveStatus})}),(0,a.jsx)(`td`,{className:`muted`,children:e.note||(n===`completed`?`Backend result ready`:`Waiting for backend progress`)})]},e.run)):(0,a.jsx)(`tr`,{children:(0,a.jsx)(`td`,{colSpan:`3`,className:`muted`,children:`Per-run backend progress will appear when the analyser reports run status.`})})})]})})]})]})}function mn(e,t){return t>=100?`Execution complete`:{Input:`Loading package`,Method:`Resolving method`,Mapping:`Applying mapping`,Ready:`Confirming readiness`,Resolve:`Resolving method inputs`,Reduce:`Reducing method runs`,Validate:`Validating output`,Accept:`Applying acceptance policy`,Write:`Writing MTDA output`,Report:`Generating reports`,Workbench:`Building workbench`,Done:`Finishing`}[e]||e}function hn(e){let t=51721+e*2,n=Math.floor(t/3600)%24,r=Math.floor(t%3600/60),i=t%60;return`${String(n).padStart(2,`0`)}:${String(r).padStart(2,`0`)}:${String(i).padStart(2,`0`)}`}Object.assign(window,{Running:fn});function gn({points:e,reference:t,cohort:n,width:r=420,height:i=168}){let o=[...e||[],...t||[],...(n||[]).flat()].filter(e=>Number.isFinite(Number(e?.x))&&Number.isFinite(Number(e?.y)));if(o.length<2)return(0,a.jsx)(_n,{message:`Evidence gap: missing plot.curve_family_curve.`});let s=Math.max(...o.map(e=>e.y))*1.08,c=Math.max(...o.map(e=>e.x))*1.02,l=e=>6+e/c*(r-12),u=e=>i-10-e/s*(i-20),d=e=>e.map((e,t)=>`${t===0?`M`:`L`}${l(e.x).toFixed(1)} ${u(e.y).toFixed(1)}`).join(` `);return(0,a.jsxs)(`div`,{className:`spark`,children:[(0,a.jsx)(`div`,{className:`spark-cap label-caps`,children:`stress–strain · focus vs cohort`}),(0,a.jsxs)(`svg`,{width:r,height:i,className:`spark-svg`,children:[n.map((e,t)=>(0,a.jsx)(`path`,{d:d(e),fill:`none`,stroke:`var(--ink-4)`,strokeWidth:`1`,opacity:`0.5`},t)),(0,a.jsx)(`path`,{d:d(t),fill:`none`,stroke:`var(--info-accent)`,strokeWidth:`1.4`,strokeDasharray:`4 3`,opacity:`0.85`}),(0,a.jsx)(`path`,{d:d(e),fill:`none`,stroke:`var(--warn-accent)`,strokeWidth:`2`})]}),(0,a.jsxs)(`div`,{className:`spark-legend`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--warn-accent)`}}),`this run`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--info-accent)`}}),`reference`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--ink-4)`}}),`cohort`]})]})]})}function _n({message:e}){return(0,a.jsxs)(`div`,{className:`spark plot-gap`,children:[(0,a.jsx)(`div`,{className:`spark-cap label-caps`,children:`diagnostic plot`}),(0,a.jsx)(`div`,{className:`plot-gap-body`,children:e||`Evidence gap: diagnostic plot data unavailable.`})]})}function vn(e,...t){for(let n of t){let t=e?.[n];if(t==null||t===``)continue;let r=Number(t);if(Number.isFinite(r))return r;let i=String(t).match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/i);if(i){let e=Number(i[0]);if(Number.isFinite(e))return e}}return null}function yn(e,t=`not reported`){let n=Number(e);return Number.isFinite(n)?`${Ln(n)}%`:t}function bn(e){let t=Array.isArray(e?.evidence_refs)?e.evidence_refs.map(String).filter(Boolean):[];return t.length?t.slice(0,2).join(` · `):``}function xn(e){return Bn(e,`bending`)?`bending`:Bn(e,`curve family`)||Bn(e,`curve shape`)?`curve_family`:`decision_context`}function Sn(e){let t=String(e?.value??``);if(t&&!Number.isFinite(Number(t)))return In(t);let n=String(e?.message||e?.reason||``).toLowerCase();return n.includes(`sustained`)?`Sustained bending`:n.includes(`transient`)?`Transient bending`:n.includes(`window`)?`Windowed bending review`:`Bending review`}function Cn(e){if(e==null||e===``)return null;if(typeof e==`number`)return Number.isFinite(e)?e:null;let t=String(e).trim().replace(/,/g,`.`),n=Number(t);if(Number.isFinite(n))return n;let r=t.match(/-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/i);if(!r)return null;let i=Number(r[0]);return Number.isFinite(i)?i:null}function wn(e,...t){for(let n of t){let t=Cn(e?.[n]);if(t!==null)return t}return null}function Tn(e,...t){for(let n of t){let t=e?.[n];if(t==null)continue;let r=String(t).trim();if(r)return r}return``}function En(e,t,n,r=[]){return Array.isArray(e)?e.map(e=>{let i=wn(e,...t),a=wn(e,...n);return i===null||a===null?null:{x:i,y:a,runId:Tn(e,...r)}}).filter(Boolean):[]}function Dn(e,t=``){let n=Number(e);return Number.isFinite(n)?`${Math.abs(n)>=1e3?Ln(n/1e3)+`k`:Ln(n)}${t}`:``}function On(e,t,n=4){let r=Number(e),i=Number(t);if(!Number.isFinite(r)||!Number.isFinite(i)||i<=r)return[];let a=Math.max(1,n-1);return Array.from({length:a+1},(e,t)=>r+(i-r)*t/a)}function kn({xTicks:e,yTicks:t,xAt:n,yAt:r,xLabel:i,yLabel:o,plotLeft:s,plotRight:c,plotTop:l,plotBottom:u,xSuffix:d=``,ySuffix:f=``}){return(0,a.jsxs)(`g`,{className:`plot-axes`,children:[t.map((e,t)=>{let n=r(e);return(0,a.jsxs)(`g`,{children:[(0,a.jsx)(`line`,{x1:s,y1:n,x2:c,y2:n,stroke:`var(--border)`,strokeWidth:`1`,opacity:t===0?`0.85`:`0.45`}),(0,a.jsx)(`text`,{x:s-7,y:n+3,textAnchor:`end`,fontSize:`9`,fill:`var(--ink-4)`,fontFamily:`var(--mono)`,children:Dn(e,f)})]},`y-${t}`)}),e.map((e,t)=>{let r=n(e);return(0,a.jsxs)(`g`,{children:[(0,a.jsx)(`line`,{x1:r,y1:l,x2:r,y2:u,stroke:`var(--border)`,strokeWidth:`1`,opacity:`0.28`}),(0,a.jsx)(`text`,{x:r,y:u+13,textAnchor:`middle`,fontSize:`9`,fill:`var(--ink-4)`,fontFamily:`var(--mono)`,children:Dn(e,d)})]},`x-${t}`)}),(0,a.jsx)(`rect`,{x:s,y:l,width:c-s,height:u-l,fill:`none`,stroke:`var(--border)`,strokeWidth:`1`}),(0,a.jsx)(`text`,{x:(s+c)/2,y:u+29,textAnchor:`middle`,fontSize:`10`,fill:`var(--ink-4)`,children:i}),(0,a.jsx)(`text`,{x:9,y:(l+u)/2,transform:`rotate(-90 9 ${(l+u)/2})`,textAnchor:`middle`,fontSize:`10`,fill:`var(--ink-4)`,children:o})]})}function An({cockpit:e,width:t=420,height:n=176}){let r=e?.plot||{},i=En(Array.isArray(r.trace_points)?r.trace_points:Array.isArray(e?.trace_points)?e.trace_points:[],[`load_N`,`load`,`x`],[`bending_percent`,`bending`,`y`]).map(({x:e,y:t})=>({x:e,y:t}));if(i.length<2)return(0,a.jsx)(Zt,{series:Array.isArray(r.series)?r.series:Array.isArray(e.series)?e.series:[],threshold:r.threshold??e.threshold??0,peak:r.peak??e.peak??0,window:e.window,segments:e.segments,width:t,height:n});let o=Number(r.threshold??0),s=i.map(e=>e.x),c=i.map(e=>e.y),l=Math.min(...s),u=Math.max(...s)>l?Math.max(...s):l+1,d=Math.min(0,...c),f=Math.max(...c,Number.isFinite(o)?o:0,.01),p=f>d?f*1.08:d+1,m=t-12,h=n-34,g=e=>52+(e-l)/(u-l)*(m-52),_=e=>h-(e-d)/(p-d)*(h-12),v=i.map((e,t)=>`${t===0?`M`:`L`}${g(e.x).toFixed(1)} ${_(e.y).toFixed(1)}`).join(` `),y=Array.isArray(r.assessment_window)?r.assessment_window.map(Number):[],b=Array.isArray(r.exceedance_segments)?r.exceedance_segments:[],x=Number.isFinite(o)?_(o):null,S=On(l,u,4),C=On(d,p,4);return(0,a.jsxs)(`div`,{className:`spark`,"data-plot-source":`mtda-bending-trace`,children:[(0,a.jsx)(`div`,{className:`spark-cap label-caps`,children:`bending % vs load · 10–90 % window`}),(0,a.jsxs)(`svg`,{width:t,height:n,className:`spark-svg`,children:[(0,a.jsx)(kn,{xTicks:S,yTicks:C,xAt:g,yAt:_,xLabel:`Load / N`,yLabel:`Bending / %`,plotLeft:52,plotRight:m,plotTop:12,plotBottom:h,ySuffix:`%`}),y.length===2&&Number.isFinite(y[0])&&Number.isFinite(y[1])&&(0,a.jsx)(`rect`,{x:Math.max(52,Math.min(m,g(Math.min(y[0],y[1])))),y:12,width:Math.max(0,Math.min(m,g(Math.max(y[0],y[1])))-Math.max(52,g(Math.min(y[0],y[1])))),height:h-12,fill:`var(--info-accent)`,opacity:`0.07`}),b.map((e,t)=>{let n=Number(e.start_load_N),r=Number(e.end_load_N);if(!Number.isFinite(n)||!Number.isFinite(r))return null;let i=Math.max(52,Math.min(m,g(Math.min(n,r)))),o=Math.max(52,Math.min(m,g(Math.max(n,r))));return(0,a.jsx)(`rect`,{x:i,y:12,width:Math.max(0,o-i),height:h-12,fill:`var(--warn-accent)`,opacity:`0.16`},t)}),x!==null&&(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`line`,{x1:52,y1:x,x2:m,y2:x,stroke:`var(--danger)`,strokeWidth:`1`,strokeDasharray:`3 3`,opacity:`0.75`}),(0,a.jsxs)(`text`,{x:m-2,y:x-4,textAnchor:`end`,fontSize:`9`,fill:`var(--danger)`,fontFamily:`var(--mono)`,children:[`thr `,Ln(o)]})]}),(0,a.jsx)(`path`,{d:v,fill:`none`,stroke:`var(--accent)`,strokeWidth:`2`,strokeLinejoin:`round`})]})]})}function jn({cockpit:e,width:t=420,height:n=168}){let r=e?.plot||{},i=Array.isArray(r.points)?r.points:Array.isArray(e?.points)?e.points:[],o=Array.isArray(r.reference_points)?r.reference_points:Array.isArray(e?.reference_points)?e.reference_points:Array.isArray(e.reference)?e.reference:[],s=En(i,[`x`,`x_common`,`experiment_progress`,`strain_percent`,`strain`,`run_strain`],[`stress`,`y`,`y_reference`,`stress_MPa`,`y_observed`,`y_aligned`,`stress_mpa`],[`run_id`,`run`,`runId`,`id`]),c=[],l=new Map,u=String(r.focus_run_id||e.focus_run_id||``);s.forEach(e=>{let t=e.runId;if(!t){c.push({x:e.x,y:e.y});return}l.has(t)||l.set(t,[]),l.get(t).push({x:e.x,y:e.y})}),l.size===0&&c.length>0&&l.set(u||`run`,c);let d=En(o,[`x`,`x_common`,`experiment_progress`,`strain_percent`],[`stress`,`y`,`y_reference`,`stress_MPa`]).map(e=>({x:e.x,y:e.y}));if(!l.size)return(0,a.jsx)(gn,{points:i,reference:o,cohort:Array.isArray(r.cohort)?r.cohort:Array.isArray(e?.cohort)?e.cohort:[],width:t,height:n});let f=String(r.focus_run_id||e.focus_run_id||``),p=[...Array.from(l.values()).flat(),...d],m=Math.min(...p.map(e=>e.x)),h=Math.max(...p.map(e=>e.x))>m?Math.max(...p.map(e=>e.x)):m+1,g=Math.min(0,...p.map(e=>e.y)),_=Math.max(.01,...p.map(e=>e.y)),v=_>g?_*1.08:g+1,y=t-12,b=n-36,x=e=>52+(e-m)/(h-m)*(y-52),S=e=>b-(e-g)/(v-g)*(b-12),C=e=>e.map((e,t)=>`${t===0?`M`:`L`}${x(e.x).toFixed(1)} ${S(e.y).toFixed(1)}`).join(` `),w=On(m,h,4),T=On(g,v,4);return(0,a.jsxs)(`div`,{className:`spark`,"data-plot-source":`mtda-curve-family`,children:[(0,a.jsx)(`div`,{className:`spark-cap label-caps`,children:`stress-strain · focus vs cohort`}),(0,a.jsxs)(`svg`,{width:t,height:n,className:`spark-svg`,children:[(0,a.jsx)(kn,{xTicks:w,yTicks:T,xAt:x,yAt:S,xLabel:`Normalised strain / %`,yLabel:`Stress`,plotLeft:52,plotRight:y,plotTop:12,plotBottom:b}),Array.from(l.entries()).sort(([e],[t])=>e.localeCompare(t)).map(([e,t])=>t.length>=2?(0,a.jsx)(`path`,{d:C(t),fill:`none`,stroke:e===f?`var(--danger)`:`var(--ink-4)`,strokeWidth:e===f?`2.4`:`1`,opacity:e===f?`0.95`:`0.48`},e):null),d.length>=2&&(0,a.jsx)(`path`,{d:C(d),fill:`none`,stroke:`var(--ink-1)`,strokeWidth:`1.4`,strokeDasharray:`4 3`,opacity:`0.82`})]}),(0,a.jsxs)(`div`,{className:`spark-legend`,children:[(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--danger)`}}),`this run`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--ink-1)`}}),`reference`]}),(0,a.jsxs)(`span`,{children:[(0,a.jsx)(`i`,{style:{background:`var(--ink-4)`}}),`cohort`]})]})]})}function Mn({cockpit:e}){return(0,a.jsxs)(`div`,{className:`cockpit`,children:[(0,a.jsx)(`div`,{className:`cockpit-plot`,children:e.kind===`decision_context`?(0,a.jsxs)(`div`,{className:`decision-context`,children:[(0,a.jsx)(`div`,{className:`label-caps`,children:e.title||`Decision context`}),(0,a.jsx)(`div`,{className:`decision-context-summary`,children:e.summary||`Review the run validity before accepting the final report selection.`}),e.evidence&&(0,a.jsx)(`div`,{className:`muted`,children:e.evidence})]}):e.kind===`bending`?(0,a.jsx)(An,{cockpit:e}):e.kind===`curve_family`?(0,a.jsx)(jn,{cockpit:e}):(0,a.jsx)(_n,{message:(e.plot?.missing_required_keys||[]).length?`Evidence gap: missing ${e.plot.missing_required_keys.join(`, `)}.`:`Evidence gap: diagnostic plot data unavailable.`})}),(0,a.jsx)(`div`,{className:`cockpit-cards`,children:e.cards.map(e=>(0,a.jsxs)(`div`,{className:`metric`,"data-tone":e.level===`warn`?`warn`:``,children:[(0,a.jsx)(`div`,{className:`metric-k label-caps`,children:e.label}),(0,a.jsx)(`div`,{className:`metric-v`,children:Rn(e.value)}),(0,a.jsx)(`div`,{className:`metric-sub`,children:Rn(e.sub)})]},e.key))})]})}function Nn({f:e}){let[t,n]=Z(0),r=e.cockpits||[];return(0,a.jsxs)(`div`,{className:`evidence fade-in`,children:[r.length>1&&(0,a.jsx)(`div`,{className:`cockpit-tabs`,children:r.map((e,r)=>(0,a.jsx)(`button`,{className:`cockpit-tab`+(t===r?` on`:``),onClick:()=>n(r),children:e.tab},r))}),r.length>=1&&(0,a.jsx)(Mn,{cockpit:r[Math.min(t,r.length-1)]}),e.narrative&&(0,a.jsx)(`div`,{className:`ev-narrative`,dangerouslySetInnerHTML:{__html:Rn(e.narrative)}})]})}function Pn({f:e,open:t,decision:n,reason:r,onToggle:i,onDecide:o,onReason:s,onRestore:c}){if(e.excluded)return(0,a.jsx)(`div`,{className:`acc-row-wrap excluded`,children:(0,a.jsxs)(`div`,{className:`acc-row`,children:[(0,a.jsx)(`div`,{className:`a-run`,children:e.run}),(0,a.jsx)(`div`,{children:(0,a.jsx)(`span`,{className:`excluded-tag`,children:`excluded`})}),(0,a.jsx)(`div`,{className:`a-defects`,children:e.defects.join(` + `)}),(0,a.jsx)(`div`,{className:`a-reason`,children:e.reason}),(0,a.jsx)(`div`,{className:`acc-decide`,children:(0,a.jsx)($,{size:`sm`,icon:`undo`,onClick:c,children:`Restore…`})})]})});let l=n===`Keep`,u=l&&e.defaultCall===`Remove`,d=e.defects.join(` + `);return(0,a.jsxs)(`div`,{className:`acc-row-wrap`,children:[(0,a.jsxs)(`div`,{className:`acc-row`+(t?` open`:``),onClick:i,children:[(0,a.jsxs)(`div`,{className:`a-run`,children:[(0,a.jsx)(Q,{name:`chevron`,className:`exp`,style:{width:13,height:13}}),e.run]}),(0,a.jsx)(`div`,{children:(0,a.jsx)(Yt,{tone:e.defaultCall===`Keep`?`ok`:`err`,dot:!1,children:e.defaultCall})}),(0,a.jsx)(`div`,{className:`a-defects`,title:d,children:e.defects.map(e=>(0,a.jsx)(`span`,{className:`defect-chip`,children:e},e))}),(0,a.jsx)(`div`,{className:`a-reason`,title:Rn(e.reason),children:Rn(e.reason)}),(0,a.jsxs)(`div`,{className:`acc-decide`,onClick:e=>e.stopPropagation(),children:[(0,a.jsx)(`button`,{className:`dbtn keep`+(l?` on`:``),onClick:()=>o(`Keep`),children:`Keep run`}),(0,a.jsx)(`button`,{className:`dbtn remove`+(l?``:` on`),onClick:()=>o(`Remove`),children:`Remove run`})]})]}),t&&(0,a.jsx)(Nn,{f:e}),t&&u&&(0,a.jsxs)(`div`,{className:`justify fade-in`,children:[(0,a.jsxs)(`div`,{className:`col`,style:{gap:2,flex:`none`,maxWidth:220},children:[(0,a.jsx)(`span`,{className:`j-k`,children:`Why keep?`}),(0,a.jsxs)(`span`,{className:`j-scope`,children:[`Motivate every override covered by this run decision: `,d]})]}),(0,a.jsx)(`input`,{className:`field-input`,placeholder:`Motivate keeping this run despite ${d.toLowerCase()}`,value:r,onChange:e=>s(e.target.value),autoFocus:!0})]})]})}function Fn(e){return String(e??``).replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`).replace(/'/g,`&#39;`)}function In(e){let t=String(e||`acceptance finding`).replace(/[_-]+/g,` `).trim();return t?t.split(/\s+/).map(e=>e.charAt(0).toUpperCase()+e.slice(1)).join(` `):`Acceptance finding`}function Ln(e,t=3){let n=Number(e);if(!Number.isFinite(n))return String(e??``);if(n===0)return`0`;let r=Math.abs(n);if(r<1){let e=Math.max(0,t-1-Math.floor(Math.log10(r)));return n.toFixed(e).replace(/0+$/,``).replace(/\.$/,``)}let i=Number(n.toPrecision(t));return String(i)}function Rn(e){return e==null?``:typeof e==`number`?Ln(e):String(e).replace(/-?\d+\.\d{4,}(?:e[+-]?\d+)?/gi,e=>Ln(Number(e)))}function zn(e){let t=String(e?.severity||``).toLowerCase();return[`exclude`,`error`,`critical`,`invalid`].includes(t)?3:[`review`,`warn_review`,`requires_review`].includes(t)?2:+!![`warn`,`warning`].includes(t)}function Bn(e,t){return[e?.category,e?.source,e?.rule_id,e?.flag_id,e?.message,e?.reason,...Array.isArray(e?.evidence_refs)?e.evidence_refs:[]].join(` `).toLowerCase().replace(/[_-]+/g,` `).includes(String(t||``).toLowerCase().replace(/[_-]+/g,` `))}function Vn(e){let t=[];return e.forEach(e=>{let n=``;n=Bn(e,`bending`)?`Bending`:Bn(e,`curve family`)||Bn(e,`curve shape`)?`Curve shape`:In(e?.category||e?.rule_id||e?.flag_id),n&&!t.includes(n)&&t.push(n)}),t.length?t:[`Acceptance finding`]}function Hn(e){return String(e?.selection_effect||``).toLowerCase().includes(`excluded`)}function Un(e){return{severity:String(e?.severity||`flag`),category:String(e?.category||`acceptance`),message:String(e?.message||e?.reason||`Acceptance flag requires review`),evidence_refs:Array.isArray(e?.evidence_refs)?e.evidence_refs.map(String):String(e?.evidence_refs||``).split(`;`).map(e=>e.trim()).filter(Boolean),flag_id:String(e?.flag_id||``),rule_id:String(e?.rule_id||``),source:String(e?.source||``),selection_effect:String(e?.selection_effect||``),value:e?.value,threshold:e?.threshold,metric:e?.metric,points_above_threshold:e?.points_above_threshold,assessed_points:e?.assessed_points}}function Wn(e){let t=Array.isArray(e?.points)?e.points:Array.isArray(e?.plot?.points)?e.plot.points:[],n=Array.isArray(e?.reference_points)?e.reference_points:Array.isArray(e?.reference)?e.reference:Array.isArray(e?.plot?.reference_points)?e.plot.reference_points:[],r=Array.isArray(e?.series)?e.series:Array.isArray(e?.plot?.series)?e.plot.series:[],i=Array.isArray(e?.trace_points)?e.trace_points:Array.isArray(e?.plot?.trace_points)?e.plot.trace_points:[],a={...e?.plot&&typeof e.plot==`object`?e.plot:{},...i.length?{trace_points:i}:{},...r.length?{series:r}:{},...t.length?{points:t}:{},...n.length?{reference_points:n}:{},...e?.focus_run_id?{focus_run_id:String(e.focus_run_id)}:{},...Array.isArray(e?.missing_required_keys)?{missing_required_keys:e.missing_required_keys}:{}},o=String(a.plot_kind||``).toLowerCase(),s=o.includes(`bending`)?`bending`:o.includes(`curve_family`)||o.includes(`curve_shape`)||o.includes(`curve-family`)||Array.isArray(a.points)||Array.isArray(a.reference_points)||Array.isArray(e?.points)?`curve_family`:Array.isArray(a.trace_points)||Array.isArray(a.series)||Array.isArray(e?.series)?`bending`:`diagnostic`;return{...e,kind:e?.kind||s,tab:e?.tab||In(a.plot_kind||`Diagnostic`),title:e?.title||a.title||`Diagnostic evidence`,plot:a,points:t,reference:n,series:r,trace_points:i,cards:Array.isArray(e?.cards)?e.cards.map((e,t)=>({key:String(e?.key||e?.evidence_key||`card-${t}`),label:String(e?.label||e?.key||`Evidence`),value:e?.value??``,sub:e?.sub??e?.subtext??``,level:String(e?.level||``),state:String(e?.state||``)})):[]}}function Gn(e){if(!e||typeof e!=`object`)return{};let t={};return Object.entries(e).forEach(([e,n])=>{n!==void 0&&(t[e]=n)}),t}function Kn(e){if(e?.kind===`bending`){let t=e?.plot||{},n=(Array.isArray(t.trace_points)?t.trace_points:Array.isArray(e?.trace_points)?e.trace_points:[]).filter(e=>{let t=wn(e,`load_N`,`load`,`x`),n=wn(e,`bending_percent`,`bending`,`y`);return t!==null&&n!==null}),r=(Array.isArray(t.series)?t.series:Array.isArray(e?.series)?e.series:[]).filter(e=>Number.isFinite(Number(e)));return n.length>=2||r.length>=2}if(e?.kind===`curve_family`){let t=e?.plot||{},n=Array.isArray(t.points)?t.points:Array.isArray(e?.points)?e.points:[],r=Array.isArray(t.reference_points)?t.reference_points:Array.isArray(e?.reference_points)?e.reference_points:Array.isArray(e?.reference)?e.reference:[],i=n.filter(e=>{let t=wn(e,`x`,`x_common`,`experiment_progress`,`strain_percent`,`strain`,`run_strain`),n=wn(e,`stress`,`y`,`y_reference`,`stress_MPa`,`y_observed`,`y_aligned`,`stress_mpa`);return t!==null&&n!==null}),a=r.filter(e=>{let t=wn(e,`x`,`x_common`,`experiment_progress`,`strain_percent`,`strain`,`run_strain`),n=wn(e,`stress`,`y`,`y_reference`,`stress_MPa`,`y_observed`,`y_aligned`,`stress_mpa`);return t!==null&&n!==null});return i.length>=2||a.length>=2}return!1}function qn(e){return e?.kind===`bending`||e?.kind===`curve_family`}function Jn(e,t,n){let r=new Map;t.forEach(e=>{let t=xn(e);r.has(t)||r.set(t,[]),r.get(t).push(e)});let i=Gn(e),a=[];Array.isArray(i.bending_trace_points)&&i.bending_trace_points.length&&a.push(`bending`),Array.isArray(i.bending_series)&&i.bending_series.length&&a.push(`bending`),Array.isArray(i.curve_family_points)&&i.curve_family_points.length&&a.push(`curve_family`),Array.isArray(i.curve_family_reference_points)&&i.curve_family_reference_points.length&&a.push(`curve_family`);let o=[];a.includes(`bending`)&&o.push(`bending`),a.includes(`curve_family`)&&o.push(`curve_family`),[`decision_context`].forEach(e=>{r.has(e)&&o.push(e)});let s=[];for(let e of o)s.includes(e)||s.push(e);return s.map(e=>{if(e===`bending`){let e=r.get(`bending`)?.[0]||{},t=vn(e,`threshold`,`bending_threshold`)??i.bending_threshold??.1,a=vn(e,`value`,`bending_peak`,`measured_value`)??i.bending_peak??t*1.35,o=vn(e,`points_above_threshold`)??i.bending_points_above_threshold??1,s=vn(e,`assessed_points`)??i.bending_assessed_points??1;return{kind:`bending`,tab:`Bending`,title:`Bending evidence`,plot:{plot_kind:`bending_evidence`,series:Array.isArray(i.bending_series)?i.bending_series:[],trace_points:Array.isArray(i.bending_trace_points)?i.bending_trace_points:[],threshold:t,peak:a,assessment_window:Array.isArray(i.bending_assessment_window)?i.bending_assessment_window:[.1,.9],exceedance_segments:Array.isArray(i.bending_exceedance_segments)?i.bending_exceedance_segments:[]},window:[.1,.9],segments:Array.isArray(i.bending_exceedance_segments)&&i.bending_exceedance_segments.length>0?i.bending_exceedance_segments:[],cards:[{key:`bending.call`,label:`Observed signal`,value:Sn(e),sub:`opposite-face strain imbalance`,level:`warn`},{key:`bending.max_percent`,label:`Peak imbalance`,value:yn(a),sub:e?.value?`reported by acceptance check`:`estimated from analysis evidence`,level:`warn`},{key:`bending.threshold_percent`,label:`Review limit`,value:t?yn(t):`not configured`,sub:`method threshold for bending review`,level:t?`info`:`warn`},{key:`bending.points_above_threshold`,label:`Persistence`,value:String(o),sub:`${o} of ${s} assessed points above limit`,level:`warn`},{key:`selection.consequence_summary`,label:`Recommended action`,value:n===`Remove`?Wt:Ut,sub:`final report consequence`,level:`info`}]}}if(e===`curve_family`){let e=r.get(`curve_family`)?.[0]||{},t=vn(e,`value`,`curve_family_value`)??i.curve_family_value,a=vn(e,`threshold`,`curve_family_threshold`)??i.curve_family_threshold,o=vn(e,`value`,`curve_family_value`)??t;return{kind:`curve_family`,tab:`Curve shape`,title:`Curve-shape evidence`,plot:{plot_kind:`curve_family`,points:Array.isArray(i.curve_family_points)?i.curve_family_points:[],reference_points:Array.isArray(i.curve_family_reference_points)?i.curve_family_reference_points:[],focus_run_id:String(i.curve_family_focus_run_id||``)},points:Array.isArray(i.curve_family_points)?i.curve_family_points:[],reference:Array.isArray(i.curve_family_reference_points)?i.curve_family_reference_points:[],cohort:[],cards:[{key:`curve_family.classification`,label:`Scientific call`,value:String(o>(a||0)?`Distance outlier`:`Within family`),sub:`curve-shape assessment`,level:o>(a||0)?`warn`:`info`},{key:`curve_family.metric`,label:`Primary metric`,value:`${In(e?.metric||`shape distance`)} ${Ln(o)}`,sub:`review limit ${Ln(a)}`,level:o>(a||0)?`warn`:`info`},{key:`curve_family.source`,label:`Comparison`,value:`run vs cohort`,sub:`stress-strain family`,level:`info`},{key:`selection.consequence_summary`,label:`Recommended action`,value:n===`Remove`?Wt:Ut,sub:`final report consequence`,level:`info`}]}}return e===`decision_context`&&r.has(`decision_context`)?Qn(r.get(`decision_context`)[0],n,r.get(`decision_context`)):null}).filter(Boolean)}function Yn(e,t,n,r){let i=Array.isArray(e)?e:[],a=i.filter(qn),o=i.filter(e=>!qn(e)),s=Jn(r,t,n),c=new Map(s.map(e=>[e.kind,e])),l=new Set,u=[];for(let e of a){let t=e?.kind;if(Kn(e)){u.push(e),t&&l.add(t);continue}if(t&&c.has(t)){u.push(c.get(t)),c.delete(t),l.add(t);continue}u.push(e),t&&l.add(t)}let d=s.filter(e=>!l.has(e.kind));return u.length?[...u,...d,...o]:d.length?[...d,...o]:i.length?i:Zn(t,n)}function Xn(e){let t=e?.result?.review_rows||e?.review_rows||e?.result?.reviewRows||e?.reviewRows;return!Array.isArray(t)||!t.length?[]:t.map((e,t)=>{let n=Array.isArray(e?.acceptance_flags)?e.acceptance_flags:[],r=n.map(Un),i=String(e?.default_call||e?.defaultCall||e?.default_decision||e?.decision||`Remove`),a=String(e?.run_id||e?.run||e?.runId||e?.id||``);return{rowKey:String(e?.row_id||e?.key||e?.review_id||a||`review-row-${t}`),run:a,defaultCall:i,excluded:!!(e?.is_excluded||e?.excluded),defects:Array.isArray(e?.defect_labels)&&e.defect_labels.length?e.defect_labels.map(String):Vn(n),reason:String(e?.reason||`Acceptance flag requires review`),flags:r,narrative:r.length?$n(r,i):String(e?.narrative_html||Fn(e?.reason||`Acceptance evidence requires operator review.`)),cockpits:Yn(Array.isArray(e?.cockpits)?e.cockpits.map(Wn):[],r,i,e)}}).filter(e=>e.run)}function Zn(e,t){let n=new Map;return e.forEach(e=>{let t=xn(e);n.has(t)||n.set(t,[]),n.get(t).push(e)}),[`bending`,`curve_family`,`decision_context`].filter(e=>n.has(e)).map(e=>Qn(n.get(e)[0],t,n.get(e)))}function Qn(e,t,n=[e]){let r=xn(e),i=t===`Remove`?Wt:Ut,a=String(e?.message||e?.reason||`Acceptance flag requires review.`);if(r===`bending`){let t=vn(e,`threshold`,`bending_threshold`)??.1,n=vn(e,`value`,`bending_peak`,`measured_value`)??t*1.35,r=vn(e,`points_above_threshold`)??(a.toLowerCase().includes(`sustained`)?6:1),o=vn(e,`assessed_points`)??41,s=o?r/o:0;return{kind:`bending`,tab:`Bending`,title:`Bending evidence`,plot:{plot_kind:`bending_evidence`,series:[],trace_points:[],threshold:t,peak:n,assessment_window:[.1,.9],exceedance_segments:[]},window:[.1,.9],segments:r>1?[[.52,.52+Math.min(.32,s+.06)]]:[],cards:[{key:`bending.call`,label:`Observed signal`,value:Sn(e),sub:`opposite-face strain imbalance`,level:`warn`},{key:`bending.max_percent`,label:`Peak imbalance`,value:yn(n),sub:e?.value?`reported by acceptance check`:`estimated from review flag`,level:`warn`},{key:`bending.threshold_percent`,label:`Review limit`,value:e?.threshold?yn(t):`not configured`,sub:`method threshold for bending review`,level:e?.threshold?`info`:`warn`},{key:`bending.points_above_threshold`,label:`Persistence`,value:String(r),sub:`${r} of ${o} assessed points above limit`,level:`warn`},{key:`selection.consequence_summary`,label:`Recommended action`,value:i,sub:`final report consequence`,level:`info`}]}}if(r===`curve_family`){let t=vn(e,`value`,`metric`)??.214,n=vn(e,`threshold`)??.15;return{kind:`curve_family`,tab:`Curve shape`,title:`Curve-shape evidence`,plot:{plot_kind:`curve_family`,points:[],reference_points:[]},points:[],reference:[],cohort:[],cards:[{key:`curve_family.classification`,label:`Scientific call`,value:t>n?`Distance outlier`:`Within family`,sub:`curve-shape assessment`,level:t>n?`warn`:`info`},{key:`curve_family.metric`,label:`Primary metric`,value:`${In(e?.metric||`shape distance`)} ${Ln(t)}`,sub:`review limit ${Ln(n)}`,level:t>n?`warn`:`info`},{key:`curve_family.source`,label:`Comparison`,value:`run vs cohort`,sub:`stress-strain family`,level:`info`},{key:`selection.consequence_summary`,label:`Recommended action`,value:i,sub:`final report consequence`,level:`info`}]}}let o=In(e?.category||e?.source||`run validity`);return{kind:`decision_context`,tab:o,title:o,summary:a,evidence:bn(e),cards:[{key:`run.validity`,label:`Validity call`,value:In(e?.value||e?.severity||`review`),sub:o,level:zn(e)>=2?`warn`:`info`},{key:`selection.consequence_summary`,label:`Recommended action`,value:i,sub:`final report consequence`,level:`info`},{key:`review.scope`,label:`Review scope`,value:n.length>1?`${n.length} linked findings`:`single finding`,sub:`same run decision`,level:`info`}]}}function $n(e,t){let n=e[0]||{};return`${Fn(n.message||n.reason||`Review this run before confirming the final report selection.`)}<br><span>${Fn(t===`Remove`?`Default is remove. Keep only if the scientific evidence supports inclusion and record the justification.`:`Default is keep. Remove only if the evidence shows the run should not contribute to the final report.`)}</span>`}function er(e,t={}){let n=t.flagCockpits!==!1,r=Array.isArray(e?.flags)?e.flags.filter(e=>e&&typeof e==`object`):[];if(!r.length)return[];let i=e?.run_states&&typeof e.run_states==`object`?e.run_states:{},a=new Map;return r.forEach(e=>{let t=String(e.run_id||``).trim();t&&(a.has(t)||a.set(t,[]),a.get(t).push(e))}),Array.from(a.entries()).sort(([e],[t])=>e.localeCompare(t)).map(([e,t])=>{let r=[...t].sort((e,t)=>zn(t)-zn(e)),a=r[0]||{},o=String(i[e]||``).toLowerCase(),s=zn(a),c=r.some(Hn);if(![`review_required`,`excluded`].includes(o)&&s<2&&!c)return null;let l=[`review_required`,`excluded`].includes(o)||c?`Remove`:`Keep`,u=String(a.message||a.reason||`Acceptance flag requires review`);Array.isArray(a.evidence_refs)&&a.evidence_refs.map(String).filter(Boolean);let d=r.map(Un);return{rowKey:`acceptance:${e}`,run:e,defaultCall:l,excluded:o===`excluded`,defects:Vn(r),reason:r.length===1?u:`${u} (+${r.length-1} more)`,flags:d,narrative:$n(d,l),cockpits:n?Zn(d,l):[]}}).filter(Boolean)}function tr(e){return e?.run?.result?.acceptance_report||e?.run?.acceptance_report||e?.acceptance_report||null}function nr(e){let t=e?.result?.review_rows||e?.review_rows||e?.result?.reviewRows||e?.reviewRows;return Array.isArray(t)?t.length:0}function rr(e){let t=e?.run||{};if(!e?.session_id||t.status!==`completed`||nr(t)>0)return!1;let n=tr(e);return Array.isArray(n?.flags)&&n.flags.length>0}function ir(e){return e?.summary&&typeof e.summary==`object`?e.summary:{}}function ar(e){return e?.rowKey||e?.run||``}function or(){try{return new URLSearchParams(window.location.search||``).has(`demo`)}catch{return!1}}function sr(e){return Array.isArray(e)?e.map(e=>String(e??``).trim()).filter(Boolean):[]}function cr(e){return e?.run?.result||e?.result||{}}function lr(e){let t=cr(e);return e?.acceptance_decisions||e?.run?.acceptance_decisions||t?.acceptance_decisions||null}function ur(e){let t=e?.selection_sets?.selection_sets||e?.selection_sets;return Array.isArray(t)?t:[]}function dr(e,t){let n=String(t||``).trim();if(!n)return[];let r=ur(e).find(e=>String(e?.selection_id||e?.id||``).trim()===n);return sr(r?.run_ids||r?.runs)}function fr(e){let t=dr(e,`all_runs`);if(t.length)return t;let n=e?.run_states&&typeof e.run_states==`object`?Object.keys(e.run_states):[];return n.length?n:sr((Array.isArray(e?.flags)?e.flags:[]).map(e=>e?.run_id))}function pr(e){let t=e?.summary&&typeof e.summary==`object`?e.summary:{},n=dr(e,e?.default_selection_set||t.default_selection_set||`default_report`);if(n.length)return n;let r=e?.run_states&&typeof e.run_states==`object`?e.run_states:{};return Object.entries(r).filter(([,e])=>![`excluded`,`review_required`,`removed`,`invalid`].includes(String(e||``).toLowerCase())).map(([e])=>e)}function mr(e,t){let n=sr(lr(e)?.final_selected_run_ids);if(n.length)return n;let r=cr(e),i=(Array.isArray(r?.final_report_runs)?r.final_report_runs:[]).filter(e=>e?.included!==!1&&e?.final_included!==!1).map(e=>e?.run_id||e?.run||e?.id);return i.length?sr(i):pr(t)}function hr(e){let t=lr(e),n=Array.isArray(t?.records)?t.records:[],r=new Map;return n.forEach(e=>{let t=String(e?.run_id||e?.run||``).trim();t&&r.set(t,e)}),r}function gr(e){let t=cr(e),n=Array.isArray(t?.specimen_results)?t.specimen_results:[],r=new Map;return n.forEach((e,t)=>{let n=String(e?.run_id||e?.run||`run_${String(t+1).padStart(3,`0`)}`).trim();n&&r.set(n,e)}),r}function _r(e){let t=new Map;return(Array.isArray(e)?e:[]).forEach(e=>{let n=String(e?.run||e?.run_id||``).trim();n&&t.set(n,e)}),t}function vr(e,t,n,r){let i=[],a=e=>sr(e).forEach(e=>{i.includes(e)||i.push(e)}),o=lr(e);return a(fr(t)),a(o?.default_selected_run_ids),a(o?.final_selected_run_ids),a(r),a((Array.isArray(n)?n:[]).map(e=>e.run)),a(Array.from(gr(e).keys())),i.sort((e,t)=>e.localeCompare(t,void 0,{numeric:!0,sensitivity:`base`}))}function yr(e,t,n,r,i){let a=String(r?.reason||r?.override_reason||r?.review_note||``).trim(),o=String(n?.reason||``).trim(),s=Array.isArray(n?.defects)?n.defects.join(` + `):``;if(n?.excluded)return`excluded before final report${o?` - ${o}`:``}`;if(r){let e=r?.default_keep??r?.default_included??r?.default_selected;return t&&e===!1?`kept with justification${a?` - ${a}`:o?` - ${o}`:``}`:!t&&e===!0?`removed by review${a?` - ${a}`:o?` - ${o}`:``}`:t?`included after review${a?` - ${a}`:``}`:`removed by method rule${o?` - ${o}`:``}`}if(n){let e=String(n.defaultCall||``).toLowerCase();return t?e===`remove`?`kept with justification${o?` - ${o}`:s?` - ${s}`:``}`:`kept${o?` - ${o}`:``}`:`removed${o?` - ${o}`:s?` - ${s}`:``}`}let c=i?.compressive_strength_MPa??i?.strength_MPa??i?.compressive_strength;return t&&Number.isFinite(Number(c))?`complete - compressive strength ${Ln(c)} MPa`:t?`included in final report`:`excluded from final report`}function br({session:e,report:t,reviewRows:n,demoRows:r=[]}){if(!(e?.session_id||e?.run?.run_id||t||cr(e)?.specimen_results)&&!r.length)return[];let i=new Set(mr(e,t)),a=hr(e),o=_r(n),s=gr(e),c=vr(e,t,n,i);return(c.length?c:sr(r.map(e=>e.run))).map(e=>{let t=a.get(e),n=o.get(e),r=s.get(e),c=t?.keep??t?.included??t?.selected,l=typeof c==`boolean`?c:i.has(e);return{run:e,included:l,reason:Rn(yr(e,l,n,t,r))}})}function xr({rows:e,totalRuns:t,decisions:n,setDecisions:r,reasons:i,setReasons:o,expanded:s,setExpanded:c,onRestore:l,onDecisionPersist:u}){let d=Array.isArray(e)?e:[],f=d.filter(e=>!e.excluded),p=Number.isFinite(Number(t))?Number(t):0,m=qt(()=>{let e=f.filter(e=>(n[ar(e)]??e.defaultCall)!==e.defaultCall).length,t=f.filter(e=>(n[ar(e)]??e.defaultCall)===`Keep`&&e.defaultCall===`Remove`&&!(i[ar(e)]||``).trim()).length,r=f.filter(e=>(n[ar(e)]??e.defaultCall)===`Remove`).length+d.filter(e=>e.excluded).length;return{overrides:e,missing:t,finalRuns:Math.max(0,p-r)}},[f,n,d,i,p]),h=[{k:`TOTAL RUNS`,v:p,sub:`in package`},{k:`FLAGGED`,v:f.length,sub:`need review`,tone:`warn`},{k:`FINAL REPORT`,v:m.finalRuns,sub:`selected runs`},{k:`OVERRIDES`,v:m.overrides,sub:m.missing?`${m.missing} missing reason${m.missing>1?`s`:``}`:m.overrides?`justified overrides`:`none`,tone:m.missing?`warn`:m.overrides?`ok`:`idle`}];return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:`One decision before output`}),(0,a.jsx)(`div`,{className:`sub`,children:f.length?(0,a.jsxs)(a.Fragment,{children:[`Execution and validation passed · `,(0,a.jsxs)(`b`,{children:[f.length,` runs flagged`]}),` for a decision.`]}):(0,a.jsxs)(a.Fragment,{children:[`Execution and validation passed · `,(0,a.jsx)(`b`,{children:`no runs flagged`}),` for a decision.`]})})]}),(0,a.jsx)(`div`,{className:`review-summary`,children:h.map(e=>(0,a.jsxs)(`div`,{className:`rev-tile`,"data-tone":e.tone||``,children:[(0,a.jsx)(`div`,{className:`rev-k`,children:e.k}),(0,a.jsx)(`div`,{className:`rev-v`,children:e.v}),(0,a.jsx)(`div`,{className:`rev-sub`,children:e.sub})]},e.k))}),(0,a.jsxs)(`div`,{className:`task`,children:[(0,a.jsxs)(`div`,{className:`task-head bare`,children:[(0,a.jsx)(`span`,{className:`task-flag`,children:`needs you`}),(0,a.jsx)(`span`,{className:`task-title`,children:`Confirm flagged runs`}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:`var(--t-xs)`},children:`Click a row to inspect diagnostic evidence`})]}),(0,a.jsxs)(`div`,{className:`acc-list`,children:[(0,a.jsxs)(`div`,{className:`acc-head`,children:[(0,a.jsx)(`span`,{children:`Run`}),(0,a.jsx)(`span`,{children:`Default`}),(0,a.jsx)(`span`,{children:`Defects`}),(0,a.jsx)(`span`,{children:`Reason`}),(0,a.jsx)(`span`,{style:{textAlign:`right`},children:`Decision`})]}),d.map(e=>{let t=ar(e);return(0,a.jsx)(Pn,{f:e,open:s===t,decision:n[t]??e.defaultCall,reason:i[t]||``,onToggle:()=>c(e=>e===t?null:t),onDecide:n=>{r(e=>({...e,[t]:n})),u?.(e,n,i[t]||``)},onReason:e=>o(n=>({...n,[t]:e})),onRestore:()=>l(e.run)},t)})]})]})]})}Object.assign(window,{Review:xr});function Sr({title:e,summary:t,tone:n,defaultOpen:r=!1,children:i}){let[o,s]=Z(r);return(0,a.jsxs)(`div`,{className:`collapse`+(o?` open`:``),children:[(0,a.jsxs)(`button`,{className:`collapse-head`,onClick:()=>s(e=>!e),children:[(0,a.jsx)(`span`,{className:`label-caps`,children:e}),(0,a.jsx)(`span`,{className:`collapse-sum`+(n?` `+n:``),children:t}),(0,a.jsx)(Q,{name:`chevron`,className:`collapse-chev`,style:{width:15,height:15}})]}),o&&(0,a.jsx)(`div`,{className:`collapse-body fade-in`,children:i})]})}function Cr({onFinalized:e,finalized:t,note:n,setNote:r,reviewer:i,setReviewer:o,reasonKind:s,setReasonKind:c,onOpenArtifact:l,onCopyPath:u,onReviewFields:d,onJumpRun:f,fieldsResolved:p,reviewSummary:m,outputPath:h,runManifest:g=[]}){let _=X.OUTPUT,v=h||``,y=!!v,b=Math.max(0,_.requiredMissing-(p.required||0)),x=Math.max(0,_.recommendedMissing-(p.recommended||0)),S=b+x,C=b===0&&n.trim().length>0&&!t,w=Array.isArray(g)?g:[],T=w.filter(e=>e.included).length,E=w.length-T,D=X.FINAL_CHECKS,O=D.issues.filter(e=>!(e.jump===`report`&&e.level===`error`&&b===0)&&!(e.jump===`report`&&e.level===`report`&&x===0));return(0,a.jsxs)(`div`,{className:`spotlight fade-in`,children:[(0,a.jsxs)(`div`,{className:`page-head`,children:[(0,a.jsx)(`h1`,{children:t?`MTDA finalized`:`Output is ready`}),(0,a.jsx)(`div`,{className:`sub`,children:!y&&!t?(0,a.jsx)(a.Fragment,{children:`MTDA output will appear after an analysed dataset has produced artifacts.`}):t?(0,a.jsxs)(a.Fragment,{children:[`Review state locked · `,(0,a.jsx)(`b`,{children:_.mtda}),` issued as `,(0,a.jsx)(`b`,{children:_.mtdaVersion}),`.`]}):(0,a.jsxs)(a.Fragment,{children:[`Test Report has warnings · MTDA is in `,(0,a.jsx)(`b`,{children:`draft`}),`.`]})})]}),(0,a.jsxs)(`div`,{className:`final-grid`,children:[(0,a.jsxs)(`div`,{className:`card`,style:{overflow:`hidden`},children:[(0,a.jsxs)(`div`,{style:{padding:`11px 16px`,borderBottom:`1px solid var(--border)`,display:`flex`,alignItems:`center`},children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Open output artifacts`}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsx)(`span`,{className:`muted-3`,style:{fontSize:`var(--t-xs)`,fontFamily:`var(--mono)`},children:y?`${_.archiveMembers} archive members`:`analysis pending`})]}),y?_.artifacts.filter(e=>e.id!==`folder`&&e.id!==`open_mtda`).map(e=>(0,a.jsxs)(`div`,{className:`artifact`,onClick:()=>l(e),children:[(0,a.jsx)(`div`,{className:`a-ic`,children:(0,a.jsx)(Q,{name:e.icon})}),(0,a.jsxs)(`div`,{className:`a-main`,children:[(0,a.jsx)(`div`,{className:`a-title`,children:e.title}),(0,a.jsx)(`div`,{className:`a-role`,children:e.role})]}),(0,a.jsx)(Yt,{tone:e.status===`warn`?`warn`:`ok`,dot:!1,children:e.statusLabel}),(0,a.jsx)(Q,{name:`arrowR`,className:`a-go`})]},e.id)):(0,a.jsx)(`div`,{className:`empty-state`,children:`Generated reports and archive browser links will appear after method execution.`}),(0,a.jsxs)(`div`,{style:{padding:`11px 16px`,borderTop:`1px solid var(--border)`},children:[(0,a.jsx)(`div`,{className:`label-caps`,style:{marginBottom:6},children:`MTDA output`}),(0,a.jsxs)(`div`,{className:`path-field`,children:[(0,a.jsx)(Q,{name:`folder`,style:{width:14,height:14,flex:`none`,opacity:.6}}),(0,a.jsx)(`span`,{children:v||`No MTDA output generated`}),(0,a.jsxs)(`div`,{className:`path-actions`,children:[(0,a.jsx)(`button`,{className:`path-act`,title:`Open MTDA archive browser`,disabled:!y,onClick:()=>l({title:`Open MTDA`}),children:(0,a.jsx)(Q,{name:`package`,style:{width:14,height:14}})}),(0,a.jsx)(`button`,{className:`path-act`,title:`Open output folder`,disabled:!y,onClick:()=>l({title:`Output folder`}),children:(0,a.jsx)(Q,{name:`folder`,style:{width:14,height:14}})}),(0,a.jsx)(`button`,{className:`path-act`,title:`Copy MTDA path`,disabled:!y,onClick:u,children:(0,a.jsx)(Q,{name:`copy`,style:{width:14,height:14}})})]})]})]})]}),(0,a.jsxs)(`div`,{className:`card final-panel`,children:[(0,a.jsxs)(`div`,{className:`row`,style:{gap:8},children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Finalize MTDA`}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsx)(`span`,{className:`draft-badge`+(t?` final`:``),style:{fontSize:11},children:t?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(Q,{name:`check`,style:{width:12,height:12}}),_.mtdaVersion]}):(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(Q,{name:`warn`,style:{width:12,height:12}}),`Draft`]})})]}),!t&&(0,a.jsxs)(`div`,{className:`finalize-readout`,children:[(0,a.jsxs)(`button`,{className:`fr-item`,onClick:d,children:[(0,a.jsx)(`span`,{className:`fr-v`,"data-tone":S>0?`warn`:`ok`,children:S}),(0,a.jsxs)(`span`,{className:`fr-k`,children:[`report gap`,S===1?``:`s`,(0,a.jsx)(`br`,{}),(0,a.jsxs)(`span`,{className:`muted-3`,children:[b,` required`]})]})]}),(0,a.jsxs)(`button`,{className:`fr-item`,disabled:!w.length,onClick:()=>f&&f(w.find(e=>!e.included)?.run),children:[(0,a.jsx)(`span`,{className:`fr-v`,children:w.length?`${T}/${w.length}`:`—`}),(0,a.jsxs)(`span`,{className:`fr-k`,children:[`runs in report`,(0,a.jsx)(`br`,{}),(0,a.jsx)(`span`,{className:`muted-3`,children:w.length?`${E} excluded`:`analysis pending`})]})]}),(0,a.jsxs)(`div`,{className:`fr-item static`,children:[(0,a.jsx)(`span`,{className:`fr-v`,"data-tone":O.length?`warn`:`ok`,children:O.length?O.length:(0,a.jsx)(Q,{name:`check`,style:{width:18,height:18}})}),(0,a.jsxs)(`span`,{className:`fr-k`,children:[O.length?`open checks`:`checks pass`,(0,a.jsx)(`br`,{}),(0,a.jsxs)(`span`,{className:`muted-3`,children:[D.passed.length,` passed`]})]})]})]}),b>0&&!t&&(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`warn`,style:{cursor:`pointer`},onClick:d,children:[(0,a.jsx)(Q,{name:`warn`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,children:[(0,a.jsxs)(`b`,{children:[b,` required field`,b>1?`s`:``,` must be resolved`]}),` before finalize.`]}),(0,a.jsx)(Q,{name:`arrowR`,className:`b-ic`,style:{alignSelf:`center`}})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsx)(`label`,{className:`label-caps`,children:`Reviewer`}),(0,a.jsx)(`input`,{className:`field-input`,placeholder:`Reviewer / operator`,value:i,onChange:e=>o(e.target.value),disabled:t})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsxs)(`label`,{className:`label-caps`,children:[`Amendment reason `,!t&&(0,a.jsx)(`span`,{style:{color:`var(--err-ink)`},children:`*`})]}),(0,a.jsx)(`select`,{className:`field-input`,value:s,onChange:e=>c(e.target.value),disabled:t,children:X.FINAL_REASON_KINDS.map(([e,t])=>(0,a.jsx)(`option`,{value:e,children:t},e))})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsxs)(`label`,{className:`label-caps`,children:[`Finalization note `,!t&&(0,a.jsx)(`span`,{style:{color:`var(--err-ink)`},children:`*`})]}),(0,a.jsx)(`textarea`,{className:`field-input`,placeholder:`Required note — summarize review decisions and any overrides`,value:n,onChange:e=>r(e.target.value),disabled:t})]}),(0,a.jsx)($,{variant:`primary`,className:`lg`,icon:b>0?`warn`:`check`,disabled:!C,onClick:e,children:t?`Finalized · ${_.mtdaVersion}`:b>0?`Resolve required fields first`:`Finalize & issue ${_.mtdaVersion}`}),(0,a.jsx)(`div`,{className:`muted`,style:{fontSize:`var(--t-xs)`,lineHeight:1.5},children:t?`MTDA is locked. Re-open the wizard to record a further amendment version.`:(0,a.jsxs)(a.Fragment,{children:[`Source package is never modified — the amendment is recorded against `,(0,a.jsx)(`b`,{children:_.mtdaVersion}),`.`]})})]})]}),(0,a.jsx)(Sr,{title:`Run manifest`,tone:E?`warn`:`ok`,summary:w.length?(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`b`,{children:[T,` of `,w.length]}),` runs included · `,E,` excluded`]}):(0,a.jsx)(a.Fragment,{children:`No analysed run manifest available`}),children:w.length?w.map(e=>(0,a.jsxs)(`div`,{className:`manifest-row`+(e.included?``:` out`),onClick:()=>!e.included&&f&&f(e.run),children:[(0,a.jsx)(`span`,{className:`mf-check`,children:e.included?(0,a.jsx)(Q,{name:`check`,style:{width:14,height:14}}):(0,a.jsx)(Q,{name:`x`,style:{width:13,height:13}})}),(0,a.jsx)(`span`,{className:`mf-run mono`,children:e.run}),(0,a.jsx)(`span`,{className:`mf-reason`,children:e.reason}),!e.included&&(0,a.jsx)(`span`,{className:`mf-jump`,children:`review →`})]},e.run)):(0,a.jsx)(`div`,{className:`empty-state`,children:`Run inclusion will appear after an analysed dataset has produced acceptance decisions.`})}),(0,a.jsx)(Sr,{title:`Pre-finalize checks`,tone:O.length?`warn`:`ok`,summary:(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`b`,{children:[D.passed.length,` passed`]}),` · `,D.outOfScope.length,` out of scope`,O.length>0&&(0,a.jsxs)(a.Fragment,{children:[` · `,O.length,` open`]})]}),children:(0,a.jsxs)(`div`,{className:`checks-list`,children:[D.passed.map(e=>(0,a.jsxs)(`div`,{className:`check-line ok`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:13,height:13}}),e]},e)),O.map(e=>(0,a.jsxs)(`div`,{className:`check-line `+(e.level===`error`?`err`:`rep`),onClick:()=>d(),style:{cursor:`pointer`},children:[(0,a.jsx)(Q,{name:e.level===`error`?`warn`:`info`,style:{width:13,height:13}}),e.label,(0,a.jsx)(`span`,{className:`check-fix`,children:`fix →`})]},e.label)),D.outOfScope.map(e=>(0,a.jsxs)(`div`,{className:`check-line oos`,children:[(0,a.jsx)(`span`,{className:`oos-dot`,children:`·`}),e,` `,(0,a.jsx)(`span`,{className:`oos-tag`,children:`out of scope`})]},e))]})})]})}Object.assign(window,{Finalize:Cr});var wr={File:[[`New method run`,`Ctrl+N`],[`Open package…`,`Ctrl+O`],[`sep`],[`Close wizard`,`Ctrl+W`]],Workflow:[[`Choose package…`,``],[`Choose method…`,``],[`Edit mapping…`,``],[`sep`],[`Check readiness`,``],[`Run method`,`Ctrl+R`]],Output:[[`Open Test Report`,``],[`Open Audit Report`,``],[`sep`],[`Open output folder`,``],[`Copy MTDA path`,``]],View:[[`Back a step`,``],[`Next step`,``],[`sep`],[`Toggle activity log`,`L`],[`Toggle context detail`,``],[`Tweaks…`,``]],Help:[[`Shortcuts`,``],[`About Method Analysis`,``]]};function Tr({onAction:e,openMenu:t,setOpenMenu:n}){let r=!!window.desktopApi,i=Kt(!1),o=e=>{let t=`button,.menu-item,.menu-pop,[data-window-control],[role="button"]`,n=e?.nativeEvent?.composedPath?.()||[];return e?.target?.closest&&e.target.closest(t)?!0:n.some(e=>e&&e.nodeType===1&&e.matches&&e.matches(t))};return(0,a.jsxs)(`div`,{className:`menubar`,"data-window-drag":`true`,onDoubleClick:e=>{if(!r||o(e))return;e.preventDefault();let t=window.desktopApi?.toggleMaximizeWindow?.();Promise.resolve(t).then(e=>{e&&typeof e==`object`&&window.__compressionSyncWindowState?.(e)}).catch(()=>{})},children:[(0,a.jsx)(`span`,{className:`menubar-title`,"data-window-drag":`true`,children:`Method Analysis`}),(0,a.jsx)(`nav`,{className:`menubar-menus`,children:Object.keys(wr).map(r=>(0,a.jsxs)(`div`,{className:`menu-item`+(t===r?` open`:``),role:`button`,tabIndex:0,onMouseDown:e=>{e.preventDefault(),e.stopPropagation(),i.current=!0,n(e=>e===r?null:r)},onClick:e=>{if(e.preventDefault(),e.stopPropagation(),i.current){i.current=!1;return}n(e=>e===r?null:r)},onMouseEnter:()=>t&&n(r),children:[r,t===r&&(0,a.jsx)(`div`,{className:`menu-pop`,onMouseDown:e=>e.stopPropagation(),onClick:e=>e.stopPropagation(),children:wr[r].map((t,r)=>{let i=t[2]||``;return t[0]===`sep`?(0,a.jsx)(`div`,{className:`sep`},r):(0,a.jsxs)(`button`,{disabled:!!i,title:i||void 0,onClick:()=>{n(null),e(t[0])},children:[t[0],(t[1]||i)&&(0,a.jsx)(`span`,{className:`k`,children:i?`Deferred`:t[1]})]},r)})})]},r))}),(0,a.jsx)(`span`,{className:`menubar-spacer`,"aria-hidden":`true`}),(0,a.jsx)(w,{className:`menubar-windowctrls`})]})}var Er=[`Package`,`Method`,`Mapping`,`Ready`,`Run`,`Validate`,`Accept`,`Output`];function Dr({states:e,onJump:t,phase:n}){let r=e=>e===`done`||e===`active`||e===`warn`||e===`error`;return(0,a.jsx)(`div`,{className:`spine`,children:(0,a.jsx)(`div`,{className:`spine-track`,children:Er.map((n,i)=>{let o=e[n]||`todo`,s=i<Er.length-1&&r(e[Er[i+1]]);return(0,a.jsxs)(`button`,{className:`step`,"data-state":o,onClick:()=>t&&t(n),title:`Go to ${n}`,children:[i>0&&(0,a.jsx)(`span`,{className:`rail rail-l`,"data-on":r(o)}),i<Er.length-1&&(0,a.jsx)(`span`,{className:`rail rail-r`,"data-on":s}),(0,a.jsx)(`span`,{className:`node`,children:o===`done`?`✓`:o===`warn`?`!`:o===`error`?`×`:i+1}),(0,a.jsx)(`span`,{className:`lbl`,children:n})]},n)})})})}function Or({pkg:e,method:t,mapping:n,output:r,open:i,onToggle:o,onAction:s}){return(0,a.jsxs)(a.Fragment,{children:[(0,a.jsxs)(`div`,{className:`contextbar`+(i?` open`:``),onClick:o,children:[(0,a.jsx)(`span`,{className:`cx`,children:(0,a.jsx)(`b`,{children:`ISO 14126`})}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsx)(`span`,{className:`cx`,children:e?e.name:`no package`}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsx)(`span`,{className:`cx`,children:t?`method `+t.standard:`method not selected`}),(0,a.jsx)(`span`,{className:`dot`,children:`·`}),(0,a.jsx)(`span`,{className:`cx cx-warn`,children:n?`mapping iso14126_manual.json (7 report gaps)`:`mapping not selected`}),(0,a.jsx)(Q,{name:`chevron`,className:`chev`,style:{width:14,height:14}})]}),i&&(0,a.jsxs)(`div`,{className:`context-detail fade-in`,children:[(0,a.jsx)(`span`,{className:`cd-k`,children:`Package`}),(0,a.jsx)(`span`,{className:`cd-v`,children:e?e.name:`—`}),(0,a.jsx)(`span`,{className:`cd-k`,children:`Method`}),(0,a.jsx)(`span`,{className:`cd-v`,children:t?t.title:`—`}),(0,a.jsx)(`span`,{className:`cd-k`,children:`Mapping`}),(0,a.jsx)(`span`,{className:`cd-v`,children:`iso14126_manual.json`}),(0,a.jsx)(`span`,{className:`cd-k`,children:`Output`}),(0,a.jsx)(`span`,{className:`cd-v mono`,children:r}),(0,a.jsxs)(`div`,{className:`cd-actions`,children:[(0,a.jsx)($,{size:`sm`,onClick:()=>s(`Choose package…`),children:`Change package…`}),(0,a.jsx)($,{size:`sm`,onClick:()=>s(`Choose method…`),children:`Change method…`}),(0,a.jsx)($,{size:`sm`,icon:`edit`,onClick:()=>s(`Edit mapping…`),children:`Edit mapping…`})]})]})]})}function kr({tone:e,state:t,logCount:n,onLog:r}){return(0,a.jsxs)(`div`,{className:`statusbar`,"data-tone":e,children:[(0,a.jsx)(`span`,{className:`sb-dot`}),(0,a.jsx)(`span`,{children:t}),(0,a.jsx)(`span`,{className:`sb-spacer`}),(0,a.jsx)(`span`,{className:`sb-note`,children:`draft · raw files untouched`}),(0,a.jsxs)(`span`,{className:`sb-link`,onClick:r,children:[`Activity log · `,n]}),(0,a.jsxs)(`span`,{className:`sb-ver`,children:[`mtdp `,X.APP_VERSION]})]})}function Ar({entries:e,onClose:t}){let[n,r]=Z(`all`),i=Kt(null);Gt(()=>{i.current&&(i.current.scrollTop=i.current.scrollHeight)},[e]);let o=e.filter(e=>n===`all`||e.level===n);return(0,a.jsxs)(a.Fragment,{children:[(0,a.jsx)(`div`,{className:`drawer-scrim`,onClick:t}),(0,a.jsxs)(`div`,{className:`drawer`,children:[(0,a.jsxs)(`div`,{className:`drawer-head`,children:[(0,a.jsx)(`span`,{className:`dh-t`,children:`Activity log`}),(0,a.jsxs)(`span`,{className:`dh-c`,children:[e.length,` entries`]}),(0,a.jsx)(`button`,{className:`dh-x`,onClick:t,children:(0,a.jsx)(Q,{name:`x`})})]}),(0,a.jsx)(`div`,{className:`drawer-filter`,children:[`all`,`info`,`ok`,`warn`,`err`].map(e=>(0,a.jsx)(`button`,{className:n===e?`on`:``,onClick:()=>r(e),children:e===`ok`?`success`:e===`err`?`error`:e},e))}),(0,a.jsxs)(`div`,{className:`drawer-body`,ref:i,children:[o.length===0&&(0,a.jsx)(`div`,{style:{padding:`16px`,color:`var(--log-ts)`,fontSize:12},children:`No entries at this level yet.`}),o.map((e,t)=>(0,a.jsxs)(`div`,{className:`log-entry`,"data-l":e.level,children:[(0,a.jsx)(`span`,{className:`l-ts`,children:e.ts}),(0,a.jsxs)(`span`,{className:`l-msg`,children:[(0,a.jsx)(`span`,{className:`l-lvl`,children:e.level===`ok`?`ok `:e.level}),`  `,e.msg]})]},t))]})]})]})}function jr({density:e,setDensity:t,accent:n,setAccent:r,onClose:i}){return(0,a.jsxs)(`div`,{className:`tweaks`,onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsxs)(`div`,{className:`tw-h`,children:[(0,a.jsx)(Q,{name:`edit`,style:{width:15,height:15}}),(0,a.jsx)(`span`,{className:`t`,children:`Tweaks`}),(0,a.jsx)(`button`,{onClick:i,children:(0,a.jsx)(Q,{name:`x`})})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Density`}),(0,a.jsx)(`div`,{className:`tw-seg`,children:[[`comfortable`,`Comfort`],[`balanced`,`Balanced`],[`dense`,`Dense`]].map(([n,r])=>(0,a.jsx)(`button`,{className:e===n?`on`:``,onClick:()=>t(n),children:r},n))})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Accent`}),(0,a.jsx)(`div`,{className:`tw-swatches`,children:[[`#0f6cbd`,`Azure`],[`#2f6f5e`,`Teal`],[`#5b53b8`,`Indigo`],[`#9a5a2c`,`Amber`]].map(([e,t])=>(0,a.jsx)(`div`,{className:`tw-sw`+(n===e?` on`:``),style:{background:e},title:t,onClick:()=>r(e)},e))})]})]})}function Mr({f:e,onChange:t}){return e.type===`enum`?(0,a.jsxs)(`select`,{className:`field-input`,value:e.value,onChange:e=>t(e.target.value),children:[(0,a.jsx)(`option`,{value:``,children:`Choose…`}),e.choices.map(e=>(0,a.jsx)(`option`,{value:e,children:e},e))]}):e.type===`bool`?(0,a.jsx)(`div`,{className:`seg`,style:{width:`fit-content`},children:[`yes`,`no`].map(n=>(0,a.jsx)(`button`,{className:e.value===n?`on`:``,onClick:()=>t(n),children:n},n))}):e.type===`float`?(0,a.jsxs)(`div`,{className:`float-row`,children:[(0,a.jsx)(`input`,{className:`field-input`,type:`number`,min:e.min,step:`any`,placeholder:e.example,value:e.value,onChange:e=>t(e.target.value)}),e.units&&e.units.length>1?(0,a.jsx)(`select`,{className:`field-input float-unit`,defaultValue:e.unit,children:e.units.map(e=>(0,a.jsx)(`option`,{children:e},e))}):(0,a.jsx)(`span`,{className:`float-unit-static mono`,children:e.unit})]}):e.type===`date`?(0,a.jsx)(`input`,{className:`field-input`,type:`date`,value:e.value,onChange:e=>t(e.target.value)}):(0,a.jsx)(`input`,{className:`field-input`,placeholder:e.example,value:e.value,onChange:e=>t(e.target.value)})}function Nr(e){return String(e||``).replace(/^report\./,``)}function Pr(e,t,n){let r=t.trim()||`Report completion amendment recorded from Finalize report dialog.`;return e.filter(e=>String(e.value||``).trim()).map(e=>({field_key:Nr(e.field),value:e.value,reason:r,reviewer:n||``,section:e.section||``,source_surface:`method_run_wizard.report_completion_editor`}))}function Fr({onClose:e,onResolveAll:t,onApplyAmendments:n,reviewer:r=``}){let[i,o]=Z(()=>X.REPORT_FIELDS.map(e=>({...e}))),[s,c]=Z(`missing`),[l,u]=Z(i[0].field),[d,f]=Z(``),[p,m]=Z(!1),h=i.find(e=>e.field===l),g=i.filter(e=>e.level===`required`&&!e.value.trim()).length,_=i.filter(e=>e.level===`recommended`&&!e.value.trim()).length,v={required:X.OUTPUT.requiredMissing-g,recommended:X.OUTPUT.recommendedMissing-_},y=Pr(i,d,r);function b(e){o(t=>t.map(t=>t.field===l?{...t,value:e,source:e.trim()?`report_override`:`missing`}:t))}async function x(){m(!0);try{if(n){if(await n({fields:i,counts:v,note:d.trim(),report_overrides:y})===!1)return}else t(v);e()}finally{m(!1)}}let S=[[`missing`,`Missing`,i.filter(e=>!e.value.trim()).length],[`required`,`Required`,i.filter(e=>e.level===`required`).length],[`recommended`,`Recommended`,i.filter(e=>e.level===`recommended`).length],[`overridden`,`Overridden`,i.filter(e=>e.value.trim()).length],[`all`,`All`,i.length]],C=i.filter(e=>s===`all`||s===`missing`&&!e.value.trim()||s===`overridden`&&e.value.trim()||s===e.level);return(0,a.jsx)(`div`,{className:`scrim no-flicker-overlay`,onMouseDown:t=>t.target===t.currentTarget&&e(),children:(0,a.jsxs)(`div`,{className:`dialog`,style:{width:`min(940px, 94vw)`,height:`min(640px, 90%)`},onMouseDown:e=>e.stopPropagation(),children:[(0,a.jsxs)(`div`,{className:`dialog-head`,children:[(0,a.jsx)(Q,{name:`report`}),(0,a.jsxs)(`div`,{className:`col`,style:{gap:1},children:[(0,a.jsx)(`h2`,{children:`Report completion`}),(0,a.jsx)(`span`,{className:`dh-sub`,children:`Report-only · source package untouched.`})]})]}),(0,a.jsxs)(`div`,{className:`dialog-body`,style:{display:`flex`,flexDirection:`column`,gap:12},children:[(0,a.jsx)(`div`,{className:`seg`,style:{alignSelf:`flex-start`},children:S.map(([e,t,n])=>(0,a.jsxs)(`button`,{className:s===e?`on`:``,onClick:()=>c(e),children:[t,` · `,n]},e))}),(0,a.jsxs)(`div`,{style:{display:`grid`,gridTemplateColumns:`1.35fr 1fr`,gap:14,flex:1,minHeight:0},children:[(0,a.jsx)(`div`,{className:`card`,style:{overflow:`auto`},children:(0,a.jsxs)(`table`,{className:`tbl`,children:[(0,a.jsx)(`thead`,{children:(0,a.jsxs)(`tr`,{children:[(0,a.jsx)(`th`,{children:`Field`}),(0,a.jsx)(`th`,{children:`Type`}),(0,a.jsx)(`th`,{children:`Requirement`}),(0,a.jsx)(`th`,{children:`Status`})]})}),(0,a.jsx)(`tbody`,{children:C.map(e=>(0,a.jsxs)(`tr`,{className:`click`,onClick:()=>u(e.field),style:l===e.field?{background:`var(--accent-soft)`}:null,children:[(0,a.jsxs)(`td`,{className:`mono`,children:[e.field,` `,(0,a.jsx)(en,{level:e.level})]}),(0,a.jsx)(`td`,{children:(0,a.jsx)(`span`,{className:`type-chip mono`,children:e.type})}),(0,a.jsx)(`td`,{children:(0,a.jsx)(Yt,{tone:e.level===`required`?`warn`:`idle`,dot:!1,children:e.level})}),(0,a.jsx)(`td`,{children:(0,a.jsx)(Yt,{tone:e.value.trim()?`ok`:e.level===`required`?`err`:`warn`,children:e.value.trim()?`resolved`:`missing`})})]},e.field))})]})}),(0,a.jsxs)(`div`,{className:`card card-pad`,style:{display:`flex`,flexDirection:`column`,gap:12},children:[(0,a.jsxs)(`div`,{children:[(0,a.jsx)(`div`,{className:`r-input mono`,style:{fontWeight:700},children:h.field}),(0,a.jsxs)(`div`,{className:`muted`,style:{fontSize:`var(--t-xs)`,marginTop:3},children:[X.IMPORTANCE_LABEL[h.level],` · example “`,h.example,`”`]})]}),(0,a.jsxs)(`div`,{className:`banner`,"data-tone":`info`,style:{padding:`8px 11px`},children:[(0,a.jsx)(Q,{name:`info`,className:`b-ic`,style:{width:15,height:15}}),(0,a.jsxs)(`div`,{className:`b-txt`,style:{fontSize:`var(--t-xs)`},children:[X.SOURCE_TYPE_LABEL[h.source],`. `,h.level===`required`?`Resolve this before final issue.`:`Add a value or status. Unresolved recommended fields finalize with warnings.`]})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsxs)(`div`,{className:`row`,style:{gap:7},children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Value`}),(0,a.jsxs)(`span`,{className:`type-chip mono`,children:[X.TYPE_HINT[h.type]||`text`,h.type===`enum`?` · ${h.choices.length}`:``,h.type===`float`&&h.unit?` · ${h.unit}`:``]})]}),(0,a.jsx)(Mr,{f:h,onChange:b})]}),(0,a.jsxs)(`div`,{className:`tw-group`,children:[(0,a.jsx)(`span`,{className:`label-caps`,children:`Reviewer note`}),(0,a.jsx)(`textarea`,{className:`field-input`,placeholder:`Optional provenance note`,value:d,onChange:e=>f(e.target.value)})]}),(0,a.jsxs)(`div`,{className:`banner`,"data-tone":g?`warn`:`ok`,style:{marginTop:`auto`},children:[(0,a.jsx)(Q,{name:g?`warn`:`check`,className:`b-ic`}),(0,a.jsxs)(`div`,{className:`b-txt`,style:{fontSize:`var(--t-xs)`},children:[g,` required · `,_,` recommended still missing.`]})]})]})]})]}),(0,a.jsxs)(`div`,{className:`dialog-foot`,children:[(0,a.jsx)(`span`,{className:`muted`,style:{fontSize:`var(--t-xs)`},children:`Amendments recorded in the report override ledger.`}),(0,a.jsx)(`span`,{className:`spacer`}),(0,a.jsx)($,{onClick:e,children:`Cancel`}),(0,a.jsx)($,{variant:`primary`,icon:`check`,onClick:x,disabled:p,children:p?`Applying`:`Apply amendments`})]})]})})}Object.assign(window,{MenuBar:Tr,Spine:Dr,ContextBar:Or,StatusBar:kr,LogDrawer:Ar,Tweaks:jr,ReportCompletionDialog:Fr,PIPELINE:Er});function Ir(e=0){let t=51721+e,n=Math.floor(t/3600)%24,r=Math.floor(t%3600/60),i=t%60;return`${String(n).padStart(2,`0`)}:${String(r).padStart(2,`0`)}:${String(i).padStart(2,`0`)}`}var Lr=[`setup`,`running`,`review`,`finalize`];function Rr(){if(typeof window>`u`)return``;let e=new URLSearchParams(window.location.search||``);return e.get(`initial_package_path`)||e.get(`package_path`)||``}function zr(e){if(!e)return null;let t=[e.schema_id,e.schema_version?`v`+e.schema_version:``].filter(Boolean).join(` · `),n=e.package_path||``;return{name:e.package_name||`Selected package`,family:e.analysis_type||e.schema_id||`analysis package`,runs:Number(e.run_count||0),schema:t||`Package schema`,path:n,channels:Array.isArray(e.available_channels)?e.available_channels:[],mtime:`loaded`,note:Zr(n)||`Opened package`,backendPreview:e}}function Br(e){if(!e)return null;let t=e.path||e.package_path||``;return t?{name:e.name||Xr(t),family:e.kind||e.extension||`analysis package`,runs:e.run_count||e.runs||null,path:t,mtime:e.modified_label||e.modified_at||``,note:e.parent||Zr(t)}:null}function Vr(e){let t=e?.package||{},n=e?.package_path||t.package_path||``;return n?{name:t.package_name||Xr(n),family:t.analysis_type||t.schema_id||`analysis package`,runs:t.run_count||null,path:n,mtime:`just opened`,note:Zr(n)}:null}function Hr(e,t,n=12){if(!t?.path)return e;let r=String(t.path);return[t,...e.filter(e=>String(e.path||``)!==r)].slice(0,n)}function Ur(e){let t=String(e||``).trim();return t?t.startsWith(`v`)?t:`v`+t:``}function Wr(e){return(Array.isArray(e?.eligible_methods)&&e.eligible_methods.length?e.eligible_methods:Array.isArray(e?.methods)?e.methods:[]).map(t=>Gr(t,e))}function Gr(e,t=null){if(!e)return null;let n=t?.selected_method?.method_id===e.method_id?t.selected_method:null,r={...e,...n||{}},i=r.method_name||r.label||r.method_id||`Backend method`,a=r.standard_reference||String(i).match(/ISO\s+\d+/i)?.[0]||r.analysis_type||`registered method`,o=Ur(r.version),s=Array.isArray(r.required_inputs)?r.required_inputs.length:0,c=Array.isArray(r.recipe_steps)?r.recipe_steps.length:0,l=[r.analysis_type,s?`${s} required inputs`:``,c?`${c} recipe steps`:``].filter(Boolean),u=t?.selected_method?.method_id===e.method_id?t?.mapping:null;return{id:r.method_id,title:i,short:[i,o].filter(Boolean).join(` — `),version:o||r.version||``,standard:a,summary:l.length?l.join(` · `):`Backend registered method from MethodRegistry.`,registry:`Backend MethodRegistry`,backendSummary:r,mappingSummary:u}}function Kr(e){let t=e?.preview||e?.mappingPreview||null,n=Array.isArray(t?.rows)?t.rows:Array.isArray(e?.mapped_fields)?e.mapped_fields:[],r=Array.isArray(t?.candidate_rows)?t.candidate_rows:[];return n.map((e,t)=>qr(e,t,r)).filter(Boolean)}function qr(e,t,n){if(!e)return null;let r=e.method_field||e.requirement_id||e.source_role||`mapping.${t+1}`,i=String(e.severity||e.required_or_recommended||``).toLowerCase(),a=i===`execution_critical`||i===`required`?`required`:`recommended`,o=String(e.status||e.operator_status||``).toLowerCase(),s=e.mapped_source||e.source||``,c=o===`pass`||o===`found`?`matched`:o===`ambiguous`||o===`warning`?`ambiguous`:s?`manual`:`unmapped`,l=e.source_role||r,u=n.filter(e=>{let t=e.method_field||e.requirement_id||``,n=e.source_role||``;return t===r||n===l}).map(t=>({source:t.source_name||t.candidate_source||t.mapped_source||``,kind:t.source_kind||e.source_kind||`field`,scope:t.scope||e.scope||``,coverage:t.coverage||e.coverage||`—`,confidence:Number(t.confidence||e.confidence||0),example:t.example_value||e.example_value||``,reason:t.reason||t.message||e.resolution_status||``,via:t.reason||``})).filter(e=>e.source);return s&&!u.some(e=>e.source===s)&&u.unshift({source:s,kind:e.source_kind||`field`,scope:e.scope||``,coverage:e.coverage||`—`,confidence:Number(e.confidence||1),example:e.example_value||``,reason:e.resolution_status||`backend mapping profile`,via:e.resolution_status||``}),{id:e.requirement_id||r,input:r,desc:e.description||r,req:a,kind:e.source_kind||`field`,status:c,binding:s,coverage:e.coverage||(s?`mapping declared`:`—`),unit:e.expected_unit||e.unit||e.source_unit||``,via:e.resolution_status||e.source_location||``,note:e.message||``,candidates:u,backendRow:e}}function Jr(e){return(e||[]).map(e=>{let t=e.backendRow||{};return{requirement_id:t.requirement_id||e.id||``,method_field:t.method_field||e.input||``,source_role:t.source_role||e.input?.split(`.`).at(-1)||``,source_kind:e.kind||t.source_kind||`field`,mapped_source:e.binding||``,status:e.status||``}})}function Yr(e=[]){return JSON.stringify((Array.isArray(e)?e:[]).map(e=>({id:e?.id||``,input:e?.input||``,req:e?.req||``,status:e?.status||``,binding:e?.binding||``,kind:e?.kind||``,coverage:e?.coverage||``,unit:e?.unit||``,via:e?.via||``,note:e?.note||``,desc:e?.desc||``,candidates:Array.isArray(e?.candidates)?e.candidates.map(e=>({source:e?.source||``,kind:e?.kind||``,scope:e?.scope||``,coverage:e?.coverage||``,confidence:Number(e?.confidence||0),example:e?.example||``,reason:e?.reason||``})).sort((e,t)=>e.source.localeCompare(t.source)):[]})).sort((e,t)=>e.id.localeCompare(t.id)))}function Xr(e){return e?String(e).split(/[\\/]/).pop():``}function Zr(e){let t=String(e||``),n=Math.max(t.lastIndexOf(`/`),t.lastIndexOf(`\\`));return n>0?t.slice(0,n):``}function Qr(e){let t=e?.mapping_name||Xr(e?.path)||`mapping_profile.json`;return/_wizard_edit\.(json|ya?ml)$/i.test(t)?t:`${t.replace(/\.(json|ya?ml)$/i,``)||`mapping_profile`}_wizard_edit.json`}function $r(e){return String(e?.readiness?.status||e?.readiness_status||``).trim().replace(/[-\s]+/g,`_`).toUpperCase()}function ei(e){let t=$r(e);return[`NOT_READY`,`BLOCKED`,`FAILED`,`ERROR`,`INVALID`].includes(t)}function ti(e,t=!1){let n=$r(e);return e?.run_enabled===!0||n===`READY`||n===`READY_WITH_WARNINGS`?!0:ei(e)?!1:!!t}function ni(e,t,n=``){let r=(t||e.defaultCall||`Remove`)===`Keep`,i=(e.defaultCall||`Remove`)===`Keep`;return{run_id:e.run,decision:r?`keep`:`remove`,final_included:r,default_call:e.defaultCall||(i?`Keep`:`Remove`),default_included:i,reason:n||``,defects:Array.isArray(e.defects)?e.defects:[],source_surface:`method_run_wizard.review_spotlight`,ui_context:`analysis.review`}}function ri(e,t,n=[]){return(Array.isArray(n)?n:[]).filter(e=>!e.excluded).map(n=>ni(n,e[ar(n)]??n.defaultCall,t[ar(n)]||``))}function ii(){let e=(typeof location<`u`&&location.hash||``).replace(`#`,``),t=Lr.includes(e)?e:`setup`,n=qt(()=>Rr(),[]),r=qt(()=>or(),[]),[i,o]=Z(t),[s,c]=Z(()=>r?X.PACKAGE:null),[u,d]=Z(()=>r?X.PACKAGE.path:``),[f,p]=Z(()=>r?X.METHOD:null),[m,h]=Z(()=>r),[g,_]=Z(!1),[v,y]=Z(X.BINDINGS),[b,x]=Z(!1),[S,C]=Z({}),[w,T]=Z({}),[E,D]=Z(`run_004`),[O,k]=Z(``),[A,ee]=Z(``),[te,j]=Z(X.FINAL_REASON_KINDS[0][0]),[M,N]=Z(!1),[ne,re]=Z({required:0,recommended:0}),[P,F]=Z(null),[I,L]=Z(!1),[R,z]=Z(e===`editor`),[ie,ae]=Z(!1),[oe,se]=Z(!1),[ce,le]=Z(!1),[B,ue]=Z(!1),[de,fe]=Z(`balanced`),[pe,me]=Z(`#0f6cbd`),[V,he]=Z(null),[H,U]=Z(null),[ge,W]=Z(null),[_e,ve]=Z([]),[ye,be]=Z(!1),[xe,Se]=Z(null),[Ce,we]=Z(()=>r?X.METHOD.id:``),[Te,Ee]=Z([{ts:Ir(0),level:`info`,msg:`Method Analysis opened`}]),De=Kt(1),Oe=Kt(null),ke=Kt(0),Ae=Kt(null),je=Kt(``),Me=Kt(new Set),Ne=Kt(new Set),G=Jt(e=>Ee(t=>[...t,{ts:Ir(De.current++*3),...e}]),[]),Pe=qt(()=>Wr(H),[H]),Fe=qt(()=>Kr(H?.mapping),[H?.mapping]),Ie=qt(()=>Yr(Fe),[Fe]);Gt(()=>{document.documentElement.setAttribute(`data-density`,de)},[de]),Gt(()=>()=>{if(Oe.current&&clearTimeout(Oe.current),Ae.current){try{Ae.current()}catch{}Ae.current=null}},[]),Gt(()=>{let e=document.documentElement.style;e.setProperty(`--accent`,pe);let t=(e,t)=>{try{let n=parseInt(e.slice(1),16),r=n>>16&255,i=n>>8&255,a=n&255;return r=Math.round(r*t),i=Math.round(i*t),a=Math.round(a*t),`#`+((1<<24)+(r<<16)+(i<<8)+a).toString(16).slice(1)}catch{return e}};e.setProperty(`--accent-hover`,t(pe,.85)),e.setProperty(`--accent-press`,t(pe,.72)),e.setProperty(`--accent-ink`,t(pe,.78))},[pe]);let Le=R||oe||ie||ce;Gt(()=>{let e=e=>{e.target.tagName===`INPUT`||e.target.tagName===`TEXTAREA`||e.target.tagName===`SELECT`||(e.key===`l`||e.key===`L`?L(e=>!e):(e.ctrlKey||e.metaKey)&&(e.key===`n`||e.key===`N`)?(e.preventDefault(),Ke()):(e.ctrlKey||e.metaKey)&&(e.key===`o`||e.key===`O`)?(e.preventDefault(),Ye()):(e.ctrlKey||e.metaKey)&&(e.key===`w`||e.key===`W`)?(e.preventDefault(),qe()):e.key===`ArrowRight`&&!Le?Ze(1):e.key===`ArrowLeft`&&!Le?Ze(-1):e.key===`Escape`&&(R?z(!1):oe?se(!1):ie?ae(!1):ce?le(!1):I?L(!1):B?ue(!1):P&&F(null)))};return window.addEventListener(`keydown`,e),()=>window.removeEventListener(`keydown`,e)});function K(e){he(e),setTimeout(()=>he(t=>t===e?null:t),2200)}function Re(e){let t=Array.isArray(e)?e:[];y(t),je.current=Yr(t),x(!1)}function ze(e){U(e);let t=zr(e?.package);if(!t)return null;let n=Wr(e);return c(t),d(t.path||t.name),ve(t=>Hr(t,Vr(e))),p(null),we(n[0]?.id||``),h(!1),_(!1),y(X.BINDINGS),je.current=Yr(X.BINDINGS),x(!1),W(null),t}Gt(()=>{let e=window.desktopApi?.analysis;if(!e?.listRecentPackages){ve([]),be(!1),Se(null);return}let t=!0;return be(!0),e.listRecentPackages({limit:12}).then(e=>{t&&(e?.status===`ok`?(ve((Array.isArray(e.data?.packages)?e.data.packages:[]).map(Br).filter(Boolean)),Se(null)):(ve([]),Se(e?.message||`Recent packages are unavailable.`)))}).catch(e=>{t&&(ve([]),Se(e?.message||`Recent packages are unavailable.`))}).finally(()=>{t&&be(!1)}),()=>{t=!1}},[]),Gt(()=>{if(!n)return;let e=!0,t=window.desktopApi?.analysis;if(!t?.createSession){W(`Analysis backend bridge is unavailable.`),G({level:`warn`,msg:`Analysis package handoff could not reach backend bridge`});return}return t.createSession({initial_package_path:n}).then(t=>{if(!e)return;if(t?.status!==`ok`){let e=t?.message||`Could not load handed-off package.`;W(e),G({level:`warn`,msg:e});return}let n=ze(t.data);n&&G({level:`ok`,msg:`Package loaded from Packaging · ${n.name}`})}).catch(t=>{if(!e)return;let n=t?.message||`Could not load handed-off package.`;W(n),G({level:`warn`,msg:n})}),()=>{e=!1}},[n,G]),Gt(()=>{Pe.length&&!Pe.some(e=>e.id===Ce)&&we(Pe[0].id)},[Pe,Ce]),Gt(()=>{Fe.length&&(b&&R||Ie!==je.current&&Re(Fe))},[Fe,Ie,b,R]);let Be=$r(H),Ve=!!(s&&f&&m),He=!!H?.session_id&&ti(H),Ue=ei(H),We=!!(s&&f)&&!Ue&&(He||Ve);function Ge(e=null){Oe.current&&=(clearTimeout(Oe.current),null),pt(),ke.current=0,Me.current=new Set,o(`setup`),c(null),d(``),p(null),h(!1),_(!1),y(X.BINDINGS),je.current=Yr(X.BINDINGS),x(!1),C({}),T({}),D(`run_004`),k(``),ee(``),j(X.FINAL_REASON_KINDS[0][0]),N(!1),re({required:0,recommended:0}),F(null),L(!1),z(!1),ae(!1),se(!1),ue(!1),he(null),U(e),W(null),we(Wr(e)[0]?.id||``),De.current=1,Ee([{ts:Ir(0),level:`info`,msg:`New method run opened`}])}async function Ke(){let e=window.desktopApi?.analysis;if(!e?.createSession){let e=`Analysis backend bridge is unavailable.`;Ge(null),W(e),G({level:`warn`,msg:e}),K(e);return}try{let t=await e.createSession({});if(t?.status===`ok`){Ge(t.data),G({level:`ok`,msg:`Backend analysis session opened · ${t.data?.session_id||`new session`}`}),K(`New method run ready.`);return}let n=t?.message||`Could not start a new method run.`;Ge(null),W(n),G({level:`warn`,msg:n}),K(n)}catch(e){let t=e?.message||`Could not start a new method run.`;Ge(null),W(t),G({level:`warn`,msg:t}),K(t)}}function qe(){window.desktopApi?.closeWindow?.()}async function Je(e){let t=typeof e==`string`?e:e?.path,n=typeof e==`object`&&e?.name||Xr(t);if(!t){let e=`No package path was selected.`;W(e),G({level:`warn`,msg:e}),K(e);return}let r=window.desktopApi?.analysis;if(!r?.createSession){let e=`Analysis backend bridge is unavailable.`;W(e),G({level:`warn`,msg:e}),K(e);return}try{let e=H?.session_id&&r?.loadPackage?await r.loadPackage({session_id:H.session_id,path:t}):await r.createSession({initial_package_path:t});if(e?.status===`ok`){let t=ze(e.data);if(t){G({level:`ok`,msg:`Package loaded from recent files · ${t.name}`}),K(`Package loaded — ${t.name}`),o(`setup`);return}let n=`Recent package did not return a package preview.`;W(n),G({level:`warn`,msg:n}),K(n);return}let i=e?.message||`Could not load package ${n||t}.`;W(i),G({level:`warn`,msg:i}),K(i)}catch(e){let r=e?.message||`Could not load package ${n||t}.`;W(r),G({level:`warn`,msg:r}),K(r)}}async function Ye(){let e=window.desktopApi?.analysis;if(!e?.openPackageDialog){let e=`Native analysis package dialog is unavailable.`;W(e),G({level:`warn`,msg:e}),K(e);return}try{let t=H?.session_id?{session_id:H.session_id}:{},n=await e.openPackageDialog(t);if(n?.status===`ok`){let e=ze(n.data);if(e){G({level:`ok`,msg:`Package loaded from native dialog · ${e.name}`}),K(`Package loaded — ${e.name}`),o(`setup`);return}let t=`Analysis package dialog did not return a package preview.`;W(t),G({level:`warn`,msg:t}),K(t);return}let r=n?.message||`Could not open analysis package.`;if(n?.error_type===`Cancelled`){G({level:`info`,msg:r}),K(`Open package cancelled.`);return}W(r),G({level:`warn`,msg:r}),K(r)}catch(e){let t=e?.message||`Could not open analysis package.`;W(t),G({level:`warn`,msg:t}),K(t)}}function Xe(e){if(e===`setup`){o(`setup`);return}if(!s||!f){o(`setup`),K(`Choose package and method first.`);return}o(e)}function Ze(e){let t=Lr.indexOf(i);Xe(Lr[Math.max(0,Math.min(Lr.length-1,t+e))])}async function Qe(){let e=Pe.find(e=>e.id===Ce)||X.METHOD,t=window.desktopApi?.analysis;if(H?.session_id&&t?.selectMethod&&e?.id)try{let n=await t.selectMethod({session_id:H.session_id,method_id:e.id});if(n?.status===`ok`){let t=n.data;U(t);let r=Gr(t?.selected_method,t)||Wr(t).find(e=>e.id===t?.selected_method_id)||e;we(r.id),p(r),h(!1),_(!1),G({level:`info`,msg:`Method confirmed · ${r.standard} ${r.version}`.trim()}),t?.mapping?.label&&G({level:t.mapping.critical_missing_count?`warn`:`ok`,msg:`Default mapping applied · ${t.mapping.label}`});return}let r=n?.message||`Could not select method through backend.`;W(r),G({level:`warn`,msg:r})}catch(e){let t=e?.message||`Could not select method through backend.`;W(t),G({level:`warn`,msg:t})}we(e.id),p(e),G({level:`info`,msg:`Method confirmed · ${e.standard} ${e.version}`.trim()}),G({level:`ok`,msg:`Default mapping applied · 35/35 critical inputs bound`}),G({level:`warn`,msg:`Readiness READY_WITH_WARNINGS · 7 report gaps · 38 recommended blank`})}async function $e(){let e=window.desktopApi?.analysis;if(!H?.session_id||!e?.checkReadiness){K(`Readiness READY_WITH_WARNINGS`),G({level:`warn`,msg:`Readiness check used prototype fallback`});return}try{let t=await e.checkReadiness({session_id:H.session_id});if(t?.status!==`ok`){let e=t?.message||`Readiness check failed.`;W(e),G({level:`warn`,msg:e});return}U(t.data);let n=t.data?.readiness||{},r=n.status||t.data?.readiness_status||`UNKNOWN`,i=n.summary||{},a=`${i.execution_critical_passed??0}/${i.execution_critical_total??0}`,o=i.report_missing_total??0;G({level:ti(t.data)?`ok`:`warn`,msg:`Readiness ${r} · ${a} critical inputs · ${o} report gaps`}),K(`Readiness ${r}`)}catch(e){let t=e?.message||`Readiness check failed.`;W(t),G({level:`warn`,msg:t})}}function et(){h(!0),G({level:`ok`,msg:`Report bindings saved · iso14126_manual_wizard_edit.json`}),K(`Report bindings saved.`)}function tt(){h(!0),G({level:`warn`,msg:`Report bindings skipped · warnings accepted`})}function nt(){se(!0)}function rt(){_(!0),G({level:`warn`,msg:`38 recommended metadata fields left blank · warnings accepted`})}async function it(){let e=window.desktopApi?.analysis;if(!H?.session_id||!e?.openMappingDialog){let e=`Mapping profile browsing requires the desktop backend bridge.`;return G({level:`warn`,msg:e}),K(e),null}try{let t={session_id:H.session_id},n=Zr(H?.mapping?.path);n&&(t.initial_dir=n);let r=await e.openMappingDialog(t);if(r?.status===`ok`){U(r.data);let e=Kr(r.data?.mapping);return Re(e),h(!1),G({level:`ok`,msg:`Mapping profile loaded · ${r.data?.mapping?.mapping_name||`backend profile`}`}),e}let i=r?.message||`Could not load mapping profile.`;r?.error_type!==`Cancelled`&&W(i),G({level:r?.error_type===`Cancelled`?`info`:`warn`,msg:i})}catch(e){let t=e?.message||`Could not load mapping profile.`;W(t),G({level:`warn`,msg:t})}return null}async function at(e){let t=window.desktopApi?.analysis;if(!H?.session_id||!t?.saveMappingDialog){let e=`Mapping profile Save-as requires the desktop backend bridge.`;return G({level:`warn`,msg:e}),K(e),null}try{let n={session_id:H.session_id,bindings:Jr(e),default_name:Qr(H?.mapping)},r=Zr(H?.mapping?.path);r&&(n.initial_dir=r);let i=await t.saveMappingDialog(n);if(i?.status===`ok`){U(i.data);let e=Kr(i.data?.mapping);Re(e);let t=e.filter(e=>e.req===`required`&&!rn(e)).length;return h(t===0&&!!i.data?.mapping_confirmed),G({level:`ok`,msg:`Mapping profile saved · ${i.data?.mapping?.mapping_name||`backend profile`}`}),e}let a=i?.message||`Could not save mapping profile.`;i?.error_type!==`Cancelled`&&W(a),G({level:i?.error_type===`Cancelled`?`info`:`warn`,msg:a})}catch(e){let t=e?.message||`Could not save mapping profile.`;W(t),G({level:`warn`,msg:t})}return null}async function ot(e,t){let n=Array.isArray(e)?e:[];if(H?.session_id&&t){let t=window.desktopApi?.analysis;if(!t?.applyMappingPatch){let e=`Mapping edits need backend applyMappingPatch before they can be saved.`;G({level:`warn`,msg:e}),K(e);return}try{let n=await t.applyMappingPatch({session_id:H.session_id,bindings:Jr(e)});if(n?.status===`ok`){U(n.data),Re(Kr(n.data?.mapping)),h(!0),z(!1),G({level:`ok`,msg:`Mapping edits saved · ${n.data?.mapping?.mapping_name||`backend profile`}`});return}let r=n?.message||`Could not save mapping edits.`;W(r),G({level:`warn`,msg:r})}catch(e){let t=e?.message||`Could not save mapping edits.`;W(t),G({level:`warn`,msg:t})}return}if(H?.session_id&&window.desktopApi?.analysis?.confirmMapping){try{let e=await window.desktopApi.analysis.confirmMapping({session_id:H.session_id});if(e?.status===`ok`){U(e.data);let t=Kr(e.data?.mapping);t.length?Re(t):x(!1),h(!0),z(!1),G({level:`ok`,msg:`Mapping profile confirmed · ${e.data?.mapping?.mapping_name||`backend profile`}`});return}let t=e?.message||`Could not confirm mapping profile.`;W(t),G({level:`warn`,msg:t})}catch(e){let t=e?.message||`Could not confirm mapping profile.`;W(t),G({level:`warn`,msg:t})}return}Re(n),h(!n.some(e=>e.req===`required`&&!rn(e))),z(!1),G({level:t?`ok`:`info`,msg:t?`Repaired mapping saved · iso14126_manual_wizard_edit.json`:`Mapping profile confirmed`})}function st(e){U(e);let t=e?.run||{};if(t.status===`completed`){let n=`${e?.session_id||``}:${t.run_id||``}`;return rr(e)&&window.desktopApi?.analysis?.getSession&&!Ne.current.has(n)?(Ne.current.add(n),dt(e.session_id),!0):(pt(),G({level:`ok`,msg:`Method run complete · ${t.result?.output_path||t.output_path||`MTDA output ready`}`}),o(`review`),!0)}if(t.status===`failed`){pt();let e=t.errors?.[0]||t.message||`Method run failed.`;return W(e),G({level:`warn`,msg:e}),!0}return t.status===`cancelled`?(pt(),G({level:`warn`,msg:t.message||`Run cancelled by operator · returned to setup`}),o(`setup`),!0):!1}function q(e){let t=String(e?.data?.status||e?.event||``).toLowerCase();return t.includes(`fail`)||t.includes(`cancel`)?`warn`:t.includes(`complete`)||t.includes(`finalized`)?`ok`:`info`}function ct(e,t=0){return e?.event_id||`${e?.event||`event`}:${e?.data?.phase||``}:${e?.data?.message||``}:${t}`}function lt(e){(e?.events||[]).forEach((e,t)=>{let n=ct(e,t);if(Me.current.has(n))return;Me.current.add(n);let r=e?.data||{},i=r.message||r.phase||e?.event||`backend event`;G({level:q(e),msg:`Backend ${e?.event||`event`}: ${i}`})})}function ut(e){let t=Array.isArray(e?.events)?e.events:[];t.length&&U(n=>{if(!n||e?.session_id&&n.session_id!==e.session_id)return n;let r=n.run||{},i=Array.isArray(r.events)?r.events:[],a=new Set(i.map((e,t)=>ct(e,t))),o=[...i];t.forEach((e,t)=>{let n=ct(e,t);a.has(n)||(a.add(n),o.push(e))});let s=(t[t.length-1]||{}).data||{},c={...r,events:o,run_id:r.run_id||e?.run_id,phase:s.phase||r.phase,message:s.message||r.message};return s.progress_percent!==void 0&&(c.progress_percent=Number(s.progress_percent)),{...n,run:c}})}async function dt(e){let t=window.desktopApi?.analysis;if(!(!e||!t?.getSession))try{let n=await t.getSession({session_id:e});if(n?.status===`ok`){st(n.data);return}let r=n?.message||`Could not refresh method run state.`;W(r),G({level:`warn`,msg:r})}catch(e){let t=e?.message||`Could not refresh method run state.`;W(t),G({level:`warn`,msg:t})}}function ft(e){if(e?.status===`error`){G({level:`warn`,msg:e.message||`Backend event stream failed.`});return}let t=e?.data||e||{},n=Number(t.next_cursor??ke.current);Number.isFinite(n)&&(ke.current=Math.max(ke.current,n)),ut(t),lt(t),(t.events||[]).some(e=>{let t=String(e?.data?.status||e?.event||``).toLowerCase();return t.includes(`completed`)||t.includes(`failed`)||t.includes(`cancelled`)})&&dt(t.session_id)}async function pt(){let e=Ae.current;if(Ae.current=null,e)try{await e()}catch(e){G({level:`warn`,msg:e?.message||`Could not stop backend event stream.`})}}async function mt(e){let t=window.desktopApi?.analysis;if(!e||!t?.subscribeEvents)return;await pt();let n=await t.subscribeEvents({session_id:e,cursor:ke.current,limit:100},{onEvent:ft});if(n?.status===`ok`&&typeof n.unsubscribe==`function`){Ae.current=n.unsubscribe,G({level:`info`,msg:`Backend event stream connected`});return}n?.status===`error`&&n?.error_type!==`BridgeUnavailable`&&G({level:`warn`,msg:n.message||`Backend event stream unavailable.`})}async function ht(e){let t=window.desktopApi?.analysis;if(!(!e||!t?.getEvents))try{let n=await t.getEvents({session_id:e,cursor:ke.current,limit:100});if(n?.status!==`ok`)return;let r=n.data||{},i=Number(r.next_cursor??ke.current);Number.isFinite(i)&&(ke.current=i),ut(r),lt(r)}catch(e){G({level:`warn`,msg:e?.message||`Could not read backend event stream.`})}}function gt(e){Oe.current&&clearTimeout(Oe.current);let t=async()=>{let n=window.desktopApi?.analysis;if(n?.getSession)try{let r=await n.getSession({session_id:e});if(r?.status!==`ok`){let e=r?.message||`Could not refresh method run state.`;W(e),G({level:`warn`,msg:e});return}await ht(r.data?.session_id||e),st(r.data)||(Oe.current=setTimeout(t,650))}catch(e){let t=e?.message||`Could not refresh method run state.`;W(t),G({level:`warn`,msg:t})}};Oe.current=setTimeout(t,450)}async function _t(){let e=window.desktopApi?.analysis;if(H?.session_id&&e?.startRun){o(`running`),ke.current=0,G({level:`info`,msg:`Method execution requested through backend`});try{let t=await e.startRun({session_id:H.session_id,output_path:H.output_path,overwrite:!0,generate_workbench:!0});if(t?.status!==`ok`){let e=t?.message||`Could not start method run.`;W(e),G({level:`warn`,msg:e}),o(`setup`);return}await mt(t.data?.session_id||H.session_id),await ht(t.data?.session_id||H.session_id),st(t.data)||(G({level:`info`,msg:`Backend method run started · ${t.data?.run?.run_id||`active run`}`}),gt(t.data.session_id))}catch(e){let t=e?.message||`Could not start method run.`;W(t),G({level:`warn`,msg:t}),o(`setup`)}return}o(`running`),G({level:`info`,msg:`Method execution started`})}function vt(){o(`review`);let e=H?.run||{};G({level:`ok`,msg:e.result?.output_path?`Reduction complete · ${e.result.output_path}`:`Reduction complete · 3 runs flagged for review`})}async function yt(){let e=window.desktopApi?.analysis;if(Oe.current&&clearTimeout(Oe.current),H?.session_id&&e?.cancelRun&&H?.run?.status===`running`)try{let t=await e.cancelRun({session_id:H.session_id});t?.status===`ok`&&(await ht(t.data?.session_id||H.session_id),U(t.data))}catch(e){let t=e?.message||`Could not cancel backend method run.`;W(t),G({level:`warn`,msg:t})}await pt(),o(`setup`),G({level:`warn`,msg:`Run cancelled by operator · returned to setup`})}async function J(e,t,n=``){let r=window.desktopApi?.analysis;if(!(!H?.session_id||!r?.updateAcceptanceDecision))try{let i=await r.updateAcceptanceDecision({session_id:H.session_id,method_run_id:H.run?.run_id,decision_patch:ni(e,t,n)});if(i?.status===`ok`){U(i.data);return}let a=i?.message||`Could not persist acceptance decision.`;W(a),G({level:`warn`,msg:a})}catch(e){let t=e?.message||`Could not persist acceptance decision.`;W(t),G({level:`warn`,msg:t})}}async function bt(){let e=window.desktopApi?.analysis;if(H?.session_id&&e?.confirmReview){try{let t=await e.confirmReview({session_id:H.session_id,method_run_id:H.run?.run_id,decisions:ri(S,w,kt)});if(t?.status===`ok`){U(t.data),o(`finalize`),G({level:`ok`,msg:`Acceptance confirmed through backend · opening output`});return}let n=t?.message||`Could not confirm acceptance review.`;W(n),G({level:`warn`,msg:n})}catch(e){let t=e?.message||`Could not confirm acceptance review.`;W(t),G({level:`warn`,msg:t})}return}o(`finalize`),G({level:`ok`,msg:`Acceptance confirmed · opening output`})}function xt(e){G({level:`info`,msg:`${e} restore requested · failure-mode re-classification`}),K(`${e} — reopen failure-mode classification to restore.`)}async function St({report_overrides:e,counts:t,note:n}){let r=window.desktopApi?.analysis,i=t||{required:0,recommended:0};if(H?.session_id&&r?.applyReportAmendments)try{let t=await r.applyReportAmendments({session_id:H.session_id,method_run_id:H.run?.run_id,report_overrides:e,reviewer:A,reason:n||`Report completion amendment recorded from Finalize report dialog.`});if(t?.status===`ok`)return U(t.data),re(i),_(!0),G({level:`ok`,msg:`Report amendments applied through backend · ${t.data?.report_amendments?.output_path||t.data?.output_path||`MTDA output`}`}),!0;let a=t?.message||`Could not apply report amendments.`;return W(a),G({level:`warn`,msg:a}),!1}catch(e){let t=e?.message||`Could not apply report amendments.`;return W(t),G({level:`warn`,msg:t}),!1}return re(i),_(!0),G({level:`ok`,msg:`Report amendments applied`}),!0}async function Ct(){let e=window.desktopApi?.analysis;if(H?.session_id&&e?.finalizeMtda){try{let t=await e.finalizeMtda({session_id:H.session_id,method_run_id:H.run?.run_id,reviewer:A,note:O,reason_kind:te});if(t?.status===`ok`){U(t.data),N(!0);let e=t.data?.finalization?.output_path||t.data?.output_path||X.OUTPUT.mtdaVersion;G({level:`ok`,msg:`MTDA finalized by ${A||`operator`} · ${e} · amendment recorded`}),K(`MTDA finalized — ${X.OUTPUT.mtdaVersion} issued, review state locked.`);return}let n=t?.message||`Could not finalize MTDA.`;W(n),G({level:`warn`,msg:n})}catch(e){let t=e?.message||`Could not finalize MTDA.`;W(t),G({level:`warn`,msg:t})}return}N(!0),G({level:`ok`,msg:`MTDA finalized by ${A||`operator`} · ${X.OUTPUT.mtdaVersion} · amendment recorded`}),K(`MTDA finalized — ${X.OUTPUT.mtdaVersion} issued, review state locked.`)}async function wt(){let e=window.desktopApi?.analysis,t=H?.finalization?.output_path||H?.output_path||H?.run?.output_path||H?.run?.result?.output_path||``;if(H?.session_id&&e?.copyOutputPath)try{let n=await e.copyOutputPath({session_id:H.session_id});if(n?.status===`ok`)t=n.data?.path||n.data?.output_path||t;else{let e=n?.message||`Could not read MTDA output path.`;W(e),G({level:`warn`,msg:e});return}}catch(e){let t=e?.message||`Could not read MTDA output path.`;W(t),G({level:`warn`,msg:t});return}if(!t){K(`No MTDA output path is available yet.`),G({level:`warn`,msg:`Copy MTDA path requested before output exists`});return}try{await navigator.clipboard?.writeText?.(t)}catch{}K(`MTDA path copied to clipboard`),G({level:`info`,msg:`MTDA path copied to clipboard · ${t}`})}async function Tt(e){let t=window.desktopApi?.analysis,n=typeof e==`string`?e:e?.title||`Output artifact`,i=e?.id||ci(n);if(!H?.session_id&&!Mt&&!r){K(`${n} is unavailable until method output exists.`),G({level:`warn`,msg:`${n} requested before output exists`});return}if(H?.session_id&&t?.openArtifact){try{let e=await t.openArtifact({session_id:H.session_id,artifact_kind:i});if(e?.status===`ok`){let t=e.data?.path||e.data?.target_path||n;K(`${n} opened`),G({level:`info`,msg:`${n} opened · ${t}`});return}let r=e?.message||`Could not open ${n}.`;W(r),G({level:`warn`,msg:r})}catch(e){let t=e?.message||`Could not open ${n}.`;W(t),G({level:`warn`,msg:t})}return}K(`${n} — opens generated artifact`),G({level:`info`,msg:`${n} opened`})}function Et(e){o(`review`),D(e),G({level:`info`,msg:`Jumped to ${e} in review`})}let Dt=qt(()=>tr(H),[H]),Ot=qt(()=>{let e=Xn(H?.run);return e.length?e:Dt?er(Dt,{flagCockpits:!0}):r?X.FLAGGED:[]},[Dt,r,H]),kt=Ot.length?Ot:r?X.FLAGGED:[],At=qt(()=>br({session:H,report:Dt,reviewRows:kt,demoRows:r?X.FLAGGED:[]}),[Dt,H,r,kt]),Y=Number(ir(Dt).total_runs||At.length||s?.runs||(r?X.PACKAGE.runs:0));Gt(()=>{i===`review`&&kt.length&&E&&!kt.some(e=>ar(e)===E)&&D(ar(kt[0]))},[E,i,kt]);let jt=qt(()=>{let e=kt.filter(e=>!e.excluded),t=e.filter(e=>(S[ar(e)]??e.defaultCall)!==e.defaultCall).length,n=e.filter(e=>(S[ar(e)]??e.defaultCall)===`Keep`&&e.defaultCall===`Remove`&&!(w[ar(e)]||``).trim()).length,r=e.filter(e=>(S[ar(e)]??e.defaultCall)===`Remove`).length+kt.filter(e=>e.excluded).length;return{totalRuns:Y,flaggedRuns:kt.length,overrides:t,missing:n,finalRuns:Math.max(0,Y-r),amendments:0,notes:0}},[S,w,kt,Y]),Mt=H?.finalization?.output_path||H?.output_path||H?.run?.output_path||H?.run?.result?.output_path||(r?X.OUTPUT.path:``),Nt=qt(()=>ai(i,{pkg:s,method:f,mappingResolved:m,metadataResolved:g,runEnabled:We,finalized:M}),[i,s,f,m,g,We,M]),Pt=oi(i,{pkg:s,method:f,pkgSel:u,runEnabled:We,mappingResolved:m,metadataResolved:g,choosePackage:Ye,confirmMethod:Qe,startRun:_t,cancelRun:yt,confirmReview:bt,reviewBlock:jt.missing,openMapping:()=>z(!0),openLog:()=>L(!0),finalized:M,outputAvailable:!!Mt,openTestReport:()=>{Tt({id:`test_report`,title:`Test Report`})}}),Ft=si(i,{finalized:M,runEnabled:We,mappingResolved:m,metadataResolved:g});function It(e){switch(e){case`Back a step`:Lt();break;case`Next step`:Ze(1);break;case`Toggle activity log`:L(e=>!e);break;case`Toggle context detail`:ue(e=>!e);break;case`Tweaks…`:ae(!0);break;case`New method run`:Ke();break;case`Open package…`:Ye();break;case`Choose package…`:o(`setup`),Ye();break;case`Choose method…`:o(`setup`),p(null),we(Pe[0]?.id||X.METHOD.id);break;case`Edit mapping…`:f&&z(!0);break;case`Check readiness`:$e();break;case`Run method`:i===`setup`&&We&&_t();break;case`Close wizard`:qe();break;case`Open Test Report`:Tt({id:`test_report`,title:`Test Report`});break;case`Open Audit Report`:Tt({id:`audit_report`,title:`Audit Report`});break;case`Open output folder`:Tt({id:`output_folder`,title:`Output folder`});break;case`Copy MTDA path`:wt();break;case`Shortcuts`:K(`L · log   ← → or swipe · step   Esc · close`);break;case`About Method Analysis`:le(!0);break;default:{let t=`Unsupported menu action: ${e}`;W(t),G({level:`warn`,msg:t}),K(`Unsupported menu action.`)}}}function Lt(){i===`finalize`?Xe(`review`):i===`review`?Xe(`running`):i===`running`&&Xe(`setup`)}let Rt=Kt(null),[zt,Bt]=Z(0);Gt(()=>{let e=Rt.current;if(!e)return;let t=0,n=0,r=0,i=!1,a=e=>{if(Le)return;let a=e.touches?e.touches[0]:e;t=a.clientX,n=a.clientY,r=Date.now(),i=!0},o=e=>{if(!i)return;let r=e.touches?e.touches[0]:e,a=r.clientX-t,o=r.clientY-n;Math.abs(a)>24&&Math.abs(a)>Math.abs(o)*1.6&&Bt(a<0?1:-1)},s=e=>{if(!i){Bt(0);return}i=!1;let a=e.changedTouches?e.changedTouches[0]:e,o=a.clientX-t,s=a.clientY-n,c=Date.now()-r;Bt(0),Math.abs(o)>Math.abs(s)*1.6&&(Math.abs(o)>70||Math.abs(o)>42&&c<320)&&Ze(o<0?1:-1)};return e.addEventListener(`touchstart`,a,{passive:!0}),e.addEventListener(`touchmove`,o,{passive:!0}),e.addEventListener(`touchend`,s,{passive:!0}),()=>{e.removeEventListener(`touchstart`,a),e.removeEventListener(`touchmove`,o),e.removeEventListener(`touchend`,s)}});function Vt(e){if([`Package`,`Method`,`Mapping`,`Ready`].includes(e)){if(i===`setup`)return;Xe(`setup`)}else e===`Run`?Xe(`running`):[`Validate`,`Accept`].includes(e)?Xe(`review`):e===`Output`&&Xe(`finalize`)}return(0,a.jsxs)(`div`,{className:`app`,onClick:()=>P&&F(null),children:[(0,a.jsx)(Tr,{onAction:It,openMenu:P,setOpenMenu:F}),(0,a.jsx)(Dr,{states:Nt,onJump:Vt,phase:i}),(0,a.jsxs)(`div`,{className:`stage`,ref:Rt,"data-nudge":zt,children:[i===`setup`&&(0,a.jsx)(nn,{pkg:s,method:f,pkgSel:u,setPkgSel:d,backendPackageError:ge,analysisSession:H,recentPackages:_e,recentPackageLoading:ye,recentPackageError:xe,runEnabled:We,readinessStatus:Be||(We?`READY_WITH_WARNINGS`:``),methodOptions:Pe,selectedMethodId:Ce,onSelectMethodId:we,mappingSummary:f?H?.mapping:null,onChoosePackage:Je,onConfirmMethod:Qe,mappingResolved:m,metadataResolved:g,onSaveBindings:et,onSkipBindings:tt,onEditMapping:()=>z(!0),onOpenMetadata:nt,onAcceptMetadata:rt,onOpenPackageDialog:Ye,onChangePackage:Ye,onChangeMethod:()=>{p(null),we(Pe[0]?.id||X.METHOD.id)}}),i===`running`&&(0,a.jsx)(fn,{onComplete:vt,onCancel:yt,pushLog:G,backendRun:H?.run,backendMode:!!H?.session_id,demoMode:r}),i===`review`&&(0,a.jsx)(xr,{rows:kt,totalRuns:Y,decisions:S,setDecisions:C,reasons:w,setReasons:T,expanded:E,setExpanded:D,onRestore:xt,onDecisionPersist:J}),i===`finalize`&&(0,a.jsx)(Cr,{finalized:M,note:O,setNote:k,reviewer:A,setReviewer:ee,reasonKind:te,setReasonKind:j,fieldsResolved:ne,reviewSummary:jt,outputPath:Mt,runManifest:At,onFinalized:Ct,onReviewFields:()=>se(!0),onCopyPath:wt,onJumpRun:Et,onOpenArtifact:Tt})]}),(0,a.jsxs)(`div`,{className:`actionbar`,children:[i!==`setup`&&(0,a.jsx)($,{className:`ab-back`,icon:`undo`,onClick:Lt,children:`Back`}),Pt.secondary&&Pt.secondary.length>0&&(0,a.jsx)(`div`,{className:`ab-left`,children:Pt.secondary.map((e,t)=>(0,a.jsx)($,{icon:e.icon,onClick:e.onClick,variant:e.variant,children:e.label},t))}),(0,a.jsxs)(`div`,{className:`ab-status`,children:[(0,a.jsx)(`span`,{className:`ab-title`,children:Pt.title}),(0,a.jsx)(`span`,{className:`ab-hint`+(Pt.hintTone?` `+Pt.hintTone:``),children:Pt.hint})]}),(0,a.jsx)(`span`,{className:`ab-spacer`}),i===`setup`&&We&&(0,a.jsxs)(`span`,{className:`chip`,"data-tone":`warn`,children:[(0,a.jsx)(Q,{name:`check`,style:{width:12,height:12}}),Be||`READY_WITH_WARNINGS`]}),Pt.primary&&(0,a.jsx)($,{variant:Pt.primary.danger?`danger solid`:`primary`,className:`lg`,icon:Pt.primary.icon,disabled:Pt.primary.disabled,onClick:Pt.primary.onClick,title:Pt.primary.title,children:Pt.primary.label})]}),(0,a.jsx)(Or,{pkg:s,method:f,mapping:!!f,output:X.OUTPUT.mtda,open:B,onToggle:()=>ue(e=>!e),onAction:It}),(0,a.jsx)(kr,{tone:Ft.tone,state:Ft.state,logCount:Te.length,onLog:()=>L(!0)}),R&&(0,a.jsx)(an,{initial:v,mappingSummary:H?.mapping,onClose:()=>z(!1),onSave:ot,onBrowse:it,onSaveAs:at,onDirtyChange:x}),oe&&(0,a.jsx)(Fr,{onClose:()=>se(!1),onResolveAll:e=>{re(e),_(!0),G({level:`ok`,msg:`Report amendments applied`})},onApplyAmendments:St,reviewer:A}),ce&&(0,a.jsx)(l,{section:`analysis`,onClose:()=>le(!1)}),I&&(0,a.jsx)(Ar,{entries:Te,onClose:()=>L(!1)}),ie&&(0,a.jsx)(`div`,{className:`drawer-scrim`,style:{background:`transparent`},onMouseDown:()=>ae(!1),children:(0,a.jsx)(jr,{density:de,setDensity:fe,accent:pe,setAccent:me,onClose:()=>ae(!1)})}),V&&(0,a.jsx)(`div`,{className:`toast`,children:V})]})}function ai(e,{pkg:t,method:n,mappingResolved:r,metadataResolved:i,runEnabled:a,finalized:o}){let s=[`setup`,`running`,`review`,`finalize`].indexOf(e),c={};return c.Package=t?`done`:e===`setup`?`active`:`todo`,c.Method=n?`done`:e===`setup`&&t?`active`:`todo`,c.Mapping=s>0?`done`:n?r&&i?`done`:`warn`:t?`active`:`todo`,c.Ready=s>0?`done`:a?`warn`:`todo`,c.Run=e===`running`?`active`:s>1?`done`:`todo`,c.Validate=s>1?`done`:`todo`,c.Accept=e===`review`?`active`:s>2?`done`:`todo`,c.Output=e===`finalize`?o?`done`:`warn`:`todo`,c}function oi(e,t){if(e===`setup`){if(!t.pkg)return{title:`Choose package`,hint:``,primary:{label:`Choose package...`,icon:`package`,onClick:t.choosePackage}};if(!t.method)return{title:`Choose method`,hint:``,primary:{label:`Confirm method`,icon:`arrowR`,onClick:t.confirmMethod}};let e=(t.mappingResolved?``:`7 unmapped report bindings`)+(!t.mappingResolved&&!t.metadataResolved?` · `:``)+(t.metadataResolved?``:`38 recommended fields blank`);return{title:t.mappingResolved&&t.metadataResolved?`Ready to run`:`Ready · with warnings`,hint:t.mappingResolved&&t.metadataResolved?``:e+` · method runs either way.`,hintTone:`warn`,secondary:[{label:`Edit mapping…`,icon:`edit`,onClick:t.openMapping}],primary:{label:`Run method`,icon:`play`,onClick:t.startRun,disabled:!t.runEnabled}}}return e===`running`?{title:`Method execution in progress`,hint:``,secondary:[{label:`View full log`,onClick:t.openLog}],primary:{label:`Cancel run`,danger:!0,icon:`x`,onClick:t.cancelRun}}:e===`review`?{title:`One decision before output`,hint:t.reviewBlock?`${t.reviewBlock} kept run${t.reviewBlock>1?`s`:``} need a justification`:``,hintTone:t.reviewBlock?`block`:``,primary:{label:`Confirm & open output`,icon:`arrowR`,disabled:t.reviewBlock>0,onClick:t.confirmReview,title:t.reviewBlock?`Add a justification for every kept flagged run`:`Confirm acceptance and open output`}}:e===`finalize`?{title:t.finalized?`MTDA finalized`:`Output ready — draft`,hint:t.outputAvailable?``:`No analysed output is available yet.`,hintTone:t.finalized?``:`warn`,primary:{label:`Open Test Report`,icon:`report`,disabled:!t.outputAvailable,onClick:t.openTestReport}}:{title:``,hint:``}}function si(e,{finalized:t,runEnabled:n}){switch(e){case`setup`:return n?{tone:`warn`,state:`Ready with warnings · run enabled`}:{tone:``,state:`Choose workflow inputs`};case`running`:return{tone:``,state:`Method execution in progress`};case`review`:return{tone:`warn`,state:`Acceptance review pending`};case`finalize`:return{tone:t?`ok`:`warn`,state:t?`MTDA finalized`:`Output ready · draft`};default:return{tone:``,state:``}}}function ci(e){let t=String(e||``).toLowerCase();return t.includes(`test report`)?`test_report`:t.includes(`audit report`)?`audit_report`:t.includes(`folder`)?`output_folder`:t.includes(`mtda`)?`open_mtda`:t.includes(`browser`)||t.includes(`workbench`)?`workbench`:t.replace(/[^a-z0-9]+/g,`_`).replace(/^_+|_+$/g,``)}var li=class extends i.Component{constructor(e){super(e),this.state={err:null}}static getDerivedStateFromError(e){return{err:e}}componentDidCatch(e,t){console.error(`BOUNDARY`,e,t)}render(){return this.state.err?(0,a.jsx)(`div`,{style:{position:`fixed`,inset:20,zIndex:99999,background:`#fff`,border:`3px solid red`,padding:16,font:`12px monospace`,whiteSpace:`pre-wrap`,overflow:`auto`},children:`RENDER ERROR:
`+(this.state.err&&this.state.err.stack||String(this.state.err))}):this.props.children}};function ui(){return(0,a.jsx)(li,{children:(0,a.jsx)(ii,{})})}var di=`/* ============================================================
   Method Run Wizard — redesigned design system
   Evolved from the existing Fluent-flavored tokens:
   keeps status-color meanings, refines hues, fixes hierarchy.
   ============================================================ */

:root {
  /* ---- Neutrals (cool-tinted, very low chroma) ---- */
  --canvas:        #eceef1;
  --canvas-deep:   #e4e7ea;
  --surface:       #ffffff;
  --surface-2:     #f6f7f9;
  --surface-3:     #eef0f3;
  --border:        #e1e4e8;
  --border-strong: #cbd0d6;

  /* ---- Ink ---- */
  --ink:   #1b1e23;
  --ink-2: #5a626c;
  --ink-3: #8b929c;
  --ink-4: #aab0b9;

  /* ---- Accent (refined blue, keeps the learned hue) ---- */
  --accent:       #0f6cbd;
  --accent-hover: #0b5aa1;
  --accent-press: #094c89;
  --accent-soft:  #e7f1fb;
  --accent-ink:   #0a4d8c;
  --accent-ring:  rgba(15, 108, 189, 0.30);

  /* ---- Status: OK / complete (green) ---- */
  --ok-bg: #e9f3e6;  --ok-border: #b7d2a4;  --ok-ink: #38591f;  --ok-accent: #5a8636;
  /* ---- Status: warn / attention (amber) ---- */
  --warn-bg: #fbf3df; --warn-border: #e7cf90; --warn-ink: #785812; --warn-accent: #bd8814;
  /* ---- Status: error / fail (red) ---- */
  --err-bg: #fbe8e3; --err-border: #e2ab9c; --err-ink: #7f311e; --err-accent: #bf462b;
  /* ---- Status: info / active (blue) ---- */
  --info-bg: #e7f0f9; --info-border: #a7c8e4; --info-ink: #1b4c76; --info-accent: #2c6da3;
  /* ---- neutral / not reached ---- */
  --idle-bg: var(--surface); --idle-border: var(--border); --idle-ink: var(--ink-3);

  --danger:       #c4392a;
  --danger-hover: #a82e20;

  /* ---- Activity log (dark) ---- */
  --log-bg: #1c1f24; --log-panel: #23272e; --log-fg: #d4d8de; --log-ts: #767e8a;
  --log-info: #8fb6e0; --log-ok: #93c47d; --log-warn: #e3c483; --log-err: #e08a78;
  --log-now: #ffffff; --log-border: #343a42;

  /* ---- Type ---- */
  --font: "Segoe UI Variable", "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: "Cascadia Code", "JetBrains Mono", ui-monospace, "SF Mono", Consolas, monospace;

  --t-caps: 10.5px;
  --t-xs: 12px;
  --t-sm: 13px;
  --t-md: 14px;
  --t-lg: 15.5px;
  --t-h2: 17px;
  --t-h1: 22px;
  --t-pct: 33px;

  /* ---- Radius ---- */
  --r-sm: 4px;
  --r-md: 6px;
  --r-lg: 9px;
  --r-pill: 999px;

  /* ---- Elevation ---- */
  --sh-1: 0 1px 2px rgba(20, 24, 31, 0.05), 0 1px 1px rgba(20, 24, 31, 0.04);
  --sh-2: 0 2px 6px rgba(20, 24, 31, 0.07), 0 1px 2px rgba(20, 24, 31, 0.05);
  --sh-3: 0 8px 28px rgba(20, 24, 31, 0.16), 0 2px 8px rgba(20, 24, 31, 0.10);
  --sh-pop: 0 18px 50px rgba(15, 22, 33, 0.30), 0 4px 14px rgba(15, 22, 33, 0.18);

  /* ---- Density (overridden by Tweaks) ---- */
  --row-h: 38px;
  --pad-card: 16px;
  --gap: 12px;
}

:root[data-density="dense"]      { --row-h: 32px; --pad-card: 12px; --gap: 9px;  --t-sm: 12.5px; }
:root[data-density="comfortable"]{ --row-h: 44px; --pad-card: 20px; --gap: 16px; }

* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body {
  font-family: var(--font);
  font-size: var(--t-sm);
  color: var(--ink);
  background: var(--canvas-deep);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
button, input, select, textarea { font-family: inherit; }
::selection { background: var(--accent-ring); }

/* thin, calm scrollbars to read as a native app */
*::-webkit-scrollbar { width: 11px; height: 11px; }
*::-webkit-scrollbar-thumb { background: #c2c8cf; border-radius: 8px; border: 3px solid transparent; background-clip: content-box; }
*::-webkit-scrollbar-thumb:hover { background: #aab0b9; background-clip: content-box; }
*::-webkit-scrollbar-track { background: transparent; }

/* ============================================================ APP FRAME */
#root { height: 100%; }
.app {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--canvas);
  overflow: hidden;
  position: relative;
}

/* ---- Menu bar ---- */
.menubar {
  height: 30px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 0 10px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  user-select: none;
  position: relative;
  z-index: 40;
}
.menubar-title {
  flex: none;
  font-size: var(--t-xs);
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0;
  white-space: nowrap;
  padding: 0 4px;
}
.menubar-menus {
  display: flex;
  align-items: center;
  gap: 2px;
}
.menu-item {
  font-size: var(--t-xs);
  color: var(--ink-2);
  padding: 5px 9px;
  border-radius: var(--r-sm);
  cursor: default;
  position: relative;
}
.menu-item:hover, .menu-item.open { background: var(--surface-3); color: var(--ink); }
.menubar-spacer { flex: 1; }
.menubar-windowctrls { margin-left: 0; }
.menu-pop {
  position: absolute;
  top: 28px;
  left: 4px;
  min-width: 216px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--r-md);
  box-shadow: var(--sh-3);
  padding: 5px;
  z-index: 60;
}
.menu-pop button {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: none;
  border: 0;
  text-align: left;
  font-size: var(--t-sm);
  color: var(--ink);
  padding: 7px 9px;
  border-radius: var(--r-sm);
  cursor: pointer;
}
.menu-pop button:hover { background: var(--accent-soft); color: var(--accent-ink); }
.menu-pop button:disabled {
  color: var(--ink-3);
  cursor: default;
  opacity: .72;
}
.menu-pop button:disabled:hover { background: none; color: var(--ink-3); }
.menu-pop button .k { color: var(--ink-3); font-size: var(--t-xs); font-family: var(--mono); }
.menu-pop .sep { height: 1px; background: var(--border); margin: 5px 4px; }

/* ============================================================ PROCESS SPINE (clean connected stepper) */
.spine {
  flex: none;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 12px 30px 13px;
  position: relative;
  z-index: 20;
}
.spine-track { display: flex; align-items: flex-start; }
.step {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  position: relative;
  cursor: pointer;
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
}
.step .rail { position: absolute; top: 13px; height: 2px; background: var(--border); z-index: 0; }
.step .rail-l { left: 0; right: 50%; }
.step .rail-r { left: 50%; right: 0; }
.step .rail[data-on="true"] { background: var(--ok-accent); }
.step .node {
  position: relative; z-index: 1;
  flex: none;
  width: 26px; height: 26px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 11px; font-weight: 700;
  border: 1.5px solid var(--border-strong);
  background: var(--surface);
  color: var(--ink-3);
  transition: all .18s ease;
}
.step .lbl { font-size: var(--t-xs); color: var(--ink-3); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; transition: color .18s; }

.step[data-state="done"] .node  { background: var(--ok-accent); border-color: var(--ok-accent); color: #fff; }
.step[data-state="done"] .lbl   { color: var(--ink-2); }
.step[data-state="active"] .node { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: 0 0 0 4px var(--accent-ring); }
.step[data-state="active"] .lbl  { color: var(--accent-ink); font-weight: 700; }
.step[data-state="warn"] .node  { background: var(--warn-accent); border-color: var(--warn-accent); color: #fff; }
.step[data-state="warn"] .lbl   { color: var(--warn-ink); font-weight: 700; }
.step[data-state="error"] .node { background: var(--danger); border-color: var(--danger); color: #fff; }
.step[data-state="error"] .lbl  { color: var(--err-ink); }
.step[data-state="todo"]:hover .node { border-color: var(--ink-3); color: var(--ink-2); }
.step:hover .lbl { color: var(--ink); }

/* ============================================================ SPOTLIGHT (content) */
.stage {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 22px 26px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}
.spotlight {
  width: 100%;
  max-width: 1180px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-head { display: flex; flex-direction: column; gap: 3px; }
.page-head h1 { font-size: var(--t-h1); font-weight: 700; margin: 0; letter-spacing: -0.01em; }
.page-head .sub { font-size: var(--t-sm); color: var(--ink-2); }
.page-head .sub b { color: var(--ink); font-weight: 600; }

/* ---- Generic card ---- */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--sh-1); }
.card-pad { padding: var(--pad-card); }

/* ---- Input summary tiles row ---- */
.inputs-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.input-tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 13px 15px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  box-shadow: var(--sh-1);
  position: relative;
  transition: border-color .15s, box-shadow .15s;
}
.input-tile .tile-k { font-size: var(--t-caps); letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; display: flex; align-items: center; gap: 7px; }
.input-tile .tile-v { font-size: var(--t-md); font-weight: 600; color: var(--ink); line-height: 1.25; }
.input-tile .tile-meta { font-size: var(--t-xs); color: var(--ink-2); }
.input-tile .tile-link { font-size: var(--t-xs); color: var(--accent); font-weight: 600; cursor: pointer; margin-top: 1px; width: fit-content; }
.input-tile .tile-link:hover { text-decoration: underline; }
.input-tile[data-done="true"] { background: linear-gradient(0deg, var(--ok-bg), var(--ok-bg)); border-color: var(--ok-border); }
.input-tile[data-done="true"] .tile-k { color: var(--ok-ink); }
.input-tile[data-warn="true"] { background: var(--warn-bg); border-color: var(--warn-border); }
.input-tile[data-warn="true"] .tile-k { color: var(--warn-ink); }
.input-tile[data-pending="true"] .tile-v { color: var(--ink-3); font-weight: 500; }
.tile-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ink-4); }
.input-tile[data-done="true"] .tile-dot { background: var(--ok-accent); }
.input-tile[data-warn="true"] .tile-dot { background: var(--warn-accent); }

/* ============================================================ BUTTONS */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  font-size: var(--t-sm); font-weight: 600;
  padding: 8px 15px;
  border-radius: var(--r-md);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  transition: background .14s, border-color .14s, box-shadow .14s, color .14s;
  user-select: none;
}
.btn:hover { background: var(--surface-2); border-color: var(--ink-3); }
.btn:active { background: var(--surface-3); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; box-shadow: var(--sh-1); }
.btn.primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.btn.primary:active { background: var(--accent-press); }
.btn.danger { background: var(--surface); border-color: var(--err-border); color: var(--danger); }
.btn.danger:hover { background: var(--err-bg); border-color: var(--danger); }
.btn.danger.solid { background: var(--danger); border-color: var(--danger); color: #fff; }
.btn.danger.solid:hover { background: var(--danger-hover); }
.btn.ghost { border-color: transparent; background: transparent; color: var(--accent); padding-left: 9px; padding-right: 9px; }
.btn.ghost:hover { background: var(--accent-soft); }
.btn.sm { padding: 5px 11px; font-size: var(--t-xs); }
.btn.lg { padding: 10px 20px; font-size: var(--t-md); }
.btn:disabled { opacity: .5; cursor: not-allowed; pointer-events: none; }
.btn .ic { width: 15px; height: 15px; flex: none; }

/* ============================================================ TASK CARD */
.task {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  box-shadow: var(--sh-1);
  overflow: hidden;
}
.task-head { display: flex; align-items: center; gap: 11px; padding: 13px 16px; border-bottom: 1px solid var(--border); }
.task-head.bare { border-bottom: 0; }
.task-flag {
  font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; font-weight: 700;
  padding: 3px 8px; border-radius: var(--r-sm); white-space: nowrap; flex: none;
  background: var(--warn-bg); color: var(--warn-ink); border: 1px solid var(--warn-border);
}
.task-flag[data-tone="info"] { background: var(--info-bg); color: var(--info-ink); border-color: var(--info-border); }
.task-flag[data-tone="ok"] { background: var(--ok-bg); color: var(--ok-ink); border-color: var(--ok-border); }
.task-title { font-size: var(--t-lg); font-weight: 700; }
.task-body { padding: 16px; }

/* ============================================================ ACTION BAR (single source of truth) */
.actionbar {
  flex: none;
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 11px 26px;
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 15;
}
.actionbar .ab-status { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.actionbar .ab-title { font-size: var(--t-sm); font-weight: 700; color: var(--ink); }
.actionbar .ab-hint { font-size: var(--t-xs); color: var(--ink-2); }
.actionbar .ab-hint.block { color: var(--err-ink); }
.actionbar .ab-hint.warn { color: var(--warn-ink); }
.actionbar .ab-spacer { flex: 1; }
.actionbar .ab-left { display: flex; gap: 8px; }

/* ============================================================ CONTEXT + STATUS BARS */
.contextbar {
  flex: none;
  height: 30px;
  background: var(--surface-2);
  border-top: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 26px;
  gap: 8px;
  font-size: var(--t-xs);
  color: var(--ink-2);
  cursor: pointer;
  user-select: none;
}
.contextbar:hover { background: var(--surface-3); }
.contextbar .cx { display: flex; align-items: center; gap: 6px; }
.contextbar .cx b { color: var(--ink); font-weight: 600; }
.contextbar .cx-warn { color: var(--warn-ink); }
.contextbar .dot { color: var(--ink-4); }
.contextbar .chev { margin-left: auto; color: var(--ink-3); transition: transform .18s; }
.contextbar.open .chev { transform: rotate(180deg); }
.context-detail {
  flex: none;
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 12px 26px;
  display: grid;
  grid-template-columns: max-content 1fr max-content;
  gap: 8px 18px;
  align-items: center;
  font-size: var(--t-sm);
}
.context-detail .cd-k { font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; }
.context-detail .cd-v { color: var(--ink); font-weight: 500; }
.context-detail .cd-actions { grid-column: 3; grid-row: 1 / span 4; display: flex; flex-direction: column; gap: 7px; align-self: start; }

.statusbar {
  flex: none;
  height: 26px;
  background: var(--accent);
  color: #fff;
  display: flex; align-items: center;
  padding: 0 14px 0 12px;
  gap: 9px;
  font-size: var(--t-xs);
}
.statusbar[data-tone="warn"] { background: var(--warn-accent); }
.statusbar[data-tone="error"] { background: var(--danger); }
.statusbar[data-tone="ok"] { background: var(--ok-accent); }
.statusbar .sb-dot { width: 7px; height: 7px; border-radius: 50%; background: rgba(255,255,255,.9); }
.statusbar .sb-spacer { flex: 1; }
.statusbar .sb-link { color: #fff; opacity: .92; cursor: pointer; }
.statusbar .sb-link:hover { opacity: 1; text-decoration: underline; }
.statusbar .sb-ver { opacity: .8; font-family: var(--mono); }

/* ============================================================ STATUS CHIP */
.chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: var(--t-xs); font-weight: 600;
  padding: 2px 8px; border-radius: var(--r-pill);
  border: 1px solid var(--border); background: var(--surface-2); color: var(--ink-2);
  white-space: nowrap;
}
.chip .cdot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; opacity: .85; }
.chip[data-tone="ok"]   { background: var(--ok-bg);   color: var(--ok-ink);   border-color: var(--ok-border); }
.chip[data-tone="warn"] { background: var(--warn-bg); color: var(--warn-ink); border-color: var(--warn-border); }
.chip[data-tone="err"]  { background: var(--err-bg);  color: var(--err-ink);  border-color: var(--err-border); }
.chip[data-tone="info"] { background: var(--info-bg); color: var(--info-ink); border-color: var(--info-border); }
.chip[data-tone="idle"] { background: var(--surface-2); color: var(--ink-3); border-color: var(--border); }

/* banner */
.banner {
  display: flex; align-items: flex-start; gap: 11px;
  padding: 11px 14px;
  border-radius: var(--r-md);
  border: 1px solid var(--warn-border);
  background: var(--warn-bg);
  border-left: 4px solid var(--warn-accent);
}
.banner[data-tone="ok"]   { border-color: var(--ok-border);   background: var(--ok-bg);   border-left-color: var(--ok-accent); }
.banner[data-tone="info"] { border-color: var(--info-border); background: var(--info-bg); border-left-color: var(--info-accent); }
.banner[data-tone="err"]  { border-color: var(--err-border);  background: var(--err-bg);  border-left-color: var(--danger); }
.banner .b-ic { flex: none; width: 17px; height: 17px; margin-top: 1px; }
.banner .b-txt { font-size: var(--t-sm); line-height: 1.45; }
.banner .b-txt b { font-weight: 700; }
.banner[data-tone="warn"] .b-txt { color: var(--warn-ink); }
.banner[data-tone="ok"] .b-txt { color: var(--ok-ink); }
.banner[data-tone="info"] .b-txt { color: var(--info-ink); }
.banner[data-tone="err"] .b-txt { color: var(--err-ink); }

/* ============================================================ TABLES */
.tbl { width: 100%; border-collapse: collapse; font-size: var(--t-sm); }
.tbl thead th {
  text-align: left; font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase;
  color: var(--ink-3); font-weight: 700; padding: 9px 12px;
  background: var(--surface-2); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 1;
}
.tbl tbody td { padding: 0 12px; height: var(--row-h); border-bottom: 1px solid var(--border); color: var(--ink); vertical-align: middle; }
.tbl tbody tr:last-child td { border-bottom: 0; }
.tbl tbody tr.click { cursor: pointer; }
.tbl tbody tr.click:hover { background: var(--surface-2); }
.tbl .mono { font-family: var(--mono); font-size: var(--t-xs); }
.tbl .muted { color: var(--ink-3); }

.field-input {
  width: 100%;
  font-size: var(--t-sm);
  padding: 7px 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--r-sm);
  background: var(--surface);
  color: var(--ink);
  outline: none;
  transition: border-color .14s, box-shadow .14s;
}
.field-input::placeholder { color: var(--ink-4); }
.field-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-ring); }
textarea.field-input { resize: vertical; min-height: 56px; line-height: 1.5; }
select.field-input { cursor: pointer; appearance: none; background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M2 4l4 4 4-4' stroke='%235a626c' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>"); background-repeat: no-repeat; background-position: right 10px center; padding-right: 30px; }

.label-caps { font-size: var(--t-caps); letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; }

/* ============================================================ MODAL / DIALOG */
.scrim {
  position: absolute; inset: 0;
  background: rgba(20, 26, 33, 0.42);
  backdrop-filter: none;
  display: grid; place-items: center;
  z-index: 80;
  will-change: auto;
}
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.dialog {
  width: min(1080px, 94vw);
  max-height: 90%;
  background: var(--canvas);
  border: 1px solid var(--border-strong);
  border-radius: var(--r-lg);
  box-shadow: var(--sh-pop);
  display: flex; flex-direction: column;
  overflow: hidden;
  animation: pop .16s cubic-bezier(.2,.8,.3,1);
  will-change: auto;
}
@keyframes pop { from { transform: translateY(8px) scale(.99); } to { transform: none; } }
.dialog-head { background: var(--surface); border-bottom: 1px solid var(--border); padding: 15px 20px; display: flex; align-items: center; gap: 14px; }
.dialog-head h2 { margin: 0; font-size: var(--t-h2); font-weight: 700; }
.dialog-head .dh-sub { font-size: var(--t-xs); color: var(--ink-2); }
.dialog-body { flex: 1; min-height: 0; overflow: auto; padding: 16px 20px; }
.dialog-foot { background: var(--surface); border-top: 1px solid var(--border); padding: 12px 20px; display: flex; align-items: center; gap: 10px; }

/* segmented control */
.seg { display: inline-flex; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--r-md); padding: 2px; gap: 2px; }
.seg button { border: 0; background: none; font-size: var(--t-xs); font-weight: 600; color: var(--ink-2); padding: 5px 12px; border-radius: 4px; cursor: pointer; }
.seg button.on { background: var(--surface); color: var(--ink); box-shadow: var(--sh-1); }
.seg button:hover:not(.on) { color: var(--ink); }

/* ============================================================ UTIL */
.row { display: flex; align-items: center; gap: 10px; }
.col { display: flex; flex-direction: column; }
.spacer { flex: 1; }
.mono { font-family: var(--mono); }
.muted { color: var(--ink-2); }
.muted-3 { color: var(--ink-3); }
.fade-in { animation: riseIn .2s ease; }
@keyframes riseIn { from { transform: translateY(6px); } to { transform: none; } }
.no-flicker-overlay .dialog { animation: none !important; transform: none !important; }
.no-flicker-overlay .fade-in { animation: none !important; }
.placeholder-img {
  background-color: var(--surface-2);
  background-image: repeating-linear-gradient(45deg, transparent, transparent 7px, rgba(0,0,0,.025) 7px, rgba(0,0,0,.025) 14px);
  border: 1px dashed var(--border-strong);
  border-radius: var(--r-md);
  display: grid; place-items: center;
  color: var(--ink-3); font-family: var(--mono); font-size: var(--t-xs);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}

/* ============================================================
   Screen + component styles (layer 2)
   ============================================================ */

/* ---- Confidence meter ---- */
.conf { display: flex; flex-direction: column; gap: 3px; }
.conf-bars { display: flex; gap: 2px; }
.conf-bars span { width: 12px; height: 5px; border-radius: 1px; }
.conf-label { font-size: var(--t-xs); font-weight: 700; white-space: nowrap; }
.conf { align-items: flex-end; flex: none; }

/* ---- Sparkline ---- */
.spark { display: flex; flex-direction: column; gap: 5px; width: min(100%, 420px); }
.spark-cap { color: var(--ink-3); }
.spark-svg { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-md); display: block; max-width: 100%; height: auto; }
.plot-gap-body {
  min-height: 96px;
  display: grid;
  place-items: center;
  padding: 12px;
  color: var(--ink-3);
  background: var(--surface-2);
  border: 1px dashed var(--border);
  border-radius: var(--r-md);
  text-align: center;
}

/* ---- Metric tile ---- */
.metric { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 9px 11px; display: flex; flex-direction: column; gap: 2px; }
.metric-k { color: var(--ink-3); }
.metric-v { font-size: var(--t-lg); font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }
.metric[data-tone="warn"] .metric-v { color: var(--warn-ink); }
.metric[data-tone="err"] .metric-v { color: var(--err-ink); }
.metric-sub { font-size: var(--t-xs); color: var(--ink-3); }

/* ============================================================ SETUP: package picker */
.pick-list { display: flex; flex-direction: column; }
.pick {
  display: flex; align-items: center; gap: 14px;
  padding: 13px 15px; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background .12s;
}
.pick:last-child { border-bottom: 0; }
.pick:hover { background: var(--surface-2); }
.pick.sel { background: var(--accent-soft); }
.pick .p-ic { width: 34px; height: 34px; border-radius: var(--r-md); background: var(--surface-3); display: grid; place-items: center; color: var(--ink-2); flex: none; }
.pick.sel .p-ic { background: var(--accent); color: #fff; }
.pick .p-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.pick .p-name { font-size: var(--t-md); font-weight: 600; }
.pick .p-meta { font-size: var(--t-xs); color: var(--ink-2); }
.pick .p-runs { font-size: var(--t-xs); color: var(--ink-3); font-family: var(--mono); flex: none; }
.pick .p-check { flex: none; color: var(--accent); opacity: 0; }
.pick.sel .p-check { opacity: 1; }

/* method detail */
.method-detail { display: grid; grid-template-columns: 1.4fr 1fr; gap: 0; }
.method-detail .md-main { padding: 16px; border-right: 1px solid var(--border); }
.method-detail .md-side { padding: 16px; background: var(--surface-2); display: flex; flex-direction: column; gap: 12px; }
.md-stat { display: flex; flex-direction: column; gap: 1px; }
.md-stat .v { font-size: var(--t-h2); font-weight: 700; font-variant-numeric: tabular-nums; }
.md-stat .k { font-size: var(--t-xs); color: var(--ink-2); }

.kv-line { display: flex; gap: 8px; font-size: var(--t-sm); padding: 5px 0; }
.kv-line .kk { color: var(--ink-3); width: 92px; flex: none; }
.kv-line .vv { color: var(--ink); font-weight: 500; }

.bound-chips { display: flex; flex-wrap: wrap; gap: 7px; }

/* ============================================================ MAPPING EDITOR */
.map-grid { display: grid; grid-template-columns: minmax(190px, 300px) minmax(0, 1fr); gap: 12px; align-items: start; min-height: 0; }
@media (max-width: 560px) { .map-grid { grid-template-columns: 1fr; } }

/* ---- rail: slim spine that floats over the workspace; persists when .open, reopens on hover ---- */
.map-repair { position: relative; padding-left: 50px; flex: 1; min-height: 0; display: flex; }
.workspace-full { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.rail-float { position: absolute; left: 0; top: 0; bottom: 0; width: 40px; z-index: 6; }

/* collapsed strip — plain bar, click or hover reopens; no per-item controls */
.rail-strip { height: 100%; width: 100%; display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 12px 0; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--sh-1); cursor: pointer; transition: opacity .14s ease, background .12s; font: inherit; }
.rail-strip:hover { background: var(--surface-2); }
.rail-strip-hint { color: var(--ink-3); flex: none; }
.rail-strip-label { writing-mode: vertical-rl; transform: rotate(180deg); font-size: var(--t-caps); letter-spacing: .12em; text-transform: uppercase; font-weight: 700; color: var(--ink-3); margin: 2px 0; }
.rail-strip-cap { margin-top: auto; font-size: 11px; font-weight: 800; border-radius: var(--r-pill); min-width: 22px; height: 20px; padding: 0 6px; display: grid; place-items: center; font-variant-numeric: tabular-nums; }
.rail-strip-cap[data-tone="warn"] { color: var(--warn-ink); background: var(--warn-bg); border: 1px solid var(--warn-border); }
.rail-strip-cap[data-tone="ok"] { color: var(--ok-accent); background: var(--ok-bg); border: 1px solid var(--ok-border); }

/* expanded floating panel */
.rail-panel { position: absolute; left: 0; top: 0; bottom: 0; width: 296px; overflow: hidden; display: flex; flex-direction: column;
  background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-lg);
  box-shadow: var(--sh-3); opacity: 0; transform: translateX(-10px) scale(.99); transform-origin: left center; pointer-events: none; transition: opacity .16s ease, transform .16s cubic-bezier(.2,.8,.3,1); }
.rail-float.open .rail-panel { opacity: 1; transform: none; pointer-events: auto; }
.rail-float.open .rail-strip { opacity: 0; pointer-events: none; }
.rail-panel .bind-list { flex: 1; min-height: 0; overflow: auto; }

.bind-rail-head { display: flex; align-items: center; gap: 8px; padding: 11px 10px 11px 15px; flex: none; background: var(--surface-2); border-bottom: 1px solid var(--border); }
.bind-rail-head .brh-t { font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; font-weight: 700; display: flex; align-items: center; gap: 7px; }
.bind-rail-head .brh-t[data-tone="warn"] { color: var(--warn-ink); }
.bind-rail-head .brh-t[data-tone="ok"] { color: var(--ok-ink); }
.bind-rail-head .brh-t[data-tone="ok"] svg { color: var(--ok-accent); }
.brh-close { margin-left: auto; flex: none; width: 24px; height: 24px; display: grid; place-items: center; border: 1px solid var(--border); border-radius: var(--r-sm); background: var(--surface); color: var(--ink-3); cursor: pointer; }
.brh-close:hover { background: var(--surface-3); color: var(--ink); border-color: var(--border-strong); }

.map-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.sumtile { border: 1px solid var(--border); border-radius: var(--r-md); padding: 10px 12px; background: var(--surface); display: flex; flex-direction: column; gap: 3px; }
.sumtile .st-k { font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase; font-weight: 700; color: var(--ink-3); }
.sumtile .st-v { font-size: var(--t-h2); font-weight: 700; font-variant-numeric: tabular-nums; }
.sumtile .st-sub { font-size: var(--t-xs); color: var(--ink-3); }
.sumtile[data-tone="ok"]   { background: var(--ok-bg); border-color: var(--ok-border); }
.sumtile[data-tone="ok"] .st-k, .sumtile[data-tone="ok"] .st-v { color: var(--ok-ink); }
.sumtile[data-tone="warn"] { background: var(--warn-bg); border-color: var(--warn-border); }
.sumtile[data-tone="warn"] .st-k, .sumtile[data-tone="warn"] .st-v { color: var(--warn-ink); }

/* binding list */
.bind-list { display: flex; flex-direction: column; overflow: auto; }
.bind-group-h { font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; font-weight: 700; color: var(--ink-3); padding: 12px 14px 6px; display: flex; align-items: center; gap: 8px; position: sticky; top: 0; background: var(--surface); z-index: 2; }
.bind-group-h .gcount { background: var(--surface-3); border-radius: var(--r-pill); padding: 1px 7px; font-size: 10px; }
.bind {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  gap: 11px; align-items: center;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background .12s; position: relative;
}
.bind::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: transparent; }
.bind:hover { background: var(--surface-2); }
.bind.sel { background: var(--accent-soft); }
.bind.sel::before { background: var(--accent); }
.bind .b-state { width: 12px; height: 12px; border-radius: 50%; flex: none; }
.bind .b-state[data-s="matched"]  { background: var(--ok-accent); }
.bind .b-state[data-s="manual"]   { background: var(--ok-accent); box-shadow: inset 0 0 0 2px var(--surface), 0 0 0 1.5px var(--ok-accent); }
.bind .b-state[data-s="bound"]    { background: var(--ok-accent); }
.bind .b-state[data-s="warning"]  { background: var(--warn-accent); }
.bind .b-state[data-s="ambiguous"]{ background: var(--info-accent); }
.bind .b-state[data-s="gap"]      { background: var(--surface); border: 2px solid var(--warn-border); }
.bind .b-state[data-s="unmapped"] { background: var(--surface); border: 2px solid var(--err-border); }
.bind .b-state[data-s="blocker"]  { background: var(--surface); border: 2px solid var(--err-border); }
.bind .b-main { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bind .b-input { font-family: var(--mono); font-size: var(--t-xs); color: var(--ink); font-weight: 600; }
.bind .b-bind { font-size: var(--t-xs); color: var(--ink-2); display: flex; align-items: center; gap: 5px; }
.bind .b-bind .arrow { color: var(--ink-4); }
.bind .b-bind .val { font-family: var(--mono); color: var(--ok-ink); }
.bind .b-bind .none { color: var(--err-ink); font-style: italic; }
.bind .b-bind .amb { color: var(--info-ink); font-style: italic; }
.bind .b-right { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; flex: none; }

/* resolution panel — workspace */
.resolve { display: flex; flex-direction: column; min-height: 0; height: 100%; }
.resolve-head { padding: 15px 18px 14px; border-bottom: 1px solid var(--border); background: var(--surface-2); position: relative; }
.resolve-head::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; }
.resolve-head[data-tone="ok"]::before { background: var(--ok-accent); }
.resolve-head[data-tone="info"]::before { background: var(--info-accent); }
.resolve-head[data-tone="warn"]::before { background: var(--warn-accent); }
.resolve-head[data-tone="err"]::before { background: var(--danger); }
.resolve-head .rh-line { display: flex; align-items: center; gap: 9px; }
.resolve-head .r-input { font-family: var(--mono); font-size: var(--t-h2); font-weight: 800; letter-spacing: -0.01em; color: var(--ink); }
.resolve-head .rh-req { margin-left: auto; font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); }
.resolve-head .rh-req[data-req="required"] { color: var(--info-ink); }
.resolve-head .r-desc { font-size: var(--t-xs); color: var(--ink-2); margin-top: 5px; line-height: 1.5; }
.resolve-head .rh-state { font-size: var(--t-sm); color: var(--ink-2); margin-top: 8px; }
.resolve-head .rh-bound { color: var(--ok-ink); font-weight: 700; background: var(--ok-bg); border: 1px solid var(--ok-border); border-radius: var(--r-sm); padding: 1px 7px; }
.resolve-head .rh-via { color: var(--ink-3); }
.resolve-body { padding: 14px 18px; display: flex; flex-direction: column; gap: 10px; overflow: auto; flex: 1; min-height: 0; }
.resolve-body > .label-caps { color: var(--ink-3); }

/* candidate source cards */
.cand {
  position: relative; border: 1px solid var(--border); border-radius: var(--r-md);
  padding: 12px 14px; display: flex; flex-direction: column; gap: 9px; background: var(--surface);
  cursor: pointer; overflow: hidden; transition: border-color .14s, box-shadow .14s;
}
.cand::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: transparent; transition: background .14s; }
.cand:hover { border-color: var(--accent); box-shadow: var(--sh-2); }
.cand:hover .cand-cta { color: var(--accent); }
.cand.applied { border-color: var(--ok-border); background: var(--ok-bg); cursor: default; }
.cand.applied::before { background: var(--ok-accent); }
.cand-top { display: flex; align-items: flex-start; gap: 12px; }
.cand-top .c-src { font-family: var(--mono); font-size: var(--t-sm); font-weight: 700; color: var(--ink); word-break: break-all; }
.cand-meta { display: flex; align-items: center; gap: 8px; font-size: var(--t-xs); color: var(--ink-2); margin-top: 4px; }
.cand-meta .cm-sep { color: var(--ink-4); }
.cand-meta .ex { font-family: var(--mono); background: var(--surface-2); border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; color: var(--ink-2); }
.cand.applied .cand-meta .ex { background: rgba(255,255,255,.5); }
.cand-foot { display: flex; align-items: center; gap: 10px; justify-content: space-between; padding-top: 9px; border-top: 1px dashed var(--border); }
.cand.applied .cand-foot { border-top-color: var(--ok-border); }
.cand-reason { font-size: var(--t-xs); color: var(--ink-3); font-style: italic; flex: 1; min-width: 0; }
.cand-cta { flex: none; display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-xs); font-weight: 700; color: var(--ink-3); transition: color .14s; }
.cand-applied { flex: none; display: inline-flex; align-items: center; gap: 5px; font-size: var(--t-xs); font-weight: 700; color: var(--ok-ink); }

/* custom binding folded into a disclosure → dropdown of package variables */
.custom-details { font-size: var(--t-xs); border-top: 1px solid var(--border); padding-top: 11px; margin-top: 2px; }
.custom-details > summary { cursor: pointer; color: var(--accent); font-weight: 600; list-style: none; padding: 3px 0; user-select: none; display: inline-flex; align-items: center; gap: 5px; }
.custom-details > summary::-webkit-details-marker { display: none; }
.custom-details > summary::before { content: "+"; font-weight: 700; }
.custom-details[open] > summary::before { content: "−"; }
.custom-details > summary:hover { text-decoration: underline; }
.custom-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
.custom-hint { font-size: 11px; color: var(--ink-4); margin-top: 7px; line-height: 1.4; }

.clear-link { background: none; border: 0; padding: 2px 0; font: inherit; font-size: var(--t-xs); color: var(--danger); cursor: pointer; align-self: flex-start; }
.clear-link:hover { text-decoration: underline; }

/* resolution report */
.rr-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.rr-stat { border: 1px solid var(--border); border-radius: var(--r-md); padding: 11px 14px; background: var(--surface); display: flex; flex-direction: column; gap: 2px; position: relative; overflow: hidden; }
.rr-stat::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--ink-4); }
.rr-stat[data-tone="ok"]::before { background: var(--ok-accent); }
.rr-stat[data-tone="warn"]::before { background: var(--warn-accent); }
.rr-stat[data-tone="err"]::before { background: var(--danger); }
.rr-stat[data-tone="info"]::before { background: var(--info-accent); }
.rr-stat[data-tone="idle"]::before { background: var(--border-strong); }
.rr-v { font-size: var(--t-h1); font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1; color: var(--ink); }
.rr-v .rr-tot { font-size: var(--t-md); font-weight: 600; color: var(--ink-3); }
.rr-k { font-size: var(--t-xs); color: var(--ink-2); }
.rr-tbl td { vertical-align: middle; }

/* typed field — format chip + float unit (mirrors MTDP typed schema) */
.type-chip { font-size: 10px; font-weight: 600; color: var(--ink-3); background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--r-sm); padding: 1px 6px; white-space: nowrap; }
.float-row { display: flex; gap: 8px; }
.float-row .field-input[type="number"] { flex: 1; min-width: 0; }
.float-unit { flex: none; width: 92px; }
.float-unit-static { flex: none; align-self: center; color: var(--ink-2); font-size: var(--t-sm); padding: 0 4px; }

/* bound-inputs summary — collapsed by default (the decision is about UNbound fields) */
.bound-summary { font-size: var(--t-sm); }
.bound-summary > summary { cursor: pointer; list-style: none; display: inline-flex; align-items: center; gap: 8px; color: var(--ok-ink); font-weight: 600; padding: 3px 0; user-select: none; }
.bound-summary > summary::-webkit-details-marker { display: none; }
.bound-summary > summary .bs-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok-accent); flex: none; }
.bound-summary > summary::after { content: "show"; margin-left: 4px; font-size: 11px; font-weight: 600; color: var(--ink-3); text-transform: none; }
.bound-summary[open] > summary::after { content: "hide"; }
.bound-summary > summary:hover { text-decoration: underline; }

/* segmented tabs for mapping */
.map-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); }
.map-tab { font-size: var(--t-sm); font-weight: 600; color: var(--ink-2); padding: 9px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.map-tab:hover { color: var(--ink); }
.map-tab.on { color: var(--accent-ink); border-bottom-color: var(--accent); }

/* ============================================================ RUNNING */
.run-head { display: flex; align-items: flex-start; gap: 20px; }
.run-head .rh-main { flex: 1; min-width: 0; }
.run-phase { font-size: var(--t-h2); font-weight: 700; }
.run-meta { font-size: var(--t-xs); color: var(--ink-2); margin-top: 3px; font-family: var(--mono); }
.run-pct { font-size: var(--t-pct); font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1; color: var(--accent-ink); letter-spacing: -0.02em; }
.progress { height: 8px; background: var(--surface-3); border-radius: var(--r-pill); overflow: hidden; margin-top: 4px; }
.progress > div { height: 100%; background: linear-gradient(90deg, var(--accent), #2b86d6); border-radius: var(--r-pill); transition: width .4s ease; }

.stage-strip { display: grid; grid-template-columns: repeat(6, 1fr); gap: 7px; }
.stagebox {
  border: 1px solid var(--border); border-radius: var(--r-sm); padding: 8px 6px;
  text-align: center; font-size: var(--t-xs); font-weight: 600; color: var(--ink-3);
  background: var(--surface); position: relative; transition: all .25s;
}
.stagebox[data-s="done"]   { background: var(--ok-bg); border-color: var(--ok-border); color: var(--ok-ink); }
.stagebox[data-s="active"] { background: var(--info-bg); border-color: var(--info-accent); color: var(--info-ink); box-shadow: 0 0 0 2px var(--accent-ring); }
.stagebox[data-s="active"]::after { content: ""; position: absolute; left: 0; right: 0; bottom: -1px; height: 2px; background: var(--accent); animation: pulsebar 1.1s ease-in-out infinite; }
@keyframes pulsebar { 0%,100% { opacity: .4; } 50% { opacity: 1; } }

.run-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.run-stat { border: 1px solid var(--border); border-radius: var(--r-md); padding: 10px 13px; background: var(--surface-2); }
.run-stat .k { font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; }
.run-stat .v { font-size: var(--t-md); font-weight: 600; margin-top: 3px; }

.trace { background: #1c1f24; border: 1px solid var(--log-border); border-radius: var(--r-md); padding: 4px 0; height: 168px; overflow: auto; font-family: var(--mono); font-size: 12px; }
.trace-line { display: flex; gap: 10px; padding: 3px 14px; line-height: 1.5; animation: traceIn .25s ease; }
@keyframes traceIn { from { transform: translateY(3px); } to { transform: none; } }
.trace-line .t-ts { color: var(--log-ts); flex: none; }
.trace-line .t-pct { color: #6f7783; flex: none; width: 34px; text-align: right; }
.trace-line .t-msg { color: var(--log-fg); }
.trace-line[data-l="ok"] .t-msg { color: var(--log-ok); }
.trace-line[data-l="warn"] .t-msg { color: var(--log-warn); }
.trace-line[data-l="err"] .t-msg { color: var(--log-err); }
.trace-line[data-l="info"] .t-msg { color: var(--log-info); }

.run-status-pill { font-size: var(--t-xs); font-weight: 700; }
.run-status-pill[data-s="complete"] { color: var(--ok-ink); }
.run-status-pill[data-s="running"]  { color: var(--accent-ink); }
.run-status-pill[data-s="flagged"]  { color: var(--warn-ink); }
.run-status-pill[data-s="queued"]   { color: var(--ink-3); }

/* ============================================================ REVIEW */
.acc-list { display: flex; flex-direction: column; }
.acc-head, .acc-row { display: grid; grid-template-columns: 88px 84px minmax(110px, 1fr) minmax(150px, 1.5fr) 198px; gap: 12px; align-items: center; }
.acc-head { padding: 9px 16px; border-bottom: 1px solid var(--border); background: var(--surface-2); }
.acc-head span { font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; }
.acc-row-wrap { border-bottom: 1px solid var(--border); }
.acc-row-wrap:last-child { border-bottom: 0; }
.acc-row { padding: 12px 16px; cursor: pointer; transition: background .12s; }
.acc-row:hover { background: var(--surface-2); }
.acc-row .a-run { font-family: var(--mono); font-weight: 700; font-size: var(--t-sm); display: flex; align-items: center; gap: 7px; }
.acc-row .a-run .exp { color: var(--ink-3); transition: transform .18s; }
.acc-row.open .a-run .exp { transform: rotate(180deg); }
.acc-row .a-reason { font-size: var(--t-sm); color: var(--ink-2); }
.acc-decide { display: flex; gap: 6px; justify-content: flex-end; }
.dbtn { font-size: var(--t-xs); font-weight: 700; padding: 5px 13px; border-radius: var(--r-sm); border: 1px solid var(--border-strong); background: var(--surface); cursor: pointer; color: var(--ink-2); }
.dbtn:hover { border-color: var(--ink-3); }
.dbtn.keep.on { background: var(--ok-accent); border-color: var(--ok-accent); color: #fff; }
.dbtn.remove.on { background: var(--danger); border-color: var(--danger); color: #fff; }

.evidence { padding: 10px 16px 16px; background: var(--surface-2); border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 12px; }
.evidence .ev-narrative { font-size: var(--t-sm); line-height: 1.55; color: var(--ink); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 12px 14px; }
.evidence .ev-narrative b { font-weight: 700; }
.justify { display: flex; align-items: center; gap: 12px; padding: 11px 13px; background: var(--warn-bg); border: 1px solid var(--warn-border); border-left: 4px solid var(--warn-accent); border-radius: var(--r-md); }
.justify .j-k { font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase; font-weight: 700; color: var(--warn-ink); flex: none; }

/* ============================================================ FINALIZE */
.final-grid { display: grid; grid-template-columns: 1.25fr 1fr; gap: 14px; align-items: start; flex: none; }
@media (max-width: 1000px) { .final-grid { grid-template-columns: 1fr; } }
.artifact { display: flex; align-items: center; gap: 13px; padding: 13px 15px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background .12s; }
.artifact:last-child { border-bottom: 0; }
.artifact:hover { background: var(--surface-2); }
.artifact .a-ic { width: 36px; height: 36px; border-radius: var(--r-md); background: var(--accent-soft); color: var(--accent-ink); display: grid; place-items: center; flex: none; }
.artifact .a-main { flex: 1; min-width: 0; }
.artifact .a-title { font-size: var(--t-md); font-weight: 600; }
.artifact .a-role { font-size: var(--t-xs); color: var(--ink-2); }
.artifact .a-go { color: var(--ink-3); flex: none; }
.artifact:hover .a-go { color: var(--accent); }

.final-panel { display: flex; flex-direction: column; gap: 13px; padding: 16px; }
.final-status-tiles { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }

.draft-badge { display: inline-flex; align-items: center; gap: 7px; font-size: var(--t-xs); font-weight: 700; padding: 4px 11px; border-radius: var(--r-pill); background: var(--warn-bg); color: var(--warn-ink); border: 1px solid var(--warn-border); }
.draft-badge.final { background: var(--ok-bg); color: var(--ok-ink); border-color: var(--ok-border); }

.path-field { display: flex; align-items: center; gap: 8px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-sm); padding: 7px 10px; font-family: var(--mono); font-size: var(--t-xs); color: var(--ink-2); }
.path-field span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ============================================================ ACTIVITY LOG DRAWER */
.drawer-scrim { position: absolute; inset: 0; background: rgba(15,20,27,.35); z-index: 70; }
.drawer {
  position: absolute; top: 0; right: 0; bottom: 0; width: 420px; max-width: 88vw;
  background: var(--log-bg); border-left: 1px solid var(--log-border);
  z-index: 71; display: flex; flex-direction: column;
  box-shadow: var(--sh-pop); animation: slidein .22s cubic-bezier(.2,.8,.3,1);
}
@keyframes slidein { from { transform: translateX(30px); } to { transform: none; } }
.drawer-head { display: flex; align-items: center; gap: 10px; padding: 13px 16px; border-bottom: 1px solid var(--log-border); }
.drawer-head .dh-t { font-size: var(--t-md); font-weight: 700; color: var(--log-fg); }
.drawer-head .dh-c { font-size: var(--t-xs); color: var(--log-ts); }
.drawer-head .dh-x { margin-left: auto; color: var(--log-ts); cursor: pointer; background: none; border: 0; padding: 4px; border-radius: var(--r-sm); }
.drawer-head .dh-x:hover { background: var(--log-hover, #2b2b2b); color: var(--log-fg); }
.drawer-filter { display: flex; gap: 6px; padding: 9px 16px; border-bottom: 1px solid var(--log-border); }
.drawer-filter button { font-size: var(--t-xs); font-weight: 600; color: var(--log-ts); background: var(--log-panel); border: 1px solid var(--log-border); border-radius: var(--r-sm); padding: 4px 10px; cursor: pointer; }
.drawer-filter button.on { color: var(--log-now); border-color: #4a525c; background: #2c333b; }
.drawer-body { flex: 1; overflow: auto; padding: 6px 0; font-family: var(--mono); font-size: 12px; }
.log-entry { display: grid; grid-template-columns: 58px 1fr; gap: 10px; padding: 5px 16px; line-height: 1.5; }
.log-entry:hover { background: var(--log-hover, #2b2b2b); }
.log-entry .l-ts { color: var(--log-ts); }
.log-entry .l-msg { color: var(--log-fg); }
.log-entry[data-l="ok"] .l-msg { color: var(--log-ok); }
.log-entry[data-l="warn"] .l-msg { color: var(--log-warn); }
.log-entry[data-l="err"] .l-msg { color: var(--log-err); }
.log-entry[data-l="info"] .l-msg { color: var(--log-info); }
.log-entry .l-lvl { color: var(--log-ts); text-transform: uppercase; font-size: 9px; letter-spacing: .08em; }

/* ============================================================ RATIONALE / TWEAKS */
.notes-pop { width: min(680px, 94vw); }
.notes-pop h3 { font-size: var(--t-md); font-weight: 700; margin: 18px 0 7px; }
.notes-pop h3:first-child { margin-top: 0; }
.notes-pop ul { margin: 0; padding-left: 18px; }
.notes-pop li { font-size: var(--t-sm); line-height: 1.6; color: var(--ink-2); margin-bottom: 4px; }
.notes-pop li b { color: var(--ink); }
.notes-pop .diag { background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-md); padding: 13px 15px; font-size: var(--t-sm); line-height: 1.55; color: var(--ink-2); }

.tweaks {
  position: absolute; top: 40px; right: 14px; width: 248px; z-index: 65;
  background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-lg);
  box-shadow: var(--sh-3); padding: 13px; display: flex; flex-direction: column; gap: 13px;
  animation: pop .16s ease;
}
.tweaks .tw-h { display: flex; align-items: center; gap: 8px; }
.tweaks .tw-h .t { font-size: var(--t-sm); font-weight: 700; }
.tweaks .tw-h button { margin-left: auto; background: none; border: 0; color: var(--ink-3); cursor: pointer; padding: 2px; }
.tw-group { display: flex; flex-direction: column; gap: 6px; }
.tw-group > .label-caps { color: var(--ink-3); }
.tw-seg { display: flex; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--r-md); padding: 2px; }
.tw-seg button { flex: 1; border: 0; background: none; font-size: var(--t-xs); font-weight: 600; color: var(--ink-2); padding: 5px 6px; border-radius: 4px; cursor: pointer; }
.tw-seg button.on { background: var(--surface); color: var(--ink); box-shadow: var(--sh-1); }
.tw-swatches { display: flex; gap: 8px; }
.tw-sw { width: 30px; height: 30px; border-radius: var(--r-md); cursor: pointer; border: 2px solid transparent; }
.tw-sw.on { border-color: var(--ink); box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--ink-3); }

/* ---- Toast ---- */
.toast {
  position: absolute; bottom: 64px; left: 50%; transform: translateX(-50%);
  background: #23272e; color: #fff; font-size: var(--t-sm); font-weight: 500;
  padding: 10px 18px; border-radius: var(--r-pill); box-shadow: var(--sh-3);
  z-index: 90; animation: pop .18s ease; white-space: nowrap;
}

/* ============================================================
   v0.3.0 additions — aligned-to-implementation components
   ============================================================ */

/* ---- Prototype scenario bar (dark) ---- */
.protobar {
  flex: none; height: 30px; display: flex; align-items: center; gap: 12px;
  padding: 0 12px; background: #20242b; border-bottom: 1px solid #11141a;
  user-select: none; z-index: 30;
}
.protobar .pb-tag { font-size: 9.5px; letter-spacing: .14em; font-weight: 700; color: #7b8390; }
.protobar .pb-tabs { display: flex; gap: 3px; }
.protobar .pb-tab { font-size: var(--t-xs); font-weight: 600; color: #aeb6c1; background: none; border: 0; padding: 4px 11px; border-radius: var(--r-sm); cursor: pointer; }
.protobar .pb-tab:hover { background: #2c333c; color: #fff; }
.protobar .pb-tab.on { background: var(--accent); color: #fff; }
.protobar .pb-spacer { flex: 1; }
.protobar .pb-hint { font-size: 11px; color: #7b8390; }
.protobar .pb-hint kbd { font-family: var(--mono); font-size: 10px; background: #2c333c; border: 1px solid #3a414b; border-radius: 3px; padding: 0 4px; color: #cdd3db; margin: 0 1px; }

/* ---- task card extras ---- */
.taskWhy { font-size: var(--t-xs); color: var(--ink-2); line-height: 1.4; }
.task-chev { flex: none; transition: transform .18s; }
.method-pick-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }

/* ---- requirement markers (recovered from Enricher) ---- */
.reqmark { font-weight: 800; font-size: 11px; cursor: help; }
.reqmark.req { color: var(--danger); }
.reqmark.rep { color: var(--warn-accent); }
.reqmark.rec { color: var(--ink-3); }

/* ---- chip link (show all) ---- */
.chip-link { font-size: var(--t-xs); font-weight: 600; color: var(--accent); cursor: pointer; align-self: center; padding: 2px 4px; }
.chip-link:hover { text-decoration: underline; }

/* ---- input tile data-state (setup) ---- */
.input-tile[data-state="ok"] { background: var(--ok-bg); border-color: var(--ok-border); }
.input-tile[data-state="ok"] .tile-k { color: var(--ok-ink); }
.input-tile[data-state="ok"] .tile-dot { background: var(--ok-accent); }
.input-tile[data-state="warn"] { background: var(--warn-bg); border-color: var(--warn-border); }
.input-tile[data-state="warn"] .tile-k { color: var(--warn-ink); }
.input-tile[data-state="warn"] .tile-dot { background: var(--warn-accent); }
.input-tile[data-state="err"] { background: var(--err-bg); border-color: var(--err-border); }
.input-tile[data-state="err"] .tile-k { color: var(--err-ink); }
.input-tile[data-state="err"] .tile-dot { background: var(--danger); }
.input-tile[data-state="pending"] .tile-v { color: var(--ink-3); font-weight: 500; }

/* ---- setup empty state ---- */
.setup-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 20px; background: var(--surface); border: 1px solid var(--ok-border); border-radius: var(--r-lg); box-shadow: var(--sh-1); text-align: center; }
.setup-empty .se-ic { width: 44px; height: 44px; border-radius: 50%; background: var(--ok-accent); color: #fff; display: grid; place-items: center; }
.setup-empty .se-ic svg { width: 24px; height: 24px; }
.setup-empty .se-t { font-size: var(--t-lg); font-weight: 700; color: var(--ok-ink); }
.setup-empty .se-s { font-size: var(--t-sm); color: var(--ink-2); }

/* ---- review summary strip ---- */
.review-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.rev-tile { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--sh-1); padding: 12px 15px; display: flex; flex-direction: column; gap: 3px; }
.rev-tile[data-tone="warn"] { background: var(--warn-bg); border-color: var(--warn-border); }
.rev-tile[data-tone="ok"] { background: var(--ok-bg); border-color: var(--ok-border); }
.rev-k { font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; color: var(--ink-3); font-weight: 700; }
.rev-tile[data-tone="warn"] .rev-k { color: var(--warn-ink); }
.rev-tile[data-tone="ok"] .rev-k { color: var(--ok-ink); }
.rev-v { font-size: var(--t-h1); font-weight: 800; font-variant-numeric: tabular-nums; }
.rev-sub { font-size: var(--t-xs); color: var(--ink-2); }

/* ---- defects column ---- */
.a-defects { display: flex; flex-wrap: wrap; gap: 4px; min-width: 0; }
.defect-chip { font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: var(--r-pill); background: var(--warn-bg); color: var(--warn-ink); border: 1px solid var(--warn-border); white-space: nowrap; }
.acc-row .a-reason { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* excluded rows */
.acc-row-wrap.excluded { opacity: .72; }
.acc-row-wrap.excluded .acc-row { cursor: default; }
.acc-row-wrap.excluded .a-run { color: var(--ink-3); }
.excluded-tag { font-size: var(--t-xs); font-weight: 700; color: var(--ink-3); font-style: italic; }

/* ---- diagnostic cockpit ---- */
.cockpit-tabs { display: flex; gap: 3px; background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--r-md); padding: 2px; width: fit-content; }
.cockpit-tab { font-size: var(--t-xs); font-weight: 600; color: var(--ink-2); background: none; border: 0; padding: 5px 14px; border-radius: 4px; cursor: pointer; }
.cockpit-tab.on { background: var(--surface); color: var(--ink); box-shadow: var(--sh-1); }
.cockpit { display: grid; grid-template-columns: minmax(360px, 420px) minmax(0, 1fr); gap: 16px; align-items: start; }
@media (max-width: 880px) { .cockpit { grid-template-columns: 1fr; } }
.cockpit-plot { min-width: 0; }
.decision-context { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 14px; min-height: 150px; display: flex; flex-direction: column; justify-content: center; gap: 8px; }
.decision-context-summary { font-weight: 700; color: var(--ink-1); line-height: 1.35; }
.cockpit-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
@media (max-width: 1080px) { .cockpit-cards { grid-template-columns: repeat(2, 1fr); } }

/* curve sparkline legend */
.spark-legend { display: flex; gap: 12px; font-size: 10.5px; color: var(--ink-3); }
.spark-legend span { display: inline-flex; align-items: center; gap: 4px; }
.spark-legend i { width: 11px; height: 2.5px; border-radius: 1px; display: inline-block; }

/* acceptance findings */
.findings { background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--ink-3); border-radius: var(--r-md); padding: 10px 13px; display: flex; flex-direction: column; gap: 4px; }
.findings-h { font-size: var(--t-caps); letter-spacing: .06em; text-transform: uppercase; font-weight: 700; color: var(--ink-3); }
.finding-line { font-size: var(--t-xs); color: var(--ink-2); font-family: var(--mono); }
.finding-line b { color: var(--ink); text-transform: uppercase; font-size: 10px; letter-spacing: .04em; }

/* justify scope */
.j-scope { font-size: 10.5px; color: var(--warn-ink); line-height: 1.35; opacity: .85; }

/* status bar trust note */
.statusbar .sb-note { font-size: var(--t-xs); opacity: .85; }
.statusbar .sb-note::after { content: "·"; margin: 0 8px; opacity: .6; }

/* ============================================================ v0.5.0 — finalize recoveries */
/* copy folded into path field */
.path-field { position: relative; }
.path-copy { margin-left: auto; flex: none; background: none; border: 0; color: var(--ink-3); cursor: pointer; padding: 3px; border-radius: var(--r-sm); display: grid; place-items: center; }
.path-copy:hover { background: var(--surface-3); color: var(--accent); }
.path-actions { margin-left: auto; display: flex; gap: 2px; flex: none; }
.path-act { width: 26px; height: 26px; display: grid; place-items: center; background: none; border: 1px solid transparent; border-radius: var(--r-sm); color: var(--ink-3); cursor: pointer; transition: background .12s, color .12s, border-color .12s; }
.path-act:hover { background: var(--surface); color: var(--accent); border-color: var(--border); }

/* run-inclusion manifest (Enricher F6) */
.manifest-count { font-size: var(--t-xs); color: var(--ink-2); }
.manifest-count b { color: var(--ink); font-weight: 700; }
.manifest-row { display: flex; align-items: center; gap: 11px; padding: 9px 16px; border-bottom: 1px solid var(--border); cursor: default; }
.manifest-row:last-child { border-bottom: 0; }
.manifest-row.out { cursor: pointer; }
.manifest-row.out:hover { background: var(--surface-2); }
.mf-check { flex: none; width: 18px; height: 18px; border-radius: 50%; display: grid; place-items: center; background: var(--ok-accent); color: #fff; }
.manifest-row.out .mf-check { background: var(--err-bg); color: var(--danger); border: 1px solid var(--err-border); }
.mf-run { flex: none; width: 64px; font-weight: 600; font-size: var(--t-xs); }
.mf-reason { flex: 1; min-width: 0; font-size: var(--t-xs); color: var(--ink-2); }
.manifest-row.out .mf-reason { color: var(--err-ink); }
.mf-jump { flex: none; font-size: var(--t-xs); font-weight: 600; color: var(--accent); }

/* pre-finalize checks (Enricher F7) */
.checks-card { display: flex; flex-direction: column; gap: 10px; }
.checks-summary { font-size: var(--t-xs); font-weight: 600; }
.checks-summary .ok { color: var(--ok-ink); display: inline-flex; align-items: center; gap: 3px; }
.checks-summary .warn { color: var(--warn-ink); }
.checks-list { display: flex; flex-direction: column; gap: 2px; }
.check-line { display: flex; align-items: center; gap: 8px; font-size: var(--t-sm); padding: 5px 2px; color: var(--ink); }
.check-line.ok svg { color: var(--ok-accent); flex: none; }
.check-line.err { color: var(--err-ink); }
.check-line.err svg { color: var(--danger); flex: none; }
.check-line.rep { color: var(--warn-ink); }
.check-line.rep svg { color: var(--warn-accent); flex: none; }
.check-line.oos { color: var(--ink-3); }
.check-line .oos-dot { color: var(--ink-4); font-weight: 700; width: 13px; text-align: center; flex: none; }
.check-line .oos-tag { font-size: 10px; font-style: italic; color: var(--ink-4); margin-left: auto; }
.check-line .check-fix { margin-left: auto; font-size: var(--t-xs); font-weight: 700; color: var(--accent); }

/* version bump (Method-Editor versioning ritual) */
.version-bump { display: inline-flex; align-items: center; gap: 6px; font-size: var(--t-xs); font-family: var(--mono); }
.version-bump .vb-from { color: var(--ink-3); }
.version-bump .vb-to { color: var(--ok-ink); font-weight: 700; background: var(--ok-bg); border: 1px solid var(--ok-border); border-radius: var(--r-sm); padding: 1px 6px; }
.version-bump svg { color: var(--ink-4); }

/* action-bar back button */
.actionbar .ab-back { flex: none; }

/* ============================================================ v0.6.0 — progressive disclosure */
/* collapsible secondary section (finalize manifest + checks) */
.collapse { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--sh-1); overflow: hidden; flex: none; }
.collapse-head { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 16px; background: none; border: 0; cursor: pointer; text-align: left; font: inherit; }
.collapse-head:hover { background: var(--surface-2); }
.collapse-head .label-caps { flex: none; }
.collapse-sum { font-size: var(--t-sm); color: var(--ink-2); }
.collapse-sum b { color: var(--ink); font-weight: 700; }
.collapse-sum.warn { color: var(--warn-ink); } .collapse-sum.warn b { color: var(--warn-ink); }
.collapse-sum.ok { color: var(--ok-ink); } .collapse-sum.ok b { color: var(--ok-ink); }
.collapse-chev { margin-left: auto; flex: none; color: var(--ink-3); transition: transform .18s; }
.collapse.open .collapse-chev { transform: rotate(180deg); }
.collapse-body { border-top: 1px solid var(--border); }
.collapse-body .checks-list { padding: 10px 16px; }

/* finalize readout: 3 compact stats replacing 3 stacked panels */
.finalize-readout { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.fr-item { display: flex; align-items: center; gap: 9px; padding: 10px 11px; background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--r-md); cursor: pointer; text-align: left; font: inherit; }
.fr-item.static { cursor: default; }
button.fr-item:hover { border-color: var(--border-strong); background: var(--surface-3); }
.fr-v { font-size: var(--t-h2); font-weight: 800; font-variant-numeric: tabular-nums; color: var(--ink); display: inline-flex; align-items: center; }
.fr-v[data-tone="warn"] { color: var(--warn-ink); }
.fr-v[data-tone="ok"] { color: var(--ok-accent); }
.fr-k { font-size: var(--t-xs); color: var(--ink-2); line-height: 1.3; }

/* ============================================================ mapping editor — compact readout + disclosure */
/* one status line replacing the four wasteful summary tiles */
.map-readout { display: flex; align-items: center; gap: 12px; padding: 11px 14px; border-radius: var(--r-md); border: 1px solid var(--border); background: var(--surface-2); }
.map-readout[data-tone="err"]  { background: var(--err-bg);  border-color: var(--err-border);  border-left: 4px solid var(--danger); }
.map-readout[data-tone="warn"] { background: var(--warn-bg); border-color: var(--warn-border); border-left: 4px solid var(--warn-accent); }
.map-readout[data-tone="ok"]   { background: var(--ok-bg);   border-color: var(--ok-border);   border-left: 4px solid var(--ok-accent); }
.map-readout .mr-ic { flex: none; width: 17px; height: 17px; }
.map-readout[data-tone="err"] .mr-ic { color: var(--danger); }
.map-readout[data-tone="warn"] .mr-ic { color: var(--warn-accent); }
.map-readout[data-tone="ok"] .mr-ic { color: var(--ok-accent); }
.map-readout .mr-text { flex: 1; min-width: 0; font-size: var(--t-sm); line-height: 1.4; }
.map-readout[data-tone="err"] .mr-text { color: var(--err-ink); }
.map-readout[data-tone="warn"] .mr-text { color: var(--warn-ink); }
.map-readout[data-tone="ok"] .mr-text { color: var(--ok-ink); }
.map-readout .mr-text b { font-weight: 700; }
.map-readout .mr-stats { display: flex; gap: 7px; flex: none; }
.mr-stat { font-size: var(--t-xs); font-weight: 600; color: var(--ink-2); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-pill); padding: 3px 10px; white-space: nowrap; }
.mr-stat b { color: var(--ink); font-variant-numeric: tabular-nums; }
.mr-stat.amb { background: var(--info-bg); border-color: var(--info-border); color: var(--info-ink); }
.mr-stat.amb b { color: var(--info-ink); }

/* resolved-group disclosure toggle in the binding list */
.bind-group-toggle { display: flex; align-items: center; gap: 7px; width: 100%; padding: 10px 14px; background: var(--surface-2); border: 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); cursor: pointer; font: inherit; font-size: var(--t-caps); letter-spacing: .07em; text-transform: uppercase; font-weight: 700; color: var(--ok-ink); }
.bind-group-toggle:hover { background: var(--surface-3); }
.bind-group-toggle .gcount { background: var(--surface-3); border-radius: var(--r-pill); padding: 1px 7px; font-size: 10px; }
.bind-allclear { display: flex; align-items: center; gap: 8px; padding: 14px; color: var(--ok-ink); font-size: var(--t-sm); font-weight: 600; }
.bind-allclear svg { color: var(--ok-accent); }

/* ambiguous disambiguation hint + provenance */
.amb-hint { display: flex; align-items: center; gap: 8px; padding: 9px 11px; background: var(--info-bg); border: 1px solid var(--info-border); border-radius: var(--r-md); font-size: var(--t-xs); color: var(--info-ink); line-height: 1.4; }
.amb-hint svg { color: var(--info-accent); }
.cand-via { color: var(--ink-3); font-style: normal; }

/* swipe-nav feedback: gentle peek while dragging horizontally */
.stage { transition: transform .16s ease; }
.stage[data-nudge="1"]  > .spotlight { transform: translateX(-10px); transition: transform .12s ease; }
.stage[data-nudge="-1"] > .spotlight { transform: translateX(10px);  transition: transform .12s ease; }
.spotlight { transition: transform .18s cubic-bezier(.2,.8,.3,1); }
`;function fi(){return(0,a.jsx)(x,{css:di+wt+Tt,className:`analysis-shadow`,children:(0,a.jsx)(ui,{})})}var pi=class extends i.Component{constructor(e){super(e),this.state={error:null}}static getDerivedStateFromError(e){return{error:e}}componentDidUpdate(e){e.resetKey!==this.props.resetKey&&this.state.error&&this.setState({error:null})}componentDidCatch(e,t){console.error(`[CompressionGuiErrorBoundary]`,e,t),window.__COMPRESSION_GUI_MOUNT_STATE=`error`,window.__COMPRESSION_GUI_BOOT_ERROR=e?.stack||e?.message||String(e)}render(){if(this.state.error){let e=this.state.error?.stack||this.state.error?.message||String(this.state.error);return(0,a.jsxs)(`div`,{className:`suite-screen-error`,children:[(0,a.jsx)(`h2`,{children:`Interface segment failed to render`}),(0,a.jsx)(`p`,{children:`The mock GUI shell caught a render error instead of leaving the viewport blank.`}),(0,a.jsx)(`pre`,{children:e})]})}return this.props.children}};function mi(e){return e&&e.nodeType===1&&typeof e.matches==`function`}function hi(e){return e.some(e=>{if(!mi(e))return!1;if(e.matches(`button,input,textarea,select,a,[role="button"],[contenteditable="true"],[data-window-control],[data-window-action],.window-control`)||e.matches(`.menu-item,.menu__btn,.menu__pop,.menu-pop,.menubar__schema,.desktop-window-control,.modal,.drawer-scrim,.scrim`))return!0;let t=window.getComputedStyle(e).cursor;return t===`pointer`||t===`text`})}function gi(e,t,n){if(n.some(e=>mi(e)&&e.matches(`[data-window-drag],.menubar--desktop,.menubar`)))return!0;let r={home:30,packaging:30,"method-editor":30,analysis:30}[e]||34;return t.clientY>=0&&t.clientY<=r}function _i(e){Promise.resolve(e).then(e=>{e&&typeof e==`object`&&window.__compressionSyncWindowState?.(e)}).catch(()=>{})}function vi({screen:e}){return i.useEffect(()=>{let t=t=>{if(t.button!==0||t.detail>1||!window.desktopApi?.host||!window.desktopApi?.startWindowDrag)return;let n=t.composedPath?t.composedPath():[];hi(n)||gi(e,t,n)&&(t.preventDefault(),window.desktopApi.startWindowDrag({source:`browser-event`,screen:e,clientX:t.clientX,clientY:t.clientY}))},n=t=>{if(t.button!==0||!window.desktopApi?.host||!window.desktopApi?.toggleMaximizeWindow)return;let n=t.composedPath?t.composedPath():[];hi(n)||gi(e,t,n)&&(t.preventDefault(),t.stopPropagation(),_i(window.desktopApi.toggleMaximizeWindow()))};return document.addEventListener(`mousedown`,t,!0),document.addEventListener(`dblclick`,n,!0),()=>{document.removeEventListener(`mousedown`,t,!0),document.removeEventListener(`dblclick`,n,!0)}},[e]),null}var yi={home:{label:`Launcher`,title:`Compression Model Launcher`,width:980,height:930,minWidth:980,minHeight:930},packaging:{label:`Dataset Packaging`,title:`Dataset Packaging`,width:1480,height:960,minWidth:1360,minHeight:860},"method-editor":{label:`Method Editor`,title:`Analysis Method Editor`,width:988,height:960,minWidth:988,minHeight:900},analysis:{label:`Method Analysis`,title:`Method Analysis`,width:1460,height:940,minWidth:1280,minHeight:820}};function bi(e){if(e&&typeof e==`object`)return bi(e.screen||e.target||`home`);let t={dataset:`packaging`,"dataset-packaging":`packaging`,method:`method-editor`,"method-editor":`method-editor`,mtdp:`packaging`}[e]||e;return yi[t]?t:`home`}function xi(){return bi(new URLSearchParams(window.location.search).get(`screen`)||`home`)}function Si(){let e=new URLSearchParams(window.location.search),t=e.get(`mode`)||e.get(`window`);if(t)return t===`child`?`child`:`launcher`;let n=bi(e.get(`screen`));return n&&n!==`home`?`child`:`launcher`}function Ci({onReady:e}={}){let[t]=i.useState(Si),[n]=i.useState(()=>t===`child`?xi():`home`),r=i.useCallback(async e=>{let t=bi(e);if(t===`home`)return;let n=yi[t],r={...e&&typeof e==`object`?e:{},screen:t,...n};if(window.desktopApi?.openChildWindow){await window.desktopApi.openChildWindow(r);return}let i=new URL(window.location.href);i.searchParams.set(`mode`,`child`),i.searchParams.set(`screen`,t),(r.initial_package_path||r.package_path)&&i.searchParams.set(`initial_package_path`,r.initial_package_path||r.package_path),window.open(i.toString(),n.title,`popup=yes,width=${n.width},height=${n.height},minWidth=${n.minWidth},minHeight=${n.minHeight}`)},[]);i.useEffect(()=>(window.__compressionSuiteOpenChild=r,()=>{window.__compressionSuiteOpenChild===r&&delete window.__compressionSuiteOpenChild}),[r]);let o=i.useCallback((r={})=>{e?.({screen:n,windowMode:t,...r})},[e,n,t]);return i.useEffect(()=>{if(t===`launcher`||t===`child`&&(n===`home`||n===`method-editor`))return;let e=window.setTimeout(()=>o({source:`react-screen`}),0);return()=>window.clearTimeout(e)},[o,n,t]),i.useEffect(()=>{let e=new URL(window.location.href),r=e.searchParams.get(`mode`)||e.searchParams.get(`window`)||`launcher`;(e.searchParams.get(`screen`)!==n||r!==t)&&(e.searchParams.set(`screen`,n),e.searchParams.set(`mode`,t),window.history.replaceState(null,``,e))},[n,t]),i.useEffect(()=>{let e=e=>{if(e.target&&([`INPUT`,`TEXTAREA`,`SELECT`].includes(e.target.tagName)||e.target.closest?.(`[contenteditable="true"]`)))return;let t=e.key.toLowerCase();if(e.key===`F11`||e.altKey&&e.key===`Enter`){e.preventDefault(),window.desktopApi?.toggleMaximizeWindow?.();return}if((e.ctrlKey||e.metaKey)&&t===`w`){e.preventDefault(),window.desktopApi?.closeWindow?.();return}if((e.ctrlKey||e.metaKey)&&t===`q`){e.preventDefault(),(window.desktopApi?.quitApplication||window.desktopApi?.closeWindow)?.();return}if((e.ctrlKey||e.metaKey)&&e.shiftKey&&t===`m`){e.preventDefault(),window.desktopApi?.minimizeWindow?.();return}!(e.ctrlKey||e.metaKey)||e.altKey||e.shiftKey||(t===`d`&&(e.preventDefault(),r(`packaging`)),t===`m`&&(e.preventDefault(),r(`method-editor`)),t===`a`&&(e.preventDefault(),r(`analysis`)))};return window.addEventListener(`keydown`,e),()=>window.removeEventListener(`keydown`,e)},[r]),(0,a.jsxs)(`div`,{className:`suite-root`,"data-screen":n,"data-window-mode":t,children:[(0,a.jsx)(vi,{screen:n}),(0,a.jsx)(`main`,{className:`suite-screen`,"aria-label":yi[n]?.label||`Compression suite`,children:(0,a.jsxs)(pi,{resetKey:`${t}:${n}`,children:[t===`launcher`&&(0,a.jsx)(m,{onLaunch:r,onReady:o}),t===`child`&&n===`packaging`&&(0,a.jsx)(Dt,{}),t===`child`&&n===`method-editor`&&(0,a.jsx)(Ht,{onReady:o}),t===`child`&&n===`analysis`&&(0,a.jsx)(fi,{}),t===`child`&&n===`home`&&(0,a.jsx)(m,{onLaunch:r,onReady:o})]})})]})}export{Ci as default};