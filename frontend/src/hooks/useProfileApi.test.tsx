import { renderHook } from '@testing-library/react';
import useProfileApi from './useProfileApi';
import { useAuthFetch } from './useAuthFetch';

jest.mock('./useAuthFetch');

describe('useProfileApi', () => {
  const authFetch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthFetch as jest.Mock).mockReturnValue({ authFetch });
  });

  it('getUserProfile GETs /users/me', async () => {
    authFetch.mockResolvedValue({ id: '1' });
    const { result } = renderHook(() => useProfileApi());
    await result.current.getUserProfile();
    expect(authFetch).toHaveBeenCalledWith('/users/me');
  });

  it('updateUserProfile PATCHes /users/me with the payload', async () => {
    authFetch.mockResolvedValue({ id: '1' });
    const { result } = renderHook(() => useProfileApi());
    await result.current.updateUserProfile({ first_name: 'Ada', bio: 'hi' });
    const [path, opts] = authFetch.mock.calls[0];
    expect(path).toBe('/users/me');
    expect(opts.method).toBe('PATCH');
    expect(JSON.parse(opts.body)).toEqual({ first_name: 'Ada', bio: 'hi' });
  });

  it('deleteUserAccount DELETEs /users/me', async () => {
    authFetch.mockResolvedValue(undefined);
    const { result } = renderHook(() => useProfileApi());
    await result.current.deleteUserAccount();
    expect(authFetch).toHaveBeenCalledWith('/users/me', { method: 'DELETE' });
  });
});
