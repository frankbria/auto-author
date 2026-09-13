import { act, renderHook, waitFor } from '@testing-library/react';

// This suite tests the real hook — undo the global stub from jest.setup.ts.
jest.unmock('@/hooks/useUserPreferences');

const mockGetUserProfile = jest.fn();
jest.mock('@/hooks/useProfileApi', () => ({
  useProfileApi: () => ({ getUserProfile: mockGetUserProfile }),
}));

import {
  useUserPreferences,
  invalidateUserPreferencesCache,
} from '@/hooks/useUserPreferences';

describe('useUserPreferences', () => {
  beforeEach(() => {
    mockGetUserProfile.mockReset();
    invalidateUserPreferencesCache();
  });

  it('loads preferences from the profile endpoint', async () => {
    mockGetUserProfile.mockResolvedValue({
      preferences: { theme: 'dark', default_writing_style: 'academic' },
    });

    const { result } = renderHook(() => useUserPreferences());
    expect(result.current).toBeNull();

    await waitFor(() =>
      expect(result.current).toMatchObject({ default_writing_style: 'academic' })
    );
  });

  it('shares one fetch across consumers via the module cache', async () => {
    mockGetUserProfile.mockResolvedValue({
      preferences: { theme: 'dark', auto_save_interval: 10 },
    });

    const first = renderHook(() => useUserPreferences());
    await waitFor(() => expect(first.result.current).not.toBeNull());

    const second = renderHook(() => useUserPreferences());
    // Cached value is available synchronously; no second request
    expect(second.result.current).toMatchObject({ auto_save_interval: 10 });
    expect(mockGetUserProfile).toHaveBeenCalledTimes(1);
  });

  it('returns null (defaults apply) when the fetch fails', async () => {
    mockGetUserProfile.mockRejectedValue(new Error('offline'));

    const { result } = renderHook(() => useUserPreferences());
    // Give the rejected promise a tick to settle
    await waitFor(() => expect(mockGetUserProfile).toHaveBeenCalled());
    expect(result.current).toBeNull();
  });

  it('serves updated values after invalidation with a replacement', async () => {
    mockGetUserProfile.mockResolvedValue({ preferences: { theme: 'dark' } });
    const first = renderHook(() => useUserPreferences());
    await waitFor(() => expect(first.result.current).not.toBeNull());

    act(() => {
      invalidateUserPreferencesCache({
        theme: 'light',
        email_notifications: true,
        marketing_emails: false,
        default_writing_style: 'creative',
      });
    });

    const second = renderHook(() => useUserPreferences());
    expect(second.result.current).toMatchObject({ default_writing_style: 'creative' });
  });

  it('pushes an invalidation to consumers that are already mounted', async () => {
    // The gap the effect-mirror left (#584): the settings and profile pages call
    // `invalidateUserPreferencesCache(updated)` after a save, but a consumer that
    // had already mounted kept the old object — its effect had run, and nothing
    // re-ran it. The test above only proved a *newly rendered* hook sees the new
    // value. Every real consumer (editor, draft generator, export modal) is
    // mounted at that moment, which is exactly the case that was broken.
    mockGetUserProfile.mockResolvedValue({ preferences: { theme: 'dark' } });

    const mounted = renderHook(() => useUserPreferences());
    await waitFor(() => expect(mounted.result.current).toMatchObject({ theme: 'dark' }));

    act(() => {
      invalidateUserPreferencesCache({
        theme: 'light',
        email_notifications: true,
        marketing_emails: false,
        default_writing_style: 'creative',
      });
    });

    expect(mounted.result.current).toMatchObject({
      theme: 'light',
      default_writing_style: 'creative',
    });
  });

  it('lets a consumer mounted during an in-flight fetch receive the result', async () => {
    // The old hook attached its own `.then` to the shared promise. Subscribers
    // replace that, so this pins that the second consumer still gets the value
    // rather than waiting for a remount.
    let resolveProfile: (value: unknown) => void = () => {};
    mockGetUserProfile.mockReturnValue(
      new Promise((resolve) => {
        resolveProfile = resolve;
      })
    );

    const first = renderHook(() => useUserPreferences());
    const second = renderHook(() => useUserPreferences());
    expect(first.result.current).toBeNull();
    expect(second.result.current).toBeNull();

    await act(async () => {
      resolveProfile({ preferences: { theme: 'dark', auto_save_interval: 30 } });
    });

    expect(first.result.current).toMatchObject({ auto_save_interval: 30 });
    expect(second.result.current).toMatchObject({ auto_save_interval: 30 });
    expect(mockGetUserProfile).toHaveBeenCalledTimes(1);
  });
});
