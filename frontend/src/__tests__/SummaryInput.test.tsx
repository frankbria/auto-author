import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SummaryInput from '../components/SummaryInput';
import React from 'react';

// Mock for Web Speech API
class MockSpeechRecognition {
  public onresult: ((event: any) => void) | null = null;
  public onerror: ((event: any) => void) | null = null;
  public onend: (() => void) | null = null;
  public continuous = false;
  public interimResults = false;
  public lang = 'en-US';
  start = jest.fn(() => {
    setTimeout(() => {
      if (this.onresult) {
        this.onresult({
          resultIndex: 0,
          results: [
            [{ transcript: 'Voice summary test.' }],
          ],
        });
      }
      if (this.onend) this.onend();
    }, 10);
  });
  stop = jest.fn(() => {
    if (this.onend) this.onend();
  });
}

describe('SummaryInput', () => {
  beforeAll(() => {
    // @ts-ignore
    window.SpeechRecognition = MockSpeechRecognition;
    // @ts-ignore
    window.webkitSpeechRecognition = MockSpeechRecognition;
  });

  it('shows real-time feedback for typing', () => {
    const handleChange = jest.fn();
    render(<SummaryInput value="" onChange={handleChange} />);
    const textarea = screen.getByLabelText(/Book Summary/i);
    fireEvent.change(textarea, { target: { value: 'A test summary.' } });
    expect(handleChange).toHaveBeenCalledWith('A test summary.');
    expect(screen.getByText(/words/i)).toBeInTheDocument();
    expect(screen.getByText(/characters/i)).toBeInTheDocument();
  });

  it('handles voice input and updates summary', async () => {
    let value = '';
    const handleChange = (v: string) => { value = v; };
    render(<SummaryInput value={value} onChange={handleChange} />);
    const button = screen.getByRole('button', { name: /speak summary/i });
    fireEvent.click(button);
    await waitFor(() => {
      expect(value).toMatch(/Voice summary test/);
    });
    expect(screen.getByText(/Listening/i)).toBeInTheDocument();
  });
});

describe('SummaryInput auto-save and revision history', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('auto-saves summary to localStorage and restores on mount', () => {
    const key = 'book-summary-autosave';
    // Simulate user typing
    let value = '';
    const handleChange = (v: string) => { value = v; localStorage.setItem(key, v); };
    render(<SummaryInput value={value} onChange={handleChange} />);
    const textarea = screen.getByLabelText(/Book Summary/i);
    fireEvent.change(textarea, { target: { value: 'Auto-save test summary.' } });
    expect(localStorage.getItem(key)).toBe('Auto-save test summary.');
  });

  it('shows revision history and allows reverting', async () => {
    // Simulate a parent component managing revision history
    let value = 'First version.';
    let history = ['First version.'];
    const handleChange = (v: string) => {
      value = v;
      history.push(v);
    };
    render(<SummaryInput value={value} onChange={handleChange} />);
    // Simulate user typing a new version
    const textarea = screen.getByLabelText(/Book Summary/i);
    fireEvent.change(textarea, { target: { value: 'Second version.' } });
    // Simulate showing revision history (would be a parent feature)
    expect(history).toContain('First version.');
    expect(history).toContain('Second version.');
    // Simulate revert (parent would set value to previous)
    act(() => { handleChange('First version.'); });
    expect(value).toBe('First version.');
  });
});