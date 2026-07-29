import {
  isBenignSpeechError,
  describeSpeechError,
  isSpeechRecognitionSupported,
} from '../speechRecognitionErrors';

describe('isBenignSpeechError', () => {
  // These two fire in normal use — a silent listening window, or the user
  // stopping/navigating. Treating them as failures is what made working
  // dictation look broken (#348).
  it.each(['no-speech', 'aborted'])('treats %s as benign', (code) => {
    expect(isBenignSpeechError(code)).toBe(true);
  });

  it.each(['not-allowed', 'audio-capture', 'network', 'service-not-allowed'])(
    'treats %s as a real error',
    (code) => {
      expect(isBenignSpeechError(code)).toBe(false);
    }
  );

  it('handles a missing code', () => {
    expect(isBenignSpeechError(undefined)).toBe(false);
  });
});

describe('describeSpeechError', () => {
  it.each(['no-speech', 'aborted'])('returns null for benign code %s', (code) => {
    expect(describeSpeechError(code)).toBeNull();
  });

  it.each([
    ['not-allowed', /allow microphone access/i],
    ['service-not-allowed', /allow microphone access/i],
    ['audio-capture', /no microphone was found/i],
    ['network', /internet connection/i],
    ['language-not-supported', /not available for this language/i],
  ])('gives actionable copy for %s', (code, pattern) => {
    expect(describeSpeechError(code)).toMatch(pattern as RegExp);
  });

  it('never leaks the raw code to the user', () => {
    // The old behaviour was `Error recording audio: ${event.error}`.
    for (const code of [
      'not-allowed',
      'audio-capture',
      'network',
      'language-not-supported',
      'bad-grammar',
      'some-future-code',
    ]) {
      expect(describeSpeechError(code)).not.toContain(code);
    }
  });

  it('falls back to actionable copy for an unknown code', () => {
    expect(describeSpeechError('totally-new-code')).toMatch(/try again/i);
  });
});

describe('isSpeechRecognitionSupported', () => {
  const original = {
    SpeechRecognition: (window as never)['SpeechRecognition'],
    webkitSpeechRecognition: (window as never)['webkitSpeechRecognition'],
    mediaDevices: navigator.mediaDevices,
  };

  afterEach(() => {
    (window as never)['SpeechRecognition'] = original.SpeechRecognition;
    (window as never)['webkitSpeechRecognition'] = original.webkitSpeechRecognition;
    // jest.setup.ts defines mediaDevices as writable but NOT configurable, so
    // assign rather than redefine.
    (navigator as unknown as Record<string, unknown>).mediaDevices = original.mediaDevices;
  });

  it('is true when a constructor and getUserMedia are both present', () => {
    expect(isSpeechRecognitionSupported()).toBe(true);
  });

  it('is false without either constructor (Firefox)', () => {
    delete (window as never)['SpeechRecognition'];
    delete (window as never)['webkitSpeechRecognition'];
    expect(isSpeechRecognitionSupported()).toBe(false);
  });

  it('is false without getUserMedia (insecure context)', () => {
    // Chrome over plain HTTP exposes the constructor but cannot reach the mic,
    // so a constructor check alone advertises a capability that does not work.
    (navigator as unknown as Record<string, unknown>).mediaDevices = undefined;
    expect(isSpeechRecognitionSupported()).toBe(false);
  });
});
