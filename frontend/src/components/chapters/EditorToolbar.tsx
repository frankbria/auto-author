'use client';

import { memo } from 'react';
import { type Editor, useEditorState } from '@tiptap/react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { HugeiconsIcon } from '@hugeicons/react';
import {
  TextBoldIcon,
  TextItalicIcon,
  TextUnderlineIcon,
  Strikethrough,
  Heading01Icon,
  Heading02Icon,
  Heading03Icon,
  ListViewIcon,
  MenuSquareIcon,
  QuoteUpIcon,
  CodeIcon,
  Undo02Icon,
  Redo02Icon,
  MinusSignIcon
} from '@hugeicons/core-free-icons';

// Required types declaration to avoid TypeScript errors
declare module '@tiptap/react' {
  interface Commands<ReturnType> {
    toggleBold: () => ReturnType;
    toggleItalic: () => ReturnType;
    toggleUnderline: () => ReturnType;
    toggleStrike: () => ReturnType;
    toggleHeading: (attributes: { level: 1 | 2 | 3 | 4 | 5 | 6 }) => ReturnType;
    toggleBulletList: () => ReturnType;
    toggleOrderedList: () => ReturnType;
    toggleBlockquote: () => ReturnType;
    toggleCodeBlock: () => ReturnType;
    undo: () => ReturnType;
    redo: () => ReturnType;
    setHorizontalRule: () => ReturnType;
  }
}

interface EditorToolbarProps {
  editor: Editor | null;
}

/** Every toggle off — used when there is no editor yet (useEditorState returns null). */
const NO_ACTIVE_MARKS = {
  isBold: false,
  isItalic: false,
  isUnderline: false,
  isStrike: false,
  isH1: false,
  isH2: false,
  isH3: false,
  isBulletList: false,
  isOrderedList: false,
  isBlockquote: false,
  isCodeBlock: false,
  canUndo: false,
  canRedo: false,
} as const;

