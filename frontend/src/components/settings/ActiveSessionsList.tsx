'use client';

import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { authClient, useSession } from '@/lib/auth-client';
import { toast } from '@/lib/toast';

interface SessionInfo {
  token: string;
  userAgent?: string | null;
  ipAddress?: string | null;
  createdAt?: string | Date;
  updatedAt?: string | Date;
}

function describeUserAgent(userAgent: string | null | undefined): string {
  if (!userAgent) return 'Unknown device';
  if (/mobile|android|iphone|ipad/i.test(userAgent)) return 'Mobile device';
  if (/firefox/i.test(userAgent)) return 'Firefox browser';
  if (/edg/i.test(userAgent)) return 'Edge browser';
  if (/chrome/i.test(userAgent)) return 'Chrome browser';
  if (/safari/i.test(userAgent)) return 'Safari browser';
  return 'Desktop browser';
}

function formatLastActive(value: string | Date | undefined): string {
  if (!value) return 'Unknown';
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString();
}

/**
 * Lists the user's active better-auth sessions with per-device revocation.
 * Uses better-auth's native session APIs — auth sessions are the source of
 * truth (the legacy backend /sessions store is not populated by logins).
 */
export default function ActiveSessionsList() {
  const { data: session } = useSession();
  const currentToken = session?.session?.token;

  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [revokingToken, setRevokingToken] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setLoadState('loading');
    try {
      const { data, error } = await authClient.listSessions();
      if (error) throw new Error(error.message || 'Failed to load sessions');
      setSessions((data ?? []) as SessionInfo[]);
      setLoadState('loaded');
    } catch {
      setLoadState('error');
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const revokeSession = async (token: string) => {
    setRevokingToken(token);
    try {
      const { error } = await authClient.revokeSession({ token });
      if (error) throw new Error(error.message || 'Failed to revoke session');
      setSessions((prev) => prev.filter((s) => s.token !== token));
      toast({ title: 'Session revoked' });
    } catch (err) {
      toast({
        title: 'Could not revoke session',
        description: err instanceof Error ? err.message : 'Try again.',
        variant: 'destructive',
      });
    } finally {
      setRevokingToken(null);
    }
  };

  const revokeOthers = async () => {
    setRevokingToken('__others__');
    try {
      const { error } = await authClient.revokeOtherSessions();
      if (error) throw new Error(error.message || 'Failed to revoke sessions');
      setSessions((prev) => prev.filter((s) => s.token === currentToken));
      toast({ title: 'Signed out of other devices' });
    } catch (err) {
      toast({
        title: 'Could not sign out other devices',
        description: err instanceof Error ? err.message : 'Try again.',
        variant: 'destructive',
      });
    } finally {
      setRevokingToken(null);
    }
  };

  const hasOtherSessions = sessions.some((s) => s.token !== currentToken);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Sessions</CardTitle>
        <CardDescription>Devices currently signed in to your account</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loadState === 'loading' && (
          <p role="status" className="text-sm text-muted-foreground">
            Loading sessions…
          </p>
        )}

        {loadState === 'error' && (
          <div role="alert" className="flex items-center justify-between text-sm text-destructive">
            <span>Couldn&apos;t load your sessions.</span>
            <Button variant="outline" size="sm" onClick={() => void loadSessions()}>
              Retry
            </Button>
          </div>
        )}

        {loadState === 'loaded' && (
          <>
            <ul className="space-y-3">
              {sessions.map((s, index) => {
                const isCurrent = s.token === currentToken;
                return (
                  <li key={s.token}>
                    {index > 0 && <Separator className="mb-3" />}
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium">
                          {describeUserAgent(s.userAgent)}
                          {isCurrent && (
                            <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary">
                              This device
                            </span>
                          )}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Last active: {formatLastActive(s.updatedAt ?? s.createdAt)}
                        </p>
                      </div>
                      {!isCurrent && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => void revokeSession(s.token)}
                          disabled={revokingToken !== null}
                        >
                          {revokingToken === s.token ? 'Revoking…' : 'Revoke'}
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            {hasOtherSessions && (
              <Button
                variant="outline"
                onClick={() => void revokeOthers()}
                disabled={revokingToken !== null}
              >
                {revokingToken === '__others__' ? 'Signing out…' : 'Sign out other devices'}
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
