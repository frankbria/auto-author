import { render, screen, fireEvent, waitFor } from '@testing-library/react';

import PasswordChangeForm from '@/components/settings/PasswordChangeForm';
import TwoFactorSetup from '@/components/settings/TwoFactorSetup';
import ActiveSessionsList from '@/components/settings/ActiveSessionsList';
import { authClient, useSession } from '@/lib/auth-client';
import { toast } from '@/lib/toast';

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));
const mockToast = toast as unknown as jest.Mock;

// authClient is globally mocked in jest.setup.ts; grab typed handles here.
const mockChangePassword = authClient.changePassword as jest.Mock;
const mockTwoFactorEnable = authClient.twoFactor.enable as jest.Mock;
const mockTwoFactorDisable = authClient.twoFactor.disable as jest.Mock;
const mockVerifyTotp = authClient.twoFactor.verifyTotp as jest.Mock;
const mockListSessions = authClient.listSessions as jest.Mock;
const mockRevokeSession = authClient.revokeSession as jest.Mock;
const mockRevokeOtherSessions = authClient.revokeOtherSessions as jest.Mock;
const mockUseSession = useSession as jest.Mock;

const fillPasswordForm = (current: string, next: string, confirm: string) => {
  fireEvent.change(screen.getByLabelText('Current Password'), { target: { value: current } });
  fireEvent.change(screen.getByLabelText('New Password'), { target: { value: next } });
  fireEvent.change(screen.getByLabelText('Confirm New Password'), {
    target: { value: confirm },
  });
};

describe('PasswordChangeForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockChangePassword.mockResolvedValue({ data: {}, error: null });
  });

  it('changes the password and revokes other sessions', async () => {
    render(<PasswordChangeForm />);
    fillPasswordForm('old-password', 'new-password-123', 'new-password-123');
    fireEvent.click(screen.getByRole('button', { name: /change password/i }));

    await waitFor(() =>
      expect(mockChangePassword).toHaveBeenCalledWith({
        currentPassword: 'old-password',
        newPassword: 'new-password-123',
        revokeOtherSessions: true,
      })
    );
    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Password changed' })
      )
    );
  });

  it('rejects a mismatched confirmation without calling the API', () => {
    render(<PasswordChangeForm />);
    fillPasswordForm('old-password', 'new-password-123', 'different');
    fireEvent.click(screen.getByRole('button', { name: /change password/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/do not match/i);
    expect(mockChangePassword).not.toHaveBeenCalled();
  });

  it('rejects a too-short new password without calling the API', () => {
    render(<PasswordChangeForm />);
    fillPasswordForm('old-password', 'short', 'short');
    fireEvent.click(screen.getByRole('button', { name: /change password/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/at least 8 characters/i);
    expect(mockChangePassword).not.toHaveBeenCalled();
  });

  it('surfaces an API error (wrong current password) as a destructive toast', async () => {
    mockChangePassword.mockResolvedValue({
      data: null,
      error: { message: 'Invalid password' },
    });
    render(<PasswordChangeForm />);
    fillPasswordForm('wrong', 'new-password-123', 'new-password-123');
    fireEvent.click(screen.getByRole('button', { name: /change password/i }));

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Password change failed', variant: 'destructive' })
      )
    );
  });
});