function EditorToolbarComponent({ editor }: EditorToolbarProps) {
  // `useEditor` re-renders its host on every ProseMirror transaction. Reading
  // `editor.isActive(...)` inline meant all fourteen buttons — and their icon
  // components — reconciled on every keystroke (#347).
  //
  // `useEditorState` subscribes to a selector instead: this component re-renders
  // only when one of these booleans actually flips (moving the caret into bold
  // text, say), not per character. The `memo` below stops the parent's own
  // per-keystroke re-render from cascading in, which is only sound because
  // `editor` is a stable instance for the editor's lifetime.
  //
  // The subscription is what makes `memo` safe here: with `memo` alone the
  // active states — and therefore `aria-pressed` — would silently go stale.
  const state = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      isBold: e?.isActive('bold') ?? false,
      isItalic: e?.isActive('italic') ?? false,
      isUnderline: e?.isActive('underline') ?? false,
      isStrike: e?.isActive('strike') ?? false,
      isH1: e?.isActive('heading', { level: 1 }) ?? false,
      isH2: e?.isActive('heading', { level: 2 }) ?? false,
      isH3: e?.isActive('heading', { level: 3 }) ?? false,
      isBulletList: e?.isActive('bulletList') ?? false,
      isOrderedList: e?.isActive('orderedList') ?? false,
      isBlockquote: e?.isActive('blockquote') ?? false,
      isCodeBlock: e?.isActive('codeBlock') ?? false,
      // Undo/redo availability is *also* a per-transaction read. Leaving it out
      // of the selector would freeze the disabled state at mount: typing makes
      // undo possible, but with nothing in the selector changing the memoized
      // component would never re-render, and the button would stay greyed out.
      canUndo: e?.can().chain().focus().undo().run() ?? false,
      canRedo: e?.can().chain().focus().redo().run() ?? false,
    }),
  }) ?? NO_ACTIVE_MARKS;

  if (!editor) {
    return null;
  }

  return (
    // role="toolbar" + aria-label groups these controls; each icon-only button needs
    // its own aria-label (title alone is an unreliable accessible name for screen readers).
    <div
      role="toolbar"
      aria-label="Text formatting"
      className="flex flex-wrap gap-1 items-center"
    >
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isBold ? 'bg-muted' : 'bg-transparent'
        )}
        title="Bold"
        aria-label="Bold"
        aria-pressed={state.isBold}
        type="button"
      >
        <HugeiconsIcon icon={TextBoldIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isItalic ? 'bg-muted' : 'bg-transparent'
        )}
        title="Italic"
        aria-label="Italic"
        aria-pressed={state.isItalic}
        type="button"
      >
        <HugeiconsIcon icon={TextItalicIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isUnderline ? 'bg-muted' : 'bg-transparent'
        )}
        title="Underline"
        aria-label="Underline"
        aria-pressed={state.isUnderline}
        type="button"
      >
        <HugeiconsIcon icon={TextUnderlineIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleStrike().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isStrike ? 'bg-muted' : 'bg-transparent'
        )}
        title="Strikethrough"
        aria-label="Strikethrough"
        aria-pressed={state.isStrike}
        type="button"
      >
        <HugeiconsIcon icon={Strikethrough} size={16} />
      </Button>

      <div className="w-px h-6 bg-border mx-1" />

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isH1 ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 1"
        aria-label="Heading 1"
        aria-pressed={state.isH1}
        type="button"
      >
        <HugeiconsIcon icon={Heading01Icon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isH2 ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 2"
        aria-label="Heading 2"
        aria-pressed={state.isH2}
        type="button"
      >
        <HugeiconsIcon icon={Heading02Icon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isH3 ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 3"
        aria-label="Heading 3"
        aria-pressed={state.isH3}
        type="button"
      >
        <HugeiconsIcon icon={Heading03Icon} size={16} />
      </Button>

      <div className="w-px h-6 bg-border mx-1" />

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isBulletList ? 'bg-muted' : 'bg-transparent'
        )}
        title="Bullet List"
        aria-label="Bullet List"
        aria-pressed={state.isBulletList}
        type="button"
      >
        <HugeiconsIcon icon={ListViewIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isOrderedList ? 'bg-muted' : 'bg-transparent'
        )}
        title="Ordered List"
        aria-label="Ordered List"
        aria-pressed={state.isOrderedList}
        type="button"
      >
        <HugeiconsIcon icon={MenuSquareIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isBlockquote ? 'bg-muted' : 'bg-transparent'
        )}
        title="Blockquote"
        aria-label="Blockquote"
        aria-pressed={state.isBlockquote}
        type="button"
      >
        <HugeiconsIcon icon={QuoteUpIcon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        className={cn(
          'h-11 w-11 p-0',
          state.isCodeBlock ? 'bg-muted' : 'bg-transparent'
        )}
        title="Code Block"
        aria-label="Code Block"
        aria-pressed={state.isCodeBlock}
        type="button"
      >
        <HugeiconsIcon icon={CodeIcon} size={16} />
      </Button>

      <div className="w-px h-6 bg-border mx-1" />

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!state.canUndo}
        className="h-11 w-11 p-0 bg-transparent"
        title="Undo"
        aria-label="Undo"
        type="button"
      >
        <HugeiconsIcon icon={Undo02Icon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!state.canRedo}
        className="h-11 w-11 p-0 bg-transparent"
        title="Redo"
        aria-label="Redo"
        type="button"
      >
        <HugeiconsIcon icon={Redo02Icon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        className="h-11 w-11 p-0 bg-transparent"
        title="Horizontal Rule"
        aria-label="Horizontal Rule"
        type="button"
      >
        <HugeiconsIcon icon={MinusSignIcon} size={16} />
      </Button>
    </div>
  );
}

export const EditorToolbar = memo(EditorToolbarComponent);
