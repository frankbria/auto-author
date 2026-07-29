/**
 * Shared interpretation of Web Speech API error codes (#348).
 *
 * Both dictation surfaces — the chapter editor's VoiceTextInput and the book
 * summary page — used to render the raw code straight to the user
 * ("Error recording audio: no-speech"). Two problems with that:
 *
 *  - `no-speech` and `aborted` are routine. The API fires `no-speech` whenever a
 *    listening window passes without audio, and `aborted` when the user stops or
 *    navigates. Surfacing them as red errors makes working dictation look
 *    broken, which trains people to ignore the error region entirely.
 *  - `not-allowed` is the one code the user can actually act on, and a bare
 *    "not-allowed" tells them nothing about how.
 *
 * Kept as a plain module rather than a hook so both surfaces share one mapping;
 * they have quite different component shapes but identical error semantics.
 */

/**
 * Codes that mean "nothing happened", not "something went wrong". Callers should
 * clear any in-progress state but show no error.
 */
const BENIGN_CODES = new Set(['no-speech', 'aborted']);

export function isBenignSpeechError(code: string | undefined): boolean {
  return BENIGN_CODES.has(code ?? '');
}

/**
 * User-facing copy for a speech-recognition error code.
 *
 * Each message names what to do, not just what failed. Returns null for benign
 * codes so a caller can pass the result straight to its error state.
 */
export function describeSpeechError(code: string | undefined): string | null {
  if (isBenignSpeechError(code)) {
    return null;
  }

  switch (code) {
    case 'not-allowed':
    case 'service-not-allowed':
      return (
        'Microphone access is blocked. Allow microphone access for this site in ' +
        'your browser settings, then start dictation again.'
      );
    case 'audio-capture':
      return (
        'No microphone was found. Check that one is connected and not in use by ' +
        'another app, then try again.'
      );
    case 'network':
      return (
        'Dictation needs an internet connection to transcribe speech. Check your ' +
        'connection and try again.'
      );
    case 'language-not-supported':
      return 'Dictation is not available for this language in your browser.';
    case 'bad-grammar':
      // Not reachable without a grammar list, but the API can emit it.
      return 'Dictation could not process the audio. Try again.';
    default:
      return 'Dictation stopped unexpectedly. Try again.';
  }
}

/**
 * Whether this browser/context can do speech recognition at all.
 *
 * Must run in an effect, never during render: the constructors live on `window`,
 * and a server render would report every browser unsupported. Also false in an
 * insecure context, where Chrome exposes the constructor but refuses the mic.
 */
export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  const ctor =
    (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
  if (!ctor) {
    return false;
  }
  // getUserMedia is absent in insecure contexts, where recognition cannot work
  // even though the constructor is present.
  return Boolean(navigator?.mediaDevices?.getUserMedia);
}

/** Guidance shown in place of the dictation control when it cannot work. */
export const SPEECH_UNSUPPORTED_MESSAGE =
  'Dictation is not available in this browser. Chrome or Edge support it over ' +
  'HTTPS; you can still type your summary below.';
