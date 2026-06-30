/**
 * Accessibility tests for EditorToolbar (#50) — every icon-only button must
 * expose an accessible name, and the group must be a labeled toolbar.
 */
import { render, screen } from '@testing-library/react';
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

const mockEditor = {
  chain: () => makeChain(),
  can: () => ({ chain: () => makeChain() }),
  isActive: () => false,
} as never;

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

  it('has no axe violations', async () => {
    const { container } = render(<EditorToolbar editor={mockEditor} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders nothing without an editor', () => {
    const { container } = render(<EditorToolbar editor={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
