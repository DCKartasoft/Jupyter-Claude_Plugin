import { CommandRegistry } from '@lumino/commands';

import { ILabShell, JupyterFrontEnd } from '@jupyterlab/application';
import { ICommandPalette } from '@jupyterlab/apputils';
import {
  INotebookTracker,
  NotebookActions,
  NotebookPanel
} from '@jupyterlab/notebook';

import { ChatPanelWidget } from './panel';

export const CommandIDs = {
  openChat: 'jclaude:open-chat',
  generateCell: 'jclaude:generate-cell',
  explainCell: 'jclaude:explain-cell',
  fixLastError: 'jclaude:fix-last-error'
};

interface LastError {
  notebookId: string;
  cellSource: string;
  errorName: string;
  errorValue: string;
  traceback: string[];
}

const lastErrors = new Map<string, LastError>();

function activeCell(tracker: INotebookTracker): {
  panel: NotebookPanel;
  source: string;
} | null {
  const panel = tracker.currentWidget;
  if (!panel || !panel.content.activeCell) return null;
  const source = panel.content.activeCell.model.sharedModel.getSource();
  return { panel, source };
}

function trackCellErrors(tracker: INotebookTracker): void {
  NotebookActions.executed.connect((_, args) => {
    const { notebook, cell, success } = args as {
      notebook: { id?: string };
      cell: { model: { sharedModel: { getSource(): string }; outputs?: any } };
      success: boolean;
      error?: unknown;
    };
    if (success) return;

    const nbId = notebook.id ?? tracker.currentWidget?.id ?? 'unknown';
    const source = cell.model.sharedModel.getSource();

    let errName = 'Error';
    let errValue = '';
    let traceback: string[] = [];
    const outputs: any = cell.model.outputs;
    if (outputs && typeof outputs.length === 'number') {
      for (let i = 0; i < outputs.length; i++) {
        const out = outputs.get?.(i) ?? outputs[i];
        const data = out?.toJSON?.() ?? out;
        if (data && data.output_type === 'error') {
          errName = data.ename ?? errName;
          errValue = data.evalue ?? '';
          traceback = data.traceback ?? [];
          break;
        }
      }
    }

    lastErrors.set(nbId, {
      notebookId: nbId,
      cellSource: source,
      errorName: errName,
      errorValue: errValue,
      traceback
    });
  });
}

export function registerCommands(
  app: JupyterFrontEnd,
  tracker: INotebookTracker,
  labShell: ILabShell,
  palette: ICommandPalette | null,
  chatPanel: ChatPanelWidget
): void {
  const commands: CommandRegistry = app.commands;
  const category = 'Claude';

  trackCellErrors(tracker);

  commands.addCommand(CommandIDs.openChat, {
    label: 'Open Claude Chat',
    caption: 'Open the Claude assistant panel',
    execute: () => {
      if (!chatPanel.isAttached) {
        labShell.add(chatPanel, 'right', { rank: 900 });
      }
      labShell.activateById(chatPanel.id);
    }
  });

  commands.addCommand(CommandIDs.generateCell, {
    label: 'Generate cell with Claude…',
    caption: 'Ask Claude to generate a new cell in the current notebook',
    isEnabled: () => tracker.currentWidget !== null,
    execute: async () => {
      const panel = tracker.currentWidget;
      if (!panel) return;
      const prompt = window.prompt('Describe the cell to generate:');
      if (!prompt) return;
      if (!chatPanel.isAttached) {
        labShell.add(chatPanel, 'right', { rank: 900 });
      }
      labShell.activateById(chatPanel.id);
      chatPanel.sendMessage(
        `Please insert a new code cell in the current notebook that does the following: ${prompt}\n\nUse the mcp__jupyter__insert_execute_code_cell tool (or insert_cell followed by execute_cell) to add it. Do not just show the code as text.`
      );
    }
  });

  commands.addCommand(CommandIDs.explainCell, {
    label: 'Explain this cell with Claude',
    caption: 'Ask Claude to insert a markdown cell explaining the active cell',
    isEnabled: () => activeCell(tracker) !== null,
    execute: async () => {
      const info = activeCell(tracker);
      if (!info) return;
      if (!chatPanel.isAttached) {
        labShell.add(chatPanel, 'right', { rank: 900 });
      }
      labShell.activateById(chatPanel.id);
      chatPanel.sendMessage(
        `Please insert a markdown cell ABOVE the currently active cell in the notebook that explains what this code does. The code to explain is:\n\n\`\`\`\n${info.source}\n\`\`\`\n\nUse mcp__jupyter__insert_cell with cell_type=markdown at the appropriate position. Keep the explanation focused and technical.`
      );
    }
  });

  commands.addCommand(CommandIDs.fixLastError, {
    label: "Fix last error with Claude",
    caption:
      'Ask Claude to insert a corrected cell for the most recent cell error',
    isEnabled: () => {
      const nb = tracker.currentWidget;
      return nb !== null && lastErrors.has(nb.id);
    },
    execute: async () => {
      const nb = tracker.currentWidget;
      if (!nb) return;
      const err = lastErrors.get(nb.id);
      if (!err) {
        window.alert('No recent cell error captured for this notebook.');
        return;
      }
      if (!chatPanel.isAttached) {
        labShell.add(chatPanel, 'right', { rank: 900 });
      }
      labShell.activateById(chatPanel.id);
      const traceback = err.traceback.join('\n');
      chatPanel.sendMessage(
        `A cell in the current notebook raised an error. Please insert a new code cell BELOW the failed cell containing a corrected version. Use mcp__jupyter__insert_execute_code_cell.\n\nFailed cell source:\n\`\`\`\n${err.cellSource}\n\`\`\`\n\nError: ${err.errorName}: ${err.errorValue}\n\nTraceback:\n\`\`\`\n${traceback}\n\`\`\``
      );
    }
  });

  if (palette) {
    for (const command of Object.values(CommandIDs)) {
      palette.addItem({ command, category });
    }
  }

  app.contextMenu.addItem({
    command: CommandIDs.explainCell,
    selector: '.jp-Notebook .jp-Cell',
    rank: 100
  });
  app.contextMenu.addItem({
    command: CommandIDs.fixLastError,
    selector: '.jp-Notebook .jp-Cell',
    rank: 101
  });
}
