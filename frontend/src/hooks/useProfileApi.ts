import { useCallback } from 'react';

import { useAuthFetch } from '@/hooks/useAuthFetch';
import { apiFetch, browser } from '@/lib/api/unauthorized';
import { toast } from '@/lib/toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/** Why the download did not start, as the toast says it. */
function exportRefusal(response: Response | null): { title: string; description: string } {
  if (response?.status === 429) {
    const minutes = Math.max(1, Math.ceil(Number(response.headers.get('Retry-After')) / 60) || 1);
    return {
      title: 'Download limit reached',
      description: `You can download your data again in ${minutes} minute${minutes === 1 ? '' : 's'}.`,
    };
  }
  if (response?.status === 401) {
    return { title: 'Your session has expired', description: 'Sign in again to download your data.' };
  }
  return { title: "Couldn't start the download", description: 'Please try again.' };
}

/**
 * The account data download (#790). A single-use token is requested first
 * (#966), so a refusal is shown here and the user stays on the page; with the
 * token, the browser fetches the attachment and streams it to disk.
 */
export async function downloadAccountData(): Promise<void> {
  let response: Response | null = null;
  try {
    response = await apiFetch(`${API_BASE_URL}/users/me/export/token`, {
      method: 'POST',
      credentials: 'include',
    });
    if (response.ok) {
      const { token } = await response.json();
      browser.go(`${API_BASE_URL}/users/me/export?token=${encodeURIComponent(token)}`);
      return;
    }
  } catch {
    // No network: fall through to the generic message.
  }
  toast({ ...exportRefusal(response), variant: 'destructive' });
}

export type UserPreferences = {
  theme: 'light' | 'dark' | 'system';
  email_notifications: boolean;
  marketing_emails: boolean;
  // Writing preferences (#64)
  default_writing_style?: 'professional' | 'conversational' | 'academic' | 'creative' | 'technical';
  auto_save_interval?: number; // seconds, 3-30
  // Export preferences (#64)
  default_export_format?: 'pdf' | 'docx' | 'epub' | 'markdown';
  default_page_size?: 'letter' | 'A4';
  include_empty_chapters?: boolean;
  // Notification preferences (#64)
  writing_reminders?: boolean;
  progress_updates?: boolean;
  backup_notifications?: boolean;
};

export type UserProfile = {
  id: string;
  auth_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  preferences: UserPreferences;
  plan?: string; // Entitlement plan (issue #174); optional to tolerate older responses
  stripe_customer_id?: string | null; // Stripe linkage (issue #221/#222)
};

export type ProfileUpdateData = {
  first_name?: string;
  last_name?: string;
  display_name?: string;
  bio?: string;
  preferences?: Partial<UserPreferences>;
};

/**
 * Hook for user profile operations against the better-auth backend.
 * All requests are cookie-authenticated via useAuthFetch (credentials: 'include').
 */
export const useProfileApi = () => {
  const { authFetch } = useAuthFetch({ baseUrl: API_BASE_URL });

  // Memoized so callers can safely list these in effect dependencies.
  const getUserProfile = useCallback(async (): Promise<UserProfile> => {
    return authFetch<UserProfile>('/users/me');
  }, [authFetch]);

  const updateUserProfile = useCallback(
    async (profileData: ProfileUpdateData): Promise<UserProfile> => {
      return authFetch<UserProfile>('/users/me', {
        method: 'PATCH',
        body: JSON.stringify(profileData),
      });
    },
    [authFetch]
  );

  const deleteUserAccount = useCallback(async (): Promise<void> => {
    await authFetch('/users/me', { method: 'DELETE' });
  }, [authFetch]);

  return {
    getUserProfile,
    updateUserProfile,
    deleteUserAccount,
  };
};

export default useProfileApi;
