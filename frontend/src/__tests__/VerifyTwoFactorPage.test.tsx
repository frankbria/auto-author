import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/navigation';

import VerifyTwoFactorPage from '@/app/auth/verify-2fa/page';
import { authClient } from '@/lib/auth-client';

jest.mock('@/lib/toast', () => ({
  toast: Object.assign(jest.fn(), {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
  }),
}));

const mockVerifyTotp = authClient.twoFactor.verifyTotp as jest.Mock;
const mockVerifyBackupCode = authClient.twoFactor.verifyBackupCode as jest.Mock;

describe('VerifyTwoFactorPage', () => {
  const mockPush = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
    mockVerifyTotp.mockResolvedValue({ data: {}, error: null });
    mockVerifyBackupCode.mockResolvedValue({ data: {}, error: null });
  });

  it('auto-submits a complete 6-digit code and continues to the dashboard', async () => {
    render(<VerifyTwoFactorPage />);

    fireEvent.change(screen.getByLabelText('Verification Code'), {
      target: { value: '123456' },
    });

    await waitFor(() =>
      expect(mockVerifyTotp).toHaveBeenCalledWith({ code: '123456', trustDevice: false })
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/dashboard'));
  });

  it('passes trustDevice when the checkbox is ticked', async () => {
    render(<VerifyTwoFactorPage />);

    fireEvent.click(screen.getByLabelText(/trust this device/i));
    fireEvent.change(screen.getByLabelText('Verification Code'), {
      target: { value: '654321' },
    });

    await waitFor(() =>
      expect(mockVerifyTotp).toHaveBeenCalledWith({ code: '654321', trustDevice: true })
    );
  });

  it('clears the code and stays put when verification fails', async () => {
    mockVerifyTotp.mockResolvedValue({ data: null, error: { message: 'bad code' } });
    render(<VerifyTwoFactorPage />);

    fireEvent.change(screen.getByLabelText('Verification Code'), {
      target: { value: '000000' },
    });

    await waitFor(() => expect(mockVerifyTotp).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByLabelText('Verification Code')).toHaveValue('')
    );
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('verifies a backup code via the alternate flow', async () => {
    render(<VerifyTwoFactorPage />);

    fireEvent.click(screen.getByRole('button', { name: /use a backup code instead/i }));
    fireEvent.change(screen.getByLabelText('Backup Code'), {
      target: { value: 'AAAA-1111' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^verify$/i }));

    await waitFor(() =>
      expect(mockVerifyBackupCode).toHaveBeenCalledWith({
        code: 'AAAA-1111',
        trustDevice: false,
      })
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/dashboard'));
  });
});
