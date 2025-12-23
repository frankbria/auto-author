/**
 * Tests for useOnlineStatus hook
 */

import { renderHook, act } from '@testing-library/react';
import { useOnlineStatus } from '../useOnlineStatus';

describe('useOnlineStatus', () => {
  let onlineListener: ((event: Event) => void) | null = null;
  let offlineListener: ((event: Event) => void) | null = null;

  beforeEach(() => {
    // Mock navigator.onLine
    Object.defineProperty(window.navigator, 'onLine', {
      writable: true,
      value: true,
    });

    // Mock addEventListener to capture listeners
    jest.spyOn(window, 'addEventListener').mockImplementation((event, listener) => {
      if (event === 'online') {
        onlineListener = listener as (event: Event) => void;
      } else if (event === 'offline') {
        offlineListener = listener as (event: Event) => void;
      }
    });

    // Mock removeEventListener
    jest.spyOn(window, 'removeEventListener').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
    onlineListener = null;
    offlineListener = null;
  });

  it('should return online status initially', () => {
    const { result } = renderHook(() => useOnlineStatus());

    expect(result.current.isOnline).toBe(true);
    expect(result.current.wasOffline).toBe(false);
  });

  it('should update status when going offline', () => {
    const { result } = renderHook(() => useOnlineStatus());

    // Simulate going offline
    act(() => {
      Object.defineProperty(window.navigator, 'onLine', {
        writable: true,
        value: false,
      });
      if (offlineListener) {
        offlineListener(new Event('offline'));
      }
    });

    expect(result.current.isOnline).toBe(false);
    expect(result.current.wasOffline).toBe(false);
  });

  it('should set wasOffline flag when coming back online', () => {
    const { result } = renderHook(() => useOnlineStatus());

    // Go offline first
    act(() => {
      Object.defineProperty(window.navigator, 'onLine', {
        writable: true,
        value: false,
      });
      if (offlineListener) {
        offlineListener(new Event('offline'));
      }
    });

    expect(result.current.isOnline).toBe(false);

    // Come back online
    act(() => {
      Object.defineProperty(window.navigator, 'onLine', {
        writable: true,
        value: true,
      });
      if (onlineListener) {
        onlineListener(new Event('online'));
      }
    });

    expect(result.current.isOnline).toBe(true);
    expect(result.current.wasOffline).toBe(true);
  });

  it('should reset wasOffline flag after delay', async () => {
    jest.useFakeTimers();

    const { result } = renderHook(() => useOnlineStatus());

    // Go offline
    act(() => {
      Object.defineProperty(window.navigator, 'onLine', {
        writable: true,
        value: false,
      });
      if (offlineListener) {
        offlineListener(new Event('offline'));
      }
    });

    // Come back online
    act(() => {
      Object.defineProperty(window.navigator, 'onLine', {
        writable: true,
        value: true,
      });
      if (onlineListener) {
        onlineListener(new Event('online'));
      }
    });

    expect(result.current.wasOffline).toBe(true);

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(result.current.wasOffline).toBe(false);

    jest.useRealTimers();
  });

  it('should cleanup event listeners on unmount', () => {
    const { unmount } = renderHook(() => useOnlineStatus());

    unmount();

    expect(window.removeEventListener).toHaveBeenCalledWith('online', expect.any(Function));
    expect(window.removeEventListener).toHaveBeenCalledWith('offline', expect.any(Function));
  });
});
