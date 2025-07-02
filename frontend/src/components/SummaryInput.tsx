import React, { useRef, useState } from 'react';
import { Textarea } from './ui/textarea';
import { Button } from './ui/button';

// TypeScript types for SpeechRecognition
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}


/**
 * SummaryInput - A text area for users to enter a book summary or synopsis.
 * Includes clear labeling, helpful prompts, example summaries, and voice-to-text.
 */
export const SummaryInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}> = ({ value, onChange, disabled }) => {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  const handleVoiceInput = () => {
    setError(null);
    const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionClass) {
      setError('Speech recognition is not supported in your browser.');
      return;
    }
    const recognition = new SpeechRecognitionClass();
    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    setIsListening(true);
    recognition.onresult = (event: unknown) => {
      const e = event as SpeechRecognitionEvent;
      let transcript = '';
      for (let i = e.resultIndex; i < e.results.length; ++i) {
        transcript += e.results[i][0].transcript;
      }
      onChange(value ? value + ' ' + transcript : transcript);
      setIsListening(false);
    };
    recognition.onerror = (event: unknown) => {
      const e = event as { error?: string };
      setError('Speech recognition error: ' + (e.error || 'Unknown error'));
      setIsListening(false);
    };
    recognition.onend = () => {
      setIsListening(false);
    };
    recognition.start();
  };

  const handleStop = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  };

  // Calculate character and word count
  const charCount = value.length;
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const maxChars = 2000;

  return (
    <div className="space-y-2">
      <label htmlFor="summary-input" className="text-lg font-semibold">
        Book Summary / Synopsis
      </label>
      <Textarea
        id="summary-input"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="Write a brief summary of your book. For best results, include the main idea, genre, and any key themes or characters."
        rows={7}
        maxLength={maxChars}
        className="text-zinc-100 placeholder:text-zinc-400 bg-zinc-900 border-zinc-700"
        disabled={disabled || isListening}
        aria-describedby="summary-help"
      />
      <div className="flex items-center gap-3 mt-1">
        <Button type="button" variant="outline" onClick={isListening ? handleStop : handleVoiceInput} disabled={disabled}>
          {isListening ? 'Stop Listening' : 'Speak Summary'}
        </Button>
        {isListening && <span className="text-indigo-400 animate-pulse">Listening...</span>}
        {error && <span className="text-red-400 text-xs ml-2">{error}</span>}
        <span className="ml-auto text-xs text-zinc-400">
          {wordCount} words &bull; {charCount}/{maxChars} characters
        </span>
      </div>
      <div id="summary-help" className="text-xs text-zinc-400 mt-2">
        <div>Guidelines: Aim for 1-3 paragraphs. Include the main idea, genre, and any key themes or characters. Minimum 30 words recommended.</div>
        <div className="italic text-zinc-500 mt-1">
          &quot;A young orphan discovers a hidden world of magic and must stop a dark sorcerer from conquering both realms. The story explores friendship, courage, and the power of believing in oneself.&quot;
        </div>
      </div>
    </div>
  );
};

export default SummaryInput;