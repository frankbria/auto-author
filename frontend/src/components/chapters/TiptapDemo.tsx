'use client';

import { useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import { Button } from '@/components/ui/button';
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
  ListSettingIcon,
  Note01Icon,
  CodeIcon,
  Undo02Icon,
  Redo02Icon,
  MinusSignIcon
} from '@hugeicons/core-free-icons';
import { cn } from '@/lib/utils';
import './editor.css';

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

export function TiptapDemo() {
  const [content, setContent] = useState<string>('<h2>Welcome to the Tiptap Editor Demo</h2><p>This is a rich text editor with a modest toolbar for formatting.</p><p>Try out the various formatting options:</p><ul><li>Use the <strong>Bold</strong>, <em>Italic</em>, and <u>Underline</u> buttons</li><li>Create headings and lists</li><li>Insert blockquotes and code blocks</li></ul><p>The editor has been integrated to replace the plain textarea component, while maintaining all the existing functionality like auto-save.</p>');
  
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Placeholder.configure({
        placeholder: 'Start typing here...',
      }),
      CharacterCount,
    ],
    content,
    onUpdate: ({ editor }) => {
      setContent(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'focus:outline-none text-black',
      },
    },
    // Set this to false to avoid SSR hydration issues
    immediatelyRender: false,
  });

  return (
    <div className="w-full max-w-4xl mx-auto my-8 border border-gray-300 rounded-md shadow-sm overflow-hidden">
      <div className="bg-white p-6">
        <h1 className="text-2xl font-bold mb-6 text-center">Tiptap Editor Integration Demo</h1>
        
        <div className="border border-gray-200 rounded-md overflow-hidden">
          {/* Editor Toolbar */}
          <div className="border-b border-border p-1 bg-muted/30 flex flex-wrap gap-1 items-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleBold().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('bold') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Bold"
              type="button"
            >
              <HugeiconsIcon icon={TextBoldIcon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('italic') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Italic"
              type="button"
            >
              <HugeiconsIcon icon={TextItalicIcon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleUnderline().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('underline') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Underline"
              type="button"
            >
              <HugeiconsIcon icon={TextUnderlineIcon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleStrike().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('strike') ? 'bg-muted' : 'bg-transparent'
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
              onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('heading', { level: 1 }) ? 'bg-muted' : 'bg-transparent'
              )}
              title="Heading 1"
              type="button"
            >
              <HugeiconsIcon icon={Heading01Icon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('heading', { level: 2 }) ? 'bg-muted' : 'bg-transparent'
              )}
              title="Heading 2"
              type="button"
            >
              <HugeiconsIcon icon={Heading02Icon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('heading', { level: 3 }) ? 'bg-muted' : 'bg-transparent'
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
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('bulletList') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Bullet List"
              type="button"
            >
              <HugeiconsIcon icon={ListViewIcon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('orderedList') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Ordered List"
              type="button"
            >
              <HugeiconsIcon icon={ListSettingIcon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleBlockquote().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('blockquote') ? 'bg-muted' : 'bg-transparent'
              )}
              title="Blockquote"
              type="button"
            >
              <HugeiconsIcon icon={Note01Icon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().toggleCodeBlock().run()}
              className={cn(
                'h-8 w-8 p-0',
                editor?.isActive('codeBlock') ? 'bg-muted' : 'bg-transparent'
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
              onClick={() => editor?.chain().focus().undo().run()}
              disabled={!editor?.can().chain().focus().undo().run()}
              className="h-8 w-8 p-0 bg-transparent"
              title="Undo"
              type="button"
            >
              <HugeiconsIcon icon={Undo02Icon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().redo().run()}
              disabled={!editor?.can().chain().focus().redo().run()}
              className="h-8 w-8 p-0 bg-transparent"
              title="Redo"
              type="button"
            >
              <HugeiconsIcon icon={Redo02Icon} size={16} />
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => editor?.chain().focus().setHorizontalRule().run()}
              className="h-8 w-8 p-0 bg-transparent"
              title="Horizontal Rule"
              type="button"
            >
              <HugeiconsIcon icon={MinusSignIcon} size={16} />
            </Button>
          </div>
          
          {/* Editor Content */}
          <div className="p-4 bg-white">
            <EditorContent 
              editor={editor} 
              className="w-full min-h-[400px] tiptap-editor text-black" 
            />
          </div>
          
          {/* Editor Footer */}
          <div className="border-t border-border p-4 flex justify-between items-center bg-muted/20">
            <div className="flex items-center gap-4">
              <span className="text-sm text-foreground">
                {editor?.storage.characterCount.characters() ?? 0} characters
              </span>
            </div>
            <Button
              onClick={() => alert('Content saved!\n\n' + content)}
            >
              Save
            </Button>
          </div>
        </div>
        
        <div className="mt-8 border-t border-gray-200 pt-4">
          <h2 className="text-xl font-semibold mb-3">HTML Output</h2>
          <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto text-sm">
            {content}
          </pre>
        </div>
      </div>
    </div>
  );
}
