import { useSyncExternalStore } from 'react';

import { isSpeechRecognitionSupported } from './speechRecognitionErrors';

/**
 * Whether this browser can do speech recognition.
 *
 * `useSyncExternalStore` rather than `useState` + a mount effect (#584,
 * react-hooks/set-state-in-effect). The capability is a property of the
 * environment, not state this app owns, and it cannot change while the page is
 * open — hence the no-op subscribe.
 *
 * The shape it replaces (`useState(false)` plus an effect that sets the real
 * value) rendered `false` once on the client even where support exists, so the
 * voice affordance flickered in on mount. Reading it during render removes both
 * the extra render pass and that frame.
 *
 * `getServerSnapshot` returns `false`, matching the old initial value, so server
 * output and the first client render still agree.
 */
const subscribe = () => () => {};

export function useSpeechRecognitionSupported(): boolean {
  return useSyncExternalStore(
    subscribe,
    isSpeechRecognitionSupported,
    () => false
  );
}
