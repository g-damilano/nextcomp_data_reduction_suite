import React from 'react';
import * as ReactDOMClient from 'react-dom/client';
import { afterEach, beforeAll, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/react';
import visualBaseline from './fixtures/visual-baseline.json';

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

async function renderApp({ screen = 'home', mode = 'launcher' } = {}) {
  window.history.replaceState(null, '', `/?mode=${mode}&screen=${screen}`);
  vi.resetModules();
  const { default: App } = await import('../App.jsx');
  return render(<App />);
}

function shadowHosts(container) {
  return Array.from(container.querySelectorAll('.shadow-screen-host'));
}

function shadowElements(container, selector = '*') {
  return shadowHosts(container).flatMap((host) => Array.from(host.shadowRoot?.querySelectorAll(selector) || []));
}

function allVisibleText(container) {
  const shadowText = shadowHosts(container)
    .map((host) => host.shadowRoot?.textContent || '')
    .join('\n');
  return `${container.textContent || ''}\n${shadowText}`;
}

async function expectVisibleText(container, text) {
  await waitFor(() => {
    expect(allVisibleText(container)).toContain(text);
  }, { timeout: 5000 });
}

function assertSuiteShell(container, { screen, mode, label }) {
  const root = container.querySelector('.suite-root');
  expect(root).toBeTruthy();
  expect(root.getAttribute('data-screen')).toBe(screen);
  expect(root.getAttribute('data-window-mode')).toBe(mode);
  expect(container.querySelector('.suite-screen')?.getAttribute('aria-label')).toBe(label);
}

function allWindowControls(container) {
  return [
    ...Array.from(container.querySelectorAll('[data-window-control]')),
    ...shadowElements(container, '[data-window-control]'),
  ];
}

function allWindowControlGroups(container) {
  return [
    ...Array.from(container.querySelectorAll('[data-window-controls="true"]')),
    ...shadowElements(container, '[data-window-controls="true"]'),
  ];
}

function assertSingleChromeLayer(container) {
  expect(allWindowControlGroups(container)).toHaveLength(visualBaseline.chrome.windowControlGroupCount);
  expect(allWindowControls(container).map((control) => control.getAttribute('data-window-control')).sort()).toEqual([
    ...visualBaseline.chrome.windowControls,
  ]);
}

function assertNoLauncherLeak(container) {
  expect(container.querySelector('.launcher-hit-layer')).toBeNull();
  expect(container.querySelector('[data-launcher-hit]')).toBeNull();
  expect(container.querySelector('[data-launcher-button]')).toBeNull();
  expect(container.querySelector('.suite-floating-tools')).toBeNull();
  expect(container.querySelector('.suite-win')).toBeNull();
  expect(allVisibleText(container)).not.toContain('Data Reduction Suite');
}

function assertVisualSurfaceBaseline(container, baseline) {
  assertSuiteShell(container, {
    screen: baseline.screen,
    mode: baseline.mode,
    label: baseline.label,
  });
  assertSingleChromeLayer(container);
  if (baseline.noLauncherLeak) assertNoLauncherLeak(container);

  const hosts = shadowHosts(container);
  expect(hosts).toHaveLength(baseline.shadowHosts);
  if (baseline.shadowClass) {
    expect(hosts[0].classList.contains(baseline.shadowClass)).toBe(true);
  }
  expect(shadowElements(container, '.shadow-viewport')).toHaveLength(baseline.shadowViewports);
  expect(container.querySelectorAll('.dc-runtime-host')).toHaveLength(baseline.dcRuntimeHosts);
  expect(container.querySelectorAll('.launcher-hit-layer')).toHaveLength(baseline.launcherHitLayers);
  expect(container.querySelectorAll('[data-launcher-hit]')).toHaveLength(baseline.launcherHits);
  expect(container.querySelectorAll('[data-launcher-button]')).toHaveLength(baseline.launcherButtons);
}

describe('visual preservation shell baseline', () => {
  test('child-window sizing contract stays aligned with the routed desktop surfaces', async () => {
    vi.resetModules();
    const { SCREEN_CONFIG } = await import('../App.jsx');
    expect(visualBaseline.schema).toBe('gui-transition-visual-baseline/v1');
    expect(SCREEN_CONFIG).toEqual(visualBaseline.screenConfig);
    expect(visualBaseline.surfaces.map((item) => item.screen).sort()).toEqual(
      Object.keys(visualBaseline.screenConfig).sort(),
    );
  });

  test.each(visualBaseline.surfaces)(
    '$label surface keeps the recorded shell and visual-host baseline',
    async (baseline) => {
      const { container } = await renderApp({ screen: baseline.screen, mode: baseline.mode });
      await expectVisibleText(container, baseline.visibleText);
      assertVisualSurfaceBaseline(container, baseline);
    },
    10000,
  );

  test('shadow CSS normalisation preserves insert-panel class names ending in body', async () => {
    const { normaliseCss } = await import('../components/ShadowReactScreen.jsx');
    const normalised = normaliseCss([
      ':root{--panel:#fff;}',
      'html,body{margin:0;}',
      'body{font-family:system-ui;}',
      '.insrbody{flex:1 1 auto;display:grid;grid-template-columns:232px 1fr;min-height:0;}',
      '.rail{border-right:1px solid var(--line);background:var(--panel-2);overflow-y:auto;padding:8px 0;}',
    ].join(''));

    expect(normalised).toContain(':host{--panel:#fff;}');
    expect(normalised).toContain(':host {margin:0;}');
    expect(normalised).toContain('.shadow-viewport {font-family:system-ui;}');
    expect(normalised).toContain('.insrbody{flex:1 1 auto;display:grid;grid-template-columns:232px 1fr;min-height:0;}');
    expect(normalised).toContain('.rail{border-right:1px solid var(--line);background:var(--panel-2);overflow-y:auto;padding:8px 0;}');
    expect(normalised).not.toContain('.insr.shadow-viewport');
  });
});
