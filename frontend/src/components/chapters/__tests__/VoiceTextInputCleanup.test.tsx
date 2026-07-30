/**
 * #348: the microphone must be released when the editor unmounts, and routine
 * recognition events must not surface as errors.
 *
 * The unmount case is a privacy defect, not a tidiness one: navigating away
 * mid-dictation left recognition running with the browser's recording indicator
 * lit, and the control that would have stopped it was gone.
 */
import { StrictMode } from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VoiceTextInput } from '@/components/chapters/VoiceTextInput';

// A recognizer that records whether it was stopped, standing in for the real
// SpeechRecognition the component constructs from window.
class TrackedRecognition {
  static instances: TrackedRecognition[] = [];
  /** When set, the next start() throws — models a recognizer refusing to run. */
  static failNextStart = false;

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
    if (TrackedRecognition.failNextStart) {
      TrackedRecognition.failNextStart = false;
      throw new Error('start failed');
    }
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
  TrackedRecognition.failNextStart = false;
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

describe('VoiceTextInput releases the mic on every session end (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it('releases the stream when recognition errors', async () => {
    // A network/permission failure ends the session. Without a release here the
    // recording indicator stays lit after the error banner appears, and the Stop
    // button is gone because isRecording went false.
    const track = installMicStream();
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);
    await startRecording();

    await act(async () => {
      TrackedRecognition.instances.at(-1)?.onerror?.({ error: 'network' });
    });

    expect(track.stop).toHaveBeenCalled();
  });

  it('releases the stream when recognition ends on its own', async () => {
    // A service timeout or end-of-utterance fires onend without the user asking.
    const track = installMicStream();
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);
    await startRecording();

    await act(async () => {
      TrackedRecognition.instances.at(-1)?.onend?.();
    });

    expect(track.stop).toHaveBeenCalled();
  });

  it('does not orphan the previous stream when recording is restarted', async () => {
    // Overwriting micStreamRef without releasing would leave the first stream's
    // tracks live for the page's lifetime with no handle left to stop them.
    const firstTrack = { kind: 'audio', stop: jest.fn(), enabled: true };
    const secondTrack = { kind: 'audio', stop: jest.fn(), enabled: true };
    const streams = [
      { getTracks: () => [firstTrack], getAudioTracks: () => [firstTrack] },
      { getTracks: () => [secondTrack], getAudioTracks: () => [secondTrack] },
    ];
    let call = 0;
    (navigator as unknown as Record<string, unknown>).mediaDevices = {
      getUserMedia: jest.fn().mockImplementation(() => Promise.resolve(streams[call++])),
      enumerateDevices: jest.fn().mockResolvedValue([]),
    };

    const user = userEvent.setup();
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);

    await startRecording();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /stop voice recording/i }));
    });
    expect(firstTrack.stop).toHaveBeenCalled();

    // Second session: the first stream must already be gone, and the second must
    // be the one now held.
    await startRecording();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /stop voice recording/i }));
    });
    expect(secondTrack.stop).toHaveBeenCalled();
  });
});

describe('VoiceTextInput async-window leaks (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  /** A getUserMedia whose resolution we control, to hold the await open. */
  function installDeferredMic(count: number) {
    const tracks = Array.from({ length: count }, () => ({
      kind: 'audio',
      stop: jest.fn(),
      enabled: true,
    }));
    const resolvers: Array<() => void> = [];
    let call = 0;
    (navigator as unknown as Record<string, unknown>).mediaDevices = {
      getUserMedia: jest.fn().mockImplementation(() => {
        const track = tracks[call++];
        return new Promise((resolve) => {
          resolvers.push(() =>
            resolve({ getTracks: () => [track], getAudioTracks: () => [track] })
          );
        });
      }),
      enumerateDevices: jest.fn().mockResolvedValue([]),
    };
    return { tracks, resolvers };
  }

  it('ignores a second Start while the first is still awaiting permission', async () => {
    // Both clicks would otherwise pass the release-then-acquire guard while
    // micStreamRef is still null, and the second stream would overwrite the
    // first — orphaning its tracks with no handle left to stop them.
    const { resolvers } = installDeferredMic(2);
    const user = userEvent.setup();
    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);

    const start = screen.getByRole('button', { name: /start voice recording/i });
    await act(async () => {
      await user.click(start);
      await user.click(start);
    });

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolvers[0]?.();
    });
  });

  it('releases a stream that arrives after the component unmounted', async () => {
    // The await is a suspension point: cleanup can run against a null ref and
    // then the stream shows up, held by a component that no longer exists.
    const { tracks, resolvers } = installDeferredMic(1);
    const user = userEvent.setup();
    const { unmount } = render(
      <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /start voice recording/i }));
    });

    unmount();

    await act(async () => {
      resolvers[0]?.();
    });

    expect(tracks[0].stop).toHaveBeenCalled();
  });
});

describe('VoiceTextInput can restart after a browser-driven end (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it.each(['onend', 'onerror'])(
    'allows a new recording after %s ends the session',
    async (event) => {
      // The re-entrancy guard checks recognitionRef, so a handler that ends the
      // session without clearing it turns every later Start into a silent no-op
      // — dictation dead until the component unmounts. onend fires routinely
      // (pause, timeout), so this is the common path, not an edge case.
      installMicStream();
      const user = userEvent.setup();
      render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);

      await startRecording();
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);

      await act(async () => {
        const recognition = TrackedRecognition.instances.at(-1);
        if (event === 'onend') {
          recognition?.onend?.();
        } else {
          recognition?.onerror?.({ error: 'no-speech' });
        }
      });

      // The control is back...
      const start = await screen.findByRole('button', {
        name: /start voice recording/i,
      });
      await act(async () => {
        await user.click(start);
      });

      // ...and actually does something.
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(2);
    }
  );
});

describe('VoiceTextInput survives a failing start (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it('can start again after recognition.start() throws', async () => {
    // start() is called immediately after the handle is stored, so a throw here
    // leaves a dead recognizer that no handler will ever clear — the same brick
    // as the onend/onerror case, reached by a different route.
    installMicStream();
    const user = userEvent.setup();
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    render(<VoiceTextInput value="" mode="voice" onChange={jest.fn()} />);

    TrackedRecognition.failNextStart = true;
    await startRecording();
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(1);

    // The retry must actually reach the microphone again, not just re-render a
    // button that does nothing.
    await act(async () => {
      await user.click(
        await screen.findByRole('button', { name: /start voice recording/i })
      );
    });
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(2);

    consoleSpy.mockRestore();
  });
});

describe('VoiceTextInput under StrictMode (#348)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    installRecognition();
  });

  it('still records after StrictMode double-invokes the effects', async () => {
    // StrictMode runs mount -> cleanup -> mount in development, which is exactly
    // Next.js's default for `next dev`. A flag only ever set to true in cleanup
    // latches on that first teardown, and the unmounted-guard in startRecording
    // then aborts every recording — dictation broken for the whole dev session
    // while passing every non-StrictMode test.
    installMicStream();
    render(
      <StrictMode>
        <VoiceTextInput value="" mode="voice" onChange={jest.fn()} />
      </StrictMode>
    );

    await startRecording();

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
    // Reached the recognizer, not aborted at the guard.
    expect(TrackedRecognition.instances.at(-1)?.started).toBe(true);
  });
});
