import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { requestAPI } from './request';

/**
 * Initialization data for the @dckartasoft/jupyter-claude extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: '@dckartasoft/jupyter-claude:plugin',
  description: 'Collaborate with Claude on Jupyter notebook code and documentation',
  autoStart: true,
  optional: [ISettingRegistry],
  activate: (app: JupyterFrontEnd, settingRegistry: ISettingRegistry | null) => {
    console.log('JupyterLab extension @dckartasoft/jupyter-claude is activated!');

    if (settingRegistry) {
      settingRegistry
        .load(plugin.id)
        .then(settings => {
          console.log('@dckartasoft/jupyter-claude settings loaded:', settings.composite);
        })
        .catch(reason => {
          console.error('Failed to load settings for @dckartasoft/jupyter-claude.', reason);
        });
    }

    requestAPI<any>('hello', app.serviceManager.serverSettings)
      .then(data => {
        console.log(data);
      })
      .catch(reason => {
        console.error(
          `The jupyter_claude server extension appears to be missing.\n${reason}`
        );
      });
  }
};

export default plugin;
