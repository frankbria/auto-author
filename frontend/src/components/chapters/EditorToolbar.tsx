'use client';

import { type Editor } from '@tiptap/react';
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

export function EditorToolbar({ editor }: EditorToolbarProps) {
  if (!editor) {
    return null;
  }

  return (
    <div className="border-b border-border p-1 bg-muted/30 flex flex-wrap gap-1 items-center">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={cn(
          'h-11 w-11 p-0',
          editor.isActive('bold') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Bold"
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
          editor.isActive('italic') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Italic"
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
          editor.isActive('underline') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Underline"
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
          editor.isActive('strike') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Strikethrough"
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
          editor.isActive('heading', { level: 1 }) ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 1"
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
          editor.isActive('heading', { level: 2 }) ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 2"
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
          editor.isActive('heading', { level: 3 }) ? 'bg-muted' : 'bg-transparent'
        )}
        title="Heading 3"
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
          editor.isActive('bulletList') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Bullet List"
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
          editor.isActive('orderedList') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Ordered List"
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
          editor.isActive('blockquote') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Blockquote"
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
          editor.isActive('codeBlock') ? 'bg-muted' : 'bg-transparent'
        )}
        title="Code Block"
        type="button"
      >
        <HugeiconsIcon icon={CodeIcon} size={16} />
      </Button>

      <div className="w-px h-6 bg-border mx-1" />

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().chain().focus().undo().run()}
        className="h-11 w-11 p-0 bg-transparent"
        title="Undo"
        type="button"
      >
        <HugeiconsIcon icon={Undo02Icon} size={16} />
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().chain().focus().redo().run()}
        className="h-11 w-11 p-0 bg-transparent"
        title="Redo"
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
        type="button"
      >
        <HugeiconsIcon icon={MinusSignIcon} size={16} />
      </Button>
    </div>
  );
}
