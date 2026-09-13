import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ExportProgressModal } from '../ExportProgressModal';

/**
 * The elapsed-time counter (#584).
 *
 * `ExportProgressModal` had `setElapsedTime(0)` at the top of the effect, which
 * is a synchronous setState inside an effect body. The reset moved into the
 * effect's cleanup: `elapsedTime` is only read while the status is `processing`
 * or `pending`, so clearing it on the way out instead of on the way in is
 * invisible to the user and costs one render pass fewer.
 *
 * "Invisible" is the claim these tests check. The component had no test file at
 * all, so nothing covered the counter, the two thresholds it drives, or — the
 * part that actually changed — what a *second* export sees.
 */

const ELAPSED = /Elapsed time: (\d+)s/;

function renderProcessing(props: Partial<React.ComponentProps<typeof ExportProgressModal>> = {}) {
  return render(
    <ExportProgressModal isOpen status="processing" progress={40} onClose={jest.fn()} {...props} />
  );
}

describe('ExportProgressModal elapsed time (#584)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    // Clear rather than run: a pending interval tick fired outside `act` here
    // would warn, and these tests have already advanced everything they care
    // about.
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  it('stays hidden for the first ten seconds, then counts', () => {
    renderProcessing();
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(10_000);
    });
    // The threshold is `> 10`, so ten seconds exactly is still silent.
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(2_000);
    });
    expect(screen.getByText('Elapsed time: 12s')).toBeInTheDocument();
  });

  it('switches to the reassurance message past twenty seconds', () => {
    renderProcessing();
    act(() => {
      jest.advanceTimersByTime(21_000);
    });
    expect(screen.getByText(/taking longer than expected/i)).toBeInTheDocument();
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();
  });

  it('does not run the counter once the export finishes', () => {
    const { rerender } = renderProcessing();
    act(() => {
      jest.advanceTimersByTime(15_000);
    });
    expect(screen.getByText('Elapsed time: 15s')).toBeInTheDocument();

    rerender(<ExportProgressModal isOpen status="completed" progress={100} onClose={jest.fn()} />);
    act(() => {
      jest.advanceTimersByTime(30_000);
    });
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();
  });

  it('restarts from zero for a second export', () => {
    // This is the one the refactor moved. With the reset dropped from cleanup,
    // a second export inherits the first one's count and opens straight into
    // "this is taking longer than expected" — for an export one second old.
    const { rerender } = renderProcessing();
    act(() => {
      jest.advanceTimersByTime(25_000);
    });
    expect(screen.getByText(/taking longer than expected/i)).toBeInTheDocument();

    rerender(<ExportProgressModal isOpen status="completed" progress={100} onClose={jest.fn()} />);
    rerender(<ExportProgressModal isOpen status="processing" progress={5} onClose={jest.fn()} />);

    act(() => {
      jest.advanceTimersByTime(1_000);
    });
    expect(screen.queryByText(/taking longer than expected/i)).not.toBeInTheDocument();
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();

    act(() => {
      jest.advanceTimersByTime(11_000);
    });
    expect(screen.getByText('Elapsed time: 12s')).toBeInTheDocument();
  });

  it('restarts when pending becomes processing', () => {
    // `status` is in the dependency array, so pending -> processing tears the
    // effect down and rebuilds it. That restarted the counter before this change
    // (reset on the way in) and still restarts it now (reset on the way out).
    const { rerender } = renderProcessing({ status: 'pending' });
    act(() => {
      jest.advanceTimersByTime(15_000);
    });
    expect(screen.getByText('Elapsed time: 15s')).toBeInTheDocument();

    rerender(<ExportProgressModal isOpen status="processing" progress={10} onClose={jest.fn()} />);
    act(() => {
      jest.advanceTimersByTime(2_000);
    });
    expect(screen.queryByText(ELAPSED)).not.toBeInTheDocument();
  });
});
