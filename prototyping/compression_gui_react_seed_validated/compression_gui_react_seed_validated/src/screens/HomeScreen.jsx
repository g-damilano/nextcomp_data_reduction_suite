import React from 'react';
import { DcRuntimeHost } from '../components/DcRuntimeHost.jsx';
import { HOME_DC, HOME_LOGIC } from '../generated/dcSources.js';

export default function HomeScreen({ onLaunch, onReady }) {
  const [openMenu, setOpenMenu] = React.useState(null);
  const [modal, setModal] = React.useState(null);

  const openModule = React.useCallback((screen) => {
    setOpenMenu(null);
    onLaunch?.(screen);
  }, [onLaunch]);

  const exitApp = React.useCallback(() => {
    setOpenMenu(null);
    const quit = window.desktopApi?.quitApplication || window.desktopApi?.closeWindow;
    quit?.();
  }, []);

  const closeOverlay = React.useCallback(() => {
    setOpenMenu(null);
    setModal(null);
  }, []);

  const openModal = React.useCallback((nextModal) => {
    setOpenMenu(null);
    setModal(nextModal);
  }, []);

  React.useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        closeOverlay();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [closeOverlay]);

  return (
    <>
      <DcRuntimeHost
        name="CompressionSuiteHome"
        template={HOME_DC}
        logic={HOME_LOGIC}
        methodReady={true}
        showWorkflow={true}
        showRecent={false}
        onNavigate={onLaunch}
        onReady={onReady}
      />
      <div className="launcher-hit-layer" aria-hidden="false">
        <button
          className="launcher-menu-hit launcher-menu-hit--file"
          type="button"
          aria-label="File"
          onClick={() => setOpenMenu((open) => open === 'file' ? null : 'file')}
        />
        <button
          className="launcher-menu-hit launcher-menu-hit--help"
          type="button"
          aria-label="Help"
          onClick={() => setOpenMenu((open) => open === 'help' ? null : 'help')}
        />
        {openMenu && (
          <>
            <button className="launcher-menu-scrim" type="button" aria-label="Close menu" onClick={() => setOpenMenu(null)} />
            {openMenu === 'file' && (
              <div className="launcher-menu-pop launcher-file-menu" role="menu" aria-label="File">
                <button type="button" role="menuitem" onClick={() => openModule('packaging')}>
                  <span>Open Dataset Packaging...</span><span>Ctrl+D</span>
                </button>
                <button type="button" role="menuitem" onClick={() => openModule('method-editor')}>
                  <span>Open Method...</span><span>Ctrl+M</span>
                </button>
                <button type="button" role="menuitem" onClick={() => openModule('analysis')}>
                  <span>Open Analysis...</span><span>Ctrl+A</span>
                </button>
                <i />
                <button type="button" role="menuitem" disabled aria-disabled="true">
                  <span>Recent sessions</span><span>Not available</span>
                </button>
                <i />
                <button type="button" role="menuitem" onClick={exitApp}>
                  <span>Exit</span>
                </button>
              </div>
            )}
            {openMenu === 'help' && (
              <div className="launcher-menu-pop launcher-help-menu" role="menu" aria-label="Help">
                <button type="button" role="menuitem" onClick={() => openModal('guide')}>
                  <span>User guidelines</span><span>Bundled</span>
                </button>
                <button type="button" role="menuitem" onClick={() => openModal('shortcuts')}>
                  <span>Keyboard shortcuts</span>
                </button>
                <button type="button" role="menuitem" onClick={() => openModal('licensing')}>
                  <span>Licensing &amp; notices...</span>
                </button>
                <i />
                <button type="button" role="menuitem" onClick={() => openModal('about')}>
                  <span>About this suite...</span>
                </button>
              </div>
            )}
          </>
        )}
        {modal && (
          <LauncherModal modal={modal} setModal={setModal} closeOverlay={closeOverlay} />
        )}
        <button className="launcher-row-hit launcher-row-hit--dataset" type="button" aria-label="Open Dataset Packaging" data-launcher-hit="dataset-packaging" onClick={() => openModule('packaging')} />
        <button className="launcher-row-hit launcher-row-hit--method" type="button" aria-label="Open Method" data-launcher-hit="method-editor" onClick={() => openModule('method-editor')} />
        <button className="launcher-row-hit launcher-row-hit--analysis" type="button" aria-label="Open Analysis" data-launcher-hit="analysis" onClick={() => openModule('analysis')} />
      </div>
    </>
  );
}

