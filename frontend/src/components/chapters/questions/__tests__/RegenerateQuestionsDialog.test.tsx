import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import RegenerateQuestionsDialog from '../RegenerateQuestionsDialog';
import { QuestionType } from '@/types/chapter-questions';

const baseProps = {
  isOpen: true,
  onOpenChange: jest.fn(),
  onConfirm: jest.fn(),
  isRegenerating: false,
};

describe('RegenerateQuestionsDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('confirms with no focus and preserve=true by default', () => {
    render(<RegenerateQuestionsDialog {...baseProps} />);
    fireEvent.click(screen.getByRole('button', { name: /^regenerate$/i }));
    expect(baseProps.onConfirm).toHaveBeenCalledWith({ focus: undefined }, true);
  });

  it('includes selected focus areas and preserve toggle state', () => {
    render(<RegenerateQuestionsDialog {...baseProps} />);
    fireEvent.click(screen.getByLabelText('Theme'));
    fireEvent.click(screen.getByRole('switch'));
    fireEvent.click(screen.getByRole('button', { name: /^regenerate$/i }));
    expect(baseProps.onConfirm).toHaveBeenCalledWith(
      { focus: [QuestionType.THEME] },
      false
    );
  });

  it('does not render content when closed', () => {
    render(<RegenerateQuestionsDialog {...baseProps} isOpen={false} />);
    expect(screen.queryByText('Regenerate all questions')).not.toBeInTheDocument();
  });
});
