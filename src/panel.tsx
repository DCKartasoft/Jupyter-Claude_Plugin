import { ReactWidget } from '@jupyterlab/apputils';
import React, { useEffect, useRef, useState } from 'react';

import { claudeIcon } from './icons';
import { ChatClient, ServerMessage } from './ws';

interface IDisplayMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  text: string;
  id: string;
}

let _idSeed = 0;
const nextId = (): string => `m${++_idSeed}`;

const TIERS: Array<'opus' | 'sonnet' | 'haiku'> = ['opus', 'sonnet', 'haiku'];

interface IChatUIProps {
  client: ChatClient;
  registerSubmit: (fn: (text: string) => void) => void;
  getUserMessagePrefix?: () => string;
  onResult?: () => void;
}

function ChatUI(props: IChatUIProps): JSX.Element {
  const [messages, setMessages] = useState<IDisplayMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [tier, setTier] = useState<'opus' | 'sonnet' | 'haiku'>('sonnet');
  const [modelLabel, setModelLabel] = useState<string>('');
  const [backend, setBackend] = useState<string>('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const off = props.client.onMessage((m: ServerMessage) => {
      setMessages(prev => {
        switch (m.type) {
          case 'ready':
            setBackend(m.backend);
            setModelLabel(m.model);
            if ((m as any).tier) setTier((m as any).tier);
            return [
              ...prev,
              {
                role: 'system',
                text: `Connected — ${m.backend} / ${m.model}`,
                id: nextId()
              }
            ];
          case 'assistant_text':
            return [...prev, { role: 'assistant', text: m.text, id: nextId() }];
          case 'tool_use':
            return [
              ...prev,
              {
                role: 'tool',
                text: `→ ${m.name}(${JSON.stringify(m.input).slice(0, 120)})`,
                id: nextId()
              }
            ];
          case 'result':
            setBusy(false);
            props.onResult?.();
            return [
              ...prev,
              {
                role: 'system',
                text: `done — ${m.num_turns} turns, ${(m.duration_ms / 1000).toFixed(1)}s, $${m.total_cost_usd?.toFixed(4) ?? '0'}`,
                id: nextId()
              }
            ];
          case 'error':
            setBusy(false);
            return [
              ...prev,
              { role: 'system', text: `error: ${m.message}`, id: nextId() }
            ];
          default:
            return prev;
        }
      });
    });
    props.client.connect();
    return () => {
      off();
    };
  }, [props.client]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [messages, busy]);

  const submitText = (text: string): void => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages(prev => [
      ...prev,
      { role: 'user', text: trimmed, id: nextId() }
    ]);
    props.client.send(trimmed);
    setBusy(true);
  };

  useEffect(() => {
    props.registerSubmit(submitText);
  }, [props.registerSubmit]);

  const submitFromInput = (): void => {
    if (busy) return;
    const trimmed = draft.trim();
    if (!trimmed) return;
    const prefix = props.getUserMessagePrefix?.() ?? '';
    // Show the user's exact text in the transcript; send prefix + text to Claude.
    setMessages(prev => [
      ...prev,
      { role: 'user', text: trimmed, id: nextId() }
    ]);
    props.client.send(prefix + trimmed);
    setBusy(true);
    setDraft('');
  };

  const onTierChange = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    if (busy) return;
    const next = e.target.value as 'opus' | 'sonnet' | 'haiku';
    setTier(next);
    props.client.setTier(next);
    setMessages(prev => [
      ...prev,
      { role: 'system', text: `Switching to ${next}…`, id: nextId() }
    ]);
  };

  return (
    <div className="jclaude-panel">
      <div className="jclaude-header">
        <label className="jclaude-header-label">Model</label>
        <select
          className="jclaude-tier-select"
          value={tier}
          onChange={onTierChange}
          disabled={busy || backend !== 'bedrock'}
          title={
            backend === 'bedrock'
              ? `Backend: ${backend}. Current model: ${modelLabel}`
              : 'Tier switching is only available on the Bedrock backend'
          }
        >
          {TIERS.map(t => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div className="jclaude-messages" ref={scrollRef}>
        {messages.map(m => (
          <div key={m.id} className={`jclaude-msg jclaude-msg-${m.role}`}>
            <div className="jclaude-msg-role">{m.role}</div>
            <div className="jclaude-msg-text">{m.text}</div>
          </div>
        ))}
        {busy && (
          <div className="jclaude-msg jclaude-msg-thinking">
            <div className="jclaude-spinner" />
            <span className="jclaude-msg-text">Claude is thinking…</span>
          </div>
        )}
      </div>
      <div className="jclaude-input-row">
        <textarea
          className="jclaude-input"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submitFromInput();
            }
          }}
          placeholder={
            busy ? 'Waiting for Claude…' : 'Ask Claude about this notebook…'
          }
          disabled={busy}
          rows={3}
        />
        <button
          className="jclaude-send"
          onClick={submitFromInput}
          disabled={busy || !draft.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export class ChatPanelWidget extends ReactWidget {
  private _submit: ((text: string) => void) | null = null;
  private _userMessagePrefix: (() => string) | null = null;
  private _onResult: (() => void) | null = null;

  constructor(private readonly client: ChatClient) {
    super();
    this.id = 'jupyter-claude:chat-panel';
    this.title.caption = 'Claude';
    this.title.label = 'Claude';
    this.title.icon = claudeIcon;
    this.addClass('jclaude-panel-widget');
  }

  /** Provide a fn that returns text to prepend to free-form user messages
   * (e.g. a notebook-context pin). Not applied to command-driven sendMessage()
   * calls — those already include their own context. */
  setUserMessagePrefixProvider(fn: () => string): void {
    this._userMessagePrefix = fn;
  }

  setOnResult(fn: () => void): void {
    this._onResult = fn;
  }

  render(): JSX.Element {
    return (
      <ChatUI
        client={this.client}
        registerSubmit={fn => {
          this._submit = fn;
        }}
        getUserMessagePrefix={() => this._userMessagePrefix?.() ?? ''}
        onResult={() => this._onResult?.()}
      />
    );
  }

  sendMessage(text: string): void {
    if (this._submit) {
      this._submit(text);
    } else {
      this.client.send(text);
    }
  }
}
