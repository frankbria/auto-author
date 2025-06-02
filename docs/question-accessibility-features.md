# Question Accessibility Features and Keyboard Shortcuts

## Overview
The question system is designed to be fully accessible to users with disabilities, following WCAG 2.1 AA guidelines. This document covers accessibility features, keyboard navigation, screen reader support, and customization options.

## Accessibility Features

### Screen Reader Support

#### ARIA Labels and Descriptions
All question components include comprehensive ARIA attributes for screen readers:

```html
<!-- Question Container -->
<div 
  role="region" 
  aria-labelledby="question-heading"
  aria-describedby="question-help"
  class="question-container"
>
  <h3 id="question-heading" aria-level="3">
    How does the protagonist's motivation change in this chapter?
  </h3>
  
  <div id="question-help" class="question-help">
    Consider the character's goals at the beginning and end of the chapter
  </div>
  
  <textarea
    aria-labelledby="question-heading"
    aria-describedby="question-help response-status"
    aria-required="false"
    placeholder="Enter your response..."
    class="response-input"
  >
  </textarea>
  
  <div id="response-status" aria-live="polite" aria-atomic="true">
    Auto-saved 30 seconds ago
  </div>
</div>
```

#### Question Metadata Announcements
Screen readers announce important question information:

- Question type (character, plot, setting, theme, research)
- Difficulty level (easy, medium, hard)
- Progress indicators (question 3 of 10)
- Response status (draft, completed)
- Save status (saved, saving, error)

#### Live Regions for Dynamic Updates
```html
<!-- Progress Updates -->
<div aria-live="polite" aria-label="Question progress">
  Completed 7 of 12 questions (58%)
</div>

<!-- Save Status -->
<div aria-live="assertive" aria-label="Save status">
  Response saved successfully
</div>

<!-- Error Messages -->
<div role="alert" aria-live="assertive">
  Failed to save response. Please try again.
</div>
```

### Keyboard Navigation

#### Tab Order and Focus Management
The question interface follows logical tab order:

1. **Question Navigation** (Previous/Next buttons)
2. **Question Text** (focusable for screen readers)
3. **Help Text Toggle** (if available)
4. **Response Textarea**
5. **Action Buttons** (Save, Mark Complete, Rate)
6. **Question Type Filter** (if visible)

#### Focus Indicators
Clear visual focus indicators for all interactive elements:

```css
/* High contrast focus indicators */
.question-container button:focus,
.question-container textarea:focus,
.question-container select:focus {
  outline: 3px solid #4A90E2;
  outline-offset: 2px;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.3);
}

/* Focus within containers */
.question-container:focus-within {
  border: 2px solid #4A90E2;
  border-radius: 8px;
}
```

### Visual Accessibility

#### High Contrast Mode Support
```css
/* High contrast mode styles */
@media (prefers-contrast: high) {
  .question-container {
    border: 2px solid ButtonText;
    background: ButtonFace;
    color: ButtonText;
  }
  
  .question-text {
    font-weight: 700;
    color: WindowText;
  }
  
  .response-input {
    border: 2px solid WindowText;
    background: Window;
    color: WindowText;
  }
}
```

#### Reduced Motion Support
```css
/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .question-transition,
  .progress-animation,
  .save-indicator {
    animation: none;
    transition: none;
  }
  
  .question-container {
    transform: none !important;
  }
}
```

#### Color and Typography
- Minimum 4.5:1 color contrast ratio for all text
- Scalable fonts that work with browser zoom up to 200%
- Information not conveyed by color alone
- Configurable font sizes and spacing

## Keyboard Shortcuts

### Global Question Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Tab` | Navigate to next element | All |
| `Shift + Tab` | Navigate to previous element | All |
| `Enter` | Activate focused button/link | Buttons, links |
| `Space` | Activate focused button | Buttons |
| `Esc` | Close modals/cancel actions | Modal dialogs |

