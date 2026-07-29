'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { HugeiconsIcon } from '@hugeicons/react';
import {
  Mic01Icon,
  TextIcon,
  Square01Icon
} from '@hugeicons/core-free-icons';
import { cn } from '@/lib/utils';
import {
  describeSpeechError,
  isSpeechRecognitionSupported,
} from '@/lib/voice/speechRecognitionErrors';

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
  // getUserMedia hands back a live MediaStream. Its tracks keep the microphone
  // open — and the browser's recording indicator lit — until something calls
  // stop() on each one; recognition.stop() does not do it. The stream used to be
  // requested and thrown away, so the mic stayed live for the life of the page,
  // even after the user pressed Stop (#348).
  const micStreamRef = useRef<MediaStream | null>(null);
  // getUserMedia is async, which opens two windows where a stream can be
  // acquired with nothing left to release it (#348):
  //   - two Start clicks before the first promise resolves: both pass the
  //     release-then-acquire guard while micStreamRef is still null, and the
  //     second overwrites the first, orphaning its tracks;
  //   - unmount while the promise is pending: cleanup runs against a null ref,
  //     then the stream arrives and is held by a component that no longer exists.
  const startingRef = useRef(false);
  const unmountedRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Mirror the latest `value` prop so the long-lived onresult handler reads the
  // current text instead of the value captured when recording started. With
  // continuous recognition, reading the stale closure made each finalized
  // segment overwrite the previous one instead of appending (#330).
  const valueRef = useRef(value);
  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  // Check for speech recognition support
  useEffect(() => {
    setIsSupported(isSpeechRecognitionSupported());
  }, []);

  // Release the microphone if this unmounts mid-recording (#348). Without this,
  // navigating away while dictating left recognition running and the browser's
  // recording indicator lit — the user has no control left to stop it.
  //
  // Empty deps so it runs only on unmount, and it reads the ref rather than
  // state so it cannot capture a stale recorder. Handlers are detached first:
  // stop() fires onend, which would otherwise call setState on an unmounted
  // component.
  useEffect(() => {
    return () => {
      unmountedRef.current = true;
      const recognition = recognitionRef.current;
      if (recognition) {
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        try {
          recognition.stop();
        } catch {
          // Already stopped/destroyed — nothing to release.
        }
        recognitionRef.current = null;
      }
      // Stopping recognition is not enough on its own — the getUserMedia tracks
      // are what hold the microphone open.
      const stream = micStreamRef.current;
      if (stream) {
        stream.getTracks().forEach((track) => {
          try {
            track.stop();
          } catch {
            // Already ended.
          }
        });
        micStreamRef.current = null;
      }
    };
  }, []);

  // Update mode when prop changes
  useEffect(() => {
    setCurrentMode(mode);
  }, [mode]);

  // Every path that ends a dictation session must run this, not just the ones
  // the user drives. Recognition can end on its own (onend) or fail (onerror),
  // and neither releases the getUserMedia tracks that actually hold the
  // microphone — so leaving either out keeps the recording indicator lit with no
  // control left to turn it off (#348).
  const releaseMicStream = useCallback(() => {
    const stream = micStreamRef.current;
    if (!stream) {
      return;
    }
    stream.getTracks().forEach((track) => {
      try {
        track.stop();
      } catch {
        // Already ended.
      }
    });
    micStreamRef.current = null;
  }, []);

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
        // Read the latest value via the ref, not the closure-captured prop, so
        // successive segments append instead of clobbering each other (#330).
        const currentValue = valueRef.current;
        // Insert at cursor position or append
        const textarea = textareaRef.current;
        if (textarea) {
          const start = textarea.selectionStart;
          const end = textarea.selectionEnd;
          const newValue = currentValue.slice(0, start) + finalTranscript + ' ' + currentValue.slice(end);
          // Publish to the ref immediately rather than waiting for the effect
          // above. Effects run after React commits, so when continuous
          // recognition delivers two finalized segments in the same tick the
          // effect cannot run between them — both handlers would read the same
          // stale value and the second would discard the first (#384).
          valueRef.current = newValue;
          onChange(newValue);

          // Move cursor to end of inserted text
          setTimeout(() => {
            const newPosition = start + finalTranscript.length + 1;
            textarea.setSelectionRange(newPosition, newPosition);
            textarea.focus();
          }, 10);
        } else {
          const newValue = currentValue + finalTranscript + ' ';
          valueRef.current = newValue;
          onChange(newValue);
        }
      }

      setInterimTranscript(interimTranscript);
    };

    recognition.onerror = (event: ErrorEvent) => {
      // no-speech/aborted are routine (a silent window, or the user stopping),
      // so they end the session without an error banner. Everything else gets
      // copy that says what to do rather than echoing the raw code (#348).
      const code = (event as unknown as { error?: string }).error;
      const message = describeSpeechError(code);
      if (message) {
        console.error('Speech recognition error:', code);
        setError(message);
      }
      releaseMicStream();
      setIsRecording(false);
    };

    recognition.onend = () => {
      // Recognition can end without the user asking — a service timeout, or the
      // browser deciding the utterance finished. The mic must go with it.
      releaseMicStream();
      setIsRecording(false);
      setInterimTranscript('');
    };

    return recognition;
  }, [isSupported, onChange, releaseMicStream]);

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

    // Ignore a second Start while one is still in flight; the button stays
    // enabled until onstart fires, so a double-click is easy to land.
    if (startingRef.current || recognitionRef.current) {
      return;
    }
    startingRef.current = true;

    try {
      // Release any stream still held from a previous attempt before acquiring
      // another; overwriting the ref would orphan the old tracks for the page's
      // lifetime with no handle left to stop them.
      releaseMicStream();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // The await above is a suspension point: this component may have unmounted
      // while permission was pending, in which case the cleanup already ran and
      // nothing will ever release this stream. Hand it back immediately.
      if (unmountedRef.current) {
        stream.getTracks().forEach((track) => {
          try {
            track.stop();
          } catch {
            // Already ended.
          }
        });
        return;
      }

      // Keep the stream so its tracks can be released again (see micStreamRef).
      micStreamRef.current = stream;

      setError(null);
      const recognition = initializeSpeechRecognition();
      if (recognition) {
        recognitionRef.current = recognition;
        recognition.start();
      }
    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Failed to access microphone. Please check permissions.');
      releaseMicStream();
    } finally {
      startingRef.current = false;
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    releaseMicStream();
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
                <HugeiconsIcon icon={Mic01Icon} size={16} />
                Switch to Voice
              </>
            ) : (
              <>
                <HugeiconsIcon icon={TextIcon} size={16} />
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
                className="flex items-center gap-2 min-h-[44px] min-w-[44px]"
                aria-label="Start voice recording"
              >
                <HugeiconsIcon icon={Mic01Icon} size={16} />
                Start Recording
              </Button>
            ) : (
              <Button
                variant="destructive"
                onClick={stopRecording}
                disabled={disabled}
                className="flex items-center gap-2 min-h-[44px] min-w-[44px]"
                aria-label="Stop voice recording"
              >
                <HugeiconsIcon icon={Square01Icon} size={16} />
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
            className="ml-2 p-0 h-auto text-destructive underline min-h-[44px] min-w-[44px]"
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
