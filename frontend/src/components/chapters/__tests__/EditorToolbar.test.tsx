/**
 * Accessibility tests for EditorToolbar (#50) — every icon-only button must
 * expose an accessible name, and the group must be a labeled toolbar.
 */
import { useState } from 'react';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { EditorToolbar } from '../EditorToolbar';

expect.extend(toHaveNoViolations);

// Minimal chainable TipTap editor mock.
function makeChain() {
  const chain: Record<string, unknown> = {};
  const methods = [
    'focus', 'toggleBold', 'toggleItalic', 'toggleUnderline', 'toggleStrike',
    'toggleHeading', 'toggleBulletList', 'toggleOrderedList', 'toggleBlockquote',
    'toggleCodeBlock', 'undo', 'redo', 'setHorizontalRule',
  ];
  methods.forEach((m) => { chain[m] = () => chain; });
  chain.run = () => true;
  return chain;
}

// EditorToolbar subscribes through useEditorState (#347), which registers a
// 'transaction' listener — so the mock needs on/off. Assertions below are
// unchanged; only the surface the component actually uses grew.
function makeEditor(isActive: (name: string, attrs?: unknown) => boolean = () => false) {
  const listeners: Record<string, Array<() => void>> = {};
  return {
    chain: () => makeChain(),
    can: () => ({ chain: () => makeChain() }),
    isActive,
    on(event: string, fn: () => void) {
      (listeners[event] ||= []).push(fn);
      return this;
    },
    off(event: string, fn: () => void) {
      listeners[event] = (listeners[event] || []).filter((f) => f !== fn);
      return this;
    },
    /** Fire a ProseMirror-style transaction, as typing would. */
    emitTransaction() {
      (listeners.transaction || []).forEach((fn) => fn());
    },
  };
}

const mockEditor = makeEditor() as never;

const EXPECTED_LABELS = [
  'Bold', 'Italic', 'Underline', 'Strikethrough',
  'Heading 1', 'Heading 2', 'Heading 3',
  'Bullet List', 'Ordered List', 'Blockquote', 'Code Block',
  'Undo', 'Redo', 'Horizontal Rule',
];

describe('EditorToolbar accessibility', () => {
  it('renders a labeled toolbar landmark', () => {
    render(<EditorToolbar editor={mockEditor} />);
    expect(screen.getByRole('toolbar', { name: /text formatting/i })).toBeInTheDocument();
  });

  it.each(EXPECTED_LABELS)('exposes an accessible name for the "%s" button', (label) => {
    render(<EditorToolbar editor={mockEditor} />);
    expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
  });

  it('reflects active state via aria-pressed on toggle buttons', () => {
    // Editor where "bold" is active; the Bold button must report aria-pressed=true
    // and an inactive control (Italic) aria-pressed=false.
    const activeEditor = makeEditor((name: string) => name === 'bold') as never;
    render(<EditorToolbar editor={activeEditor} />);
    expect(screen.getByRole('button', { name: 'Bold' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Italic' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('has no axe violations', async () => {
    const { container } = render(<EditorToolbar editor={mockEditor} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders nothing without an editor', () => {
    const { container } = render(<EditorToolbar editor={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('keeps aria-pressed live after a transaction (the subscription works)', async () => {
    // memo without a subscription would freeze aria-pressed at its first value,
    // which is worse than the perf problem it set out to fix.
    let bold = false;
    const editor = makeEditor((name: string) => name === 'bold' && bold);
    render(<EditorToolbar editor={editor as never} />);

    expect(screen.getByRole('button', { name: 'Bold' })).toHaveAttribute('aria-pressed', 'false');

    bold = true;
    await act(async () => {
      editor.emitTransaction();
    });

    expect(screen.getByRole('button', { name: 'Bold' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('does not re-render when the parent re-renders (#347)', async () => {
    // The perf half. ChapterEditor re-renders on every keystroke because
    // useEditor subscribes to transactions; memo is what stops that cascading
    // into fourteen buttons plus their icons.
    //
    // Probe: a render runs the useEditorState selector, which calls isActive.
    // If the toolbar re-renders, the call count climbs. Drop the memo and this
    // test goes red.
    const editor = makeEditor();
    const isActiveSpy = jest.spyOn(editor, 'isActive');

    function Parent() {
      const [n, setN] = useState(0);
      return (
        <>
          <button type="button" onClick={() => setN(n + 1)}>bump {n}</button>
          <EditorToolbar editor={editor as never} />
        </>
      );
    }

    render(<Parent />);
    const callsAfterMount = isActiveSpy.mock.calls.length;
    expect(callsAfterMount).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: /bump/i }));
    expect(screen.getByRole('button', { name: /bump 1/i })).toBeInTheDocument();

    expect(isActiveSpy.mock.calls.length).toBe(callsAfterMount);
  });
});
