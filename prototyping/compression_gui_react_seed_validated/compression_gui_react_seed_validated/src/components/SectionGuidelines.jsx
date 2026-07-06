import React from 'react';

export const SECTION_GUIDES = {
  suite: {
    eyebrow: 'Suite guidelines',
    title: 'Using the Data Reduction Suite',
    subtitle: 'Move from raw compression-test files to a reviewed MTDA archive.',
    intent: 'The suite is organised around the scientific record: package the data, choose the method rules, run the analysis, then review evidence before reporting.',
    workflow: [
      'Use Dataset Packaging when you need to create or inspect an MTDP input package from raw measurement files.',
      'Use Method when you need an editable method version. The ISO reference remains read-only and is kept as the baseline.',
      'Use Analysis when you have one MTDP package ready and want to produce an MTDA analysed dataset archive.',
      'Use the acceptance cockpit to decide flagged runs with plots, metrics, defaults, and justifications.',
      'Use the MTDA browser to review the archive index, test report, audit report, plots, tables, and decision register.',
    ],
    checks: [
      'Confirm package identity, run count, channels, and required metadata before analysis.',
      'Confirm any method changes were saved as a method version before selecting them in Analysis.',
      'Confirm flagged-run decisions in Accept match the Output run manifest before sharing results.',
      'Review generated reports and plots. The software prepares evidence; the final scientific judgement remains with the user.',
    ],
  },
  dataset: {
    eyebrow: 'Dataset Packaging',
    title: 'Create a clean MTDP package',
    subtitle: 'Prepare raw compression-test measurements for analysis without changing the original files.',
    intent: 'Use this section when you have raw files, sidecars, metadata, or image evidence that must be organised into a traceable package.',
    workflow: [
      'Open raw files, a source folder, or an existing MTDP package.',
      'Review the proposed grouping so each physical specimen is represented by the correct run.',
      'Check channel assignments for load, strain, time, crosshead, and any supporting traces.',
      'Complete dataset-level and run-level metadata. Use required-field filters to focus on what blocks export.',
      'Attach image evidence and supplemental files when they explain the test context.',
      'Validate the package and export the MTDP only when the review panel is clear enough for analysis.',
    ],
    checks: [
      'Original raw files are copied into the package and are not modified.',
      'Every exported run should have the expected measurement channels and specimen dimensions.',
      'Warnings may be acceptable, but hard missing fields should be resolved before moving to Analysis.',
      'Open the exported package in Analysis only after confirming the package path and run list.',
    ],
  },
  method: {
    eyebrow: 'Method',
    title: 'Create and manage method versions',
    subtitle: 'Adjust analysis rules while keeping the ISO reference protected.',
    intent: 'Use this section when the scientific method needs a controlled editable version for test range, modulus, bending, or acceptance/report settings.',
    workflow: [
      'Start from the ISO reference or an existing generated method.',
      'Create a new method when you need an editable version. Reference methods cannot be edited or deleted.',
      'Review the pipeline map: data entry, test range, stress-strain, modulus, bending, strength, acceptance, and reports.',
      'Edit only the controlled method parameters that belong in the method record.',
      'Validate the draft before use, then save the method version so it is available in Analysis.',
      'Export or import method packages when you need to move controlled method versions between workspaces.',
    ],
    checks: [
      'The Save method button should only be active after a real edit.',
      'Unsaved edits should be saved before closing or switching method versions.',
      'The stress-strain stage is derived from package data and is not edited in Method.',
      'Use the change ledger to understand what differs from the reference method before using it for analysis.',
    ],
  },
  analysis: {
    eyebrow: 'Analysis',
    title: 'Run a method and review the MTDA output',
    subtitle: 'Reduce one MTDP package with one method, then make acceptance decisions before reporting.',
    intent: 'Use this section when a packaged dataset is ready and you need reduced results, evidence plots, reports, and a reviewed MTDA archive.',
    workflow: [
      'Choose one MTDP package. Recent files help reopen known packages; Choose package lets you browse folders.',
      'Choose the ISO reference method or an editable generated method version.',
      'Review mapping so the package channels and metadata are bound to the method inputs.',
      'Check readiness, run the method, and inspect validation before acceptance.',
      'Use Accept to review flagged runs with defect-specific evidence, plots, metrics, defaults, and justification fields.',
      'Use Output to complete report-only metadata, open reports, and finalise the MTDA archive.',
    ],
    checks: [
      'Only an MTDP package is the input to a method run. MTDA archives are analysis outputs.',
      'The acceptance cockpit should help decide keep or remove. Internal software diagnostics do not belong there unless they support that decision.',
      'Accept and Output run manifests must agree before finalisation.',
      'Open the MTDA archive index, test report, audit report, and relevant plots before sharing results.',
    ],
  },
};

export function SectionGuidelinesContent({ section = 'suite' }) {
  const guide = SECTION_GUIDES[section] || SECTION_GUIDES.suite;
  return (
    <div className="section-guide">
      <div className="section-guide__lead">
        <div className="section-guide__eyebrow">{guide.eyebrow}</div>
        <h3>{guide.title}</h3>
        <p>{guide.subtitle}</p>
      </div>
      <section>
        <h4>Purpose</h4>
        <p>{guide.intent}</p>
      </section>
      <section>
        <h4>Workflow</h4>
        <ol>
          {guide.workflow.map((item) => <li key={item}>{item}</li>)}
        </ol>
      </section>
      <section>
        <h4>Before moving on</h4>
        <ul>
          {guide.checks.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
    </div>
  );
}

export function SectionGuidelinesModal({ section = 'suite', onClose }) {
  const guide = SECTION_GUIDES[section] || SECTION_GUIDES.suite;
  return (
    <div className="section-guide-scrim" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose?.()}>
      <section className="section-guide-dialog" role="dialog" aria-modal="true" aria-labelledby="section-guide-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="section-guide-dialog__chrome">
          <span className="section-guide-dialog__dot" aria-hidden="true" />
          <h2 id="section-guide-title">About {guide.eyebrow}</h2>
          <button type="button" className="section-guide-dialog__close" aria-label="Close" onClick={onClose}>x</button>
        </header>
        <div className="section-guide-dialog__body">
          <SectionGuidelinesContent section={section} />
          <div className="section-guide-dialog__actions">
            <span>Full walkthrough: GUIDELINES.md</span>
            <button type="button" onClick={onClose}>Close</button>
          </div>
        </div>
      </section>
    </div>
  );
}
