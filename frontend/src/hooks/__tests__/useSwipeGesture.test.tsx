import { useState } from 'react';
import { render, act } from '@testing-library/react';
import { useSwipeGesture } from '../useSwipeGesture';

/**
 * Dispatches a touchstart at (startX, y) then a touchend at (endX, endY) on the element.
 * jsdom has no TouchEvent constructor, so we use a plain Event with the touch fields attached.
 */
function swipe(
  el: HTMLElement,
  { startX, endX, startY = 0, endY = 0 }: { startX: number; endX: number; startY?: number; endY?: number }
) {
  const start = new Event('touchstart', { bubbles: true }) as unknown as TouchEvent;
  Object.defineProperty(start, 'touches', { value: [{ clientX: startX, clientY: startY }] });
  el.dispatchEvent(start);

  const end = new Event('touchend', { bubbles: true }) as unknown as TouchEvent;
  Object.defineProperty(end, 'changedTouches', { value: [{ clientX: endX, clientY: endY }] });
  el.dispatchEvent(end);
}

function Swipeable(props: Parameters<typeof useSwipeGesture>[0]) {
  const ref = useSwipeGesture<HTMLDivElement>(props);
  return <div ref={ref} data-testid="area">content</div>;
}

describe('useSwipeGesture', () => {
  it('fires onSwipeLeft for a leftward swipe past the threshold', () => {
    const onSwipeLeft = jest.fn();
    const onSwipeRight = jest.fn();
    const { getByTestId } = render(<Swipeable onSwipeLeft={onSwipeLeft} onSwipeRight={onSwipeRight} />);

    swipe(getByTestId('area'), { startX: 200, endX: 100 }); // dx = -100

    expect(onSwipeLeft).toHaveBeenCalledTimes(1);
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('fires onSwipeRight for a rightward swipe past the threshold', () => {
    const onSwipeRight = jest.fn();
    const { getByTestId } = render(<Swipeable onSwipeRight={onSwipeRight} />);

    swipe(getByTestId('area'), { startX: 100, endX: 200 }); // dx = +100

    expect(onSwipeRight).toHaveBeenCalledTimes(1);
  });

  it('ignores a swipe shorter than the threshold', () => {
    const onSwipeLeft = jest.fn();
    const { getByTestId } = render(<Swipeable onSwipeLeft={onSwipeLeft} threshold={50} />);

    swipe(getByTestId('area'), { startX: 100, endX: 70 }); // dx = -30 < 50

    expect(onSwipeLeft).not.toHaveBeenCalled();
  });

  it('ignores a predominantly vertical drag (does not hijack scrolling)', () => {
    const onSwipeLeft = jest.fn();
    const onSwipeRight = jest.fn();
    const { getByTestId } = render(<Swipeable onSwipeLeft={onSwipeLeft} onSwipeRight={onSwipeRight} />);

    // dx = -60 (past threshold) but dy = 200 → vertical wins, no horizontal swipe
    swipe(getByTestId('area'), { startX: 200, endX: 140, startY: 0, endY: 200 });

    expect(onSwipeLeft).not.toHaveBeenCalled();
    expect(onSwipeRight).not.toHaveBeenCalled();
  });

  it('binds to an element mounted AFTER the first render (late mount)', () => {
    // Regression: useMediaQuery starts false, so the swipeable element often only
    // mounts on a later render. A one-time effect would miss it; the callback ref
    // must bind when the node finally appears.
    const onSwipeLeft = jest.fn();
    function LateMount() {
      const ref = useSwipeGesture<HTMLDivElement>({ onSwipeLeft });
      const [show, setShow] = useState(false);
      return (
        <>
          <button data-testid="show" onClick={() => setShow(true)}>show</button>
          {show && <div ref={ref} data-testid="area">content</div>}
        </>
      );
    }
    const { getByTestId } = render(<LateMount />);
    act(() => {
      getByTestId('show').click(); // element mounts now, after initial render
    });

    swipe(getByTestId('area'), { startX: 200, endX: 100 });

    expect(onSwipeLeft).toHaveBeenCalledTimes(1);
  });

  it('removes listeners on unmount', () => {
    const onSwipeLeft = jest.fn();
    const { getByTestId, unmount } = render(<Swipeable onSwipeLeft={onSwipeLeft} />);
    const area = getByTestId('area');
    unmount();

    swipe(area, { startX: 200, endX: 100 });

    expect(onSwipeLeft).not.toHaveBeenCalled();
  });
});
