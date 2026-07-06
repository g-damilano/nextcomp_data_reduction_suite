import React from 'react';
import * as ReactDOMClient from 'react-dom/client';
import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

beforeAll(async () => {
  window.React = React;
  window.ReactDOM = ReactDOMClient;
  await import('../vendor/dc-runtime.js');
});

let consoleErrorSpy;
let consoleWarnSpy;
let windowOpenSpy;

beforeEach(() => {
  window.history.replaceState(null, '', '/?mode=launcher&screen=home');
  window.desktopApi = {
    host: true,
    openChildWindow: vi.fn().mockResolvedValue({ status: 'opened' }),
    startWindowDrag: vi.fn(),
    minimizeWindow: vi.fn(),
    toggleMaximizeWindow: vi.fn(),
    closeWindow: vi.fn(),
    quitApplication: vi.fn(),
  };
  windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => ({ closed: false }));
  consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  const errors = consoleErrorSpy.mock.calls.map((args) => args.join(' '));
  const warnings = consoleWarnSpy.mock.calls.map((args) => args.join(' '));
  consoleErrorSpy.mockRestore();
  consoleWarnSpy.mockRestore();
  windowOpenSpy.mockRestore();
  cleanup();
  delete window.__compressionSuiteOpenChild;
  expect(errors).toEqual([]);
  expect(warnings).toEqual([]);
});

async function renderApp({ screen = 'home', mode = 'launcher', params = {}, hash = '' } = {}) {
  const query = new URLSearchParams({ mode, screen });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) query.set(key, String(value));
  });
  window.history.replaceState(null, '', `/?${query.toString()}${hash}`);
  vi.resetModules();
  const { default: App } = await import('../App.jsx');
  return render(<App />);
}

function shadowHosts(container) {
  return Array.from(container.querySelectorAll('.shadow-screen-host'));
}

function shadowText(container) {
  return shadowHosts(container)
    .map((host) => host.shadowRoot?.textContent || '')
    .join('\n');
}

function allVisibleText(container) {
  return `${document.body.textContent || ''}\n${shadowText(container)}`;
}

async function expectVisibleText(container, text) {
  await waitFor(() => {
    expect(allVisibleText(container)).toContain(text);
  }, { timeout: 5000 });
}

function shadowElements(container, selector = '*') {
  return shadowHosts(container).flatMap((host) => Array.from(host.shadowRoot?.querySelectorAll(selector) || []));
}

function interactionRank(el) {
  const tag = el.tagName.toLowerCase();
  if (tag === 'button') return 0;
  if (el.getAttribute('role') === 'button') return 1;
  if (el.classList.contains('pick') || el.classList.contains('tile-link') || el.classList.contains('chip-link')) return 2;
  if ((el.getAttribute('style') || '').includes('cursor: pointer')) return 3;
  return 4;
}

async function clickShadowText(container, matcher, selector = 'button, [role="button"], .pick, .tile-link, .chip-link, div, span') {
  const re = matcher instanceof RegExp ? matcher : new RegExp(String(matcher), 'i');
  let match = null;
  await waitFor(() => {
    const candidates = shadowElements(container, selector)
      .filter((el) => re.test((el.textContent || '').replace(/\s+/g, ' ').trim()))
      .filter((el) => !el.disabled && el.getAttribute('aria-disabled') !== 'true');
    candidates.sort((a, b) =>
      interactionRank(a) - interactionRank(b) ||
      (a.textContent || '').length - (b.textContent || '').length ||
      a.querySelectorAll('*').length - b.querySelectorAll('*').length
    );
    match = candidates[0] || null;
    if (!match) {
      throw new Error(`No enabled shadow element matched ${re}. Visible text:\n${allVisibleText(container).slice(0, 4000)}`);
    }
  }, { timeout: 5000 });
  fireEvent.click(match);
  return match;
}

async function clickLauncherButton(container, launcherId) {
  let target = null;
  await waitFor(() => {
    target = container.querySelector(`[data-launcher-button="${launcherId}"]`);
    expect(target).toBeTruthy();
  }, { timeout: 5000 });
  fireEvent.click(target);
}

function lastSpawnPayload() {
  const calls = window.desktopApi.openChildWindow.mock.calls;
  return calls[calls.length - 1]?.[0];
}