### Question Navigation Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl/Cmd + →` | Next question | Question list |
| `Ctrl/Cmd + ←` | Previous question | Question list |
| `Ctrl/Cmd + Home` | First question | Question list |
| `Ctrl/Cmd + End` | Last question | Question list |
| `Ctrl/Cmd + G` | Go to specific question | Question list |
| `F` | Filter questions | Question list |

### Response Editing Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl/Cmd + S` | Save response | Response textarea |
| `Ctrl/Cmd + Enter` | Mark response complete | Response textarea |
| `Ctrl/Cmd + Shift + Enter` | Save and next question | Response textarea |
| `Ctrl/Cmd + Z` | Undo | Response textarea |
| `Ctrl/Cmd + Y` | Redo | Response textarea |
| `Ctrl/Cmd + A` | Select all text | Response textarea |
| `F11` | Toggle fullscreen editor | Response textarea |

### Question Management Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl/Cmd + N` | Generate new questions | Question generator |
| `Ctrl/Cmd + R` | Regenerate questions | Question generator |
| `Ctrl/Cmd + D` | Toggle question difficulty | Question filters |
| `Ctrl/Cmd + T` | Toggle question type filter | Question filters |
| `1-5` | Rate question (when rating mode active) | Rating interface |

### Screen Reader Specific Shortcuts

| Shortcut | Action | Screen Reader |
|----------|--------|---------------|
| `H` | Navigate by headings | NVDA, JAWS |
| `R` | Navigate by regions | NVDA, JAWS |
| `B` | Navigate by buttons | NVDA, JAWS |
| `E` | Navigate by edit fields | NVDA, JAWS |
| `Ctrl + Home` | Go to top of page | All |

## Implementation Details

### JavaScript Keyboard Handler
```typescript
// frontend/src/hooks/useKeyboardShortcuts.ts
import { useEffect, useCallback } from 'react';

interface ShortcutHandlers {
  onSave?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  onComplete?: () => void;
  onToggleFullscreen?: () => void;
}

export const useKeyboardShortcuts = (handlers: ShortcutHandlers) => {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const { key, ctrlKey, metaKey, shiftKey } = event;
    const isModifier = ctrlKey || metaKey;

    // Prevent shortcuts when typing in input fields (except specific ones)
    const target = event.target as HTMLElement;
    const isTextInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
    
    if (isTextInput && !isModifier) return;

    switch (true) {
      case isModifier && key === 's':
        event.preventDefault();
        handlers.onSave?.();
        break;
        
      case isModifier && key === 'Enter':
        event.preventDefault();
        if (shiftKey) {
          handlers.onNext?.();
        } else {
          handlers.onComplete?.();
        }
        break;
        
      case isModifier && key === 'ArrowRight':
        event.preventDefault();
        handlers.onNext?.();
        break;
        
      case isModifier && key === 'ArrowLeft':
        event.preventDefault();
        handlers.onPrevious?.();
        break;
        
      case key === 'F11':
        event.preventDefault();
        handlers.onToggleFullscreen?.();
        break;
    }
  }, [handlers]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};
```

### Focus Management Component
```typescript
// frontend/src/components/accessibility/FocusManager.tsx
import React, { useRef, useEffect } from 'react';

interface FocusManagerProps {
  children: React.ReactNode;
  focusOnMount?: boolean;
  restoreFocus?: boolean;
  trapFocus?: boolean;
}

export const FocusManager: React.FC<FocusManagerProps> = ({
  children,
  focusOnMount = false,
  restoreFocus = false,
  trapFocus = false
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<Element | null>(null);

  useEffect(() => {
    if (restoreFocus) {
      previousFocusRef.current = document.activeElement;
    }

    if (focusOnMount && containerRef.current) {
      const firstFocusable = containerRef.current.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      ) as HTMLElement;
      
      firstFocusable?.focus();
    }

    return () => {
      if (restoreFocus && previousFocusRef.current) {
        (previousFocusRef.current as HTMLElement).focus();
      }
    };
  }, [focusOnMount, restoreFocus]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!trapFocus || event.key !== 'Tab') return;

    const focusableElements = containerRef.current?.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
    );

    if (!focusableElements || focusableElements.length === 0) return;

    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  };

  return (
    <div ref={containerRef} onKeyDown={handleKeyDown}>
      {children}
    </div>
  );
};
```

