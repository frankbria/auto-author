// Frontend API client for user operations

import { authFetch } from '@/lib/utils';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface UserProfileData {
  firstName?: string;
  lastName?: string;
  bio?: string;
  avatarUrl?: string;
  theme?: string;
  emailNotifications?: boolean;
  marketingEmails?: boolean;
  [key: string]: unknown;
}

export const getUser = async () => {
  return await authFetch(`${API_BASE_URL}/users/me`);
};

export const getUserProfile = async (userId: string) => {
  return await authFetch(`${API_BASE_URL}/users/${userId}`);
};

export const updateUserProfile = async (userId: string, data: UserProfileData) => {
  return await authFetch(`${API_BASE_URL}/users/${userId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
};

export const getUserBooks = async (userId: string) => {
  return await authFetch(`${API_BASE_URL}/users/${userId}/books`);
};

// Add more API methods as needed
