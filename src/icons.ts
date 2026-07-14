import { LabIcon } from '@jupyterlab/ui-components';

// SVG source lives in ../icons/*.svg. These strings are inlined here so the
// build doesn't need an SVG loader. If you edit an SVG, paste the new content
// into the matching const below.

const claudeSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <circle cx="16" cy="16" r="5" fill="currentColor"/>
  <rect x="14" y="3" width="4" height="8" rx="2" fill="currentColor"/>
  <rect x="14" y="21" width="4" height="8" rx="2" fill="currentColor"/>
  <rect x="3" y="14" width="8" height="4" rx="2" fill="currentColor"/>
  <rect x="21" y="14" width="8" height="4" rx="2" fill="currentColor"/>
  <path d="M8 8L12 12M20 20L24 24M24 8L20 12M12 20L8 24" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
</svg>`;

const toolsSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="3"/>
  <rect x="9" y="1" width="4" height="4" fill="currentColor"/>
  <rect x="9" y="17" width="4" height="4" fill="currentColor"/>
  <rect x="1" y="9" width="4" height="4" fill="currentColor"/>
  <rect x="17" y="9" width="4" height="4" fill="currentColor"/>
  <circle cx="11" cy="11" r="2" fill="currentColor"/>
  <path d="M15 24L26 13" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
  <circle cx="15" cy="24" r="3" stroke="currentColor" stroke-width="3"/>
</svg>`;

const generateCellSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <rect x="5" y="5" width="22" height="22" stroke="currentColor" stroke-width="3"/>
  <path d="M16 5V27M5 16H27" stroke="currentColor" stroke-width="3"/>
  <path d="M10 8V14M7 11H13" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
</svg>`;

const correctCellSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <rect x="5" y="5" width="22" height="22" stroke="currentColor" stroke-width="3"/>
  <path d="M16 5V27M5 16H27" stroke="currentColor" stroke-width="3"/>
  <path d="M7 11L10 14L15 8" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const mcpServersSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <rect x="4" y="5" width="20" height="6" rx="2" stroke="currentColor" stroke-width="2"/>
  <rect x="4" y="12" width="20" height="6" rx="2" stroke="currentColor" stroke-width="2"/>
  <rect x="4" y="19" width="20" height="6" rx="2" stroke="currentColor" stroke-width="2"/>
  <circle cx="8" cy="8" r="1.5" fill="currentColor"/>
  <circle cx="8" cy="15" r="1.5" fill="currentColor"/>
  <circle cx="8" cy="22" r="1.5" fill="currentColor"/>
  <circle cx="24.5" cy="24.5" r="5.5" fill="var(--jp-layout-color1)" stroke="currentColor" stroke-width="2"/>
  <path d="M22 24L25 27L29 22" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const explainSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" fill="none">
  <rect x="4" y="5" width="24" height="18" rx="4" stroke="currentColor" stroke-width="3"/>
  <path d="M10 22V28L16 23" fill="currentColor"/>
  <rect x="9" y="10" width="14" height="2" rx="1" fill="currentColor"/>
  <rect x="9" y="15" width="11" height="2" rx="1" fill="currentColor"/>
</svg>`;

export const claudeIcon = new LabIcon({
  name: 'jclaude:claude',
  svgstr: claudeSvg
});

export const toolsIcon = new LabIcon({
  name: 'jclaude:tools',
  svgstr: toolsSvg
});

export const generateCellIcon = new LabIcon({
  name: 'jclaude:generate-cell',
  svgstr: generateCellSvg
});

export const correctCellIcon = new LabIcon({
  name: 'jclaude:correct-cell',
  svgstr: correctCellSvg
});

export const mcpServersIcon = new LabIcon({
  name: 'jclaude:mcp-servers',
  svgstr: mcpServersSvg
});

export const explainIcon = new LabIcon({
  name: 'jclaude:explain',
  svgstr: explainSvg
});
