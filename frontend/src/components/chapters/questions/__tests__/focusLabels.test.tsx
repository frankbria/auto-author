import { render, screen, fireEvent } from '@testing-library/react';
import RegenerateQuestionsDialog from '../RegenerateQuestionsDialog';
import QuestionGenerator from '../QuestionGenerator';
import { FOCUS_OPTIONS } from '@/lib/questionFocus';

describe('focus labels (#1051)', () => {
  it('QuestionGenerator shows each non-fiction label with its description', () => {
    render(<QuestionGenerator bookId="b" chapterId="c" onGenerate={jest.fn()} isGenerating={false} error={null} />);
    fireEvent.click(screen.getByText(/Show Advanced Options/i));
    for (const o of FOCUS_OPTIONS) {
      const box = screen.getByRole('checkbox', { name: new RegExp(`^${o.label}`) });
      expect(box).toHaveAccessibleDescription(o.description);
    }
    expect(screen.queryByText(/character|plot|setting/i)).not.toBeInTheDocument();
  });

  it('RegenerateQuestionsDialog shows each label with its description', () => {
    render(
      <RegenerateQuestionsDialog isOpen onOpenChange={jest.fn()} onConfirm={jest.fn()} isRegenerating={false} />
    );
    for (const o of FOCUS_OPTIONS) {
      const box = screen.getByRole('checkbox', { name: new RegExp(`^${o.label}`) });
      expect(box).toHaveAccessibleDescription(o.description);
    }
    expect(screen.queryByText(/character|plot|setting/i)).not.toBeInTheDocument();
  });
});