### Accessible Question Component
```typescript
// frontend/src/components/questions/AccessibleQuestion.tsx
import React, { useState, useRef } from 'react';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { FocusManager } from '@/components/accessibility/FocusManager';

interface AccessibleQuestionProps {
  question: Question;
  questionNumber: number;
  totalQuestions: number;
  onSave: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onComplete: () => void;
}

export const AccessibleQuestion: React.FC<AccessibleQuestionProps> = ({
  question,
  questionNumber,
  totalQuestions,
  onSave,
  onNext,
  onPrevious,
  onComplete
}) => {
  const [responseText, setResponseText] = useState('');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error' | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useKeyboardShortcuts({
    onSave: () => {
      handleSave();
      announceToScreenReader('Response saved');
    },
    onNext,
    onPrevious,
    onComplete: () => {
      handleComplete();
      announceToScreenReader('Response marked as complete');
    },
    onToggleFullscreen: () => {
      toggleFullscreen();
    }
  });

  const announceToScreenReader = (message: string) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    setTimeout(() => document.body.removeChild(announcement), 1000);
  };

  const handleSave = async () => {
    setSaveStatus('saving');
    try {
      await onSave();
      setSaveStatus('saved');
    } catch (error) {
      setSaveStatus('error');
      announceToScreenReader('Failed to save response. Please try again.');
    }
  };

  const handleComplete = async () => {
    await handleSave();
    onComplete();
  };

  const toggleFullscreen = () => {
    if (textareaRef.current) {
      textareaRef.current.classList.toggle('fullscreen-editor');
      announceToScreenReader(
        textareaRef.current.classList.contains('fullscreen-editor') 
          ? 'Fullscreen editor enabled' 
          : 'Fullscreen editor disabled'
      );
    }
  };

  const progressText = `Question ${questionNumber} of ${totalQuestions}`;
  const questionId = `question-${question.id}`;
  const helpId = `help-${question.id}`;
  const statusId = `status-${question.id}`;

  return (
    <FocusManager focusOnMount={true}>
      <div 
        role="region" 
        aria-labelledby={questionId}
        aria-describedby={`${helpId} ${statusId}`}
        className="question-container"
      >
        {/* Screen reader progress announcement */}
        <div className="sr-only" aria-live="polite">
          {progressText}
        </div>

        {/* Question header */}
        <div className="question-header">
          <h3 id={questionId} className="question-text" tabIndex={0}>
            {question.question_text}
          </h3>
          
          <div className="question-meta" role="group" aria-label="Question details">
            <span className="question-type" aria-label={`Question type: ${question.question_type}`}>
              {question.question_type}
            </span>
            <span className="question-difficulty" aria-label={`Difficulty: ${question.difficulty}`}>
              {question.difficulty}
            </span>
            <span className="question-progress" aria-label={progressText}>
              {questionNumber}/{totalQuestions}
            </span>
          </div>
        </div>

        {/* Help text */}
        {question.metadata.help_text && (
          <div id={helpId} className="question-help">
            <p>{question.metadata.help_text}</p>
          </div>
        )}

        {/* Response area */}
        <div className="response-area">
          <label htmlFor={`response-${question.id}`} className="sr-only">
            Your response to: {question.question_text}
          </label>
          <textarea
            ref={textareaRef}
            id={`response-${question.id}`}
            value={responseText}
            onChange={(e) => setResponseText(e.target.value)}
            aria-describedby={`${helpId} ${statusId}`}
            aria-label={`Response for question: ${question.question_text}`}
            placeholder="Enter your response... (Press Ctrl+S to save, Ctrl+Enter to mark complete)"
            className="response-input"
            rows={6}
          />
        </div>

        {/* Status and actions */}
        <div className="question-actions">
          <div id={statusId} aria-live="polite" aria-atomic="true" className="save-status">
            {saveStatus === 'saving' && 'Saving...'}
            {saveStatus === 'saved' && 'Saved'}
            {saveStatus === 'error' && 'Save failed'}
          </div>

          <div className="action-buttons" role="group" aria-label="Question actions">
            <button 
              onClick={onPrevious}
              disabled={questionNumber === 1}
              aria-label="Previous question"
              title="Previous question (Ctrl+Left Arrow)"
            >
              Previous
            </button>
            
            <button 
              onClick={handleSave}
              aria-label="Save response"
              title="Save response (Ctrl+S)"
            >
              Save
            </button>
            
            <button 
              onClick={handleComplete}
              aria-label="Mark response as complete"
              title="Mark complete (Ctrl+Enter)"
            >
              Complete
            </button>
            
            <button 
              onClick={onNext}
              disabled={questionNumber === totalQuestions}
              aria-label="Next question"
              title="Next question (Ctrl+Right Arrow)"
            >
              Next
            </button>
          </div>
        </div>

        {/* Keyboard shortcuts help */}
        <details className="keyboard-shortcuts">
          <summary>Keyboard shortcuts</summary>
          <ul>
            <li><kbd>Ctrl+S</kbd> - Save response</li>
            <li><kbd>Ctrl+Enter</kbd> - Mark complete</li>
            <li><kbd>Ctrl+→</kbd> - Next question</li>
            <li><kbd>Ctrl+←</kbd> - Previous question</li>
            <li><kbd>F11</kbd> - Toggle fullscreen editor</li>
          </ul>
        </details>
      </div>
    </FocusManager>
  );
};
```

