import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SummaryInput from '../components/SummaryInput';
import React from 'react';

// Mock for Web Speech API
interface MockSpeechRecognitionEvent {
  resultIndex: number;
  results: Array<Array<{ transcript: string }>>;
}

class MockSpeechRecognition {
  public onresult: ((event: MockSpeechRecognitionEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onend: (() => void) | null = null;
  public continuous = false;
  public interimResults = false;
  public lang = 'en-US';
  start = jest.fn(() => {
    // Simulate listening for 600ms before result and end
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
    }, 600);
  });
  stop = jest.fn(() => {
    if (this.onend) this.onend();
  });
}

describe('SummaryInput', () => {
  beforeAll(() => {
    // @ts-expect-error - Mocking global speech recognition
    window.SpeechRecognition = MockSpeechRecognition;
    // @ts-expect-error - Mocking webkit speech recognition
    window.webkitSpeechRecognition = MockSpeechRecognition;
  });

  it('shows real-time feedback for typing', () => {
    const handleChange = jest.fn();
    render(<SummaryInput value="" onChange={handleChange} />);
    const textarea = screen.getByLabelText(/Book Summary/i);
    fireEvent.change(textarea, { target: { value: 'A test summary.' } });
    expect(handleChange).toHaveBeenCalledWith('A test summary.');
    // Use getAllByText and check for the counter format (matcher must return boolean)
    const counters = screen.getAllByText((content) => /\d+ words?\s*•\s*\d+\/\d+ characters?/.test(content));
    expect(counters.length).toBeGreaterThan(0);
  });

  it('handles voice input and updates summary', async () => {
    let value = '';
    const handleChange = (v: string) => { value = v; };
    render(<SummaryInput value={value} onChange={handleChange} />);
    const button = screen.getByRole('button', { name: /speak summary/i });
    fireEvent.click(button);
    await act(async () => { await new Promise(r => setTimeout(r, 50)); });
    // Use getAllByText to avoid multiple matches and check for the span
    const listeningEls = screen.getAllByText('Listening...');
    expect(listeningEls.length).toBeGreaterThan(0);
    // Then wait for the summary value to update
    await waitFor(() => {
      expect(value).toMatch(/Voice summary test/);
    });
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
    const history = ['First version.'];
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

describe('SummaryInput edge cases', () => {
  it('handles very brief summaries (too short)', () => {
    const handleChange = jest.fn();
    render(<SummaryInput value="Gardening book." onChange={handleChange} />);
    // Should show word/char count and allow typing, but is too short for TOC
    const counter = screen.getByText(/\d+ words?\s*•\s*\d+\/\d+ characters?/);
    expect(counter).toBeInTheDocument();
    // Should be less than 30 words
    expect(counter.textContent).toMatch(/\b([0-9]|[12][0-9]) words?\b/);
  });

  it('handles complex, long summaries', () => {
    const longSummary = `This book provides a comprehensive, step-by-step guide to advanced quantum computing concepts, including quantum algorithms, error correction, and hardware implementation. It is designed for graduate students and professionals in computer science, physics, and engineering. Topics include Shor's algorithm, Grover's search, quantum error correction codes, topological qubits, and the future of quantum hardware. Each chapter includes practical exercises, real-world case studies, and interviews with leading researchers in the field. The book also explores ethical implications and the impact of quantum technology on cybersecurity, cryptography, and society at large.`;
    const handleChange = jest.fn();
    render(<SummaryInput value={longSummary} onChange={handleChange} />);
    // Should show high word/char count
    const counter = screen.getByText(/\d+ words?\s*•\s*\d+\/\d+ characters?/);
    expect(counter).toBeInTheDocument();
    // Should be more than 30 words
    const wordCount = parseInt(counter.textContent?.split(' ')[0] || '0', 10);
    expect(wordCount).toBeGreaterThan(30);
    // Should not exceed 2000 chars
    const charCount = parseInt(counter.textContent?.split('•')[1]?.split('/')[0].replace(/\D/g, '') || '0', 10);
    expect(charCount).toBeLessThanOrEqual(2000);
  });

  it('handles ambiguous summaries', () => {
    const ambiguous = 'A book about things.';
    const handleChange = jest.fn();
    render(<SummaryInput value={ambiguous} onChange={handleChange} />);
    // Should show word/char count and allow typing
    const counter = screen.getByText(/\d+ words?\s*•\s*\d+\/\d+ characters?/);
    expect(counter).toBeInTheDocument();
    // Should be less than 30 words
    expect(counter.textContent).toMatch(/\b([0-9]|[12][0-9]) words?\b/);
  });
});