import React from 'react';
import { ShadowReactScreen } from '../components/ShadowReactScreen.jsx';
import MtdpPackagingApp from './MtdpPackagingApp.jsx';
import baseCss from '../styles/mtdp-packaging-v4.css?raw';
import chromeCss from '../styles/window-chrome.css?raw';

const fillCss = `
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
`;

export default function PackagingScreen() {
  return (
    <ShadowReactScreen css={baseCss + fillCss + chromeCss} className="packaging-shadow">
      <div className="stage stage--desktop">
        <MtdpPackagingApp />
      </div>
    </ShadowReactScreen>
  );
}
