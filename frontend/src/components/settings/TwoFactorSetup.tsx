'use client';

import { useState } from 'react';
import QRCode from 'react-qr-code';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authClient, useSession } from '@/lib/auth-client';
import { toast } from '@/lib/toast';

type SetupStep = 'idle' | 'password' | 'verify' | 'codes';
type FlowMode = 'enable' | 'disable' | 'regenerate';

/**
 * TOTP two-factor authentication setup backed by better-auth's twoFactor
 * plugin. Enabling requires the account password, then a scanned QR code /
 * entered secret is confirmed with a 6-digit code before 2FA becomes active.
 */
export default function TwoFactorSetup() {
  const { data: session } = useSession();
  // The twoFactor plugin adds this flag to the user; the base session type doesn't know it.
  const twoFactorEnabled = Boolean(
    (session?.user as { twoFactorEnabled?: boolean } | undefined)?.twoFactorEnabled
  );

  const [step, setStep] = useState<SetupStep>('idle');
  const [mode, setMode] = useState<FlowMode>('enable');
  const [password, setPassword] = useState('');
  const [totpUri, setTotpUri] = useState<string | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verifyCode, setVerifyCode] = useState('');
  // Forced acknowledgment: enable can't complete until the user confirms
  // they saved their backup codes (they're never shown again).
  const [codesAcknowledged, setCodesAcknowledged] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Local override after a successful enable/disable — the session's
  // twoFactorEnabled flag is stale until the next refetch.
  const [localEnabledOverride, setLocalEnabledOverride] = useState<boolean | null>(null);

  const enabled = localEnabledOverride ?? twoFactorEnabled;
  // Manual-entry fallback for authenticator apps that can't scan the QR code.
  const totpSecret = (() => {
    if (!totpUri) return null;
    try {
      return new URL(totpUri).searchParams.get('secret');
    } catch {
      return null;
    }
  })();

  const startFlow = (nextMode: FlowMode) => {
    setMode(nextMode);
    setPassword('');
    setStep('password');
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      if (mode === 'enable') {
        const { data, error } = await authClient.twoFactor.enable({ password });
        if (error || !data) {
          toast({
            title: 'Could not start 2FA setup',
            description: error?.message || 'Check your password and try again.',
            variant: 'destructive',
          });
          return;
        }
        setTotpUri(data.totpURI);
        setBackupCodes(data.backupCodes ?? []);
        setVerifyCode('');
        setCodesAcknowledged(false);
        setStep('verify');
      } else if (mode === 'regenerate') {
        const { data, error } = await authClient.twoFactor.generateBackupCodes({ password });
        if (error || !data) {
          toast({
            title: 'Could not regenerate backup codes',
            description: error?.message || 'Check your password and try again.',
            variant: 'destructive',
          });
          return;
        }
        setBackupCodes(data.backupCodes ?? []);
        setCodesAcknowledged(false);
        setStep('codes');
      } else {
        const { error } = await authClient.twoFactor.disable({ password });
        if (error) {
          toast({
            title: 'Could not disable 2FA',
            description: error.message || 'Check your password and try again.',
            variant: 'destructive',
          });
          return;
        }
        setLocalEnabledOverride(false);
        setStep('idle');
        toast({ title: 'Two-factor authentication disabled' });
      }
    } finally {
      setIsSubmitting(false);
      setPassword('');
    }
  };

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Enter in the code input submits the form directly, bypassing the
    // disabled button — the handler is the acknowledgment's source of truth.
    if (!codesAcknowledged) return;
    setIsSubmitting(true);
    try {
      const { error } = await authClient.twoFactor.verifyTotp({ code: verifyCode });
      if (error) {
        toast({
          title: 'Invalid code',
          description: 'The code did not match. Check your authenticator app and try again.',
          variant: 'destructive',
        });
        return;
      }
      setLocalEnabledOverride(true);
      setStep('idle');
      setTotpUri(null);
      setBackupCodes([]);
      toast({
        title: 'Two-factor authentication enabled',
        description: 'Store your backup codes somewhere safe.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyBackupCodes = async () => {
    try {
      await navigator.clipboard.writeText(backupCodes.join('\n'));
      toast({ title: 'Backup codes copied' });
    } catch {
      toast({
        title: 'Copy failed',
        description: 'Select and copy the codes manually.',
        variant: 'destructive',
      });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Two-Factor Authentication</CardTitle>
        <CardDescription>
          Require a code from your authenticator app when signing in
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 'idle' && (
          <div className="flex items-center justify-between">
            <p className="text-sm">
              Status:{' '}
              <span className={enabled ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}>
                {enabled ? 'Enabled' : 'Disabled'}
              </span>
            </p>
            {enabled ? (
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => startFlow('regenerate')}>
                  Regenerate backup codes
                </Button>
                <Button variant="outline" onClick={() => startFlow('disable')}>
                  Disable 2FA
                </Button>
              </div>
            ) : (
              <Button onClick={() => startFlow('enable')}>Enable 2FA</Button>
            )}
          </div>
        )}

        {step === 'password' && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="two-factor-password">Confirm your password</Label>
              <Input
                id="two-factor-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting
                  ? 'Please wait…'
                  : mode === 'enable'
                    ? 'Continue'
                    : mode === 'regenerate'
                      ? 'Generate new codes'
                      : 'Disable 2FA'}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setStep('idle')}>
                Cancel
              </Button>
            </div>
          </form>
        )}

        {step === 'verify' && totpUri && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Scan this QR code with your authenticator app, then enter the 6-digit code to
              finish setup.
            </p>
            <div className="rounded-md bg-white p-4 w-fit" data-testid="two-factor-qr">
              <QRCode value={totpUri} size={160} />
            </div>
            {totpSecret && (
              <p className="text-sm text-muted-foreground">
                Can&apos;t scan? Enter this key manually:{' '}
                <code className="select-all rounded bg-muted px-1.5 py-0.5 font-mono text-foreground">
                  {totpSecret}
                </code>
              </p>
            )}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Backup Codes</Label>
                <Button type="button" variant="outline" size="sm" onClick={copyBackupCodes}>
                  Copy codes
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Each code can be used once if you lose access to your authenticator.
              </p>
              <p className="text-sm font-medium text-amber-600 dark:text-amber-500">
                These codes won&apos;t be shown again after setup — save them somewhere safe now.
              </p>
              <ul className="grid grid-cols-2 gap-1 rounded-md border p-3 font-mono text-sm">
                {backupCodes.map((code) => (
                  <li key={code}>{code}</li>
                ))}
              </ul>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="backup-codes-ack"
                  checked={codesAcknowledged}
                  onCheckedChange={(checked) => setCodesAcknowledged(checked === true)}
                />
                <Label htmlFor="backup-codes-ack" className="text-sm font-normal">
                  I&apos;ve saved my backup codes
                </Label>
              </div>
            </div>
            <form onSubmit={handleVerifySubmit} className="space-y-2">
              <Label htmlFor="two-factor-code">Verification Code</Label>
              <Input
                id="two-factor-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                required
              />
              <div className="flex gap-2">
                <Button
                  type="submit"
                  disabled={isSubmitting || verifyCode.length !== 6 || !codesAcknowledged}
                >
                  {isSubmitting ? 'Verifying…' : 'Verify & Enable'}
                </Button>
                <Button type="button" variant="ghost" onClick={() => setStep('idle')}>
                  Cancel
                </Button>
              </div>
            </form>
          </div>
        )}

        {step === 'codes' && (
          <div className="space-y-4">
            <p className="text-sm font-medium text-amber-600 dark:text-amber-500">
              Your old backup codes no longer work. Save these new codes now — they won&apos;t
              be shown again.
            </p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Backup Codes</Label>
                <Button type="button" variant="outline" size="sm" onClick={copyBackupCodes}>
                  Copy codes
                </Button>
              </div>
              <ul className="grid grid-cols-2 gap-1 rounded-md border p-3 font-mono text-sm">
                {backupCodes.map((code) => (
                  <li key={code}>{code}</li>
                ))}
              </ul>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="regenerated-codes-ack"
                  checked={codesAcknowledged}
                  onCheckedChange={(checked) => setCodesAcknowledged(checked === true)}
                />
                <Label htmlFor="regenerated-codes-ack" className="text-sm font-normal">
                  I&apos;ve saved my backup codes
                </Label>
              </div>
            </div>
            <Button
              type="button"
              disabled={!codesAcknowledged}
              onClick={() => {
                setBackupCodes([]);
                setStep('idle');
              }}
            >
              Done
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
