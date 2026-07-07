import { CommandRegistry } from '@lumino/commands';

import { ILabShell, JupyterFrontEnd } from '@jupyterlab/application';
import { ICommandPalette, InputDialog } from '@jupyterlab/apputils';
import {
  INotebookTracker,
  NotebookActions,
  NotebookPanel
} from '@jupyterlab/notebook';
import {
  addIcon,
  bugIcon,
  editIcon,
  extensionIcon
} from '@jupyterlab/ui-components';

import { claudeIcon } from './icons';
import { pickMcpServers } from './mcpDialog';
import { ChatPanelWidget } from './panel';
import { ChatClient } from './ws';

export const CommandIDs = {
  openChat: 'jclaude:open-chat',
  generateCell: 'jclaude:generate-cell',
  explainCell: 'jclaude:explain-cell',
  fixLastError: 'jclaude:fix-last-error',
  mcpServers: 'jclaude:mcp-servers'
};

interface LastError {
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
    const { cell, success } = args as {
      cell: { model: { sharedModel: { getSource(): string }; outputs?: any } };
      success: boolean;
    };
    if (success) return;

    const nbId = tracker.currentWidget?.id;
    if (!nbId) return;

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
      cellSource: source,
      errorName: errName,
      errorValue: errValue,
      traceback
    });
    console.log(
      `jupyter-claude: captured error for notebook ${nbId}: ${errName}: ${errValue}`
    );
  });
}

function revealChat(chatPanel: ChatPanelWidget, labShell: ILabShell): void {
  if (!chatPanel.isAttached) {
    labShell.add(chatPanel, 'right', { rank: 900 });
  }
  labShell.activateById(chatPanel.id);
}

export function registerCommands(
  app: JupyterFrontEnd,
  tracker: INotebookTracker,
  labShell: ILabShell,
  palette: ICommandPalette | null,
  chatPanel: ChatPanelWidget,
  chatClient: ChatClient
): void {
  const commands: CommandRegistry = app.commands;
  const category = 'Claude';

  trackCellErrors(tracker);

  commands.addCommand(CommandIDs.openChat, {
    label: 'Open Claude Chat',
    caption: 'Open the Claude assistant panel',
    icon: claudeIcon,
    execute: () => revealChat(chatPanel, labShell)
  });

  commands.addCommand(CommandIDs.generateCell, {
    label: 'Generate cell with Claude…',
    caption: 'Ask Claude to generate a new cell in the current notebook',
    icon: addIcon,
    isEnabled: () => tracker.currentWidget !== null,
    execute: async () => {
      const panel = tracker.currentWidget;
      if (!panel) return;

      const typeChoice = await InputDialog.getItem({
        title: 'Generate cell with Claude',
        label: 'Cell type:',
        items: ['code', 'markdown', 'raw'],
        current: 0,
        editable: false,
        okLabel: 'Next'
      });
      if (!typeChoice.button.accept || !typeChoice.value) return;
      const cellType = typeChoice.value as 'code' | 'markdown' | 'raw';

      const placeholders: Record<typeof cellType, string> = {
        code: 'e.g. load iris.csv into a pandas DataFrame and show df.head()',
        markdown: 'e.g. an intro section titled "Data loading" describing the next few cells',
        raw: 'e.g. an nbconvert-only LaTeX preamble block'
      };
      const description = await InputDialog.getText({
        title: `Generate ${cellType} cell with Claude`,
        label: `Describe the ${cellType} cell to generate:`,
        placeholder: placeholders[cellType],
        okLabel: 'Generate'
      });
      if (!description.button.accept || !description.value) return;

      revealChat(chatPanel, labShell);

      let prompt: string;
      if (cellType === 'code') {
        prompt = `Please insert a new code cell in the current notebook that does the following: ${description.value}\n\nUse mcp__jupyter__insert_execute_code_cell (or insert_cell followed by execute_cell) to add it. Do not just show the code as text.`;
      } else {
        prompt = `Please insert a new ${cellType} cell in the current notebook with the following content: ${description.value}\n\nUse mcp__jupyter__insert_cell with cell_type="${cellType}". Do NOT execute the cell — ${cellType} cells are not executable. Return the raw content the cell should contain.`;
      }
      chatPanel.sendMessage(prompt);
    }
  });

  commands.addCommand(CommandIDs.explainCell, {
    label: 'Explain this cell with Claude',
    caption: 'Ask Claude to insert a markdown cell explaining the active cell',
    icon: editIcon,
    isEnabled: () => activeCell(tracker) !== null,
    execute: async () => {
      const info = activeCell(tracker);
      if (!info) return;
      revealChat(chatPanel, labShell);
      chatPanel.sendMessage(
        `Please insert a markdown cell ABOVE the currently active cell in the notebook that explains what this code does. The code to explain is:\n\n\`\`\`\n${info.source}\n\`\`\`\n\nUse mcp__jupyter__insert_cell with cell_type=markdown at the appropriate position. Keep the explanation focused and technical.`
      );
    }
  });

  commands.addCommand(CommandIDs.fixLastError, {
    label: 'Fix last error with Claude',
    caption:
      'Ask Claude to insert a corrected cell for the most recent cell error',
    icon: bugIcon,
    isEnabled: () => tracker.currentWidget !== null,
    execute: async () => {
      const nb = tracker.currentWidget;
      if (!nb) return;
      const err = lastErrors.get(nb.id);
      if (!err) {
        await InputDialog.getText({
          title: 'Fix last error with Claude',
          label:
            'No recent cell error captured for this notebook. Run a cell that raises an error, then try again.'
        });
        return;
      }
      revealChat(chatPanel, labShell);
      const traceback = err.traceback.join('\n');
      chatPanel.sendMessage(
        `A cell in the current notebook raised an error. Please insert a new code cell BELOW the failed cell containing a corrected version. Use mcp__jupyter__insert_execute_code_cell.\n\nFailed cell source:\n\`\`\`\n${err.cellSource}\n\`\`\`\n\nError: ${err.errorName}: ${err.errorValue}\n\nTraceback:\n\`\`\`\n${traceback}\n\`\`\``
      );
    }
  });

  commands.addCommand(CommandIDs.mcpServers, {
    label: 'MCP servers…',
    caption: 'Choose which MCP servers Claude may use',
    icon: extensionIcon,
    execute: async () => {
      try {
        const enabled = await pickMcpServers();
        if (enabled === null) return;
        chatClient.reloadMcp();
        revealChat(chatPanel, labShell);
        console.log(`jupyter-claude: enabled MCP servers = ${enabled.join(', ')}`);
      } catch (err) {
        console.error('jupyter-claude MCP dialog failed', err);
      }
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