## Screen Reader Testing

### Testing Checklist

#### Structure and Navigation
- [ ] Headings are properly nested (H1 → H2 → H3)
- [ ] Landmarks and regions are correctly identified
- [ ] Tab order follows logical sequence
- [ ] Focus indicators are visible and clear

#### Content Accessibility
- [ ] All images have appropriate alt text
- [ ] Form labels are associated with inputs
- [ ] Error messages are announced
- [ ] Status updates are communicated

#### Interactive Elements
- [ ] Buttons have descriptive labels
- [ ] Links indicate their purpose
- [ ] Form validation is accessible
- [ ] Modal dialogs trap focus correctly

### Screen Reader Commands Reference

#### NVDA (Windows)
- `NVDA + T` - Read title
- `H` - Next heading
- `R` - Next region/landmark
- `B` - Next button
- `E` - Next edit field
- `NVDA + Space` - Review mode

#### JAWS (Windows)
- `INSERT + T` - Read title
- `H` - Next heading
- `R` - Next region
- `B` - Next button
- `E` - Next edit field
- `INSERT + Z` - Virtual cursor on/off

#### VoiceOver (macOS)
- `VO + F1` - Open help
- `VO + U` - Web rotor
- `VO + Command + H` - Next heading
- `VO + Command + L` - Next link
- `VO + Command + B` - Next button

## Customization Options

### User Preferences
```typescript
// frontend/src/store/accessibilityPreferences.ts
interface AccessibilityPreferences {
  reducedMotion: boolean;
  highContrast: boolean;
  fontSize: 'small' | 'medium' | 'large' | 'xl';
  focusIndicatorStyle: 'default' | 'high-contrast' | 'thick';
  screenReaderOptimized: boolean;
  keyboardShortcutsEnabled: boolean;
  autoSaveEnabled: boolean;
  autoSaveInterval: number; // seconds
}

export const useAccessibilityPreferences = () => {
  const [preferences, setPreferences] = useState<AccessibilityPreferences>(() => {
    // Load from localStorage or use defaults
    const saved = localStorage.getItem('accessibility-preferences');
    return saved ? JSON.parse(saved) : defaultPreferences;
  });

  const updatePreference = <K extends keyof AccessibilityPreferences>(
    key: K,
    value: AccessibilityPreferences[K]
  ) => {
    const newPreferences = { ...preferences, [key]: value };
    setPreferences(newPreferences);
    localStorage.setItem('accessibility-preferences', JSON.stringify(newPreferences));
  };

  return { preferences, updatePreference };
};
```

