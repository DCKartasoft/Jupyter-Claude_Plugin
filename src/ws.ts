import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection } from '@jupyterlab/services';

export interface AssistantTextMessage {
  type: 'assistant_text';
  text: string;
}

export interface ToolUseMessage {
  type: 'tool_use';
  id: string;
  name: string;
  input: unknown;
}

export interface SystemMessage {
  type: 'system';
  subtype: string;
  data: unknown;
}

export interface UserEchoMessage {
  type: 'user_echo';
  content: Array<{ type: string; text: string | null }>;
}

export interface ResultMessage {
  type: 'result';
  duration_ms: number;
  num_turns: number;
  total_cost_usd: number;
  usage: unknown;
}

export interface ReadyMessage {
  type: 'ready';
  backend: string;
  model: string;
}

export interface ErrorMessage {
  type: 'error';
  message: string;
  traceback?: string;
}

export type ServerMessage =
  | AssistantTextMessage
  | ToolUseMessage
  | SystemMessage
  | UserEchoMessage
  | ResultMessage
  | ReadyMessage
  | ErrorMessage;

export interface UserMessagePayload {
  type: 'user_message';
  text: string;
}

export interface SetTierPayload {
  type: 'set_tier';
  tier: 'opus' | 'sonnet' | 'haiku';
}

export interface McpReloadPayload {
  type: 'mcp_reload';
}

export type ClientMessage =
  | UserMessagePayload
  | SetTierPayload
  | McpReloadPayload;

export type MessageHandler = (msg: ServerMessage) => void;

export class ChatClient {
  private ws: WebSocket | null = null;
  private handlers = new Set<MessageHandler>();
  private reconnectDelayMs = 1000;
  private closedByUser = false;
  private queue: ClientMessage[] = [];

  constructor(private readonly settings = ServerConnection.makeSettings()) {}

  connect(): void {
    this.closedByUser = false;
    const wsUrl = URLExt.join(
      this.settings.wsUrl,
      'jupyter-claude',
      'chat'
    );
    const withToken = this.settings.token
      ? `${wsUrl}?token=${encodeURIComponent(this.settings.token)}`
      : wsUrl;

    this.ws = new WebSocket(withToken);
    this.ws.onopen = () => {
      this.reconnectDelayMs = 1000;
      while (this.queue.length > 0) {
        const m = this.queue.shift();
        if (m) this.ws?.send(JSON.stringify(m));
      }
    };
    this.ws.onmessage = ev => {
      let parsed: ServerMessage;
      try {
        parsed = JSON.parse(ev.data as string) as ServerMessage;
      } catch (e) {
        console.error('jupyter-claude: bad WS frame', ev.data, e);
        return;
      }
      this.handlers.forEach(h => h(parsed));
    };
    this.ws.onerror = ev => {
      console.error('jupyter-claude WS error', ev);
    };
    this.ws.onclose = () => {
      this.ws = null;
      if (!this.closedByUser) {
        setTimeout(() => this.connect(), this.reconnectDelayMs);
        this.reconnectDelayMs = Math.min(this.reconnectDelayMs * 2, 30_000);
      }
    };
  }

  disconnect(): void {
    this.closedByUser = true;
    this.ws?.close();
    this.ws = null;
  }

  send(text: string): void {
    const msg: ClientMessage = { type: 'user_message', text };
    this._sendRaw(msg);
  }

  setTier(tier: 'opus' | 'sonnet' | 'haiku'): void {
    const msg: ClientMessage = { type: 'set_tier', tier };
    this._sendRaw(msg);
  }

  reloadMcp(): void {
    this._sendRaw({ type: 'mcp_reload' } as ClientMessage);
  }

  private _sendRaw(msg: ClientMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      this.queue.push(msg);
      if (!this.ws) this.connect();
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
