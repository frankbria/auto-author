export interface MockSpeechRecognitionEvent {
  resultIndex: number;
  results: Array<Array<{ transcript: string; confidence: number; isFinal?: boolean }>>;
}

export interface MockSpeechSegment {
  transcript: string;
  isFinal: boolean;
}

export class MockSpeechRecognition {
  public onresult: ((event: MockSpeechRecognitionEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onend: (() => void) | null = null;
  public onspeechend: (() => void) | null = null;
  public onstart: (() => void) | null = null;
  public continuous = false;
  public interimResults = false;
  public lang = 'en-US';

  // Configurable for different test scenarios
  private delay: number;
  private transcript: string;
  private shouldError: boolean;
  private sequence?: MockSpeechSegment[];

  constructor(config: {
    delay?: number;
    transcript?: string;
    shouldError?: boolean;
    // A sequence of interim/final segments emitted on successive timers, mirroring
    // continuous recognition. Recognition stays open (no onend) until stop().
    sequence?: MockSpeechSegment[];
  } = {}) {
    this.delay = config.delay || 600;
    this.transcript = config.transcript || 'Default test transcription.';
    this.shouldError = config.shouldError || false;
    this.sequence = config.sequence;
  }

  // Deterministically fire a single recognition result. Call inside act() to
  // drive multi-segment scenarios without relying on timers.
  emitResult(segment: MockSpeechSegment) {
    if (this.onresult) {
      this.onresult({
        resultIndex: 0,
        results: [[{
          transcript: segment.transcript,
          confidence: 0.95,
          isFinal: segment.isFinal,
        }]],
      });
    }
  }

  start = jest.fn(() => {
    if (this.onstart) this.onstart();

    setTimeout(() => {
      if (this.shouldError) {
        if (this.onerror) {
          const errorEvent = new Event('error') as any;
          errorEvent.error = 'network';
          this.onerror(errorEvent);
        }
        if (this.onend) this.onend();
        return;
      }

      if (this.sequence) {
        this.sequence.forEach((segment, i) => {
          setTimeout(() => this.emitResult(segment), i * this.delay);
        });
        // Continuous recognition keeps listening until stop(); no onend here.
        return;
      }

      this.emitResult({ transcript: this.transcript, isFinal: true });
      if (this.onend) this.onend();
    }, this.delay);
  });

  stop = jest.fn(() => {
    if (this.onspeechend) this.onspeechend();
    if (this.onend) this.onend();
  });

  abort = jest.fn(() => {
    if (this.onend) this.onend();
  });
}

// Helper to setup speech recognition in tests
export function setupSpeechRecognitionMock(config = {}) {
  const mockInstance = new MockSpeechRecognition(config);
  // @ts-expect-error - Mocking global
  window.SpeechRecognition = jest.fn(() => mockInstance);
  // @ts-expect-error - Mocking global
  window.webkitSpeechRecognition = jest.fn(() => mockInstance);
  return mockInstance;
}

describe('MockSpeechRecognition', () => {
  it('should instantiate with default values', () => {
    const mock = new MockSpeechRecognition();
    expect(mock.lang).toBe('en-US');
  });
});
