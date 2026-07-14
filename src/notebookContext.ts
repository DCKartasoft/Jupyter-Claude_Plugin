import { INotebookTracker } from '@jupyterlab/notebook';

const SNAPSHOT_MAX_CELLS = 50;
const SNAPSHOT_MAX_SOURCE_CHARS = 2000;

function truncate(s: string, max: number): string {
  if (max <= 0 || s.length <= max) return s;
  return `${s.slice(0, max)}…(${s.length - max} more chars)`;
}

/**
 * Build a compact snapshot of the current notebook's cells so Claude can read
 * cell contents directly from the prompt instead of issuing a
 * `mcp__jupyter__read_notebook` round-trip. Truncates at
 * SNAPSHOT_MAX_CELLS cells and SNAPSHOT_MAX_SOURCE_CHARS per cell.
 * Returns an empty string when no notebook is focused.
 */
export function notebookSnapshot(tracker: INotebookTracker): string {
  const panel = tracker.currentWidget;
  if (!panel) return '';
  const cells = panel.content.widgets;
  const totalCells = cells.length;
  if (totalCells === 0) return '<notebook_snapshot cells="0" />\n\n';

  const activeIdx = panel.content.activeCellIndex;
  const shown = Math.min(totalCells, SNAPSHOT_MAX_CELLS);
  const truncated = totalCells > SNAPSHOT_MAX_CELLS;

  const parts: string[] = [];
  parts.push(
    `<notebook_snapshot cells="${totalCells}" shown="${shown}" active="${activeIdx}"${truncated ? ' truncated="true"' : ''}>`
  );
  for (let i = 0; i < shown; i++) {
    const cell = cells[i];
    const type = cell.model.type;
    const source = cell.model.sharedModel.getSource();
    const trimmed = truncate(source, SNAPSHOT_MAX_SOURCE_CHARS);
    const marker = i === activeIdx ? ' active="true"' : '';
    parts.push(`  <cell index="${i}" type="${type}"${marker}>`);
    parts.push(trimmed);
    parts.push(`  </cell>`);
  }
  if (truncated) {
    parts.push(
      `  <!-- ${totalCells - SNAPSHOT_MAX_CELLS} more cells omitted; use mcp__jupyter__read_cell for specific ones if needed -->`
    );
  }
  parts.push(`</notebook_snapshot>`);
  return parts.join('\n') + '\n\n';
}

/**
 * Prefix that pins Claude to the currently-focused notebook AND ships a
 * snapshot of its cells so most requests need no read tool call. Prepended to
 * every prompt (command or free-form).
 */
export function notebookPin(tracker: INotebookTracker): string {
  const panel = tracker.currentWidget;
  if (!panel) return '';
  const path = panel.context.path;
  const snapshot = notebookSnapshot(tracker);
  return (
    `The user's currently focused notebook is \`${path}\`. When you need to ` +
    `WRITE (insert / overwrite / execute) a cell, call ` +
    `mcp__jupyter__use_notebook with notebook_name="${path}" first so the ` +
    `right file is targeted (do NOT default to notebook.ipynb). For READS, ` +
    `use the <notebook_snapshot> below instead of calling read_notebook or ` +
    `read_cell — that snapshot is authoritative for the notebook's current ` +
    `state. Only call read_cell if the snapshot was marked truncated and you ` +
    `specifically need one of the omitted cells.\n\n${snapshot}`
  );
}
