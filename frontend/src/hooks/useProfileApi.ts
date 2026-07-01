import { useAuthFetch } from '@/hooks/useAuthFetch';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export type UserPreferences = {
  theme: 'light' | 'dark' | 'system';
  email_notifications: boolean;
  marketing_emails: boolean;
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

  const getUserProfile = async (): Promise<UserProfile> => {
    return authFetch<UserProfile>('/users/me');
  };

  const updateUserProfile = async (
    profileData: ProfileUpdateData
  ): Promise<UserProfile> => {
    return authFetch<UserProfile>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(profileData),
    });
  };

  const deleteUserAccount = async (): Promise<void> => {
    await authFetch('/users/me', { method: 'DELETE' });
  };

  return {
    getUserProfile,
    updateUserProfile,
    deleteUserAccount,
  };
};

export default useProfileApi;
