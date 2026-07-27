// frontend/src/__tests__/RichTextEditor.test.tsx

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../components/chapters/ChapterEditor';
import bookClient from '../lib/api/bookClient';

// Mock the book client
jest.mock('../lib/api/bookClient', () => ({
  getChapterContent: jest.fn(),
  saveChapterContent: jest.fn(),
}));

// Create mock chain to be used in the tests.
//
// Each command is its own jest.fn (rather than a plain `return this`) so a test
// can assert *which* command a toolbar button ran. A shared call count on run()
// cannot tell a correctly-wired Bold button from one wired to toggleItalic.
// This layer only proves button -> command wiring; that the command produces
// real <strong>/<h2>/<ul> output is proven in a real browser by
// src/e2e/editor-formatting.spec.ts (TipTap cannot run in jsdom).
const mockRunFn = jest.fn();
const mockChain: Record<string, jest.Mock> = { run: mockRunFn };
for (const command of [
  'focus',
  'toggleBold',
  'toggleItalic',
  'toggleUnderline',
  'toggleStrike',
  'toggleHeading',
  'toggleBulletList',
  'toggleOrderedList',
  'toggleBlockquote',
  'toggleCodeBlock',
  'undo',
  'redo',
  'setHorizontalRule',
]) {
  mockChain[command] = jest.fn(() => mockChain);
}

const mockCan = {
  chain: () => mockChain,
};

// Mock Tiptap's commands since they're not testable directly
jest.mock('@tiptap/react', () => {
  const originalModule = jest.requireActual('@tiptap/react');
  const mockEditor = {
    chain: () => mockChain,
    can: () => mockCan,
    isActive: () => false,
    getHTML: () => '<p>Test content</p>',
    commands: {
      setContent: jest.fn(),
    },
    storage: {
      characterCount: {
        characters: () => 12,
      },
    },
  };

  return {
    ...originalModule,
    useEditor: () => mockEditor,
    EditorContent: ({ className }: { className: string }) => (
      <div data-testid="editor-content" className={className}>
        Editor Content
      </div>
    ),
  };
});

describe('ChapterEditor with Rich Text', () => {
  const bookId = 'book-123';
  const chapterId = 'chapter-456';

  beforeEach(() => {
    jest.clearAllMocks();
    (bookClient.getChapterContent as jest.Mock).mockResolvedValue({ content: '<p>Initial content</p>' });
    (bookClient.saveChapterContent as jest.Mock).mockResolvedValue({});
  });

  it('renders the rich text editor with toolbar', async () => {
    await act(async () => {
      render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    });

    await waitFor(() => {
      expect(screen.getByTestId('editor-content')).toBeInTheDocument();
    });

    expect(screen.getByTitle('Bold')).toBeInTheDocument();
    expect(screen.getByTitle('Italic')).toBeInTheDocument();
    expect(screen.getByTitle('Underline')).toBeInTheDocument();
    expect(screen.getByTitle('Heading 1')).toBeInTheDocument();
    expect(screen.getByTitle('Bullet List')).toBeInTheDocument();
    expect(screen.getByTitle('Blockquote')).toBeInTheDocument();
  });

  it('shows character count in the footer', async () => {
    await act(async () => {
      render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    });

    await waitFor(() => {
      expect(screen.getByText('12 characters')).toBeInTheDocument();
    });
  });

  it('handles save button click', async () => {
    const user = userEvent.setup();

    await act(async () => {
      render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    });

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    const saveButton = screen.getByText('Save');

    await act(async () => {
      await user.click(saveButton);
    });

    await waitFor(() => {
      expect(bookClient.saveChapterContent).toHaveBeenCalledWith(
        bookId,
        chapterId,
        '<p>Test content</p>'
      );
    });
  });

  // Each toolbar button must run its own command. Asserting the command by name
  // catches a miswired button; the old assertion (a call count on the shared
  // run()) passed no matter which command each button invoked.
  it.each([
    ['Bold', 'toggleBold', undefined],
    ['Italic', 'toggleItalic', undefined],
    ['Underline', 'toggleUnderline', undefined],
    ['Heading 1', 'toggleHeading', { level: 1 }],
    ['Heading 2', 'toggleHeading', { level: 2 }],
    ['Bullet List', 'toggleBulletList', undefined],
    ['Blockquote', 'toggleBlockquote', undefined],
  ])('the %s button runs the %s command', async (title, command, args) => {
    const user = userEvent.setup();

    await act(async () => {
      render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    });

    await waitFor(() => {
      expect(screen.getByTitle(title)).toBeInTheDocument();
    });

    await act(async () => {
      await user.click(screen.getByTitle(title));
    });

    if (args === undefined) {
      expect(mockChain[command]).toHaveBeenCalledWith();
    } else {
      expect(mockChain[command]).toHaveBeenCalledWith(args);
    }
    expect(mockChain[command]).toHaveBeenCalledTimes(1);
    // The chain is focused first and executed at the end, or nothing happens.
    expect(mockChain.focus).toHaveBeenCalled();
    expect(mockRunFn).toHaveBeenCalled();
  });
});
