'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Mic,
  Type,
  Square
} from 'lucide-react';
import { cn } from '@/lib/utils';

type InputMode = 'text' | 'voice';

interface VoiceTextInputProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  onModeChange?: (mode: InputMode) => void;
  mode?: InputMode;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
  isFinal?: boolean;
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResult[][];
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  onend: (() => void) | null;
  onspeechend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}


export function VoiceTextInput({
  id,
  value,
  onChange,
  onModeChange,
  mode = 'text',
  placeholder = 'Start writing...',
  className,
  disabled = false
}: VoiceTextInputProps) {
  const [currentMode, setCurrentMode] = useState<InputMode>(mode);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Check for speech recognition support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);
  }, []);

  // Update mode when prop changes
  useEffect(() => {
    setCurrentMode(mode);
  }, [mode]);

  // Initialize speech recognition
  const initializeSpeechRecognition = useCallback(() => {
    if (!isSupported) return null;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsRecording(true);
      setError(null);
      setInterimTranscript('');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result && result[0]) {
          const transcript = result[0].transcript;
          if (result[0].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }
      }

      if (finalTranscript) {
        // Insert at cursor position or append
        const textarea = textareaRef.current;
        if (textarea) {
          const start = textarea.selectionStart;
          const end = textarea.selectionEnd;
          const newValue = value.slice(0, start) + finalTranscript + ' ' + value.slice(end);
          onChange(newValue);

          // Move cursor to end of inserted text
          setTimeout(() => {
            const newPosition = start + finalTranscript.length + 1;
            textarea.setSelectionRange(newPosition, newPosition);
            textarea.focus();
          }, 10);
        } else {
          onChange(value + finalTranscript + ' ');
        }
      }

      setInterimTranscript(interimTranscript);
    };

    recognition.onerror = (event: ErrorEvent) => {
      console.error('Speech recognition error:', event.error);
      setError(`Error recording audio: ${event.error || 'Unknown error'}`);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
      setInterimTranscript('');
    };

    return recognition;
  }, [isSupported, value, onChange]);

  const toggleMode = () => {
    const newMode = currentMode === 'text' ? 'voice' : 'text';
    setCurrentMode(newMode);
    if (onModeChange) {
      onModeChange(newMode);
    }

    // Stop recording if switching away from voice mode
    if (newMode === 'text' && isRecording) {
      stopRecording();
    }
  };

  const startRecording = async () => {
    if (!isSupported) {
      setError('Speech recognition is not supported in this browser');
      return;
    }

    try {
      // Request microphone permission
      await navigator.mediaDevices.getUserMedia({ audio: true });

      setError(null);
      const recognition = initializeSpeechRecognition();
      if (recognition) {
        recognitionRef.current = recognition;
        recognition.start();
      }
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Failed to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsRecording(false);
    setInterimTranscript('');
  };

  const handleRetry = () => {
    setError(null);
    if (currentMode === 'voice') {
      startRecording();
    }
  };

  return (
    <div className={cn('w-full space-y-4', className)}>
      {/* Mode Toggle and Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleMode}
            disabled={disabled}
            className="flex items-center gap-2 min-h-[44px] min-w-[44px]"
          >
            {currentMode === 'text' ? (
              <>
                <Mic className="h-4 w-4" />
                Switch to Voice
              </>
            ) : (
              <>
                <Type className="h-4 w-4" />
                Switch to Text
              </>
            )}
          </Button>

          {currentMode === 'voice' && !isSupported && (
            <span className="text-sm text-muted-foreground">
              Voice input not supported
            </span>
          )}
        </div>

        {currentMode === 'voice' && isSupported && (
          <div className="flex items-center gap-2">
            {!isRecording ? (
              <Button
                onClick={startRecording}
                disabled={disabled}
                className="flex items-center gap-2"
                aria-label="Start voice recording"
              >
                <Mic className="h-4 w-4" />
                Start Recording
              </Button>
            ) : (
              <Button
                variant="destructive"
                onClick={stopRecording}
                disabled={disabled}
                className="flex items-center gap-2"
                aria-label="Stop voice recording"
              >
                <Square className="h-4 w-4" />
                Stop Recording
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 text-sm rounded-md">
          {error}
          <Button
            variant="link"
            size="sm"
            onClick={handleRetry}
            className="ml-2 p-0 h-auto text-destructive underline"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Recording Status */}
      {isRecording && (
        <div
          className="bg-green-50 border border-green-200 text-green-800 px-4 py-2 text-sm rounded-md"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            Recording started - speak now
          </div>
        </div>
      )}

      {/* Content Area */}
      {currentMode === 'text' ? (
        <Textarea
          id={id}
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn("min-h-[200px] resize-none min-w-[44px]", className)}
          aria-label="Chapter content text input"
        />
      ) : (
        <div className="min-h-[200px] border rounded-md p-4 bg-background">
          <div className="text-foreground whitespace-pre-wrap">
            {value}
            {interimTranscript && (
              <span className="text-muted-foreground italic">
                {interimTranscript}
              </span>
            )}
            {!value && !interimTranscript && (
              <span className="text-muted-foreground">
                {isRecording ? 'Listening...' : 'Click "Start Recording" to begin voice input'}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Live Region for Screen Readers */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {isRecording && 'Recording started'}
        {error && `Error: ${error}`}
      </div>
    </div>
  );
}
