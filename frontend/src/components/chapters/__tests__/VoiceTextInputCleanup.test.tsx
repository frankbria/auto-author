/**
 * #348: the microphone must be released when the editor unmounts, and routine
 * recognition events must not surface as errors.
 *
 * The unmount case is a privacy defect, not a tidiness one: navigating away
 * mid-dictation left recognition running with the browser's recording indicator
 * lit, and the control that would have stopped it was gone.
 */
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VoiceTextInput } from '@/components/chapters/VoiceTextInput';

// A recognizer that records whether it was stopped, standing in for the real
// SpeechRecognition the component constructs from window.
class TrackedRecognition {
  static instances: TrackedRecognition[] = [];

  onresult: ((e: unknown) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onend: (() => void) | null = null;
  onstart: (() => void) | null = null;
  onspeechend: (() => void) | null = null;
  continuous = false;
  interimResults = false;
  lang = 'en-US';

  stopped = false;
  started = false;

  constructor() {
    TrackedRecognition.instances.push(this);
  }

  start = jest.fn(() => {
    this.started = true;
    this.onstart?.();
  });

  stop = jest.fn(() => {
    this.stopped = true;
    // The real API fires onend on stop(); the component must have detached its
    // handlers before unmount-stop or this would setState after unmount.
    this.onend?.();
  });

  abort = jest.fn(() => {
    this.stopped = true;
  });
}

function installRecognition() {
  TrackedRecognition.instances = [];
  (window as unknown as Record<string, unknown>).SpeechRecognition = TrackedRecognition;
  (window as unknown as Record<string, unknown>).webkitSpeechRecognition = TrackedRecognition;
}

/**
 * Replace getUserMedia with a stream whose track stop() we can observe.
 *
 * This is the part that actually holds the microphone: recognition.stop() does
 * not release a MediaStream, so a component that requests one and drops it keeps
 * the mic (and the browser's recording indicator) live regardless.
 */
function installMicStream() {
  const track = { kind: 'audio', stop: jest.fn(), enabled: true };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  (navigator as unknown as Record<string, unknown>).mediaDevices = {
    getUserMedia: jest.fn().mockResolvedValue(stream),
    enumerateDevices: jest.fn().mockResolvedValue([]),
  };
  return track;
}

async function startRecording() {
  const user = userEvent.setup();
  await act(async () => {
    await user.click(screen.getByRole('button', { name: /start voice recording/i }));
  });
}

describe('VoiceTextInput microphone lifecycle (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it('releases the microphone when unmounted mid-recording', async () => {
    const { unmount } = render(
      <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
    );

    await startRecording();
    const recognition = TrackedRecognition.instances.at(-1);
    expect(recognition?.started).toBe(true);
    expect(recognition?.stopped).toBe(false);

    unmount();

    expect(recognition?.stopped).toBe(true);
  });

  it('detaches handlers before stopping, so unmount cannot setState', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const { unmount } = render(
      <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
    );

    await startRecording();
    const recognition = TrackedRecognition.instances.at(-1);

    unmount();

    // stop() fires onend; if it were still attached React would warn about an
    // update on an unmounted component.
    expect(recognition?.onend).toBeNull();
    expect(recognition?.onresult).toBeNull();
    expect(
      errorSpy.mock.calls.some((c) => String(c[0]).includes('unmounted'))
    ).toBe(false);
    errorSpy.mockRestore();
  });

  it('does not stop anything when it never recorded', () => {
    const { unmount } = render(
      <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
    );
    unmount();
    expect(TrackedRecognition.instances).toHaveLength(0);
  });
});

describe('VoiceTextInput error copy (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it.each(['no-speech', 'aborted'])(
    'shows no error banner for the routine %s event',
    async (code) => {
      render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);
      await startRecording();
      const recognition = TrackedRecognition.instances.at(-1);

      await act(async () => {
        recognition?.onerror?.({ error: code });
      });

      // The old code rendered "Error recording audio: no-speech" — a red banner
      // for a silent pause, which teaches users to ignore the error region.
      expect(screen.queryByText(/error recording audio/i)).not.toBeInTheDocument();
      expect(screen.queryByText(new RegExp(code, 'i'))).not.toBeInTheDocument();
    }
  );

  it('gives actionable guidance when permission is denied', async () => {
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);
    await startRecording();
    const recognition = TrackedRecognition.instances.at(-1);

    await act(async () => {
      recognition?.onerror?.({ error: 'not-allowed' });
    });

    // getAllByText, not getByText: the copy appears twice by design — in the
    // visible banner and in the sr-only aria-live status.
    await waitFor(() => {
      expect(screen.getAllByText(/allow microphone access/i).length).toBeGreaterThan(0);
    });
    // And never the raw code.
    expect(screen.queryByText(/not-allowed/)).not.toBeInTheDocument();
  });
});

describe('VoiceTextInput releases the getUserMedia stream (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it('stops the microphone track on unmount', async () => {
    const track = installMicStream();
    const { unmount } = render(
      <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
    );

    await startRecording();
    expect(track.stop).not.toHaveBeenCalled();

    unmount();

    expect(track.stop).toHaveBeenCalled();
  });

  it('stops the microphone track when the user presses Stop', async () => {
    // The worse half of the bug: the stream outlived an explicit stop, so the
    // recording indicator stayed lit while the user sat on the page believing
    // dictation had ended.
    const track = installMicStream();
    const user = userEvent.setup();
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);

    await startRecording();
    expect(track.stop).not.toHaveBeenCalled();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /stop voice recording/i }));
    });

    expect(track.stop).toHaveBeenCalled();
  });
});