describe('TwoFactorSetup', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseSession.mockReturnValue({
      data: {
        user: { id: 'u1', email: 'a@b.com', twoFactorEnabled: false },
        session: { token: 'tok' },
      },
    });
    mockTwoFactorEnable.mockResolvedValue({
      data: {
        totpURI: 'otpauth://totp/Auto%20Author:a@b.com?secret=TESTSECRET',
        backupCodes: ['AAAA-1111', 'BBBB-2222'],
      },
      error: null,
    });
    mockVerifyTotp.mockResolvedValue({ data: {}, error: null });
    mockTwoFactorDisable.mockResolvedValue({ data: {}, error: null });
  });

  it('walks through enable: password → QR + backup codes → verify', async () => {
    render(<TwoFactorSetup />);
    expect(screen.getByText('Disabled')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /enable 2fa/i }));
    fireEvent.change(screen.getByLabelText('Confirm your password'), {
      target: { value: 'my-password' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() =>
      expect(mockTwoFactorEnable).toHaveBeenCalledWith({ password: 'my-password' })
    );
    expect(screen.getByTestId('two-factor-qr')).toBeInTheDocument();
    // Manual-entry fallback for apps that can't scan the QR code
    expect(screen.getByText('TESTSECRET')).toBeInTheDocument();
    expect(screen.getByText('AAAA-1111')).toBeInTheDocument();
    expect(screen.getByText('BBBB-2222')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Verification Code'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /verify & enable/i }));

    await waitFor(() =>
      expect(mockVerifyTotp).toHaveBeenCalledWith({ code: '123456' })
    );
    await waitFor(() => expect(screen.getByText('Enabled')).toBeInTheDocument());
  });

  it('shows a destructive toast when the enable password is wrong', async () => {
    mockTwoFactorEnable.mockResolvedValue({
      data: null,
      error: { message: 'Invalid password' },
    });
    render(<TwoFactorSetup />);
    fireEvent.click(screen.getByRole('button', { name: /enable 2fa/i }));
    fireEvent.change(screen.getByLabelText('Confirm your password'), {
      target: { value: 'bad' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() =>
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Could not start 2FA setup', variant: 'destructive' })
      )
    );
  });

  it('disables 2FA after password confirmation', async () => {
    mockUseSession.mockReturnValue({
      data: {
        user: { id: 'u1', email: 'a@b.com', twoFactorEnabled: true },
        session: { token: 'tok' },
      },
    });
    render(<TwoFactorSetup />);
    expect(screen.getByText('Enabled')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /disable 2fa/i }));
    fireEvent.change(screen.getByLabelText('Confirm your password'), {
      target: { value: 'my-password' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Disable 2FA' }));

    await waitFor(() =>
      expect(mockTwoFactorDisable).toHaveBeenCalledWith({ password: 'my-password' })
    );
    // Status flips locally even though the session flag is stale until refetch
    await waitFor(() => expect(screen.getByText('Disabled')).toBeInTheDocument());
  });
});

describe('ActiveSessionsList', () => {
  const sessions = [
    {
      token: 'tok',
      userAgent: 'Mozilla/5.0 Chrome/120',
      updatedAt: '2026-07-01T10:00:00Z',
    },
    {
      token: 'other-token',
      userAgent: 'Mozilla/5.0 iPhone Mobile Safari',
      updatedAt: '2026-06-30T09:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseSession.mockReturnValue({
      data: { user: { id: 'u1' }, session: { token: 'tok' } },
    });
    mockListSessions.mockResolvedValue({ data: sessions, error: null });
    mockRevokeSession.mockResolvedValue({ data: {}, error: null });
    mockRevokeOtherSessions.mockResolvedValue({ data: {}, error: null });
  });

  it('lists sessions, marking the current device without a revoke button', async () => {
    render(<ActiveSessionsList />);

    await waitFor(() => expect(screen.getByText('This device')).toBeInTheDocument());
    expect(screen.getByText('Mobile device')).toBeInTheDocument();
    // Only the other session is revocable
    expect(screen.getAllByRole('button', { name: /^revoke$/i })).toHaveLength(1);
  });

  it('revokes another session and removes it from the list', async () => {
    render(<ActiveSessionsList />);
    await waitFor(() => expect(screen.getByText('Mobile device')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }));

    await waitFor(() =>
      expect(mockRevokeSession).toHaveBeenCalledWith({ token: 'other-token' })
    );
    await waitFor(() =>
      expect(screen.queryByText('Mobile device')).not.toBeInTheDocument()
    );
  });

  it('signs out all other devices', async () => {
    render(<ActiveSessionsList />);
    await waitFor(() => expect(screen.getByText('Mobile device')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /sign out other devices/i }));

    await waitFor(() => expect(mockRevokeOtherSessions).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByText('Mobile device')).not.toBeInTheDocument()
    );
  });

  it('offers retry when the session list fails to load', async () => {
    mockListSessions.mockRejectedValueOnce(new Error('nope'));
    render(<ActiveSessionsList />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    await waitFor(() => expect(screen.getByText('This device')).toBeInTheDocument());
  });
});