describe('compression GUI window-shell wiring', () => {
  test('main launcher renders exactly the three primary launch controls', async () => {
    const { container } = await renderApp();
    await expectVisibleText(container, 'Data Reduction Suite');
    const launchers = Array.from(container.querySelectorAll('[data-launcher-button]'));
    expect(launchers).toHaveLength(3);
    expect(launchers.map((el) => el.getAttribute('data-launcher-button')).sort()).toEqual([
      'analysis',
      'dataset-packaging',
      'method-editor',
    ]);
    expect(container.querySelector('.suite-floating-tools')).toBeNull();
  }, 10000);

  test('launcher buttons spawn separate child windows instead of routing inside one app shell', async () => {
    const { container } = await renderApp();
    await clickLauncherButton(container, 'dataset-packaging');
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(1));
    expect(lastSpawnPayload()).toMatchObject({
      screen: 'packaging',
      title: 'Dataset Packaging',
      width: 1480,
      height: 960,
      minWidth: 1360,
      minHeight: 860,
    });
    expect(window.location.search).toContain('mode=launcher');
    await expectVisibleText(container, 'Data Reduction Suite');

    await clickLauncherButton(container, 'method-editor');
    expect(lastSpawnPayload()).toMatchObject({ screen: 'method-editor', title: 'Analysis Method Editor' });

    await clickLauncherButton(container, 'analysis');
    expect(lastSpawnPayload()).toMatchObject({ screen: 'analysis', title: 'Method Analysis' });
  }, 10000);

  test('launcher file menu opens Dataset Packaging as a child window', async () => {
    const { container } = await renderApp();
    await expectVisibleText(container, 'Data Reduction Suite');
    fireEvent.click(screen.getByLabelText('File'));
    fireEvent.click(screen.getByText(/Open Dataset Packaging/i));
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalled());
    expect(lastSpawnPayload()).toMatchObject({ screen: 'packaging', title: 'Dataset Packaging' });
    expect(allVisibleText(container)).not.toContain('MTTP enricher');
    expect(allVisibleText(container)).not.toContain('MTDP Enricher');
  });



  test('launcher File menu actions use the same child-window spawns and Exit uses the native app handler', async () => {
    const { container } = await renderApp();
    await expectVisibleText(container, 'Data Reduction Suite');

    fireEvent.click(screen.getByLabelText('File'));
    fireEvent.click(screen.getByText(/Open Dataset Packaging/i));
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(1));
    expect(lastSpawnPayload()).toMatchObject({ screen: 'packaging', title: 'Dataset Packaging' });

    fireEvent.click(screen.getByLabelText('File'));
    fireEvent.click(screen.getByText(/Open Method/i));
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(2));
    expect(lastSpawnPayload()).toMatchObject({ screen: 'method-editor', title: 'Analysis Method Editor' });

    fireEvent.click(screen.getByLabelText('File'));
    fireEvent.click(screen.getByText(/Open Analysis/i));
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(3));
    expect(lastSpawnPayload()).toMatchObject({ screen: 'analysis', title: 'Method Analysis' });

    fireEvent.click(screen.getByLabelText('File'));
    expect(screen.getAllByText('Recent sessions').some((el) => el.closest('[aria-disabled="true"]'))).toBe(true);
    fireEvent.click(screen.getByText('Exit'));
    await waitFor(() => expect(window.desktopApi.quitApplication).toHaveBeenCalledTimes(1));
  });

  test('launcher Help menu wires bundled Guidelines, About, Licensing, and Shortcuts dialogs', async () => {
    const { container } = await renderApp();
    await expectVisibleText(container, 'Data Reduction Suite');

    fireEvent.click(screen.getByLabelText('Help'));
    expect(screen.getByRole('menu', { name: 'Help' })).toBeTruthy();
    fireEvent.click(screen.getByText('User guidelines'));
    await waitFor(() => expect(screen.getByRole('dialog', { name: /User guidelines.*NextCOMP Data Reduction Suite/i })).toBeTruthy());
    expect(allVisibleText(container)).toContain('acceptance cockpit');
    expect(allVisibleText(container)).toContain('GUIDELINES.md');
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    fireEvent.click(screen.getByLabelText('Help'));
    fireEvent.click(screen.getByText(/About this suite/i));
    await waitFor(() => expect(screen.getByRole('dialog', { name: /About.*NextCOMP Data Reduction Suite/i })).toBeTruthy());
    expect(allVisibleText(container)).toContain('Giacomo Damilano');
    expect(allVisibleText(container)).toContain('Apache License, Version 2.0');

    fireEvent.click(screen.getByRole('button', { name: /Licensing & notices/i }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: /Licensing & notices.*NextCOMP Data Reduction Suite/i })).toBeTruthy());
    expect(allVisibleText(container)).toContain('AS IS');

    fireEvent.click(screen.getByRole('button', { name: /Back to About/i }));
    await waitFor(() => expect(screen.getByRole('dialog', { name: /About.*NextCOMP Data Reduction Suite/i })).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    fireEvent.click(screen.getByLabelText('Help'));
    fireEvent.click(screen.getByText('Keyboard shortcuts'));
    await waitFor(() => expect(screen.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeTruthy());
    expect(allVisibleText(container)).toContain('Ctrl+D');
    expect(allVisibleText(container)).toContain('Ctrl+Q');
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).toBeNull());
  });

  test('visible window control glyphs call native minimize, maximize and close handlers', async () => {
    const { container } = await renderApp();
    await expectVisibleText(container, 'Data Reduction Suite');
    const minimize = container.querySelector('[data-window-control="minimize"]');
    const maximize = container.querySelector('[data-window-control="maximize"]');
    const close = container.querySelector('[data-window-control="close"]');
    expect(minimize).toBeTruthy();
    expect(maximize).toBeTruthy();
    expect(close).toBeTruthy();
    fireEvent.click(minimize);
    fireEvent.click(maximize);
    fireEvent.click(close);
    await waitFor(() => {
      expect(window.desktopApi.minimizeWindow).toHaveBeenCalledTimes(1);
      expect(window.desktopApi.toggleMaximizeWindow).toHaveBeenCalledTimes(1);
      expect(window.desktopApi.closeWindow).toHaveBeenCalledTimes(1);
    });
  });
  test('child interfaces mount without the incorrect Home/Dataset/Method/Analysis overlay menu', async () => {
    const routes = {
      packaging: 'Dataset Packaging',
      'method-editor': 'Method Editor',
      analysis: 'Choose package',
    };
    for (const [route, text] of Object.entries(routes)) {
      const { container, unmount } = await renderApp({ screen: route, mode: 'child' });
      await expectVisibleText(container, text);
      expect(container.querySelector('.suite-floating-tools')).toBeNull();
      expect(container.querySelector('.suite-win')).toBeNull();
      expect(container.querySelector('[data-launcher-button]')).toBeNull();
      unmount();
    }
  }, 20000);

  test('top-right chrome controls are wired in every child interface', async () => {
    for (const route of ['packaging', 'method-editor', 'analysis']) {
      const { container, unmount } = await renderApp({ screen: route, mode: 'child' });
      await expectVisibleText(container, route === 'analysis' ? 'Choose package' : route === 'packaging' ? 'Dataset Packaging' : 'Method Editor');

      const findControl = (action) =>
        container.querySelector(`[data-window-control="${action}"]`) ||
        shadowElements(container, `[data-window-control="${action}"]`)[0];

      const minimize = findControl('minimize');
      const maximize = findControl('maximize');
      const close = findControl('close');
      expect(minimize).toBeTruthy();
      expect(maximize).toBeTruthy();
      expect(close).toBeTruthy();

      window.desktopApi.minimizeWindow.mockClear();
      window.desktopApi.toggleMaximizeWindow.mockClear();
      window.desktopApi.closeWindow.mockClear();

      fireEvent.click(minimize);
      fireEvent.click(maximize);
      fireEvent.click(close);

      await waitFor(() => {
        expect(window.desktopApi.minimizeWindow).toHaveBeenCalledTimes(1);
        expect(window.desktopApi.toggleMaximizeWindow).toHaveBeenCalledTimes(1);
        expect(window.desktopApi.closeWindow).toHaveBeenCalledTimes(1);
      });
      unmount();
    }
  }, 20000);

  test('desktop status bars remain present across launcher and child interfaces', async () => {
    const routes = [
      ['home', 'launcher', 'Ready'],
      ['packaging', 'child', 'No package loaded'],
      ['method-editor', 'child', 'Method Editor · mtdp'],
      ['analysis', 'child', 'mtdp v0.6.0'],
    ];
    for (const [route, mode, text] of routes) {
      const { container, unmount } = await renderApp({ screen: route, mode });
      await expectVisibleText(container, text);
      unmount();
    }
  }, 20000);

  test('React-owned child windows share the same window control component contract', async () => {
    for (const route of ['packaging', 'analysis']) {
      const { container, unmount } = await renderApp({ screen: route, mode: 'child' });
      await expectVisibleText(container, route === 'packaging' ? 'Dataset Packaging' : 'Choose package');
      const roots = shadowElements(container, '.desktop-window-controls');
      expect(roots).toHaveLength(1);
      expect(roots[0].querySelectorAll('.desktop-window-control')).toHaveLength(3);
      expect(roots[0].querySelector('[data-window-control="close"]').classList.contains('desktop-window-control--close')).toBe(true);
      unmount();
    }
  }, 20000);

  test('top bars do not render duplicate right-side module metadata labels', async () => {
    const { container: packaging, unmount: unmountPackaging } = await renderApp({ screen: 'packaging', mode: 'child' });
    await expectVisibleText(packaging, 'Dataset Packaging');
    expect(allVisibleText(packaging)).not.toContain('Dataset packaging');
    unmountPackaging();

    const { container: analysis } = await renderApp({ screen: 'analysis', mode: 'child' });
    await expectVisibleText(analysis, 'Choose package');
    expect(allVisibleText(analysis)).not.toContain('Method Run · ISO 14126');
  }, 20000);

  test('invalid launcher route resolves back to the main launcher', async () => {
    const { container } = await renderApp({ screen: 'not-a-real-screen', mode: 'launcher' });
    await expectVisibleText(container, 'Data Reduction Suite');
    expect(window.location.search).toContain('screen=home');
    expect(window.location.search).toContain('mode=launcher');
  });

  test('no separate drag control is rendered; shared chrome starts one browser drag bridge call', async () => {
    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await expectVisibleText(container, 'Dataset Packaging');
    expect(allVisibleText(container)).not.toContain('Drag window');
    const title = shadowElements(container, '.menubar__title')[0];
    expect(title.getAttribute('data-window-drag')).toBe('true');
    fireEvent.mouseDown(title, { button: 0, clientY: 8 });
    await waitFor(() => expect(window.desktopApi.startWindowDrag).toHaveBeenCalledTimes(1));
    expect(window.desktopApi.startWindowDrag).toHaveBeenCalledWith(
      expect.objectContaining({ source: 'browser-event', screen: 'packaging' }),
    );
  });

  test('Method Analysis top bar double-click toggles maximize without starting a drag', async () => {
    const { container } = await renderApp({ screen: 'analysis', mode: 'child' });
    await expectVisibleText(container, 'Choose package');
    const title = shadowElements(container, '.menubar-title')[0];
    expect(title.getAttribute('data-window-drag')).toBe('true');

    fireEvent.mouseDown(title, { button: 0, detail: 2, clientY: 8 });
    expect(window.desktopApi.startWindowDrag).not.toHaveBeenCalled();

    fireEvent.doubleClick(title, { button: 0, clientY: 8 });
    await waitFor(() => expect(window.desktopApi.toggleMaximizeWindow).toHaveBeenCalledTimes(1));
  });

  test('Dataset Packaging replaces the visible old MTDP/MTTP Enricher naming', async () => {
    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await expectVisibleText(container, 'Dataset Packaging');
    expect(allVisibleText(container)).not.toContain('MTTP enricher');
    expect(allVisibleText(container)).not.toContain('MTTP Enricher');
    expect(allVisibleText(container)).not.toContain('MTDP Enricher');
  });

  test('Dataset Packaging creates a backend session and uses backend schema candidates when available', async () => {
    const schemas = [
      {
        id: 'compression-0.3.0',
        label: 'Backend Compression',
        schema: 'mechanical.compression',
        version: '0.3.0',
        conf: 100,
        detected: true,
        hint: 'Returned by test backend session.',
      },
    ];
    const backendBundle = {
      name: 'Backend Schema Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Backend Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend schema fixture' } },
      groups: [{
        id: 'backend-schema-group',
        name: 'Backend schema group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'schema_run_001.csv',
          channels: [],
          evidence: [],
          values: { specimen_name: 'schema_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-test-session', status: 'empty', schemas },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-test-session',
          status: 'package_loaded',
          schemas,
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/backend_schema_package.mtdp' },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await waitFor(() => {
      const schemaButton = shadowElements(container, '.menubar__schema')[0];
      expect(schemaButton).toBeTruthy();
      fireEvent.click(schemaButton);
    }, { timeout: 5000 });
    await expectVisibleText(container, 'Backend Compression');
    await expectVisibleText(container, 'Returned by test backend session.');
  }, 15000);

  test('Dataset Packaging schema override is sent to backend session', async () => {
    const schemas = [
      {
        id: 'compression-0.3.0',
        label: 'Backend Compression',
        schema: 'mechanical.compression',
        version: '0.3.0',
        conf: 100,
        detected: true,
        hint: 'Detected by backend.',
      },
      {
        id: 'tensile-0.3.0',
        label: 'Backend Tensile',
        schema: 'mechanical.tensile',
        version: '0.3.0',
        conf: 0,
        detected: false,
        hint: 'Selectable backend schema.',
      },
    ];
    const initialBundle = {
      name: 'Backend Schema Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Backend Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend schema fixture' } },
      groups: [{
        id: 'backend-schema-group',
        name: 'Backend schema group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'schema_run_001.csv',
          channels: [],
          evidence: [],
          values: { specimen_name: 'schema_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    const overriddenBundle = {
      ...initialBundle,
      schemaId: 'tensile-0.3.0',
      schemaLabel: 'Backend Tensile',
      schemaOverridden: true,
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-schema-session', status: 'empty', schemas },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-schema-session',
          status: 'package_loaded',
          schemas,
          bundle: initialBundle,
          source_summary: { package_path: 'C:/fixtures/backend_schema_package.mtdp' },
        },
      }),
      setSchema: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-schema-session',
          status: 'package_loaded',
          schemas,
          bundle: overriddenBundle,
          source_summary: { package_path: 'C:/fixtures/backend_schema_package.mtdp' },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await waitFor(() => expect(window.desktopApi.packaging.openPackageDialog).toHaveBeenCalledTimes(1));
    const schemaButton = shadowElements(container, '.menubar__schema')[0];
    expect(schemaButton).toBeTruthy();
    fireEvent.click(schemaButton);
    await expectVisibleText(container, 'Backend Tensile');
    const radios = shadowElements(container, 'input[name="schema"]');
    fireEvent.click(radios[1]);
    await clickShadowText(container, /Use this schema/i);

    await waitFor(() => {
      expect(window.desktopApi.packaging.setSchema).toHaveBeenCalledWith({
        session_id: 'pkg-schema-session',
        schema_id: 'tensile-0.3.0',
      });
    });
    await expectVisibleText(container, 'Backend Tensile');
    await expectVisibleText(container, '(manual)');
  }, 15000);

  test('Dataset Packaging visible Open MTDP package action loads backend package view model', async () => {
    const backendBundle = {
      name: 'Backend Fixture Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend fixture' } },
      groups: [{
        id: 'backend-group',
        name: 'Backend fixture group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'golden_run_001', width: '12.0', thickness: '2.0' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-open-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-open-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
          messages: ['Loaded package golden_compression_group.mtdp.'],
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.openPackageDialog).toHaveBeenCalledWith({
        session_id: 'pkg-open-session',
      });
    });
    await expectVisibleText(container, 'Backend Fixture Package');
    await expectVisibleText(container, 'Backend fixture group');
    await expectVisibleText(container, 'golden_run_001');
    expect(allVisibleText(container)).not.toContain('Demo: opening an existing .mtdp package is out of scope here');
  }, 15000);

  test('Dataset Packaging visible Validate action renders backend validation issues', async () => {
    const backendBundle = {
      name: 'Backend Validation Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend fixture' } },
      groups: [{
        id: 'backend-group',
        name: 'Backend validation group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'golden_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    const validatedBundle = {
      ...backendBundle,
      backendValidation: {
        source: 'backend',
        group_id: 'backend-group',
        group_name: 'Backend validation group',
        ok: false,
        error_count: 1,
        warning_count: 0,
        ready_runs: 0,
        total_runs: 1,
        passed: [{ text: 'Backend schema validation ran.' }],
        skipped: [{ text: 'Metadata edit synchronization' }],
        issues: [{
          severity: 'error',
          scope: 'run',
          group_id: 'backend-group',
          run_id: 'run_001',
          category: 'metadata',
          field: 'width',
          code: 'required',
          message: 'Width is required.',
          text: 'run_001 · Width is required.',
          target: { type: 'run', groupId: 'backend-group', runId: 'run_001', fieldId: 'width' },
        }],
      },
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-validate-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-validate-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
      validateGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-validate-session',
          status: 'package_loaded',
          schemas: [],
          bundle: validatedBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Validation Package');
    await clickShadowText(container, /Validate/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.validateGroup).toHaveBeenCalledWith({
        session_id: 'pkg-validate-session',
        group_id: 'backend-group',
      });
    });
    await expectVisibleText(container, 'Issues');
    await expectVisibleText(container, 'run_001 · Width is required.');
  }, 15000);

  test('Dataset Packaging Export action writes selected group through backend bridge', async () => {
    const backendBundle = {
      name: 'Backend Export Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend export fixture' } },
      groups: [{
        id: 'export-group',
        name: 'Backend export group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          supplemental: [],
          values: {
            specimen_name: 'golden_run_001',
            width: '12.0',
            thickness: '2.0',
            validity: 'rejected',
            primary_failure_mode: 'not_recorded',
            failure_location: 'not_recorded',
          },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    const exportedBundle = {
      ...backendBundle,
      backendValidation: {
        source: 'backend',
        group_id: 'export-group',
        group_name: 'Backend export group',
        ok: true,
        error_count: 0,
        warning_count: 0,
        ready_runs: 1,
        total_runs: 1,
        passed: [{ text: 'Backend export validation passed.' }],
        skipped: [],
        issues: [],
      },
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-export-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-export-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
      exportGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-export-session',
          status: 'package_loaded',
          schemas: [],
          bundle: exportedBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
          export: {
            source: 'backend',
            groupId: 'export-group',
            fileName: 'backend_export.mtdp',
            path: 'C:/exports/backend_export.mtdp',
            runCount: 1,
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Export Package');
    await clickShadowText(container, /Export/i, 'button');
    await expectVisibleText(container, 'Export MTDP package');
    await expectVisibleText(container, '1 of 1');
    await clickShadowText(container, /Export 1 of 1 runs/i, 'button');

    await waitFor(() => {
      expect(window.desktopApi.packaging.exportGroup).toHaveBeenCalledWith({
        session_id: 'pkg-export-session',
        group_id: 'export-group',
        initial_dir: '~/Documents/MTDP exports',
        default_name: 'Backend Export Package.mtdp',
      });
    });
    await expectVisibleText(container, 'Exported backend_export.mtdp');
  }, 15000);

  test('Dataset Packaging opens the exported package in Analysis with backend handoff payload', async () => {
    const backendBundle = {
      name: 'Backend Export Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend export fixture' } },
      groups: [{
        id: 'export-group',
        name: 'Backend export group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          supplemental: [],
          values: {
            specimen_name: 'golden_run_001',
            width: '12.0',
            thickness: '2.0',
            validity: 'rejected',
            primary_failure_mode: 'not_recorded',
            failure_location: 'not_recorded',
          },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    const exportedBundle = {
      ...backendBundle,
      backendValidation: {
        source: 'backend',
        group_id: 'export-group',
        group_name: 'Backend export group',
        ok: true,
        error_count: 0,
        warning_count: 0,
        ready_runs: 1,
        total_runs: 1,
        passed: [{ text: 'Backend export validation passed.' }],
        skipped: [],
        issues: [],
      },
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-handoff-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-handoff-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
      exportGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-handoff-session',
          status: 'package_loaded',
          schemas: [],
          bundle: exportedBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
          export: {
            source: 'backend',
            groupId: 'export-group',
            fileName: 'backend_export.mtdp',
            path: 'C:/exports/backend_export.mtdp',
            runCount: 1,
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await clickShadowText(container, /Export/i, 'button');
    await clickShadowText(container, /Export 1 of 1 runs/i, 'button');
    await waitFor(() => expect(window.desktopApi.packaging.exportGroup).toHaveBeenCalledTimes(1));

    await clickShadowText(container, /^File$/i, '.menu__btn');
    await clickShadowText(container, /Open exported package in Analysis/i, '.menu__item');
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(1));
    expect(lastSpawnPayload()).toMatchObject({
      screen: 'analysis',
      title: 'Method Analysis',
      initial_package_path: 'C:/exports/backend_export.mtdp',
    });
  }, 15000);

  test('Dataset Packaging File menu exports all ready groups through backend bridge', async () => {
    const backendBundle = {
      name: 'Backend Export All Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend export fixture' } },
      groups: [{
        id: 'export-all-group',
        name: 'Backend export all group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          supplemental: [],
          values: {
            specimen_name: 'golden_run_001',
            width: '12.0',
            thickness: '2.0',
            validity: 'rejected',
            primary_failure_mode: 'not_recorded',
            failure_location: 'not_recorded',
          },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-export-all-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-export-all-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
      exportAllReady: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-export-all-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
          exportAll: {
            source: 'backend',
            outputDir: 'C:/exports',
            exportedCount: 1,
            skippedCount: 0,
            failedCount: 0,
            exports: [{ groupId: 'export-all-group', fileName: 'backend_export_all.mtdp' }],
            skipped: [],
            failed: [],
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Export All Package');
    await clickShadowText(container, /^File$/i, '.menu__btn');
    await clickShadowText(container, /Export all ready groups/i, '.menu__item');

    await waitFor(() => {
      expect(window.desktopApi.packaging.exportAllReady).toHaveBeenCalledWith({
        session_id: 'pkg-export-all-session',
        initial_dir: '~/Documents/MTDP exports',
      });
    });
    await expectVisibleText(container, 'Exported 1 ready group');
  }, 15000);

  test('Dataset Packaging metadata field edits commit to backend session on blur', async () => {
    const backendBundle = {
      name: 'Backend Editable Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend fixture' } },
      groups: [{
        id: 'backend-group',
        name: 'Backend editable group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'golden_run_001', width: '12.0', thickness: '2.0' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    const datasetEditedBundle = {
      ...backendBundle,
      dataset: { values: { sample_type: 'Edited backend fixture' } },
    };
    const runEditedBundle = {
      ...datasetEditedBundle,
      groups: [{
        ...datasetEditedBundle.groups[0],
        runs: [{
          ...datasetEditedBundle.groups[0].runs[0],
          values: { ...datasetEditedBundle.groups[0].runs[0].values, width: '13.5' },
        }],
      }],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-edit-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-edit-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/golden_compression_group.mtdp' },
        },
      }),
      updateDatasetFields: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-edit-session',
          status: 'package_loaded',
          schemas: [],
          bundle: datasetEditedBundle,
        },
      }),
      updateRunFields: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-edit-session',
          status: 'package_loaded',
          schemas: [],
          bundle: runEditedBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Editable Package');

    const datasetInput = shadowElements(container, 'input[data-fkey="sample_type"]')[0];
    expect(datasetInput).toBeTruthy();
    fireEvent.change(datasetInput, { target: { value: 'Edited backend fixture' } });
    fireEvent.blur(datasetInput);
    await waitFor(() => {
      expect(window.desktopApi.packaging.updateDatasetFields).toHaveBeenCalledWith({
        session_id: 'pkg-edit-session',
        group_id: 'backend-group',
        patch: { sample_type: 'Edited backend fixture' },
      });
    });

    await clickShadowText(container, /run_001/i);
    const widthInput = await waitFor(() => {
      const match = shadowElements(container, 'input[data-fkey="width"]')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.change(widthInput, { target: { value: '13.5' } });
    fireEvent.blur(widthInput);
    await waitFor(() => {
      expect(window.desktopApi.packaging.updateRunFields).toHaveBeenCalledWith({
        session_id: 'pkg-edit-session',
        group_id: 'backend-group',
        run_id: 'run_001',
        patch: { width: '13.5' },
      });
    });
  }, 15000);

  test('Dataset Packaging regenerates metadata forms from backend schema sections', async () => {
    const schemaForm = {
      source: 'SchemaRegistry',
      schema: 'mechanical.flexural',
      schemaId: 'flexural-0.1.0',
      version: '0.1.0',
      label: 'Flexural',
      unitSystem: 'mechanical_metric_mm_N',
      fieldsById: {
        fixture_family: {
          id: 'fixture_family',
          label: 'Fixture family',
          type: 'string',
          hardRequired: true,
          importance: 'required',
        },
        specimen_name: {
          id: 'specimen_name',
          label: 'Specimen name',
          type: 'string',
          hardRequired: true,
          importance: 'required',
        },
        span_length: {
          id: 'span_length',
          label: 'Span length',
          type: 'float',
          hardRequired: true,
          importance: 'required',
          units: ['mm', 'cm'],
          stdUnit: 'mm',
          dim: 'length',
          min: 0,
        },
      },
      datasetSections: [{
        id: 'fixture_setup',
        label: 'Fixture Setup',
        scope: 'dataset',
        fields: [{ id: 'fixture_family' }],
      }],
      runSections: [{
        id: 'flexural_geometry',
        label: 'Flexural Geometry',
        scope: 'run',
        fields: [{ id: 'specimen_name' }, { id: 'span_length' }],
      }],
      channelFamilies: [
        { id: 'load', label: 'Load', required: true, repeatable: false, units: ['N'], std: 'N', dim: 'force' },
        { id: 'deflection', label: 'Deflection', required: true, repeatable: false, units: ['mm'], std: 'mm', dim: 'length' },
        { id: 'ignore', label: 'Ignore - not exported', repeatable: true, units: ['-'], std: '-' },
      ],
      unitFactors: { length: { mm: 1, cm: 10 }, force: { N: 1 } },
    };
    const backendBundle = {
      name: 'Backend Flexural Package',
      schemaId: 'flexural-0.1.0',
      schemaLabel: 'Flexural',
      schemaVersion: '0.1.0',
      schemaForm,
      detectConfidence: 100,
      schemaOverridden: true,
      dataset: { values: { fixture_family: 'Three-point bend fixture' } },
      groups: [{
        id: 'flex-group',
        name: 'Flexural coupon',
        units: { span_length: 'mm' },
        runs: [{
          id: 'run_001',
          fileLabel: 'flex_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          supplemental: [],
          values: { specimen_name: 'flex_run_001', span_length: '80' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'flex_run_001.csv', yaml: 'flex_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-schema-form-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-schema-form-session',
          status: 'package_loaded',
          schemas: [],
          schemaForm,
          bundle: backendBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Flexural Package');
    await expectVisibleText(container, 'Fixture Setup');
    await expectVisibleText(container, 'Flexural Geometry');

    expect(shadowElements(container, 'input[data-fkey="fixture_family"]')).toHaveLength(1);
    expect(shadowElements(container, 'input[data-fkey="span_length"]')).toHaveLength(1);
    expect(shadowElements(container, 'input[data-fkey="width"]')).toHaveLength(0);
    expect(shadowElements(container, 'input[data-fkey="gauge_length"]')).toHaveLength(0);
  }, 15000);

  test('Dataset Packaging grid bulk edits and unit policy commit to backend session', async () => {
    const backendBundle = {
      name: 'Backend Grid Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Grid fixture' } },
      groups: [{
        id: 'grid-group',
        name: 'Backend grid group',
        units: { width: 'mm' },
        runs: [
          {
            id: 'run_001',
            fileLabel: 'grid_run_001.csv',
            channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
            evidence: [],
            values: { specimen_name: 'grid_run_001', width: '12.0', thickness: '2.0' },
          },
          {
            id: 'run_002',
            fileLabel: 'grid_run_002.csv',
            channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
            evidence: [],
            values: { specimen_name: 'grid_run_002', width: '13.0', thickness: '2.1' },
          },
        ],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    const bulkEditedBundle = {
      ...backendBundle,
      groups: [{
        ...backendBundle.groups[0],
        runs: backendBundle.groups[0].runs.map((run) => ({
          ...run,
          values: { ...run.values, width: '14.0' },
        })),
      }],
    };
    const runEditedBundle = {
      ...bulkEditedBundle,
      groups: [{
        ...bulkEditedBundle.groups[0],
        runs: bulkEditedBundle.groups[0].runs.map((run) => (
          run.id === 'run_001'
            ? { ...run, values: { ...run.values, width: '15.0' } }
            : run
        )),
      }],
    };
    const unitEditedBundle = {
      ...runEditedBundle,
      groups: [{
        ...runEditedBundle.groups[0],
        units: { width: 'cm' },
        runs: runEditedBundle.groups[0].runs.map((run) => ({
          ...run,
          values: { ...run.values, width__unit: 'cm' },
        })),
      }],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-grid-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grid-session',
          status: 'package_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { package_path: 'C:/fixtures/grid_package.mtdp' },
        },
      }),
      updateGroupRunFields: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grid-session',
          status: 'package_loaded',
          schemas: [],
          bundle: bulkEditedBundle,
        },
      }),
      updateRunFields: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grid-session',
          status: 'package_loaded',
          schemas: [],
          bundle: runEditedBundle,
        },
      }),
      updateRunFieldMatrix: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grid-session',
          status: 'package_loaded',
          schemas: [],
          bundle: runEditedBundle,
        },
      }),
      setGroupRunUnit: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grid-session',
          status: 'package_loaded',
          schemas: [],
          bundle: unitEditedBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Grid Package');

    await clickShadowText(container, /Grid · all runs/i);
    const allWidth = await waitFor(() => {
      const match = shadowElements(container, 'input[data-grid-all="width"]')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.change(allWidth, { target: { value: '14.0' } });
    fireEvent.blur(allWidth);
    await waitFor(() => {
      expect(window.desktopApi.packaging.updateGroupRunFields).toHaveBeenCalledWith({
        session_id: 'pkg-grid-session',
        group_id: 'grid-group',
        patch: { width: '14.0' },
      });
    });

    const runWidth = await waitFor(() => {
      const match = shadowElements(container, 'input[data-runid="run_001"][data-fkey="width"]')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.change(runWidth, { target: { value: '15.0' } });
    fireEvent.blur(runWidth);
    await waitFor(() => {
      expect(window.desktopApi.packaging.updateRunFields).toHaveBeenCalledWith({
        session_id: 'pkg-grid-session',
        group_id: 'grid-group',
        run_id: 'run_001',
        patch: { width: '15.0' },
      });
    });

    const runRow = shadowElements(container, '.trow--run')[0];
    expect(runRow).toBeTruthy();
    fireEvent.click(runRow);
    const widthUnit = await waitFor(() => {
      const match = shadowElements(container, 'select[data-unit-fkey="width"]')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.change(widthUnit, { target: { value: 'cm' } });
    await clickShadowText(container, /Convert values/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.setGroupRunUnit).toHaveBeenCalledWith({
        session_id: 'pkg-grid-session',
        group_id: 'grid-group',
        field_id: 'width',
        unit: 'cm',
        convert: true,
      });
    });
  }, 15000);

  test('Dataset Packaging grouping controls commit to backend session', async () => {
    const baseBundle = {
      name: 'Backend Grouping Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Grouping fixture' } },
      groups: [{
        id: 'group-a',
        name: 'Group A',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'grouping_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'grouping_run_001', width: '12.0', thickness: '2.0' },
        }],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    const createdBundle = {
      ...baseBundle,
      groups: [
        baseBundle.groups[0],
        { id: 'group-b', name: 'New group', units: {}, runs: [] },
      ],
    };
    const renamedBundle = {
      ...createdBundle,
      groups: [
        createdBundle.groups[0],
        { ...createdBundle.groups[1], name: 'Renamed Group' },
      ],
    };
    const movedBundle = {
      ...renamedBundle,
      groups: [
        { ...renamedBundle.groups[0], runs: [] },
        { ...renamedBundle.groups[1], runs: [renamedBundle.groups[0].runs[0]] },
      ],
    };
    const deletedBundle = {
      ...movedBundle,
      groups: [movedBundle.groups[0]],
      unassigned: [movedBundle.groups[1].runs[0]],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-grouping-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grouping-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
          source_summary: { package_path: 'C:/fixtures/grouping_package.mtdp' },
        },
      }),
      createGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grouping-session',
          status: 'package_loaded',
          schemas: [],
          bundle: createdBundle,
        },
      }),
      renameGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grouping-session',
          status: 'package_loaded',
          schemas: [],
          bundle: renamedBundle,
        },
      }),
      moveRun: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grouping-session',
          status: 'package_loaded',
          schemas: [],
          bundle: movedBundle,
        },
      }),
      deleteGroup: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-grouping-session',
          status: 'package_loaded',
          schemas: [],
          bundle: deletedBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Grouping Package');

    await clickShadowText(container, /New group/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.createGroup).toHaveBeenCalledWith({
        session_id: 'pkg-grouping-session',
        name: 'New group',
      });
    });

    const renameInput = await waitFor(() => {
      const match = shadowElements(container, 'input.renamein')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.change(renameInput, { target: { value: 'Renamed Group' } });
    fireEvent.blur(renameInput);
    await waitFor(() => {
      expect(window.desktopApi.packaging.renameGroup).toHaveBeenCalledWith({
        session_id: 'pkg-grouping-session',
        group_id: 'group-b',
        name: 'Renamed Group',
      });
    });

    const runRow = await waitFor(() => {
      const match = shadowElements(container, '.trow--run')
        .find((el) => (el.textContent || '').includes('run_001'));
      expect(match).toBeTruthy();
      return match;
    });
    const kebab = runRow.querySelector('.kebab');
    expect(kebab).toBeTruthy();
    fireEvent.click(kebab);
    await clickShadowText(container, /Move to.*Renamed Group/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.moveRun).toHaveBeenCalledWith({
        session_id: 'pkg-grouping-session',
        run_id: 'run_001',
        from_group_id: 'group-a',
        target_group_id: 'group-b',
      });
    });

    const deleteGroup = await waitFor(() => {
      const match = shadowElements(container, 'button[data-group-action="delete"][data-groupid="group-b"]')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.click(deleteGroup);
    await waitFor(() => {
      expect(window.desktopApi.packaging.deleteGroup).toHaveBeenCalledWith({
        session_id: 'pkg-grouping-session',
        group_id: 'group-b',
      });
    });
    await expectVisibleText(container, 'Unassigned');
    await expectVisibleText(container, 'grouping_run_001');
  }, 15000);

  test('Dataset Packaging Propose groups action uses backend proposal and apply commands', async () => {
    const baseBundle = {
      name: 'Backend Proposal Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend proposal fixture' } },
      groups: [{
        id: 'manual-group',
        name: 'Manual group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'proposal_run_001.csv',
          channels: [],
          evidence: [],
          values: { specimen_name: 'proposal_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    const proposedBundle = {
      ...baseBundle,
      groups: [{
        ...baseBundle.groups[0],
        id: 'backend-proposed',
        name: 'Backend Proposed Group',
      }],
    };
    const proposal = {
      id: 'SampleTypeGrouper:0.1.0',
      source: 'backend',
      engine: 'SampleTypeGrouper',
      conf: 95,
      title: '1 group - backend sample-type proposal',
      description: 'Backend SampleTypeGrouper proposal from parsed source files.',
      groups: [{ id: 'backend-proposed', name: 'Backend Proposed Group', run_count: 1 }],
      unassigned_count: 0,
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-propose-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-propose-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
          source_summary: { package_path: 'C:/fixtures/backend_proposal_package.mtdp' },
        },
      }),
      proposeGroups: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-propose-session',
          recommended_id: proposal.id,
          proposals: [proposal],
        },
      }),
      applyGroupingProposal: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-propose-session',
          status: 'package_loaded',
          schemas: [],
          bundle: proposedBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Proposal Package');

    await clickShadowText(container, /Propose groups/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.proposeGroups).toHaveBeenCalledWith({
        session_id: 'pkg-propose-session',
      });
    });
    await expectVisibleText(container, 'backend sample-type proposal');

    await clickShadowText(container, /Apply proposal/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.applyGroupingProposal).toHaveBeenCalledWith({
        session_id: 'pkg-propose-session',
        proposal_id: proposal.id,
      });
    });
    await expectVisibleText(container, 'Backend Proposed Group');
  }, 15000);

  test('Dataset Packaging evidence and supplemental dialogs commit to backend session', async () => {
    const baseBundle = {
      name: 'Backend Attachment Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Attachment fixture' } },
      groups: [{
        id: 'attachment-group',
        name: 'Attachment group',
        units: {},
        supplemental: [],
        runs: [{
          id: 'run_001',
          fileLabel: 'attachment_run_001.csv',
          channels: [],
          evidence: [],
          supplemental: [],
          values: { specimen_name: 'attachment_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [],
      supplemental: [],
    };
    const imageBundle = {
      ...baseBundle,
      groups: [{
        ...baseBundle.groups[0],
        runs: [{
          ...baseBundle.groups[0].runs[0],
          evidence: [{ name: 'run_001_failure.jpg', view: 'failure' }],
        }],
      }],
    };
    const noImageBundle = {
      ...baseBundle,
      groups: [{
        ...baseBundle.groups[0],
        runs: [{ ...baseBundle.groups[0].runs[0], evidence: [] }],
      }],
    };
    const supplementalBundle = {
      ...baseBundle,
      supplemental: [{ name: 'operator_notes.txt', scope: 'dataset', role: 'documents' }],
      groups: [{
        ...baseBundle.groups[0],
        supplemental: [{ name: 'operator_notes.txt', scope: 'dataset', role: 'documents' }],
      }],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-attach-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-attach-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
          source_summary: { package_path: 'C:/fixtures/backend_attachment_package.mtdp' },
        },
      }),
      addImageEvidence: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-attach-session',
          status: 'package_loaded',
          schemas: [],
          bundle: imageBundle,
        },
      }),
      removeImageEvidence: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-attach-session',
          status: 'package_loaded',
          schemas: [],
          bundle: noImageBundle,
        },
      }),
      addSupplementalFiles: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-attach-session',
          status: 'package_loaded',
          schemas: [],
          bundle: supplementalBundle,
        },
      }),
      removeSupplementalFile: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-attach-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend Attachment Package');

    const runRow = await waitFor(() => {
      const match = shadowElements(container, '.trow--run')
        .find((el) => (el.textContent || '').includes('run_001'));
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.click(runRow);
    await clickShadowText(container, /Manage run image evidence/i);
    await clickShadowText(container, /Add image/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.addImageEvidence).toHaveBeenCalledWith({
        session_id: 'pkg-attach-session',
        group_id: 'attachment-group',
        run_id: 'run_001',
        view: 'failure',
      });
    });
    await expectVisibleText(container, 'run_001_failure.jpg');

    const removeImage = await waitFor(() => {
      const match = shadowElements(container, '.modal .rm')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.click(removeImage);
    await waitFor(() => {
      expect(window.desktopApi.packaging.removeImageEvidence).toHaveBeenCalledWith({
        session_id: 'pkg-attach-session',
        group_id: 'attachment-group',
        run_id: 'run_001',
        index: 0,
      });
    });
    await clickShadowText(container, /Done/i);

    await clickShadowText(container, /^Attachment group/i);
    await clickShadowText(container, /Manage supplemental files/i);
    await clickShadowText(container, /Add file/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.addSupplementalFiles).toHaveBeenCalledWith({
        session_id: 'pkg-attach-session',
        group_id: 'attachment-group',
        run_id: null,
        scope: 'dataset',
      });
    });
    await expectVisibleText(container, 'operator_notes.txt');

    const removeSupplemental = await waitFor(() => {
      const match = shadowElements(container, '.modal .rm')[0];
      expect(match).toBeTruthy();
      return match;
    });
    fireEvent.click(removeSupplemental);
    await waitFor(() => {
      expect(window.desktopApi.packaging.removeSupplementalFile).toHaveBeenCalledWith({
        session_id: 'pkg-attach-session',
        group_id: 'attachment-group',
        run_id: null,
        index: 0,
      });
    });
  }, 15000);

  test('Dataset Packaging YAML sidecar rematch commits to backend session', async () => {
    const baseBundle = {
      name: 'Backend YAML Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'YAML fixture' } },
      groups: [{
        id: 'yaml-group',
        name: 'YAML group',
        units: {},
        runs: [{
          id: 'golden_run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [],
          evidence: [],
          supplemental: [],
          values: { specimen_name: 'Before rematch' },
          sidecarStatus: 'YAML detected',
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    const rematchedBundle = {
      ...baseBundle,
      groups: [{
        ...baseBundle.groups[0],
        runs: [{
          ...baseBundle.groups[0].runs[0],
          values: {
            ...baseBundle.groups[0].runs[0].values,
            specimen_name: 'CAG-CF-ER-Comp-E1',
          },
          sidecarStatus: 'YAML imported',
        }],
      }],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-yaml-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-yaml-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
          source_summary: { package_path: 'C:/fixtures/backend_yaml_package.mtdp' },
        },
      }),
      rematchYamlSidecars: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-yaml-session',
          status: 'package_loaded',
          schemas: [],
          bundle: rematchedBundle,
          yamlRematch: {
            source: 'backend',
            rule: 'same_stem',
            groupId: 'yaml-group',
            runCount: 1,
            pairedCount: 1,
            updatedCount: 1,
            requiresMappingCount: 0,
            warningCount: 0,
            warnings: [],
            pairs: [{
              runId: 'golden_run_001',
              csv: 'golden_run_001.csv',
              yaml: 'golden_run_001.yaml',
              status: 'YAML imported',
              paired: true,
              importedFieldCount: 4,
              unknownKeyCount: 0,
              conflictCount: 0,
              requiresMapping: false,
            }],
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend YAML Package');

    await clickShadowText(container, /review pairing/i, '.filesdrawer__rematch');
    await expectVisibleText(container, 'Review / re-match YAML sidecars');
    await clickShadowText(container, /Re-run matching/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.rematchYamlSidecars).toHaveBeenCalledWith({
        session_id: 'pkg-yaml-session',
        group_id: 'yaml-group',
        apply_all: true,
      });
    });
    await expectVisibleText(container, 'YAML imported');
  }, 15000);

  test('Dataset Packaging YAML mapping review applies a backend-authored mapping profile', async () => {
    const baseBundle = {
      name: 'Backend YAML Mapping Package',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 100,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'YAML mapping fixture' } },
      groups: [{
        id: 'yaml-mapping-group',
        name: 'YAML mapping group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'legacy_comp_001.csv',
          channels: [],
          evidence: [],
          supplemental: [],
          values: {},
          sidecarStatus: 'YAML needs review',
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'legacy_comp_001.csv', yaml: 'legacy_comp_001.yaml' }],
      supplemental: [],
    };
    const appliedBundle = {
      ...baseBundle,
      groups: [{
        ...baseBundle.groups[0],
        runs: [{
          ...baseBundle.groups[0].runs[0],
          values: { operator: 'Mapping Tester', width: 9.8, width__unit: 'mm' },
          sidecarStatus: 'Mapping applied',
        }],
      }],
    };
    const mappingRows = [{
      sourceKey: 'legacy.tester',
      rawText: 'Mapping Tester',
      status: 'ambiguous',
      action: 'map',
      mapping: {
        source_key: 'legacy.tester',
        action: 'map',
        target_field_id: 'operator',
        value_path: 'legacy.tester',
        unit: null,
        status: 'ambiguous',
        user_corrected: false,
      },
    }, {
      sourceKey: 'geometry.dimension_a',
      rawText: '{"unit":"mm","value":9.8}',
      status: 'alias_mapped',
      action: 'map',
      mapping: {
        source_key: 'geometry.dimension_a',
        action: 'map',
        target_field_id: 'width',
        value_path: 'geometry.dimension_a',
        unit: 'mm',
        status: 'alias_mapped',
        user_corrected: false,
      },
    }];
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-yaml-map-session', status: 'empty', schemas: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-yaml-map-session',
          status: 'package_loaded',
          schemas: [],
          bundle: baseBundle,
          source_summary: { package_path: 'C:/fixtures/backend_yaml_mapping_package.mtdp' },
        },
      }),
      reviewYamlMapping: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-yaml-map-session',
          status: 'package_loaded',
          yamlMappingReview: {
            source: 'backend',
            groupId: 'yaml-mapping-group',
            runId: 'run_001',
            yamlPath: 'C:/fixtures/legacy_comp_001.yaml',
            profileId: 'supplemental_yaml_profile',
            structureSignature: 'sha256:test',
            applyAllDefault: true,
            fieldOptions: [
              { id: 'operator', label: 'Operator', type: 'string', acceptedUnits: [] },
              { id: 'width', label: 'Width', type: 'float', acceptedUnits: ['mm'], standardUnit: 'mm' },
            ],
            rows: mappingRows,
            summary: { rowCount: 2, mappedCount: 2, reviewCount: 1 },
          },
        },
      }),
      applyYamlMappingProfile: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-yaml-map-session',
          status: 'package_loaded',
          schemas: [],
          bundle: appliedBundle,
          yamlMapping: {
            source: 'backend',
            profileId: 'supplemental_yaml_profile',
            appliedCount: 1,
            runs: [{ runId: 'run_001', status: 'Mapping applied' }],
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    await clickShadowText(container, /Open MTDP package/i);
    await expectVisibleText(container, 'Backend YAML Mapping Package');
    await clickShadowText(container, /review pairing/i, '.filesdrawer__rematch');
    await clickShadowText(container, /Review mapping/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.packaging.reviewYamlMapping).toHaveBeenCalledWith({
        session_id: 'pkg-yaml-map-session',
        group_id: 'yaml-mapping-group',
        run_id: 'run_001',
      });
    });
    await expectVisibleText(container, 'Mapping profile');
    await expectVisibleText(container, 'legacy.tester');
    await clickShadowText(container, /Apply mapping profile/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.packaging.applyYamlMappingProfile).toHaveBeenCalledWith({
        session_id: 'pkg-yaml-map-session',
        group_id: 'yaml-mapping-group',
        run_id: 'run_001',
        profile_id: 'supplemental_yaml_profile',
        apply_all: true,
        mappings: mappingRows.map((row) => row.mapping),
      });
    });
    await expectVisibleText(container, 'Mapping applied');
  }, 15000);

  test('module keyboard shortcuts spawn child windows from the launcher', async () => {
    await renderApp();
    fireEvent.keyDown(window, { key: 'd', ctrlKey: true });
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(1));
    expect(lastSpawnPayload()).toMatchObject({ screen: 'packaging', title: 'Dataset Packaging' });
    fireEvent.keyDown(window, { key: 'm', ctrlKey: true });
    expect(lastSpawnPayload()).toMatchObject({ screen: 'method-editor' });
    fireEvent.keyDown(window, { key: 'a', ctrlKey: true });
    expect(lastSpawnPayload()).toMatchObject({ screen: 'analysis' });
  });

  test('shared shell and module keyboard shortcuts work in child windows', async () => {
    await renderApp({ screen: 'packaging', mode: 'child' });
    fireEvent.keyDown(window, { key: 'F11' });
    fireEvent.keyDown(window, { key: 'm', ctrlKey: true, shiftKey: true });
    fireEvent.keyDown(window, { key: 'w', ctrlKey: true });
    await waitFor(() => {
      expect(window.desktopApi.toggleMaximizeWindow).toHaveBeenCalledTimes(1);
      expect(window.desktopApi.minimizeWindow).toHaveBeenCalledTimes(1);
      expect(window.desktopApi.closeWindow).toHaveBeenCalledTimes(1);
      expect(window.desktopApi.openChildWindow).not.toHaveBeenCalled();
    });
    fireEvent.keyDown(window, { key: 'a', ctrlKey: true });
    await waitFor(() => expect(window.desktopApi.openChildWindow).toHaveBeenCalledTimes(1));
    expect(lastSpawnPayload()).toMatchObject({ screen: 'analysis', title: 'Method Analysis' });
  });

  test('top menu buttons close their open menu on a second click', async () => {
    const packaging = await renderApp({ screen: 'packaging', mode: 'child' });
    const packagingFileMenu = await clickShadowText(packaging.container, /^File$/i, '.menu__btn');
    await waitFor(() => expect(shadowElements(packaging.container, '.menu__pop')).toHaveLength(1));
    fireEvent.click(packagingFileMenu);
    await waitFor(() => expect(shadowElements(packaging.container, '.menu__pop')).toHaveLength(0));
    cleanup();

    const analysis = await renderApp({ screen: 'analysis', mode: 'child' });
    const analysisFileMenu = await clickShadowText(analysis.container, /^File$/i, '.menu-item');
    await waitFor(() => expect(shadowElements(analysis.container, '.menu-pop')).toHaveLength(1));
    fireEvent.click(analysisFileMenu);
    await waitFor(() => expect(shadowElements(analysis.container, '.menu-pop')).toHaveLength(0));
  }, 10000);

  test('Dataset Packaging source opening does not fall back to seeded ingest data', async () => {
    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await expectVisibleText(container, 'No package loaded');
    expect(window.INITIAL_BUNDLE).toBeUndefined();
    expect(window.IngestModal).toBeUndefined();
    expect(allVisibleText(container)).not.toContain('CAG-CF-ER-Comp');

    await clickShadowText(container, /Select source folder/i);
    await expectVisibleText(container, 'Open source files requires the desktop backend bridge.');
    expect(allVisibleText(container)).not.toContain('Raw inputs → MTDP supra container');
    expect(allVisibleText(container)).not.toContain('Package ready');
  }, 12000);

  test('Dataset Packaging visible source folder action loads backend source view model', async () => {
    const backendBundle = {
      name: 'Backend Source Batch',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 94,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Backend source' } },
      groups: [{
        id: 'source-group',
        name: 'Backend source group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'golden_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'golden_run_001', width: '12.0' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'golden_run_001.csv', yaml: 'golden_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-source-session', status: 'empty', schemas: [] },
      }),
      openSourcesDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-source-session',
          status: 'sources_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { source_count: 3, paths: ['C:/fixtures/source'] },
          messages: ['Loaded 3 source files.'],
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await expectVisibleText(container, 'Dataset Packaging');
    await clickShadowText(container, /Select source folder/i);
    await waitFor(() => {
      expect(window.desktopApi.packaging.openSourcesDialog).toHaveBeenCalledWith({
        session_id: 'pkg-source-session',
        kind: 'folder',
      });
    });
    await expectVisibleText(container, 'Backend Source Batch');
    await expectVisibleText(container, 'Backend source group');
    await expectVisibleText(container, 'golden_run_001');
    expect(allVisibleText(container)).not.toContain('Raw inputs → MTDP supra container');
  }, 12000);

  test('Dataset Packaging dropzone hands dropped filesystem paths to backend source loading', async () => {
    const backendBundle = {
      name: 'Dropped Source Batch',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 92,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Dropped source' } },
      groups: [{
        id: 'dropped-group',
        name: 'Dropped source group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'dropped_run_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'dropped_run_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'dropped_run_001.csv', yaml: 'dropped_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-drop-session', status: 'empty', schemas: [] },
      }),
      loadSources: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-drop-session',
          status: 'sources_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { source_count: 1, paths: ['C:/fixtures/source/dropped_run_001.csv'] },
        },
      }),
      openSourcesDialog: vi.fn(),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    const dropzone = shadowElements(container, '.dropzone')[0];
    expect(dropzone).toBeTruthy();
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [{ path: 'C:/fixtures/source/dropped_run_001.csv', name: 'dropped_run_001.csv' }],
        getData: vi.fn(() => ''),
      },
    });

    await waitFor(() => {
      expect(window.desktopApi.packaging.loadSources).toHaveBeenCalledWith({
        session_id: 'pkg-drop-session',
        paths: ['C:/fixtures/source/dropped_run_001.csv'],
      });
    });
    expect(window.desktopApi.packaging.openSourcesDialog).not.toHaveBeenCalled();
    await expectVisibleText(container, 'Dropped Source Batch');
    await expectVisibleText(container, 'Dropped source group');
    await expectVisibleText(container, 'dropped_run_001');
    expect(allVisibleText(container)).not.toContain('Raw inputs → MTDP supra container');
  }, 12000);

  test('Dataset Packaging dropzone loads exposed dropped source paths through backend', async () => {
    const backendBundle = {
      name: 'Dropped Source Batch',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 97,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Dropped backend source' } },
      groups: [{
        id: 'dropped-source-group',
        name: 'Dropped source group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'dropped_run_001.csv',
          channels: [{ header: 'Displacement', family: 'displacement', unit: 'mm', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'dropped_run_001', width: '10.0' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'dropped_run_001.csv', yaml: 'dropped_run_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-drop-session', status: 'empty', schemas: [] },
      }),
      openSourcesDialog: vi.fn(),
      loadSources: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-drop-session',
          status: 'sources_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { source_count: 1, paths: ['C:/fixtures/drop/dropped_run_001.csv'] },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    const dropzone = shadowElements(container, '.dropzone')[0];
    expect(dropzone).toBeTruthy();
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [{ path: 'C:\\fixtures\\drop\\dropped_run_001.csv' }],
        getData: () => '',
      },
    });
    await waitFor(() => {
      expect(window.desktopApi.packaging.loadSources).toHaveBeenCalledWith({
        session_id: 'pkg-drop-session',
        paths: ['C:\\fixtures\\drop\\dropped_run_001.csv'],
      });
    });
    expect(window.desktopApi.packaging.openSourcesDialog).not.toHaveBeenCalled();
    await expectVisibleText(container, 'Dropped Source Batch');
    await expectVisibleText(container, 'Dropped source group');
    await expectVisibleText(container, 'dropped_run_001');
    expect(allVisibleText(container)).not.toContain('Raw inputs → MTDP supra container');
  }, 12000);

  test('Dataset Packaging native PySide source drop event loads backend paths', async () => {
    const backendBundle = {
      name: 'Native Dropped Source Batch',
      schemaId: 'compression-0.3.0',
      schemaLabel: 'Compression',
      schemaVersion: '0.3.0',
      detectConfidence: 96,
      schemaOverridden: false,
      dataset: { values: { sample_type: 'Native dropped source' } },
      groups: [{
        id: 'native-dropped-source-group',
        name: 'Native dropped source group',
        units: {},
        runs: [{
          id: 'run_001',
          fileLabel: 'native_drop_001.csv',
          channels: [{ header: 'Load', family: 'load', unit: 'N', status: 'matched' }],
          evidence: [],
          values: { specimen_name: 'native_drop_001' },
        }],
      }],
      unassigned: [],
      sourcePairs: [{ csv: 'native_drop_001.csv', yaml: 'native_drop_001.yaml' }],
      supplemental: [],
    };
    window.desktopApi.packaging = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { session_id: 'pkg-native-drop-session', status: 'empty', schemas: [] },
      }),
      openSourcesDialog: vi.fn(),
      loadSources: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'pkg-native-drop-session',
          status: 'sources_loaded',
          schemas: [],
          bundle: backendBundle,
          source_summary: { source_count: 1, paths: ['C:/fixtures/native/native_drop_001.csv'] },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'packaging', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.packaging.createSession).toHaveBeenCalledTimes(1));
    window.dispatchEvent(new CustomEvent('mtdp:native-source-drop', {
      detail: {
        paths: [
          'file:///C:/fixtures/native/native_drop_001.csv',
          'file:///C:/fixtures/native/native_drop_001.csv',
        ],
      },
    }));

    await waitFor(() => {
      expect(window.desktopApi.packaging.loadSources).toHaveBeenCalledWith({
        session_id: 'pkg-native-drop-session',
        paths: ['C:/fixtures/native/native_drop_001.csv'],
      });
    });
    expect(window.desktopApi.packaging.openSourcesDialog).not.toHaveBeenCalled();
    await expectVisibleText(container, 'Native Dropped Source Batch');
    await expectVisibleText(container, 'Native dropped source group');
    await expectVisibleText(container, 'native_drop_001');
  }, 12000);

  test('method editor menu/stage interactions remain stable in its child window', async () => {
    const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
    await expectVisibleText(container, 'Method Editor');
    fireEvent.click(screen.getByText('Stage'));
    const bending = screen.getAllByText('Bending').at(-1);
    fireEvent.click(bending.parentElement || bending);
    await expectVisibleText(container, 'Bending');
    fireEvent.click(screen.getByText('Help'));
    fireEvent.click(screen.getByText('Keyboard shortcuts'));
    await expectVisibleText(container, 'Keyboard shortcuts');
  }, 10000);

  test('method editor backend logic bridge removes generated demo menu actions', async () => {
    const { METHOD_EDITOR_DC, METHOD_EDITOR_LOGIC } = await import('../generated/dcSources.js');
    const { withBackendMethodEditorLogic, withBackendMethodEditorTemplate } = await import('../backend/methodEditorLogicBridge.js');
    const bridgedTemplate = withBackendMethodEditorTemplate(METHOD_EDITOR_DC);
    const bridged = withBackendMethodEditorLogic(METHOD_EDITOR_LOGIC);

    expect(bridged).not.toContain("this.fireToast('Open package… (demo)')");
    expect(bridged).not.toContain("this.fireToast('Export… (demo)')");
    expect(bridged).not.toContain("this.fireToast('Close (demo)')");
    expect(bridged).not.toContain("this.fireToast('Validating draft…')");
    expect(bridged).not.toContain("this.fireToast('Generating new method version…')");
    expect(bridged).toContain("mkItem('Import package…', 'Ctrl+O', () => this.openMethodPackageNow()),");
    expect(bridged).toContain("mkItem('Export…', 'Ctrl+E', () => this.exportGeneratedMethodNow()),");
    expect(bridged).toContain("mkItem('Close', 'Ctrl+W', () => this.requestCloseWindow()),");
    expect(bridged).toContain("mkItem('Validate draft', 'Ctrl+Enter', () => this.validateDraftNow()),");
    expect(bridged).toContain("mkItem('Save method', 'Ctrl+S', () => this.saveMethodIfDirtyNow(), !this.hasUnsavedMethodEdits()),");
    expect(bridged).toContain('methodDirty: false');
    expect(bridged).toContain('confirmDiscardUnsavedEdits');
    expect(bridged).toContain("const baseBox = { flex:'1 1 0', minWidth:'0'");
    expect(bridged).toContain('async createMethodNow()');
    expect(bridged).toContain('await this.generateVersionNow({ defaultLabel:label });');
    expect(bridged).toContain('createMethod: () => this.createMethodNow(),');
    expect(bridged).not.toContain('Rename is deferred for registered methods');
    expect(bridged).toContain('ISO reference methods are read-only');
    expect(bridged).toContain('canRename: s.backendMode ? !!(m.editable || m.generated) : true');
    expect(bridged).toContain('startRenameCurrent: () => this.startRenameMethod(cur),');
    expect(bridged).toContain('renameCurrentFromSelector');
    expect(bridged).toContain('commitMethodNameNow');
    expect(bridgedTemplate).toContain('value="{{ m.canRename }}"');
    expect(bridgedTemplate).toContain('ISO reference stays read-only');
    expect(bridgedTemplate).toContain('✓ Save method');
    expect(bridgedTemplate).toContain('pointer-events:{{ savePointerEvents }}');
    expect(bridgedTemplate).toContain('width:min(884px, calc(100vw - 96px))');
    expect(bridgedTemplate).not.toContain('top:calc(100% + 6px)');
    expect(bridgedTemplate).not.toContain('CAG-CF-Modied-ULV20.mtdp');
  });

  test('method editor visible open package action imports through backend', async () => {
    window.desktopApi.methodEditor = {
      listMethods: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          methods: [{ method_id: 'iso14126_2023', label: 'ISO 14126 Compression', version: '0.1.0' }],
          method_count: 1,
        },
      }),
      loadMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
        },
      }),
      openMethodPackage: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          generated_method: {
            method_id: 'iso14126_2023_v0_2_0',
            method_name: 'Imported Compression Method',
            version: '0.2.0',
            method_path: 'C:/generated/iso14126_2023/v0_2_0',
          },
          import: { imported: true, registered: true },
          registry: {
            registered: true,
            registry_entry: { method_id: 'iso14126_2023_v0_2_0', version: '0.2.0' },
          },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.methodEditor.listMethods).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByText('File'));
    fireEvent.click(screen.getByText('Import package…'));

    await waitFor(() => {
      expect(window.desktopApi.methodEditor.openMethodPackage).toHaveBeenCalledWith({ register: true });
    });
    await expectVisibleText(container, 'Opened Imported Compression Method');
  }, 10000);

  test('method editor generated methods can be renamed while ISO remains read-only', async () => {
    window.desktopApi.methodEditor = {
      listMethods: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              canonical: true,
              editable: false,
              deletable: false,
            },
            {
              method_id: 'iso14126_2023_v0_1_1',
              label: 'Generated Compression Method',
              version: '0.1.1',
              source: 'method_editor_generated',
              generated: true,
              editable: true,
              deletable: true,
              method_path: 'C:/generated/iso14126_2023/v0_1_1',
            },
          ],
          method_count: 2,
        },
      }),
      loadMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.methodEditor.listMethods).toHaveBeenCalledTimes(1));

    const selector = screen.getByTitle('Click to switch · double-click to rename');
    fireEvent.doubleClick(selector);
    await expectVisibleText(container, 'ISO reference methods are read-only');
    expect(screen.queryByDisplayValue('ISO 14126 Compression')).toBeNull();

    fireEvent.click(selector);
    fireEvent.click(screen.getByText('Generated Compression Method'));
    await waitFor(() => {
      expect(window.desktopApi.methodEditor.loadMethod).toHaveBeenCalledWith({ methodId: 'iso14126_2023_v0_1_1' });
    });

    fireEvent.doubleClick(screen.getByTitle('Click to switch · double-click to rename'));
    const renameInput = await screen.findByDisplayValue('Generated Compression Method');
    fireEvent.change(renameInput, { target: { value: 'Renamed Compression Method' } });
    fireEvent.keyDown(renameInput, { key: 'Enter' });

    await expectVisibleText(container, 'Renamed Compression Method');
  }, 10000);

  test('method editor asks before closing with unsaved method edits', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    window.desktopApi.methodEditor = {
      listMethods: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          methods: [{ method_id: 'iso14126_2023', label: 'ISO 14126 Compression', version: '0.1.0' }],
          method_count: 1,
        },
      }),
      loadMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
        },
      }),
    };

    try {
      const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
      await waitFor(() => expect(window.desktopApi.methodEditor.loadMethod).toHaveBeenCalledWith({ methodId: 'iso14126_2023' }));

      fireEvent.input(screen.getByDisplayValue('0.0030'), { target: { value: '0.0035' } });
      await expectVisibleText(container, 'unsaved');

      const close = shadowElements(container, '[data-window-control="close"]')[0] ||
        container.querySelector('[data-window-control="close"]');
      expect(close).toBeTruthy();

      fireEvent.click(close);
      expect(confirmSpy).toHaveBeenCalledWith('You have unsaved method edits. Close Method Editor and discard them?');
      expect(window.desktopApi.closeWindow).not.toHaveBeenCalled();

      confirmSpy.mockReturnValue(true);
      fireEvent.click(close);
      expect(window.desktopApi.closeWindow).toHaveBeenCalledTimes(1);
    } finally {
      confirmSpy.mockRestore();
    }
  }, 10000);

  test('method editor visible generate action creates, validates, generates and registers through backend', async () => {
    window.desktopApi.methodEditor = {
      listMethods: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          methods: [{ method_id: 'iso14126_2023', label: 'ISO 14126 Compression', version: '0.1.0' }],
          method_count: 1,
        },
      }),
      loadMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
        },
      }),
      createDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-backend-1',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
            base_method_id: 'iso14126_2023',
            method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
          },
        },
      }),
      updateDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-backend-1',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
            base_method_id: 'iso14126_2023',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      validateDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-backend-1',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
            base_method_id: 'iso14126_2023',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      generateVersion: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          generated_method: {
            method_id: 'iso14126_2023_v0_1_1',
            method_name: 'ISO 14126 Compression (generated 0.1.1)',
            version: '0.1.1',
            method_path: 'C:/generated/iso14126_2023/v0_1_1',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      registerGeneratedMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          registered: true,
          registry_entry: { method_id: 'iso14126_2023_v0_1_1', version: '0.1.1' },
        },
      }),
      exportMethodPackage: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          export: {
            method_id: 'iso14126_2023_v0_1_1',
            version: '0.1.1',
            method_path: 'C:/generated/iso14126_2023/v0_1_1',
            export_path: 'C:/generated/exports/iso14126_2023_v0_1_1',
            export_kind: 'directory',
            export_name: 'iso14126_2023_v0_1_1',
            file_count: 14,
            byte_count: 2048,
          },
        },
      }),
      deleteMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          deleted: true,
          method_id: 'iso14126_2023_v0_1_1',
          method_path: 'C:/generated/iso14126_2023/v0_1_1',
          registry: { deregistered: true },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.methodEditor.listMethods).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(window.desktopApi.methodEditor.loadMethod).toHaveBeenCalledWith({ methodId: 'iso14126_2023' }));

    fireEvent.click(screen.getByText('✓ Save method'));
    expect(window.desktopApi.methodEditor.createDraft).not.toHaveBeenCalled();
    await expectVisibleText(container, 'No method edits to save');

    const endStrainInput = screen.getByDisplayValue('0.0030');
    fireEvent.input(endStrainInput, { target: { value: '0.0035' } });
    await expectVisibleText(container, 'unsaved');

    fireEvent.click(screen.getByText('✓ Save method'));

    await waitFor(() => {
      expect(window.desktopApi.methodEditor.createDraft).toHaveBeenCalledWith({
        methodId: 'iso14126_2023',
        draftLabel: 'ISO 14126 Compression draft',
      });
      expect(window.desktopApi.methodEditor.updateDraft).toHaveBeenCalledWith({
        draft_id: 'draft-backend-1',
        draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
        patch: {
          parameter_group: 'modulus_chord_strain_window',
          values: { start_strain: 0.0005, end_strain: 0.0035 },
          reason: 'Method Editor UI controlled modulus update',
        },
      });
      expect(window.desktopApi.methodEditor.validateDraft).toHaveBeenCalledWith({
        draft_id: 'draft-backend-1',
        draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
      });
      expect(window.desktopApi.methodEditor.generateVersion).toHaveBeenCalledWith({
        draft_id: 'draft-backend-1',
        draft_path: 'C:/generated/iso14126_2023/drafts/draft-backend-1',
        targetVersion: '0.1.1',
      });
      expect(window.desktopApi.methodEditor.registerGeneratedMethod).toHaveBeenCalledWith({
        method_path: 'C:/generated/iso14126_2023/v0_1_1',
      });
    });
    await expectVisibleText(container, 'Saved method v0.1.1');

    fireEvent.click(screen.getByText('File'));
    fireEvent.click(screen.getByText('Export…'));
    await waitFor(() => {
      expect(window.desktopApi.methodEditor.exportMethodPackage).toHaveBeenCalledWith({
        method_path: 'C:/generated/iso14126_2023/v0_1_1',
        default_name: 'iso14126_2023_v0_1_1.zip',
      });
    });
    await expectVisibleText(container, 'Exported to C:/generated/exports/iso14126_2023_v0_1_1');

    expect(allVisibleText(container)).not.toContain('ISO 14126 Compression (generated 0.1.1)');
    fireEvent.click(screen.getByTitle('Click to switch · double-click to rename'));
    fireEvent.click(screen.getByTitle('Delete method'));
    await waitFor(() => {
      expect(window.desktopApi.methodEditor.deleteMethod).toHaveBeenCalledWith({
        method_id: 'iso14126_2023_v0_1_1',
        method_path: 'C:/generated/iso14126_2023/v0_1_1',
      });
    });
    await expectVisibleText(container, 'Deleted iso14126_2023_v0_1_1');
  }, 10000);

  test('method editor visible New method generates and registers through backend', async () => {
    window.desktopApi.methodEditor = {
      listMethods: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          methods: [{ method_id: 'iso14126_2023', label: 'ISO 14126 Compression', version: '0.1.0' }],
          method_count: 1,
        },
      }),
      loadMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
        },
      }),
      createDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-from-new-method',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-from-new-method',
            base_method_id: 'iso14126_2023',
            method: { method_id: 'iso14126_2023', method_name: 'ISO 14126 Compression', version: '0.1.0' },
          },
        },
      }),
      updateDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-from-new-method',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-from-new-method',
            base_method_id: 'iso14126_2023',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      validateDraft: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          draft: {
            draft_id: 'draft-from-new-method',
            draft_path: 'C:/generated/iso14126_2023/drafts/draft-from-new-method',
            base_method_id: 'iso14126_2023',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      generateVersion: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          generated_method: {
            method_id: 'iso14126_2023_v0_1_1',
            method_name: 'ISO 14126 Compression (generated 0.1.1)',
            version: '0.1.1',
            method_path: 'C:/generated/iso14126_2023/v0_1_1',
          },
          validation: { status: 'valid', loadable: true },
        },
      }),
      registerGeneratedMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          registered: true,
          registry_entry: { method_id: 'iso14126_2023_v0_1_1', version: '0.1.1' },
        },
      }),
    };

    const { container } = await renderApp({ screen: 'method-editor', mode: 'child' });
    await waitFor(() => expect(window.desktopApi.methodEditor.loadMethod).toHaveBeenCalledWith({ methodId: 'iso14126_2023' }));

    const newMethodButton = screen.getAllByText('+ New method').find((node) => node.tagName.toLowerCase() === 'button');
    fireEvent.click(newMethodButton);

    await waitFor(() => {
      expect(window.desktopApi.methodEditor.createDraft).toHaveBeenCalledWith({
        methodId: 'iso14126_2023',
        draftLabel: 'ISO 14126 Compression draft',
      });
      expect(window.desktopApi.methodEditor.generateVersion).toHaveBeenCalledWith({
        draft_id: 'draft-from-new-method',
        draft_path: 'C:/generated/iso14126_2023/drafts/draft-from-new-method',
        targetVersion: '0.1.1',
      });
      expect(window.desktopApi.methodEditor.registerGeneratedMethod).toHaveBeenCalledWith({
        method_path: 'C:/generated/iso14126_2023/v0_1_1',
      });
    });
    await expectVisibleText(container, 'Saved method v0.1.1');
  }, 10000);

  test('analysis wizard survives package/method setup clicks in its child window', async () => {
    window.desktopApi.analysis = {
      listRecentPackages: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          packages: [
            {
              name: 'recent_real.mtdp',
              path: 'C:/recent/recent_real.mtdp',
              parent: 'C:/recent',
              kind: 'MTDP package',
              modified_label: '2026-07-01 17:00',
            },
          ],
        },
      }),
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-recent-session',
          status: 'package_loaded',
          package_path: 'C:/recent/recent_real.mtdp',
          package: {
            package_name: 'recent_real.mtdp',
            package_path: 'C:/recent/recent_real.mtdp',
            schema_id: 'mechanical.compression',
            schema_version: '0.3.0',
            analysis_type: 'mechanical.compression',
            run_count: 4,
            available_channels: ['load_N', 'extension_mm'],
          },
          methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              analysis_type: 'mechanical.compression',
              method_path: 'src/methods/iso14126',
            },
          ],
          method_count: 1,
          eligible_methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              analysis_type: 'mechanical.compression',
              method_path: 'src/methods/iso14126',
            },
          ],
          eligible_method_count: 1,
          messages: ['Loaded package recent_real.mtdp for analysis.'],
        },
      }),
    };

    const { container } = await renderApp({ screen: 'analysis', mode: 'child' });
    await expectVisibleText(container, 'Choose package');
    await expectVisibleText(container, 'recent_real.mtdp');
    expect(allVisibleText(container)).not.toContain('CAG-CF-Baseline-ULV18.mtdp');
    await clickShadowText(container, /recent_real\.mtdp/i, '.pick');
    await waitFor(() => {
      expect(window.desktopApi.analysis.createSession).toHaveBeenCalledWith({
        initial_package_path: 'C:/recent/recent_real.mtdp',
      });
    });
    await expectVisibleText(container, 'Choose method');
  }, 10000);

  test('analysis setup Choose package opens native package picker', async () => {
    window.desktopApi.analysis = {
      listRecentPackages: vi.fn().mockResolvedValue({
        status: 'ok',
        data: { packages: [] },
      }),
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-picked-session',
          status: 'package_loaded',
          package_path: 'C:/picked/from_folder.mtdp',
          package: {
            package_name: 'from_folder.mtdp',
            package_path: 'C:/picked/from_folder.mtdp',
            schema_id: 'mechanical.compression',
            schema_version: '0.3.0',
            analysis_type: 'mechanical.compression',
            run_count: 5,
            available_channels: ['load_N'],
          },
          methods: [],
          method_count: 0,
          eligible_methods: [],
          eligible_method_count: 0,
          messages: ['Loaded package from_folder.mtdp for analysis.'],
        },
      }),
    };

    const { container } = await renderApp({ screen: 'analysis', mode: 'child' });
    await expectVisibleText(container, 'No recent packages found');
    await clickShadowText(container, /Choose package\.\.\./i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.openPackageDialog).toHaveBeenCalledWith({});
    });
    await expectVisibleText(container, 'from_folder.mtdp');
  }, 10000);

  test('analysis File menu uses backend/native actions', async () => {
    window.desktopApi.analysis = {
      openPackageDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-opened-session',
          status: 'package_loaded',
          package_path: 'C:/exports/native_export.mtdp',
          package: {
            package_name: 'native_export.mtdp',
            package_path: 'C:/exports/native_export.mtdp',
            schema_id: 'mechanical.compression',
            schema_version: '0.3.0',
            analysis_type: 'mechanical.compression',
            run_count: 3,
            available_channels: ['load_N', 'extension_mm'],
          },
          methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              analysis_type: 'mechanical.compression',
              method_path: 'src/methods/iso14126',
            },
          ],
          method_count: 1,
          eligible_methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              analysis_type: 'mechanical.compression',
              method_path: 'src/methods/iso14126',
            },
          ],
          eligible_method_count: 1,
          messages: ['Loaded package native_export.mtdp for analysis.'],
        },
      }),
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-new-session',
          status: 'empty',
          package_path: null,
          package: null,
          methods: [
            {
              method_id: 'iso14126_2023',
              label: 'ISO 14126 Compression',
              version: '0.1.0',
              analysis_type: 'mechanical.compression',
              method_path: 'src/methods/iso14126',
            },
          ],
          method_count: 1,
          eligible_methods: [],
          eligible_method_count: 0,
          messages: [],
        },
      }),
    };

    const { container } = await renderApp({ screen: 'analysis', mode: 'child' });
    await expectVisibleText(container, 'Choose package');

    await clickShadowText(container, /^File$/i, '.menu-item');
    await clickShadowText(container, /Open package/i, '.menu-pop button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.openPackageDialog).toHaveBeenCalledWith({});
    });
    await expectVisibleText(container, 'native_export.mtdp');
    await expectVisibleText(container, 'Package loaded — native_export.mtdp');

    await clickShadowText(container, /^File$/i, '.menu-item');
    await clickShadowText(container, /New method run/i, '.menu-pop button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.createSession).toHaveBeenCalledWith({});
    });
    await expectVisibleText(container, 'New method run ready.');

    await clickShadowText(container, /^File$/i, '.menu-item');
    await clickShadowText(container, /Close wizard/i, '.menu-pop button');
    await waitFor(() => {
      expect(window.desktopApi.closeWindow).toHaveBeenCalledTimes(1);
    });
    expect(allVisibleText(container)).not.toContain('mockup: stays open');
  }, 10000);

  test('analysis cockpit collapses the clicked open row without reopening the first row', async () => {
    const { container } = await renderApp({ screen: 'analysis', mode: 'child', params: { demo: '' }, hash: '#review' });
    await expectVisibleText(container, 'Confirm flagged runs');
    await waitFor(() => expect(shadowElements(container, '.evidence')).toHaveLength(1));
    await expectVisibleText(container, 'Peak imbalance');
    const plot = shadowElements(container, '.cockpit-plot .spark-svg')[0];
    expect(plot?.getAttribute('width')).toBe('420');

    await clickShadowText(container, /demo_run_001/i, '.acc-row');
    await waitFor(() => expect(shadowElements(container, '.evidence')).toHaveLength(0));
    expect(allVisibleText(container)).not.toContain('Peak imbalance');
  }, 10000);

  test('analysis backend acceptance-only fallback still shows the decision cockpit', async () => {
    window.desktopApi.analysis = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-acceptance-only-session',
          status: 'completed',
          package_path: 'C:/exports/backend_export.mtdp',
          package: {
            package_name: 'backend_export.mtdp',
            package_path: 'C:/exports/backend_export.mtdp',
            schema_id: 'mechanical.compression',
            schema_version: '0.3.0',
            analysis_type: 'mechanical.compression',
            run_count: 7,
            available_channels: ['load_N', 'front_strain', 'rear_strain'],
          },
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
          },
          mapping: {
            mapping_name: 'iso14126_manual.json',
            label: 'iso14126_manual.json · 35/35 critical inputs bound',
            bound_count: 35,
            critical_total: 35,
            critical_missing_count: 0,
            missing_report_field_count: 7,
          },
          readiness_status: 'READY_WITH_WARNINGS',
          run_enabled: true,
          run: {
            run_id: 'run-backend-acceptance-only',
            status: 'completed',
            phase: 'complete',
            message: 'Method run complete',
            output_path: 'C:/exports/backend_export.mtda',
            progress_percent: 100,
            result: {
              status: 'completed',
              output_path: 'C:/exports/backend_export.mtda',
              archive_member_count: 42,
              acceptance_report: {
                schema_id: 'method.acceptance_report.v0_1',
                summary: { total_runs: 7, review_required: 1, excluded: 0, total_flags: 1 },
                run_states: { backend_run_010: 'review_required' },
                flags: [
                  {
                    flag_id: 'backend_bending_failure:backend_run_010',
                    rule_id: 'backend_bending_failure',
                    run_id: 'backend_run_010',
                    source: 'specimen_results',
                    severity: 'review',
                    category: 'method_diagnostic',
                    message: 'Bending diagnostic indicates sustained bending above the persistence threshold.',
                    selection_effect: 'requires_review_excluded_from_default',
                    value: 0.18,
                    threshold: 0.1,
                    points_above_threshold: 3,
                    assessed_points: 5,
                  },
                ],
              },
            },
          },
          messages: ['Method run complete: backend_export.mtda.'],
        },
      }),
    };

    const { container } = await renderApp({
      screen: 'analysis',
      mode: 'child',
      hash: '#review',
      params: { initial_package_path: 'C:/exports/backend_export.mtdp' },
    });
    await expectVisibleText(container, 'backend_run_010');
    await expectVisibleText(container, 'Peak imbalance');
    await expectVisibleText(container, 'Review limit');
    await expectVisibleText(container, 'Evidence gap: missing plot.bending_curve.');
    expect(shadowElements(container, '[data-plot-source="mtda-bending-trace"]').length).toBe(0);
  }, 10000);

  test('analysis File menu fallback reports unsupported actions explicitly', async () => {
    const fs = await import('node:fs/promises');
    const path = await import('node:path');
    const source = await fs.readFile(path.resolve(process.cwd(), 'src/screens/MethodRunWizardApp.jsx'), 'utf8');

    expect(source).not.toContain('default: flash(label);');
    expect(source).toContain('Unsupported menu action: ${label}');
    expect(source).toContain('pushLog({ level: "warn", msg });');
  });

  test('analysis child window loads an initial package through the backend session bridge', async () => {
    window.desktopApi.analysis = {
      createSession: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          session_id: 'analysis-handoff-session',
          status: 'package_loaded',
          package_path: 'C:/exports/backend_export.mtdp',
          package: {
            package_name: 'backend_export.mtdp',
            package_path: 'C:/exports/backend_export.mtdp',
            schema_id: 'mechanical.compression',
            schema_version: '0.3.0',
            analysis_type: 'mechanical.compression',
            run_count: 2,
            available_channels: ['load_N', 'extension_mm'],
          },
          methods: [],
          method_count: 0,
          messages: ['Loaded package backend_export.mtdp for analysis.'],
        },
      }),
    };

    const { container } = await renderApp({
      screen: 'analysis',
      mode: 'child',
      params: { initial_package_path: 'C:/exports/backend_export.mtdp' },
    });

    await waitFor(() => {
      expect(window.desktopApi.analysis.createSession).toHaveBeenCalledWith({
        initial_package_path: 'C:/exports/backend_export.mtdp',
      });
    });
    await expectVisibleText(container, 'Loaded from Dataset Packaging.');
    await expectVisibleText(container, 'C:/exports/backend_export.mtdp');
    await expectVisibleText(container, 'backend_export.mtdp');
    await expectVisibleText(container, '2 runs');
  }, 10000);

  test('analysis run button enables after resolved decisions despite stale backend run flag', async () => {
    const selectedMethod = {
      method_id: 'iso14126_2023',
      method_name: 'ISO 14126 Compression',
      label: 'ISO 14126 Compression',
      version: '0.1.0',
      standard_reference: 'ISO 14126',
      analysis_type: 'mechanical.compression',
      method_path: 'src/methods/iso14126',
    };
    const sessionData = {
      session_id: 'analysis-stale-run-enabled-session',
      status: 'package_loaded',
      package_path: 'C:/exports/stale_flag_package.mtdp',
      output_path: 'C:/exports/stale_flag_package.mtda',
      run_enabled: false,
      package: {
        package_name: 'stale_flag_package.mtdp',
        package_path: 'C:/exports/stale_flag_package.mtdp',
        schema_id: 'mechanical.compression',
        analysis_type: 'mechanical.compression',
        run_count: 6,
        available_channels: ['load_N', 'extension_mm'],
      },
      eligible_methods: [selectedMethod],
      methods: [selectedMethod],
      method_count: 1,
      eligible_method_count: 1,
    };
    window.desktopApi.analysis = {
      createSession: vi.fn().mockResolvedValue({ status: 'ok', data: sessionData }),
      selectMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: selectedMethod.method_id,
          selected_method: selectedMethod,
          mapping: {
            mapping_name: 'iso14126_manual.json',
            path: 'C:/mappings/iso14126_manual.json',
            label: 'iso14126_manual.json · 35/35 critical inputs bound',
            bound_count: 35,
            critical_total: 35,
            critical_missing_count: 0,
            missing_report_field_count: 7,
          },
          mapping_confirmed: true,
          run_enabled: false,
        },
      }),
      startRun: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: selectedMethod.method_id,
          selected_method: selectedMethod,
          run_enabled: true,
          run: {
            run_id: 'run-stale-flag',
            status: 'completed',
            phase: 'complete',
            output_path: 'C:/exports/stale_flag_package.mtda',
            result: {
              status: 'completed',
              output_path: 'C:/exports/stale_flag_package.mtda',
            },
          },
        },
      }),
    };

    const { container } = await renderApp({
      screen: 'analysis',
      mode: 'child',
      params: { initial_package_path: 'C:/exports/stale_flag_package.mtdp' },
    });

    await clickShadowText(container, /Confirm method/i);
    await clickShadowText(container, /Skip.*accept warnings/i);
    await expectVisibleText(container, 'run enabled');
    await clickShadowText(container, /Run method/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.startRun).toHaveBeenCalledWith({
        session_id: 'analysis-stale-run-enabled-session',
        output_path: 'C:/exports/stale_flag_package.mtda',
        overwrite: true,
        generate_workbench: true,
      });
    });
  }, 10000);

  test('analysis child window confirms backend-selected method and default mapping', async () => {
    const sessionData = {
      session_id: 'analysis-handoff-session',
      status: 'package_loaded',
      package_path: 'C:/exports/backend_export.mtdp',
      output_path: 'C:/exports/backend_export.mtda',
      package: {
        package_name: 'backend_export.mtdp',
        package_path: 'C:/exports/backend_export.mtdp',
        schema_id: 'mechanical.compression',
        schema_version: '0.3.0',
        analysis_type: 'mechanical.compression',
        run_count: 2,
        available_channels: ['load_N', 'extension_mm'],
      },
      methods: [
        {
          method_id: 'iso14126_2023',
          label: 'ISO 14126 Compression',
          version: '0.1.0',
          analysis_type: 'mechanical.compression',
          method_path: 'src/methods/iso14126',
          default_mapping_path: 'mappings/iso14126_manual.json',
        },
      ],
      eligible_methods: [
        {
          method_id: 'iso14126_2023',
          label: 'ISO 14126 Compression',
          version: '0.1.0',
          analysis_type: 'mechanical.compression',
          method_path: 'src/methods/iso14126',
          default_mapping_path: 'mappings/iso14126_manual.json',
        },
      ],
      method_count: 1,
      eligible_method_count: 1,
      messages: ['Loaded package backend_export.mtdp for analysis.'],
    };
    const backendMapping = {
      mapping_name: 'iso14126_manual.json',
      path: 'C:/mappings/iso14126_manual.json',
      label: 'iso14126_manual.json · 35/35 critical inputs bound',
      bound_count: 35,
      critical_total: 35,
      critical_missing_count: 0,
      missing_report_field_count: 7,
      preview: {
        schema_name: 'mapping_preview_view_model',
        rows: [
          {
            requirement_id: 'channel.load',
            method_field: 'channel.load',
            description: 'Compressive load channel',
            severity: 'execution_critical',
            source_role: 'load',
            source_kind: 'channel',
            mapped_source: 'load_N',
            status: 'pass',
            coverage: '2/2 runs',
            example_value: '0 ... 42000 N',
            expected_unit: 'N',
          },
          {
            requirement_id: 'report.operator',
            method_field: 'report.operator',
            description: 'Operator / analyst name',
            severity: 'report_completeness',
            source_role: 'operator',
            source_kind: 'field',
            mapped_source: '',
            status: 'fail',
            coverage: 'not mapped',
          },
        ],
        candidate_rows: [
          {
            method_field: 'channel.load',
            source_role: 'load',
            source_name: 'load_N',
            source_kind: 'channel',
            coverage: '2/2 runs',
            confidence: 0.98,
            example_value: '0 ... 42000 N',
            reason: 'Name and unit match',
          },
          {
            method_field: 'report.operator',
            source_role: 'operator',
            source_name: 'fields.Operator Name',
            source_kind: 'field',
            coverage: '0/2 runs',
            confidence: 0.74,
            reason: 'Label similarity',
          },
        ],
      },
    };
    const browsedBackendMapping = {
      ...backendMapping,
      mapping_name: 'iso14126_browsed.json',
      path: 'C:/mappings/iso14126_browsed.json',
      label: 'iso14126_browsed.json · 35/35 critical inputs bound',
    };
    const savedBackendMapping = {
      ...browsedBackendMapping,
      mapping_name: 'iso14126_browsed_wizard_edit.json',
      path: 'C:/mappings/iso14126_browsed_wizard_edit.json',
      label: 'iso14126_browsed_wizard_edit.json · 35/35 critical inputs bound',
      preview: {
        ...browsedBackendMapping.preview,
        rows: browsedBackendMapping.preview.rows.map((row) => row.method_field === 'report.operator'
          ? { ...row, mapped_source: 'fields.Operator Name', status: 'pass', coverage: '2/2 runs' }
          : row),
      },
    };
    const editedBackendMapping = {
      ...savedBackendMapping,
      mapping_name: 'iso14126_manual_wizard_edit.json',
      path: 'C:/mappings/iso14126_manual_wizard_edit.json',
      label: 'iso14126_manual_wizard_edit.json · 35/35 critical inputs bound',
    };
    const unsubscribeAnalysisEvents = vi.fn().mockResolvedValue({ status: 'ok', data: { active_subscriptions: 0 } });
    window.desktopApi.analysis = {
      createSession: vi.fn().mockResolvedValue({ status: 'ok', data: sessionData }),
      selectMethod: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
            required_inputs: ['channel.load', 'geometry.width'],
            recipe_steps: ['resolve_inputs', 'reduce_runs'],
          },
          mapping: backendMapping,
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
          ],
        },
      }),
      confirmMapping: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: backendMapping,
          mapping_confirmed: true,
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Confirmed mapping iso14126_manual.json.',
          ],
        },
      }),
      openMappingDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: browsedBackendMapping,
          mapping_confirmed: false,
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Loaded mapping iso14126_browsed.json.',
          ],
        },
      }),
      saveMappingDialog: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: savedBackendMapping,
          mapping_confirmed: true,
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Saved mapping edits to iso14126_browsed_wizard_edit.json.',
          ],
        },
      }),
      applyMappingPatch: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: editedBackendMapping,
          mapping_confirmed: true,
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Saved mapping edits to iso14126_manual_wizard_edit.json.',
          ],
        },
      }),
      checkReadiness: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: editedBackendMapping,
          readiness_status: 'READY_WITH_WARNINGS',
          run_enabled: false,
          readiness: {
            status: 'READY_WITH_WARNINGS',
            summary: {
              execution_critical_passed: 35,
              execution_critical_total: 35,
              report_missing_total: 7,
            },
          },
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Readiness check complete: READY_WITH_WARNINGS.',
          ],
        },
      }),
      startRun: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: editedBackendMapping,
          readiness_status: 'READY_WITH_WARNINGS',
          run_enabled: true,
          run: {
            run_id: 'run-backend-001',
            status: 'completed',
            phase: 'complete',
            message: 'Method run complete',
            output_path: 'C:/exports/backend_export.mtda',
            progress_percent: 100,
            events: [
              {
                event_id: 'event-run-progress',
                event: 'runProgress',
                data: {
                  phase: 'write_mtda',
                  status: 'running',
                  progress_percent: 90,
                  message: 'Writing MTDA archive',
                },
              },
              {
                event_id: 'event-run-completed',
                event: 'runCompleted',
                data: {
                  phase: 'complete',
                  status: 'completed',
                  progress_percent: 100,
                  message: 'Method run complete',
                },
              },
            ],
            result: {
              status: 'completed',
              output_path: 'C:/exports/backend_export.mtda',
              archive_member_count: 42,
              acceptance_summary: { flagged_runs: 3 },
              acceptance_report: {
                schema_id: 'method.acceptance_report.v0_1',
                default_selection_set: 'auto_recommended_runs',
                summary: {
                  total_runs: 2,
                  default_selected_runs: 1,
                  review_required: 1,
                  excluded: 1,
                  total_flags: 2,
                },
                run_states: {
                  backend_run_010: 'review_required',
                  backend_run_011: 'excluded',
                },
                flags: [
                  {
                    flag_id: 'backend_bending_failure:backend_run_010',
                    rule_id: 'backend_bending_failure',
                    run_id: 'backend_run_010',
                    source: 'specimen_results',
                    severity: 'review',
                    category: 'method_diagnostic',
                    message: 'Bending diagnostic indicates sustained bending above the persistence threshold.',
                    evidence_refs: ['specimen_results:backend_run_010:bending_pattern'],
                    selection_effect: 'requires_review_excluded_from_default',
                    value: 0.18,
                    threshold: 0.1,
                  },
                  {
                    flag_id: 'backend_bending_window:backend_run_010',
                    rule_id: 'backend_bending_window',
                    run_id: 'backend_run_010',
                    source: 'validation_report',
                    severity: 'review',
                    category: 'method_diagnostic',
                    message: 'Bending signal-window evidence requires scientist review before default reporting.',
                    evidence_refs: ['validation:backend_bending_check'],
                    selection_effect: 'requires_review_excluded_from_default',
                    value: 0.16,
                    threshold: 0.1,
                  },
                  {
                    flag_id: 'backend_operator_invalid:backend_run_011',
                    rule_id: 'backend_operator_invalid',
                    run_id: 'backend_run_011',
                    source: 'specimen_results',
                    severity: 'exclude',
                    category: 'operator_failure_mode',
                    message: 'Backend validation hard fail from operator failure mode',
                    evidence_refs: ['specimen_results:backend_run_011:failure_mode'],
                    selection_effect: 'excluded_from_default',
                  },
                ],
              },
              review_rows: [
                {
                  run_id: 'backend_run_010',
                  default_call: 'Remove',
                  reason: 'Bending diagnostic indicates sustained bending above the persistence threshold.',
                  is_excluded: false,
                  defect_labels: ['Bending'],
                  narrative_html: 'Bending diagnostic indicates sustained bending above the persistence threshold.',
                  acceptance_flags: [
                    {
                      flag_id: 'backend_bending_failure:backend_run_010',
                      rule_id: 'backend_bending_failure',
                      run_id: 'backend_run_010',
                      source: 'specimen_results',
                      severity: 'review',
                      category: 'method_diagnostic',
                      message: 'Bending diagnostic indicates sustained bending above the persistence threshold.',
                      evidence_refs: ['specimen_results:backend_run_010:bending_pattern'],
                      selection_effect: 'requires_review_excluded_from_default',
                      value: 0.18,
                      threshold: 0.1,
                    },
                    {
                      flag_id: 'backend_bending_window:backend_run_010',
                      rule_id: 'backend_bending_window',
                      run_id: 'backend_run_010',
                      source: 'validation_report',
                      severity: 'review',
                      category: 'method_diagnostic',
                      message: 'Bending signal-window evidence requires scientist review before default reporting.',
                      evidence_refs: ['validation:backend_bending_check'],
                      selection_effect: 'requires_review_excluded_from_default',
                      value: 0.16,
                      threshold: 0.1,
                    },
                  ],
                  bending_trace_points: [
                    { load_N: 0, bending_percent: 0.02, point_index: 0 },
                    { load_N: 12000, bending_percent: 0.08, point_index: 1 },
                    { load_N: 24000, bending_percent: 0.18, point_index: 2 },
                    { load_N: 36000, bending_percent: 0.16, point_index: 3 },
                    { load_N: 42000, bending_percent: 0.11, point_index: 4 },
                  ],
                  bending_threshold: 0.1,
                  bending_peak: 0.18,
                  bending_assessment_window: [4200, 37800],
                  bending_exceedance_segments: [
                    { start_load_N: 24000, end_load_N: 36000, start_point_index: 2, end_point_index: 3 },
                  ],
                  bending_points_above_threshold: 3,
                  bending_assessed_points: 5,
                  cockpits: [
                    {
                      kind: 'bending',
                      tab: 'Bending',
                      title: 'Bending evidence',
                      plot: {
                        plot_kind: 'bending_evidence',
                        title: 'Bending evidence',
                        trace_points: [
                          { load_N: 0, bending_percent: 0.02, point_index: 0 },
                          { load_N: 12000, bending_percent: 0.08, point_index: 1 },
                          { load_N: 24000, bending_percent: 0.18, point_index: 2 },
                          { load_N: 36000, bending_percent: 0.16, point_index: 3 },
                          { load_N: 42000, bending_percent: 0.11, point_index: 4 },
                        ],
                        threshold: 0.1,
                        peak: 0.18,
                        assessment_window: [4200, 37800],
                        exceedance_segments: [
                          { start_load_N: 24000, end_load_N: 36000, start_point_index: 2, end_point_index: 3 },
                        ],
                      },
                      cards: [
                        { key: 'bending.call', label: 'Observed signal', value: 'Sustained bending', sub: 'opposite-face strain imbalance', level: 'warn' },
                        { key: 'bending.max_percent', label: 'Peak imbalance', value: '0.18%', sub: 'actual trace peak from backend evidence', level: 'warn' },
                        { key: 'bending.threshold_percent', label: 'Review limit', value: '0.1%', sub: 'method threshold for bending review', level: 'info' },
                      ],
                    },
                  ],
                },
                {
                  run_id: 'backend_run_011',
                  default_call: 'Remove',
                  reason: 'Backend validation hard fail from operator failure mode',
                  is_excluded: true,
                  defect_labels: ['Operator Failure Mode'],
                  narrative_html: 'Backend validation hard fail from operator failure mode',
                  acceptance_flags: [
                    {
                      flag_id: 'backend_operator_invalid:backend_run_011',
                      rule_id: 'backend_operator_invalid',
                      run_id: 'backend_run_011',
                      source: 'specimen_results',
                      severity: 'exclude',
                      category: 'operator_failure_mode',
                      message: 'Backend validation hard fail from operator failure mode',
                      evidence_refs: ['specimen_results:backend_run_011:failure_mode'],
                      selection_effect: 'excluded_from_default',
                    },
                  ],
                  cockpits: [],
                },
              ],
            },
          },
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Readiness check complete: READY_WITH_WARNINGS.',
            'Method run complete: backend_export.mtda.',
          ],
        },
      }),
      getEvents: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          schema_id: 'gui_bridge.analysis_events.v0_1',
          session_id: 'analysis-handoff-session',
          run_id: 'run-backend-001',
          cursor: 0,
          next_cursor: 2,
          event_count: 2,
          has_more: false,
          events: [
            {
              event_id: 'event-run-progress',
              event: 'runProgress',
              data: {
                phase: 'write_mtda',
                status: 'running',
                progress_percent: 90,
                message: 'Writing MTDA archive',
              },
            },
            {
              event_id: 'event-run-completed',
              event: 'runCompleted',
              data: {
                phase: 'complete',
                status: 'completed',
                progress_percent: 100,
                message: 'Method run complete',
              },
            },
          ],
        },
      }),
      subscribeEvents: vi.fn().mockImplementation(async (payload, options = {}) => {
        options.onEvent?.({
          status: 'ok',
          namespace: 'analysis',
          event: 'analysisEvents',
          session_id: payload.session_id,
          data: {
            schema_id: 'gui_bridge.analysis_events.v0_1',
            session_id: payload.session_id,
            run_id: 'run-backend-001',
            cursor: payload.cursor || 0,
            next_cursor: 1,
            event_count: 1,
            has_more: true,
            events: [
              {
                event_id: 'event-run-pushed',
                event: 'runProgress',
                data: {
                  phase: 'reduce_runs',
                  status: 'running',
                  progress_percent: 45,
                  message: 'Streaming via WebChannel',
                },
              },
            ],
          },
          warnings: [],
        });
        return {
          status: 'ok',
          data: { session_id: payload.session_id, cursor: payload.cursor || 0 },
          unsubscribe: unsubscribeAnalysisEvents,
        };
      }),
      cancelRun: vi.fn(),
      updateAcceptanceDecision: vi.fn(),
      confirmReview: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          selected_method_id: 'iso14126_2023',
          selected_method: {
            method_id: 'iso14126_2023',
            method_name: 'ISO 14126 Compression',
            label: 'ISO 14126 Compression',
            version: '0.1.0',
            standard_reference: 'ISO 14126',
            analysis_type: 'mechanical.compression',
            method_path: 'src/methods/iso14126',
          },
          mapping: editedBackendMapping,
          readiness_status: 'READY_WITH_WARNINGS',
          run_enabled: true,
          run: {
            run_id: 'run-backend-001',
            status: 'completed',
            phase: 'complete',
            message: 'Method run complete',
            output_path: 'C:/exports/backend_export.mtda',
            progress_percent: 100,
            review: {
              status: 'confirmed',
              decision_count: 3,
              override_count: 0,
              final_run_count: 2,
            },
            result: {
              status: 'completed',
              output_path: 'C:/exports/backend_export.mtda',
              archive_member_count: 42,
              acceptance_summary: { flagged_runs: 3 },
            },
          },
          review: {
            status: 'confirmed',
            decision_count: 3,
            override_count: 0,
            final_run_count: 2,
          },
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Readiness check complete: READY_WITH_WARNINGS.',
            'Method run complete: backend_export.mtda.',
            'Acceptance review confirmed: 2 final run(s).',
          ],
        },
      }),
      applyReportAmendments: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          output_path: 'C:/exports/backend_export_report_completed.mtda',
          selected_method_id: 'iso14126_2023',
          mapping: editedBackendMapping,
          readiness_status: 'READY_WITH_WARNINGS',
          run_enabled: true,
          finalization: {
            status: 'finalized',
            input_path: 'C:/exports/backend_export.mtda',
            output_path: 'C:/exports/backend_export_report_completed.mtda',
            reason_kind: 'report_completion',
            report_override_count: 2,
          },
          report_amendments: {
            status: 'finalized',
            input_path: 'C:/exports/backend_export.mtda',
            output_path: 'C:/exports/backend_export_report_completed.mtda',
            override_count: 2,
            field_keys: ['operator', 'fixture_description'],
          },
          run: {
            run_id: 'run-backend-001',
            status: 'completed',
            phase: 'complete',
            message: 'Method run complete',
            output_path: 'C:/exports/backend_export_report_completed.mtda',
            progress_percent: 100,
            report_amendments: {
              status: 'finalized',
              output_path: 'C:/exports/backend_export_report_completed.mtda',
              override_count: 2,
            },
            result: {
              status: 'completed',
              output_path: 'C:/exports/backend_export_report_completed.mtda',
              archive_member_count: 45,
            },
          },
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Readiness check complete: READY_WITH_WARNINGS.',
            'Method run complete: backend_export.mtda.',
            'Acceptance review confirmed: 2 final run(s).',
            'Report amendments applied: 2 field(s).',
          ],
        },
      }),
      finalizeMtda: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          ...sessionData,
          output_path: 'C:/exports/backend_export_finalized.mtda',
          finalization: {
            status: 'finalized',
            input_path: 'C:/exports/backend_export.mtda',
            output_path: 'C:/exports/backend_export_finalized.mtda',
            reason_kind: 'review_decisions',
            human_decision_count: 0,
          },
          run: {
            run_id: 'run-backend-001',
            status: 'completed',
            phase: 'complete',
            message: 'Method run complete',
            output_path: 'C:/exports/backend_export_finalized.mtda',
            progress_percent: 100,
            finalization: {
              status: 'finalized',
              output_path: 'C:/exports/backend_export_finalized.mtda',
            },
            result: {
              status: 'completed',
              output_path: 'C:/exports/backend_export_finalized.mtda',
              archive_member_count: 47,
            },
          },
          messages: [
            'Loaded package backend_export.mtdp for analysis.',
            'Selected method ISO 14126 Compression.',
            'Readiness check complete: READY_WITH_WARNINGS.',
            'Method run complete: backend_export.mtda.',
            'Acceptance review confirmed: 2 final run(s).',
            'MTDA finalized: backend_export_finalized.mtda.',
          ],
        },
      }),
      copyOutputPath: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          path: 'C:/exports/backend_export_finalized.mtda',
          output_path: 'C:/exports/backend_export_finalized.mtda',
          exists: true,
          clipboard_owner: 'frontend',
        },
      }),
      openArtifact: vi.fn().mockResolvedValue({
        status: 'ok',
        data: {
          artifact_kind: 'test_report',
          kind: 'test_report',
          path: 'C:/exports/backend_export_finalized/test_report.html',
          target_path: 'C:/exports/backend_export_finalized/test_report.html',
          exists: true,
          opened: false,
        },
      }),
    };

    const { container } = await renderApp({
      screen: 'analysis',
      mode: 'child',
      params: { initial_package_path: 'C:/exports/backend_export.mtdp' },
    });

    await expectVisibleText(container, 'Choose method');
    await expectVisibleText(container, 'ISO 14126 Compression — v0.1.0');
    await clickShadowText(container, /Confirm method/i);

    await waitFor(() => {
      expect(window.desktopApi.analysis.selectMethod).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
        method_id: 'iso14126_2023',
      });
    });
    await expectVisibleText(container, 'ISO 14126 Compression');
    await expectVisibleText(container, 'iso14126_manual.json');
    await expectVisibleText(container, '35/35 critical inputs bound');

    await clickShadowText(container, /Edit mapping profile/i);
    await expectVisibleText(container, 'channel.load');
    await expectVisibleText(container, 'load_N');
    await expectVisibleText(container, 'report.operator');
    await clickShadowText(container, /Browse/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.openMappingDialog).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.openMappingDialog.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      initial_dir: 'C:/mappings',
    });
    await expectVisibleText(container, 'iso14126_browsed.json');
    await clickShadowText(container, /fields\.Operator Name/i);
    await clickShadowText(container, /Save profile as/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.saveMappingDialog).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.saveMappingDialog.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      initial_dir: 'C:/mappings',
      default_name: 'iso14126_browsed_wizard_edit.json',
      bindings: expect.arrayContaining([
        expect.objectContaining({
          method_field: 'report.operator',
          source_role: 'operator',
          source_kind: 'field',
          mapped_source: 'fields.Operator Name',
          status: 'manual',
        }),
      ]),
    });
    await expectVisibleText(container, 'iso14126_browsed_wizard_edit.json');
    await clickShadowText(container, /Clear binding/i, 'button');
    await clickShadowText(container, /fields\.Operator Name/i);
    await clickShadowText(container, /Save edits & use profile/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.applyMappingPatch).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.applyMappingPatch.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      bindings: expect.arrayContaining([
        expect.objectContaining({
          method_field: 'report.operator',
          source_role: 'operator',
          source_kind: 'field',
          mapped_source: 'fields.Operator Name',
          status: 'manual',
        }),
      ]),
    });
    await expectVisibleText(container, 'iso14126_manual_wizard_edit.json');

    await clickShadowText(container, /^Workflow$/i);
    await clickShadowText(container, /Check readiness/i);
    await waitFor(() => {
      expect(window.desktopApi.analysis.checkReadiness).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
      });
    });
    await expectVisibleText(container, 'Readiness READY_WITH_WARNINGS.');
    await expectVisibleText(container, '35/35 critical inputs');

    await clickShadowText(container, /Run method/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.startRun).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
        output_path: 'C:/exports/backend_export.mtda',
        overwrite: true,
        generate_workbench: true,
      });
    });
    await waitFor(() => {
      expect(window.desktopApi.analysis.subscribeEvents).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.subscribeEvents.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      cursor: 0,
      limit: 100,
    });
    expect(window.desktopApi.analysis.subscribeEvents.mock.calls[0][1].onEvent).toEqual(expect.any(Function));
    await waitFor(() => {
      expect(window.desktopApi.analysis.getEvents).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
        cursor: 1,
        limit: 100,
      });
    });
    await waitFor(() => {
      expect(unsubscribeAnalysisEvents).toHaveBeenCalledTimes(1);
    });
    await expectVisibleText(container, 'Confirm flagged runs');
    await expectVisibleText(container, 'backend_run_010');
    await expectVisibleText(container, 'Bending diagnostic indicates sustained bending above the persistence threshold.');
    await expectVisibleText(container, 'bending % vs load');
    await expectVisibleText(container, 'Peak imbalance');
    await expectVisibleText(container, '0.18');
    await expectVisibleText(container, 'Review limit');
    await expectVisibleText(container, '0.1');
    await expectVisibleText(container, 'backend_run_011');
    await expectVisibleText(container, 'Backend validation hard fail from operator failure mode');
    expect(shadowElements(container, '.cockpit-plot .spark-svg').length).toBeGreaterThan(0);
    expect(shadowElements(container, '[data-plot-source="mtda-bending-trace"]').length).toBeGreaterThan(0);
    await expectVisibleText(container, 'Load / N');
    await expectVisibleText(container, 'Bending / %');
    expect(allVisibleText(container)).not.toContain('Method Diagnostic');
    expect(allVisibleText(container)).not.toContain('Acceptance findings');
    expect(allVisibleText(container)).not.toContain('backend acceptance policy');
    expect(allVisibleText(container)).not.toContain('value carried by backend flag');
    expect(allVisibleText(container)).not.toContain('Sustained bending 0.142 % exceeds 0.10 % limit for 6 points');
    await clickShadowText(container, /Activity log/i);
    await expectVisibleText(container, 'Backend event stream connected');
    await expectVisibleText(container, 'Streaming via WebChannel');
    await clickShadowText(container, '', '.dh-x');
    await clickShadowText(container, /Confirm & open output/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.confirmReview).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.confirmReview.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      method_run_id: 'run-backend-001',
      decisions: expect.arrayContaining([
        expect.objectContaining({
          run_id: expect.any(String),
          decision: expect.stringMatching(/keep|remove/),
          source_surface: 'method_run_wizard.review_spotlight',
        }),
      ]),
    });
    await expectVisibleText(container, 'Output is ready');
    await clickShadowText(container, /report gap/i);
    await waitFor(() => {
      expect(shadowElements(container, 'input[placeholder="G. Macori"]').length).toBeGreaterThan(0);
    });
    fireEvent.change(shadowElements(container, 'input[placeholder="G. Macori"]')[0], { target: { value: 'G. Macori' } });
    await clickShadowText(container, /report\.fixture_description/i, 'tr');
    await waitFor(() => {
      const fixtureSelect = shadowElements(container, 'select.field-input').find((el) =>
        Array.from(el.options || []).some((option) => option.value === '4-pt CLC fixture')
      );
      expect(fixtureSelect).toBeTruthy();
    });
    const fixtureSelect = shadowElements(container, 'select.field-input').find((el) =>
      Array.from(el.options || []).some((option) => option.value === '4-pt CLC fixture')
    );
    fireEvent.change(fixtureSelect, { target: { value: '4-pt CLC fixture' } });
    await clickShadowText(container, /Apply amendments/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.applyReportAmendments).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.applyReportAmendments.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      method_run_id: 'run-backend-001',
      report_overrides: expect.arrayContaining([
        expect.objectContaining({
          field_key: 'operator',
          value: 'G. Macori',
          source_surface: 'method_run_wizard.report_completion_editor',
        }),
        expect.objectContaining({
          field_key: 'fixture_description',
          value: '4-pt CLC fixture',
          source_surface: 'method_run_wizard.report_completion_editor',
        }),
      ]),
    });
    const reviewerInput = shadowElements(container, 'input[placeholder="Reviewer / operator"]')[0];
    const noteInput = shadowElements(container, 'textarea[placeholder^="Required note"]')[0];
    fireEvent.change(reviewerInput, { target: { value: 'QA' } });
    fireEvent.change(noteInput, { target: { value: 'Review gate confirmed.' } });
    await clickShadowText(container, /Finalize & issue/i, 'button');
    await waitFor(() => {
      expect(window.desktopApi.analysis.finalizeMtda).toHaveBeenCalledTimes(1);
    });
    expect(window.desktopApi.analysis.finalizeMtda.mock.calls[0][0]).toMatchObject({
      session_id: 'analysis-handoff-session',
      method_run_id: 'run-backend-001',
      reviewer: 'QA',
      note: 'Review gate confirmed.',
      reason_kind: 'review_decisions',
    });
    await expectVisibleText(container, 'MTDA finalized');
    await expectVisibleText(container, 'C:/exports/backend_export_finalized.mtda');
    await clickShadowText(container, /^Test Report/i, '.artifact');
    await waitFor(() => {
      expect(window.desktopApi.analysis.openArtifact).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
        artifact_kind: 'test_report',
      });
    });
    const outputFolderButton = shadowElements(container, 'button[title="Open output folder"]')[0];
    fireEvent.click(outputFolderButton);
    await waitFor(() => {
      expect(window.desktopApi.analysis.openArtifact).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
        artifact_kind: 'output_folder',
      });
    });
    const copyButton = shadowElements(container, 'button[title="Copy MTDA path"]')[0];
    fireEvent.click(copyButton);
    await waitFor(() => {
      expect(window.desktopApi.analysis.copyOutputPath).toHaveBeenCalledWith({
        session_id: 'analysis-handoff-session',
      });
    });
  }, 10000);
});