### Settings Panel
```typescript
// frontend/src/components/accessibility/AccessibilitySettings.tsx
export const AccessibilitySettings: React.FC = () => {
  const { preferences, updatePreference } = useAccessibilityPreferences();

  return (
    <div className="accessibility-settings">
      <h2>Accessibility Settings</h2>
      
      <fieldset>
        <legend>Visual Preferences</legend>
        
        <label>
          <input
            type="checkbox"
            checked={preferences.highContrast}
            onChange={(e) => updatePreference('highContrast', e.target.checked)}
          />
          High contrast mode
        </label>
        
        <label>
          Font size:
          <select
            value={preferences.fontSize}
            onChange={(e) => updatePreference('fontSize', e.target.value as any)}
          >
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
            <option value="xl">Extra Large</option>
          </select>
        </label>
      </fieldset>
      
      <fieldset>
        <legend>Keyboard and Navigation</legend>
        
        <label>
          <input
            type="checkbox"
            checked={preferences.keyboardShortcutsEnabled}
            onChange={(e) => updatePreference('keyboardShortcutsEnabled', e.target.checked)}
          />
          Enable keyboard shortcuts
        </label>
        
        <label>
          <input
            type="checkbox"
            checked={preferences.reducedMotion}
            onChange={(e) => updatePreference('reducedMotion', e.target.checked)}
          />
          Reduce motion and animations
        </label>
      </fieldset>
      
      <fieldset>
        <legend>Auto-save Settings</legend>
        
        <label>
          <input
            type="checkbox"
            checked={preferences.autoSaveEnabled}
            onChange={(e) => updatePreference('autoSaveEnabled', e.target.checked)}
          />
          Enable auto-save
        </label>
        
        <label>
          Auto-save interval:
          <input
            type="range"
            min="10"
            max="300"
            step="10"
            value={preferences.autoSaveInterval}
            onChange={(e) => updatePreference('autoSaveInterval', parseInt(e.target.value))}
            aria-describedby="autosave-description"
          />
          <span id="autosave-description">{preferences.autoSaveInterval} seconds</span>
        </label>
      </fieldset>
    </div>
  );
};
```

## Testing and Validation

### Automated Testing
```typescript
// frontend/src/__tests__/accessibility/QuestionAccessibility.test.tsx
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { AccessibleQuestion } from '@/components/questions/AccessibleQuestion';

expect.extend(toHaveNoViolations);

describe('Question Accessibility', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(
      <AccessibleQuestion
        question={mockQuestion}
        questionNumber={1}
        totalQuestions={10}
        onSave={jest.fn()}
        onNext={jest.fn()}
        onPrevious={jest.fn()}
        onComplete={jest.fn()}
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper heading structure', () => {
    render(<AccessibleQuestion {...props} />);
    
    const heading = screen.getByRole('heading', { level: 3 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveAttribute('id');
  });

  it('should associate labels with form controls', () => {
    render(<AccessibleQuestion {...props} />);
    
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('aria-labelledby');
    expect(textarea).toHaveAttribute('aria-describedby');
  });
});
```

### Manual Testing Checklist

#### Keyboard Navigation
- [ ] All interactive elements are reachable via keyboard
- [ ] Tab order is logical and intuitive
- [ ] Focus indicators are clearly visible
- [ ] No keyboard traps exist
- [ ] Shortcuts work as documented

#### Screen Reader Compatibility
- [ ] Content is read in logical order
- [ ] Headings and landmarks are announced
- [ ] Form labels and descriptions are read
- [ ] Status changes are announced
- [ ] Error messages are accessible

#### Visual Accessibility
- [ ] Text has sufficient color contrast
- [ ] Content scales properly at 200% zoom
- [ ] High contrast mode is supported
- [ ] Motion can be disabled
- [ ] Focus indicators are visible

---

*For technical implementation details, see [Developer Guide for Question System](developer-guide-question-system.md).*
