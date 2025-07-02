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
    // This function is deprecated - authFetch no longer works
    throw new Error('Profile API is deprecated. Use Clerk user management instead.');
  };
  
  /**
   * Update the current user's profile data
   */
  const updateUserProfile = async (profileData: ProfileUpdateData): Promise<UserProfile> => {
    // This function is deprecated - authFetch no longer works
    throw new Error('Profile API is deprecated. Use Clerk user management instead.');
  };
  
  /**
   * Delete the current user's account
   */
  const deleteUserAccount = async (): Promise<void> => {
    // This function is deprecated - authFetch no longer works
    throw new Error('Profile API is deprecated. Use Clerk user management instead.');
  };
  
  return {
    getUserProfile,
    updateUserProfile,
    deleteUserAccount,
  };
};

export default useProfileApi;
