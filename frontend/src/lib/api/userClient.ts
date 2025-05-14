// Frontend API client for user operations

import { authFetch } from '@/lib/utils';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const getUser = async () => {
  return await authFetch(`${API_BASE_URL}/users/me`);
};

export const getUserProfile = async (userId: string) => {
  return await authFetch(`${API_BASE_URL}/users/${userId}`);
};

export const updateUserProfile = async (userId: string, data: any) => {
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
