import { Dialog, ReactWidget, showDialog } from '@jupyterlab/apputils';
import React from 'react';

class PromptTextareaBody extends ReactWidget {
  value = '';

  constructor(
    private readonly initial: string,
    private readonly placeholder: string
  ) {
    super();
    this.value = initial;
    this.addClass('jclaude-prompt-dialog');
  }

  render(): JSX.Element {
    return (
      <textarea
        className="jclaude-prompt-textarea"
        autoFocus
        defaultValue={this.initial}
        placeholder={this.placeholder}
        onChange={e => {
          this.value = e.target.value;
        }}
      />
    );
  }

  getValue(): string {
    return this.value;
  }
}

/**
 * Multi-line prompt dialog. Sized ~half A5 landscape (roughly 780x280).
 * Returns the entered text, or null if cancelled / empty.
 */
export async function getMultilineText(options: {
  title: string;
  placeholder?: string;
  initial?: string;
  okLabel?: string;
}): Promise<string | null> {
  const body = new PromptTextareaBody(
    options.initial ?? '',
    options.placeholder ?? ''
  );
  const result = await showDialog<string>({
    title: options.title,
    body,
    buttons: [
      Dialog.cancelButton(),
      Dialog.okButton({ label: options.okLabel ?? 'OK' })
    ]
  });
  if (!result.button.accept) return null;
  const text = body.getValue().trim();
  return text || null;
}
