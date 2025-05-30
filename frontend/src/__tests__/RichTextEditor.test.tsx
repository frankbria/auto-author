// frontend/src/__tests__/RichTextEditor.test.tsx

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChapterEditor } from '../components/chapters/ChapterEditor';
import bookClient from '../lib/api/bookClient';

// Mock the book client
jest.mock('../lib/api/bookClient', () => ({
  getChapterContent: jest.fn(),
  saveChapterContent: jest.fn(),
}));

// Create mock chain to be used in the tests
const mockRunFn = jest.fn();
const mockChain = {
  focus: function() { return this; },
  toggleBold: function() { return this; },
  toggleItalic: function() { return this; },
  toggleUnderline: function() { return this; },
  toggleStrike: function() { return this; },
  toggleHeading: function() { return this; },
  toggleBulletList: function() { return this; },
  toggleOrderedList: function() { return this; },
  toggleBlockquote: function() { return this; },
  toggleCodeBlock: function() { return this; },
  undo: function() { return this; },
  redo: function() { return this; },
  setHorizontalRule: function() { return this; },
  run: mockRunFn,
};

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
  
  it('renders the rich text editor with toolbar', () => {
    render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    
    expect(screen.getByTestId('editor-content')).toBeInTheDocument();
    expect(screen.getByTitle('Bold')).toBeInTheDocument();
    expect(screen.getByTitle('Italic')).toBeInTheDocument();
    expect(screen.getByTitle('Underline')).toBeInTheDocument();
    expect(screen.getByTitle('Heading 1')).toBeInTheDocument();
    expect(screen.getByTitle('Bullet List')).toBeInTheDocument();
    expect(screen.getByTitle('Blockquote')).toBeInTheDocument();
  });
  
  it('shows character count in the footer', () => {
    render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    
    expect(screen.getByText('12 characters')).toBeInTheDocument();
  });
  
  it('handles save button click', async () => {
    render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    
    const saveButton = screen.getByText('Save');
    userEvent.click(saveButton);
    
    await waitFor(() => {
      expect(bookClient.saveChapterContent).toHaveBeenCalledWith(
        bookId, 
        chapterId, 
        '<p>Test content</p>'
      );
    });
  });
  
  it('toggles formatting when toolbar buttons are clicked', () => {
    render(<ChapterEditor bookId={bookId} chapterId={chapterId} />);
    
    const boldButton = screen.getByTitle('Bold');
    userEvent.click(boldButton);
    
    const italicButton = screen.getByTitle('Italic');
    userEvent.click(italicButton);
    
    const h1Button = screen.getByTitle('Heading 1');
    userEvent.click(h1Button);
    
    // We can't directly check the editor's state in this test,
    // but we can verify that the mock chain.run function was called
    // since it's attached to the end of every formatting command
    expect(mockRunFn).toHaveBeenCalledTimes(3);
  });
});
