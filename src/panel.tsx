import { ReactWidget } from '@jupyterlab/apputils';
import React, { useEffect, useRef, useState } from 'react';

import { ChatClient, ServerMessage } from './ws';

interface DisplayMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  text: string;
  id: string;
}

let _idSeed = 0;
const nextId = (): string => `m${++_idSeed}`;

function ChatUI(props: { client: ChatClient }): JSX.Element {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const off = props.client.onMessage((m: ServerMessage) => {
      setMessages(prev => {
        switch (m.type) {
          case 'ready':
            return [
              ...prev,
              {
                role: 'system',
                text: `Connected — ${m.backend} / ${m.model}`,
                id: nextId()
              }
            ];
          case 'assistant_text':
            return [
              ...prev,
              { role: 'assistant', text: m.text, id: nextId() }
            ];
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
  }, [messages]);

  const submit = (): void => {
    const text = draft.trim();
    if (!text || busy) return;
    setMessages(prev => [...prev, { role: 'user', text, id: nextId() }]);
    props.client.send(text);
    setDraft('');
    setBusy(true);
  };

  return (
    <div className="jclaude-panel">
      <div className="jclaude-messages" ref={scrollRef}>
        {messages.map(m => (
          <div key={m.id} className={`jclaude-msg jclaude-msg-${m.role}`}>
            <div className="jclaude-msg-role">{m.role}</div>
            <div className="jclaude-msg-text">{m.text}</div>
          </div>
        ))}
      </div>
      <div className="jclaude-input-row">
        <textarea
          className="jclaude-input"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
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
          onClick={submit}
          disabled={busy || !draft.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export class ChatPanelWidget extends ReactWidget {
  constructor(private readonly client: ChatClient) {
    super();
    this.id = 'jupyter-claude:chat-panel';
    this.title.caption = 'Claude';
    this.title.label = 'Claude';
    this.addClass('jclaude-panel-widget');
  }

  render(): JSX.Element {
    return <ChatUI client={this.client} />;
  }

  sendMessage(text: string): void {
    this.client.send(text);
  }
}
