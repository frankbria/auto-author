import { useCallback } from 'react';

import { useAuthFetch } from '@/hooks/useAuthFetch';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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
