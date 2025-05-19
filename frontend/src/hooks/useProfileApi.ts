import { useAuthFetch } from '@/hooks/useAuthFetch';

type UserProfile = {
  id: string;
  clerk_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  avatar_url: string | null;
  bio: string | null;
  preferences: {
    theme: "light" | "dark" | "system";
    email_notifications: boolean;
    marketing_emails: boolean;
  };
};

type ProfileUpdateData = {
  first_name?: string;
  last_name?: string;
  bio?: string;
  preferences?: {
    theme?: "light" | "dark" | "system";
    email_notifications?: boolean;
    marketing_emails?: boolean;
  };
};

/**
 * Custom hook for managing user profile operations
 */
export const useProfileApi = () => {
  const { authFetch } = useAuthFetch();
  
  /**
   * Get the current user's profile data
   */
  const getUserProfile = async (): Promise<UserProfile> => {
    const response = await authFetch('/api/users/me');
    if (!response.ok) {
      throw new Error(`Error fetching profile: ${response.statusText}`);
    }
    return await response.json();
  };
  
  /**
   * Update the current user's profile data
   */
  const updateUserProfile = async (profileData: ProfileUpdateData): Promise<UserProfile> => {
    const response = await authFetch('/api/users/me', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(profileData),
    });
    
    if (!response.ok) {
      throw new Error(`Error updating profile: ${response.statusText}`);
    }
    
    return await response.json();
  };
  
  /**
   * Delete the current user's account
   */
  const deleteUserAccount = async (): Promise<void> => {
    const response = await authFetch('/api/users/me', {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`Error deleting account: ${response.statusText}`);
    }
  };
  
  return {
    getUserProfile,
    updateUserProfile,
    deleteUserAccount,
  };
};

export default useProfileApi;
