'use client';

import ActiveSessionsList from '@/components/settings/ActiveSessionsList';
import PasswordChangeForm from '@/components/settings/PasswordChangeForm';
import TwoFactorSetup from '@/components/settings/TwoFactorSetup';

/**
 * Security tab: password change, TOTP two-factor authentication, and active
 * session management. All actions are self-contained (better-auth client) —
 * nothing here goes through the shared preferences Save button.
 */
export default function SecuritySettingsForm() {
  return (
    <div className="space-y-6">
      <PasswordChangeForm />
      <TwoFactorSetup />
      <ActiveSessionsList />
    </div>
  );
}
