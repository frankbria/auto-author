export interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
  isFinal?: boolean;
}

export interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResult[][];
}

export interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  onspeechend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognition;
    webkitSpeechRecognition?: new () => SpeechRecognition;
  }
}

export type InputMode = 'text' | 'voice';

export interface VoiceTextInputProps {
  value: string;
  onChange: (value: string) => void;
  onModeChange?: (mode: InputMode) => void;
  onAutoSave?: (content: string) => void;
  mode?: InputMode;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}
