import {
  ILabShell,
  ILayoutRestorer,
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ICommandPalette } from '@jupyterlab/apputils';
import { INotebookTracker } from '@jupyterlab/notebook';
import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { CommandIDs, registerCommands } from './commands';
import { ChatPanelWidget } from './panel';
import { ChatClient } from './ws';

const PLUGIN_ID = '@dckartasoft/jupyter-claude:plugin';

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  description:
    'Collaborate with Claude on Jupyter notebook code and documentation',
  autoStart: true,
  requires: [INotebookTracker, ILabShell],
  optional: [ISettingRegistry, ICommandPalette, ILayoutRestorer],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker,
    labShell: ILabShell,
    settingRegistry: ISettingRegistry | null,
    palette: ICommandPalette | null,
    restorer: ILayoutRestorer | null
  ) => {
    console.log(`JupyterLab extension ${PLUGIN_ID} is activated!`);

    if (settingRegistry) {
      settingRegistry
        .load(PLUGIN_ID)
        .then(settings => {
          console.log(`${PLUGIN_ID} settings loaded:`, settings.composite);
        })
        .catch(reason => {
          console.error(`Failed to load settings for ${PLUGIN_ID}.`, reason);
        });
    }

    const client = new ChatClient();
    const chatPanel = new ChatPanelWidget(client);

    registerCommands(app, tracker, labShell, palette, chatPanel, client);

    labShell.add(chatPanel, 'right', { rank: 900 });

    if (restorer) {
      restorer.add(chatPanel, chatPanel.id);
    }

    console.log(
      `${PLUGIN_ID} commands registered:`,
      Object.values(CommandIDs)
    );
  }
};

export default plugin;
