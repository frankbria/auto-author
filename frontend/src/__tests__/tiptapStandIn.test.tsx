/**
 * The TipTap stand-in (jest.setup.ts) must show what the editor holds (#1045).
 */
import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { useEditor, EditorContent } from '@tiptap/react';

const held: { editor?: ReturnType<typeof useEditor> } = {};
function Harness({ content = '<p>first</p>', onUpdate }: { content?: string; onUpdate?: () => void }) {
  const editor = useEditor({ content, onUpdate });
  React.useEffect(() => {
    held.editor = editor;
  }, [editor]);
  return <EditorContent editor={editor} />;
}

describe('TipTap stand-in textbox', () => {
  it('shows text set with setContent after the first render', () => {
    render(<Harness />);
    expect(screen.getByRole('textbox')).toHaveValue('<p>first</p>');

    act(() => {
      held.editor!.commands.setContent('<p>second</p>');
    });

    expect(screen.getByRole('textbox')).toHaveValue('<p>second</p>');
  });

  it('shows it when emitUpdate is false, and emits nothing', () => {
    const onUpdate = jest.fn();
    render(<Harness onUpdate={onUpdate} />);

    act(() => {
      held.editor!.commands.setContent('<p>quiet</p>', { emitUpdate: false });
    });

    expect(screen.getByRole('textbox')).toHaveValue('<p>quiet</p>');
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it('does not reset the content when the content option changes', () => {
    const view = render(<Harness content="<p>a</p>" />);
    act(() => {
      held.editor!.commands.setContent('<p>typed</p>');
    });

    view.rerender(<Harness content="<p>b</p>" />);

    expect(screen.getByRole('textbox')).toHaveValue('<p>typed</p>');
  });
});
