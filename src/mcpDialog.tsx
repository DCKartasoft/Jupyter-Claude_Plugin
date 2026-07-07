import { Dialog, ReactWidget, showDialog } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection } from '@jupyterlab/services';
import React, { useState } from 'react';

export interface McpServerInfo {
  name: string;
  description: string;
  enabled: boolean;
  required: boolean;
}

async function fetchServers(): Promise<McpServerInfo[]> {
  const settings = ServerConnection.makeSettings();
  const url = URLExt.join(settings.baseUrl, 'jupyter-claude', 'mcp-servers');
  const res = await ServerConnection.makeRequest(url, {}, settings);
  if (!res.ok) throw new Error(`GET mcp-servers: ${res.status}`);
  const data = (await res.json()) as { servers: McpServerInfo[] };
  return data.servers;
}

async function saveServers(enabled: string[]): Promise<string[]> {
  const settings = ServerConnection.makeSettings();
  const url = URLExt.join(settings.baseUrl, 'jupyter-claude', 'mcp-servers');
  const res = await ServerConnection.makeRequest(
    url,
    {
      method: 'POST',
      body: JSON.stringify({ enabled })
    },
    settings
  );
  if (!res.ok) throw new Error(`POST mcp-servers: ${res.status}`);
  const data = (await res.json()) as { enabled: string[] };
  return data.enabled;
}

function McpChecklist(props: {
  servers: McpServerInfo[];
  onChange: (enabled: string[]) => void;
}): JSX.Element {
  const [selection, setSelection] = useState<Set<string>>(
    new Set(props.servers.filter(s => s.enabled).map(s => s.name))
  );

  const toggle = (name: string, required: boolean): void => {
    if (required) return;
    const next = new Set(selection);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelection(next);
    props.onChange(Array.from(next));
  };

  return (
    <div className="jclaude-mcp-list">
      <p className="jclaude-mcp-hint">
        Fewer servers = faster startup. The <b>jupyter</b> server is always on
        (Claude needs it to read/write cells).
      </p>
      {props.servers.map(s => (
        <label key={s.name} className="jclaude-mcp-item">
          <input
            type="checkbox"
            checked={selection.has(s.name) || s.required}
            disabled={s.required}
            onChange={() => toggle(s.name, s.required)}
          />
          <span className="jclaude-mcp-name">
            {s.name}
            {s.required && (
              <span className="jclaude-mcp-required"> (required)</span>
            )}
          </span>
          <span className="jclaude-mcp-desc">{s.description}</span>
        </label>
      ))}
    </div>
  );
}

class McpChecklistBody extends ReactWidget {
  selection: string[];

  constructor(private readonly servers: McpServerInfo[]) {
    super();
    this.selection = servers.filter(s => s.enabled).map(s => s.name);
    this.addClass('jclaude-mcp-dialog');
  }

  render(): JSX.Element {
    return (
      <McpChecklist
        servers={this.servers}
        onChange={next => {
          this.selection = next;
        }}
      />
    );
  }

  getValue(): string[] {
    return this.selection;
  }
}

export async function pickMcpServers(): Promise<string[] | null> {
  const servers = await fetchServers();
  const body = new McpChecklistBody(servers);
  const result = await showDialog<string[]>({
    title: 'MCP servers',
    body,
    buttons: [
      Dialog.cancelButton(),
      Dialog.okButton({ label: 'Apply' })
    ]
  });
  if (!result.button.accept) return null;
  const enabled = await saveServers(body.getValue());
  return enabled;
}
