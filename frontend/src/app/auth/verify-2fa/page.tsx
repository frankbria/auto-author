'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authClient } from '@/lib/auth-client';
import { toast } from '@/lib/toast';

const TOTP_LENGTH = 6;

/**
 * Second-factor verification during sign-in. Users land here via the
 * twoFactorClient onTwoFactorRedirect handler; a successful code completes
 * the session and continues to the dashboard.
 */
export default function VerifyTwoFactorPage() {
  const router = useRouter();
  const [code, setCode] = useState('');
  const [trustDevice, setTrustDevice] = useState(false);
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  // Auto-submit fires once per typed code; retyping after an error re-arms it.
  const autoSubmittedRef = useRef(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, [useBackupCode]);

  const resetForRetry = () => {
    setCode('');
    autoSubmittedRef.current = false;
    inputRef.current?.focus();
  };

  const submitCode = async (submittedCode: string) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      const result = useBackupCode
        ? await authClient.twoFactor.verifyBackupCode({ code: submittedCode, trustDevice })
        : await authClient.twoFactor.verifyTotp({ code: submittedCode, trustDevice });
      if (result.error) {
        toast({
          title: 'Verification failed',
          description: useBackupCode
            ? 'That backup code is not valid.'
            : 'That code did not match. Codes rotate every 30 seconds — try the current one.',
          variant: 'destructive',
        });
        resetForRetry();
        return;
      }
      router.push('/dashboard');
    } catch {
      // Network/transport failure (the client throws instead of returning error)
      toast({
        title: 'Verification failed',
        description: 'Something went wrong. Check your connection and try again.',
        variant: 'destructive',
      });
      resetForRetry();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCodeChange = (value: string) => {
    const next = useBackupCode ? value : value.replace(/\D/g, '').slice(0, TOTP_LENGTH);
    setCode(next);
    // Auto-submit when a full TOTP code is typed (not for free-form backup codes).
    if (!useBackupCode && next.length === TOTP_LENGTH && !autoSubmittedRef.current) {
      autoSubmittedRef.current = true;
      void submitCode(next);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length === 0) return;
    void submitCode(code);
  };

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Two-Factor Verification</CardTitle>
          <CardDescription>
            {useBackupCode
              ? 'Enter one of your single-use backup codes'
              : 'Enter the 6-digit code from your authenticator app'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="verify-code">
                {useBackupCode ? 'Backup Code' : 'Verification Code'}
              </Label>
              <Input
                id="verify-code"
                ref={inputRef}
                inputMode={useBackupCode ? 'text' : 'numeric'}
                autoComplete="one-time-code"
                maxLength={useBackupCode ? 20 : TOTP_LENGTH}
                value={code}
                onChange={(e) => handleCodeChange(e.target.value)}
                disabled={isSubmitting}
                className="text-center text-lg tracking-widest"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="trust-device"
                checked={trustDevice}
                onCheckedChange={(checked) => setTrustDevice(checked === true)}
              />
              <Label htmlFor="trust-device" className="text-sm font-normal">
                Trust this device for 30 days
              </Label>
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting || code.length === 0}>
              {isSubmitting ? 'Verifying…' : 'Verify'}
            </Button>
            <button
              type="button"
              className="w-full text-sm text-muted-foreground underline-offset-4 hover:underline"
              onClick={() => {
                setUseBackupCode((prev) => !prev);
                setCode('');
                autoSubmittedRef.current = false;
              }}
            >
              {useBackupCode ? 'Use authenticator code instead' : 'Use a backup code instead'}
            </button>
          </form>
          <details className="mt-4 text-sm text-muted-foreground">
            <summary className="cursor-pointer underline-offset-4 hover:underline">
              Lost access to your authenticator and backup codes?
            </summary>
            <p className="mt-2">
              We can verify your identity and reset two-factor authentication manually. Email{' '}
              <a href="mailto:support@autoauthor.com" className="underline underline-offset-4">
                support@autoauthor.com
              </a>{' '}
              from the email address on your account and we&apos;ll help you regain access.
            </p>
          </details>
        </CardContent>
      </Card>
    </div>
  );
}
