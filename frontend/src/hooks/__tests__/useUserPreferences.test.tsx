import { renderHook, waitFor } from '@testing-library/react';

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

    invalidateUserPreferencesCache({
      theme: 'light',
      email_notifications: true,
      marketing_emails: false,
      default_writing_style: 'creative',
    });

    const second = renderHook(() => useUserPreferences());
    expect(second.result.current).toMatchObject({ default_writing_style: 'creative' });
  });
});
