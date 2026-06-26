/**
 * Tests for QuestionGenerator component.
 * Covers: rendering, handleGenerate, toggleQuestionType (add/remove),
 * setShowAdvancedOptions toggle, setDifficulty (radio), setQuestionCount (slider),
 * handleGenerate with focus types, error display, and button states.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import QuestionGenerator from '../QuestionGenerator';
import { QuestionDifficulty, QuestionType } from '@/types/chapter-questions';

// ---------------------------------------------------------------------------
// Mocks for complex Radix UI components
// ---------------------------------------------------------------------------

// Mock Slider to use a native input so we can fireEvent.change on it
jest.mock('@/components/ui/slider', () => ({
  Slider: ({ onValueChange, value, min, max, step, id }: any) => (
    <input
      type="range"
      id={id}
      data-testid="question-count-slider"
      defaultValue={value?.[0]}
      min={min}
      max={max}
      step={step}
      onChange={(e) => onValueChange?.([Number(e.target.value)])}
    />
  ),
}));

// Mock Tooltip to avoid portal rendering issues in jsdom
jest.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: any) => <>{children}</>,
  TooltipProvider: ({ children }: any) => <>{children}</>,
  TooltipTrigger: ({ children, asChild }: any) =>
    asChild ? children : <span>{children}</span>,
  TooltipContent: ({ children }: any) => <div role="tooltip">{children}</div>,
}));

// Mock Checkbox to render a native checkbox for simpler interaction
jest.mock('@/components/ui/checkbox', () => {
  const React = require('react');
  const Checkbox = React.forwardRef(
    ({ onCheckedChange, checked, id, className, ...props }: any, ref: any) => (
      <input
        ref={ref}
        type="checkbox"
        id={id}
        checked={checked ?? false}
        onChange={(e) => onCheckedChange?.(e.target.checked)}
        {...props}
      />
    )
  );
  Checkbox.displayName = 'Checkbox';
  return { Checkbox };
});

// Mock RadioGroup to use native radio inputs for simpler onValueChange testing
jest.mock('@/components/ui/radio-group', () => {
  const React = require('react');
  const RadioGroupContext = React.createContext<any>(null);

  const RadioGroup = ({ onValueChange, children, value }: any) => (
    <RadioGroupContext.Provider value={{ onValueChange }}>
      <div role="radiogroup">{children}</div>
    </RadioGroupContext.Provider>
  );

  const RadioGroupItem = ({ value, id }: any) => {
    const ctx = React.useContext(RadioGroupContext);
    return (
      <input
        type="radio"
        value={value}
        id={id}
        data-testid={`radio-${value || 'any'}`}
        // Use onClick so fireEvent.click triggers onValueChange
        onClick={() => ctx?.onValueChange?.(value)}
        onChange={() => {}} // silence React controlled-input warning
      />
    );
  };

  return { RadioGroup, RadioGroupItem };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const defaultProps = {
  bookId: 'book-1',
  chapterId: 'ch-1',
  onGenerate: jest.fn().mockResolvedValue(undefined),
  isGenerating: false,
  error: null,
};

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe('QuestionGenerator - rendering', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders the card description', () => {
    render(<QuestionGenerator {...defaultProps} />);
    // CardDescription is unique; avoids ambiguity with the Generate button text
    expect(screen.getByText(/Generate tailored questions/i)).toBeInTheDocument();
  });

  it('renders the Generate Interview Questions button', () => {
    render(<QuestionGenerator {...defaultProps} />);
    expect(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    ).toBeInTheDocument();
  });

  it('renders the question count label', () => {
    render(<QuestionGenerator {...defaultProps} />);
    expect(screen.getByText(/Number of questions:/)).toBeInTheDocument();
  });

  it('renders the slider', () => {
    render(<QuestionGenerator {...defaultProps} />);
    expect(screen.getByTestId('question-count-slider')).toBeInTheDocument();
  });

  it('does not render advanced options by default', () => {
    render(<QuestionGenerator {...defaultProps} />);
    expect(screen.queryByText('Question Difficulty')).not.toBeInTheDocument();
  });

  it('renders error message when error prop is set', () => {
    render(<QuestionGenerator {...defaultProps} error="Failed to generate" />);
    expect(screen.getByText('Failed to generate')).toBeInTheDocument();
  });

  it('renders "Retry" button text when error is present', () => {
    render(<QuestionGenerator {...defaultProps} error="An error occurred" />);
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
  });

  it('renders loading state when isGenerating is true', () => {
    render(<QuestionGenerator {...defaultProps} isGenerating={true} />);
    expect(screen.getByText('Generating Questions...')).toBeInTheDocument();
  });

  it('generate button is disabled when isGenerating', () => {
    render(<QuestionGenerator {...defaultProps} isGenerating={true} />);
    expect(
      screen.getByRole('button', { name: /Generating Questions/i })
    ).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// handleGenerate
// ---------------------------------------------------------------------------

describe('QuestionGenerator - handleGenerate', () => {
  beforeEach(() => jest.clearAllMocks());

  it('calls onGenerate with default count=10 when Generate button clicked', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledTimes(1);
    });
    // Default count is 10, no difficulty, no focus
    expect(onGenerate).toHaveBeenCalledWith(10, undefined, undefined);
  });

  it('passes selected focus types to onGenerate when some are checked', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    // Show advanced options to reveal checkboxes
    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    // Check the CHARACTER checkbox
    const characterCheckbox = screen.getByRole('checkbox', { name: /Character/i });
    fireEvent.click(characterCheckbox);

    // Generate
    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(
        10,
        undefined,
        [QuestionType.CHARACTER]
      );
    });
  });

  it('passes no focus types to onGenerate when none are checked (undefined)', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, undefined, undefined);
    });
  });
});

// ---------------------------------------------------------------------------
// toggleQuestionType
// ---------------------------------------------------------------------------

describe('QuestionGenerator - toggleQuestionType', () => {
  beforeEach(() => jest.clearAllMocks());

  it('adds a question type to focusTypes when checkbox is checked', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    // Reveal advanced options
    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    const plotCheckbox = screen.getByRole('checkbox', { name: /Plot/i });
    fireEvent.click(plotCheckbox);

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, undefined, [QuestionType.PLOT]);
    });
  });

  it('removes a question type from focusTypes when checkbox is unchecked', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    const plotCheckbox = screen.getByRole('checkbox', { name: /Plot/i });

    // Check then uncheck
    fireEvent.click(plotCheckbox); // adds PLOT
    fireEvent.click(plotCheckbox); // removes PLOT

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    // focus types is empty → undefined is passed
    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, undefined, undefined);
    });
  });

  it('can select multiple question types simultaneously', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    fireEvent.click(screen.getByRole('checkbox', { name: /Character/i }));
    fireEvent.click(screen.getByRole('checkbox', { name: /Theme/i }));

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      const [, , focus] = onGenerate.mock.calls[0];
      expect(focus).toContain(QuestionType.CHARACTER);
      expect(focus).toContain(QuestionType.THEME);
    });
  });
});

// ---------------------------------------------------------------------------
// setShowAdvancedOptions
// ---------------------------------------------------------------------------

describe('QuestionGenerator - advanced options toggle', () => {
  beforeEach(() => jest.clearAllMocks());

  it('clicking "Show Advanced Options" reveals difficulty and focus sections', () => {
    render(<QuestionGenerator {...defaultProps} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    expect(screen.getByText('Question Difficulty')).toBeInTheDocument();
    expect(screen.getByText('Question Focus (optional)')).toBeInTheDocument();
  });

  it('clicking "Hide Advanced Options" hides the advanced section', () => {
    render(<QuestionGenerator {...defaultProps} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));
    expect(screen.getByText('Question Difficulty')).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Hide Advanced Options/i));
    expect(screen.queryByText('Question Difficulty')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// setDifficulty via RadioGroup
// ---------------------------------------------------------------------------

describe('QuestionGenerator - setDifficulty', () => {
  beforeEach(() => jest.clearAllMocks());

  it('selecting Easy difficulty passes it to onGenerate', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    // fireEvent.click triggers the onClick → onValueChange('easy')
    fireEvent.click(screen.getByTestId('radio-easy'));

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, QuestionDifficulty.EASY, undefined);
    });
  });

  it('selecting Medium difficulty passes it to onGenerate', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    fireEvent.click(screen.getByTestId('radio-medium'));

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, QuestionDifficulty.MEDIUM, undefined);
    });
  });

  it('selecting Hard difficulty passes it to onGenerate', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    fireEvent.click(screen.getByText(/Show Advanced Options/i));

    fireEvent.click(screen.getByTestId('radio-hard'));

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(10, QuestionDifficulty.HARD, undefined);
    });
  });
});

// ---------------------------------------------------------------------------
// setQuestionCount via Slider
// ---------------------------------------------------------------------------

describe('QuestionGenerator - setQuestionCount', () => {
  beforeEach(() => jest.clearAllMocks());

  it('changing the slider updates the question count label', () => {
    render(<QuestionGenerator {...defaultProps} />);

    const slider = screen.getByTestId('question-count-slider');
    fireEvent.change(slider, { target: { value: '15' } });

    expect(screen.getByText('Number of questions: 15')).toBeInTheDocument();
  });

  it('passes updated count to onGenerate after slider change', async () => {
    const onGenerate = jest.fn().mockResolvedValue(undefined);
    render(<QuestionGenerator {...defaultProps} onGenerate={onGenerate} />);

    const slider = screen.getByTestId('question-count-slider');
    fireEvent.change(slider, { target: { value: '5' } });

    fireEvent.click(
      screen.getByRole('button', { name: /Generate Interview Questions/i })
    );

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(5, undefined, undefined);
    });
  });
});