function LauncherModal({ modal, setModal, closeOverlay }) {
  if (modal === 'guide') {
    return (
      <div className="launcher-modal-scrim" role="presentation" onMouseDown={closeOverlay}>
        <section className="launcher-modal launcher-modal--wide" role="dialog" aria-modal="true" aria-labelledby="launcher-guide-title" onMouseDown={(event) => event.stopPropagation()}>
          <ModalChrome titleId="launcher-guide-title" title="User guidelines — NextCOMP Data Reduction Suite" onClose={closeOverlay} />
          <div className="launcher-modal-body">
            <BrandPanel title="User guidelines" subtitle="Packaging, method editing, analysis, acceptance, and MTDA review." />
            <div className="launcher-guide-copy">
              <section>
                <h3>Workflow</h3>
                <ol>
                  <li>Create or inspect an MTDP package in Dataset Packaging.</li>
                  <li>Use Method Editor only for editable generated methods; ISO 14126 remains read-only.</li>
                  <li>Run Method Analysis with one MTDP package and one method.</li>
                  <li>Review validation and acceptance evidence before finalising MTDA output.</li>
                </ol>
              </section>
              <section>
                <h3>Decision rule</h3>
                <p>The acceptance cockpit is for scientific decisions. Keep only the evidence that helps decide whether a flagged run should be kept or removed: defect-specific plots, thresholds, metrics, defaults, and justifications.</p>
              </section>
              <section>
                <h3>Output review</h3>
                <p>Open the MTDA archive index, formal report, audit report, and plot viewers. Confirm that Accept and Output run manifests agree before sharing results.</p>
              </section>
              <p className="launcher-guide-note">The full screenshot walkthrough is bundled as <span>GUIDELINES.md</span> in the repository root.</p>
            </div>
            <div className="launcher-modal-actions">
              <button className="launcher-link-button" type="button" onClick={() => setModal('shortcuts')}>Keyboard shortcuts →</button>
              <button className="launcher-primary-button" type="button" onClick={closeOverlay}>Close</button>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (modal === 'about') {
    return (
      <div className="launcher-modal-scrim" role="presentation" onMouseDown={closeOverlay}>
        <section className="launcher-modal launcher-modal--wide" role="dialog" aria-modal="true" aria-labelledby="launcher-about-title" onMouseDown={(event) => event.stopPropagation()}>
          <ModalChrome titleId="launcher-about-title" title="About — NextCOMP Data Reduction Suite" onClose={closeOverlay} />
          <div className="launcher-modal-body">
            <BrandPanel title="Data Reduction Suite" subtitle="Data reduction pipeline for compression testing." />
            <dl className="launcher-about-grid">
              <dt>Version</dt><dd>1.1.0</dd>
              <dt>Scope</dt><dd>Compression testing</dd>
              <dt>Modules</dt><dd>Dataset Packaging · Method · Analysis</dd>
              <dt>Developer</dt><dd>Giacomo Damilano</dd>
              <dt>Email</dt><dd className="launcher-link-text">giacomo.damilano@gmail.com</dd>
              <dt>Project</dt><dd>NextCOMP — Next Generation Fibre-Reinforced Composites</dd>
              <dt>License</dt><dd>Apache License, Version 2.0</dd>
            </dl>
            <p className="launcher-funding-text">Funding: UK Engineering and Physical Sciences Research Council (EPSRC) programme Grant EP/T011653/1, Next Generation Fibre-Reinforced Composites (NextCOMP): a Full Scale Redesign for Compression, Imperial College London and the University of Bristol.</p>
            <div className="launcher-modal-actions">
              <button className="launcher-link-button" type="button" onClick={() => setModal('licensing')}>Licensing &amp; notices →</button>
              <button className="launcher-primary-button" type="button" onClick={closeOverlay}>Close</button>
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (modal === 'licensing') {
    return (
      <div className="launcher-modal-scrim" role="presentation" onMouseDown={closeOverlay}>
        <section className="launcher-modal launcher-modal--wide" role="dialog" aria-modal="true" aria-labelledby="launcher-licensing-title" onMouseDown={(event) => event.stopPropagation()}>
          <ModalChrome titleId="launcher-licensing-title" title="Licensing & notices — NextCOMP Data Reduction Suite" onClose={closeOverlay} />
          <div className="launcher-modal-body">
            <BrandPanel title="Licensing & notices" subtitle="Apache License, Version 2.0 · © 2026 Imperial College London" />
            <div className="launcher-license-copy">
              <p>© 2026 Imperial College London. This product includes software developed at Imperial College London, made available under the Apache License, Version 2.0.</p>
              <p>Apache-2.0 permits use, modification and redistribution, including for commercial purposes and within proprietary or sold products, provided the licence text and this NOTICE are retained.</p>
              <p>The developer, Giacomo Damilano, is expressly authorised to use, reuse, modify, sublicense and incorporate the project-authored code and documentation, including for commercial purposes and within private, proprietary or sold products, subject to the third-party boundaries set out below.</p>
              <p>The Apache-2.0 licence does not grant rights over third-party materials, standards documents, institutional or project logos, generated outputs, or external libraries identified as separately licensed or restricted. Redistributions must retain the NOTICE file and applicable third-party notices.</p>
              <p>Unless required by applicable law or agreed in writing, the software is provided on an "AS IS" basis, without warranties or conditions of any kind, express or implied.</p>
              <p>Developed for research purposes. Results and generated outputs are the user's responsibility and should be reviewed before being relied upon for engineering, certification or commercial decisions.</p>
            </div>
            <div className="launcher-modal-actions">
              <button className="launcher-link-button" type="button" onClick={() => setModal('about')}>← Back to About</button>
              <button className="launcher-primary-button" type="button" onClick={closeOverlay}>Close</button>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="launcher-modal-scrim" role="presentation" onMouseDown={closeOverlay}>
      <section className="launcher-modal launcher-modal--shortcuts" role="dialog" aria-modal="true" aria-labelledby="launcher-shortcuts-title" onMouseDown={(event) => event.stopPropagation()}>
        <ModalChrome titleId="launcher-shortcuts-title" title="Keyboard shortcuts" onClose={closeOverlay} />
        <div className="launcher-modal-body">
          <ShortcutGroup title="Open a module" rows={[
            ['Ctrl+D', 'Open Dataset Packaging'],
            ['Ctrl+M', 'Open Method'],
            ['Ctrl+A', 'Open Analysis'],
          ]} />
          <ShortcutGroup title="Window" rows={[
            ['F11 / Alt+Enter', 'Maximize or restore'],
            ['Ctrl+Shift+M', 'Minimize window'],
            ['Ctrl+W', 'Close window'],
            ['Ctrl+Q', 'Quit application'],
          ]} />
          <ShortcutGroup title="General" rows={[
            ['Esc', 'Close menus and dialogs'],
          ]} />
          <div className="launcher-modal-actions launcher-modal-actions--end">
            <button className="launcher-primary-button" type="button" onClick={closeOverlay}>Close</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function ModalChrome({ titleId, title, onClose }) {
  return (
    <header className="launcher-modal-chrome">
      <div className="launcher-modal-title-dot" />
      <h2 id={titleId}>{title}</h2>
      <button type="button" className="launcher-modal-close" aria-label="Close dialog" onClick={onClose}>×</button>
    </header>
  );
}

function BrandPanel({ title, subtitle }) {
  return (
    <div className="launcher-brand-panel">
      <div>
        <div className="launcher-brand-eyebrow">NextCOMP</div>
        <div className="launcher-brand-title">{title}</div>
        <div className="launcher-brand-subtitle">{subtitle}</div>
      </div>
      <img src="assets/nextcomp-logo.png" alt="NextCOMP" />
    </div>
  );
}

function ShortcutGroup({ title, rows }) {
  return (
    <section className="launcher-shortcut-group">
      <h3>{title}</h3>
      {rows.map(([keys, label]) => (
        <div className="launcher-shortcut-row" key={`${title}-${keys}`}>
          <span>{label}</span>
          <kbd>{keys}</kbd>
        </div>
      ))}
    </section>
  );
}
