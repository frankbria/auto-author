"use client";

import { useSession as useBetterAuthSession } from "@/lib/auth-client";
import { useState, useEffect, useCallback, useRef } from "react";

export interface SessionStatus {
  session_id: string;
  is_active: boolean;
  is_suspicious: boolean;
  created_at: string;
  last_activity: string;
  expires_at: string | null;
  idle_seconds: number;
  idle_warning: boolean;
  time_until_expiry_seconds: number | null;
  request_count: number;
  device_type: string | null;
  browser: string | null;
}

export interface UseSessionOptions {
  /** Enable automatic session refresh before expiry (default: true) */
  autoRefresh?: boolean;
  /** Interval for checking session status in ms (default: 60000 = 1 minute) */
  statusCheckInterval?: number;
  /** Callback when session is about to expire */
  onSessionExpiring?: () => void;
  /** Callback when session becomes idle */
  onSessionIdle?: () => void;
  /** Callback when session is flagged as suspicious */
  onSuspiciousActivity?: () => void;
}

export function useSession(options: UseSessionOptions = {}) {
  const {
    autoRefresh = true,
    statusCheckInterval = 60000, // 1 minute
    onSessionExpiring,
    onSessionIdle,
    onSuspiciousActivity,
  } = options;

  const { data: session, isPending } = useBetterAuthSession();
  const [sessionStatus, setSessionStatus] = useState<SessionStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Track if callbacks have been called to avoid duplicates
  const callbacksCalledRef = useRef({
    expiring: false,
    idle: false,
    suspicious: false,
  });

  /**
   * Fetch current session status from backend
   */
  const fetchSessionStatus = useCallback(async () => {
    if (!session) {
      return;
    }

    try {
      const token = session.session?.token;
      if (!token) return;

      const response = await fetch("/api/v1/sessions/current", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const status: SessionStatus = await response.json();
        setSessionStatus(status);
        setError(null);

        // Check for callbacks
        if (
          status.time_until_expiry_seconds !== null &&
          status.time_until_expiry_seconds < 300
        ) {
          // Less than 5 minutes until expiry
          if (!callbacksCalledRef.current.expiring && onSessionExpiring) {
            callbacksCalledRef.current.expiring = true;
            onSessionExpiring();
          }
        } else {
          callbacksCalledRef.current.expiring = false;
        }

        if (status.idle_warning && !callbacksCalledRef.current.idle && onSessionIdle) {
          callbacksCalledRef.current.idle = true;
          onSessionIdle();
        } else if (!status.idle_warning) {
          callbacksCalledRef.current.idle = false;
        }

        if (
          status.is_suspicious &&
          !callbacksCalledRef.current.suspicious &&
          onSuspiciousActivity
        ) {
          callbacksCalledRef.current.suspicious = true;
          onSuspiciousActivity();
        }
      } else if (response.status === 404) {
        // No active session
        setSessionStatus(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }, [session, onSessionExpiring, onSessionIdle, onSuspiciousActivity]);

  /**
   * Refresh the current session to extend its expiry
   */
  const refreshSession = useCallback(async () => {
    if (!session) {
      throw new Error("User is not signed in");
    }

    setLoading(true);
    setError(null);

    try {
      const token = session.session?.token;
      if (!token) {
        throw new Error("No authentication token");
      }

      const response = await fetch("/api/v1/sessions/refresh", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to refresh session: ${response.statusText}`);
      }

      const data = await response.json();

      // Re-fetch session status
      await fetchSessionStatus();

      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [session, fetchSessionStatus]);

  /**
   * Logout from the current session
   */
  const logout = useCallback(async () => {
    if (!session) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = session.session?.token;
      if (!token) return;

      await fetch("/api/v1/sessions/logout", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setSessionStatus(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [session]);

  /**
   * Logout from all sessions (except current if keepCurrent is true)
   */
  const logoutAll = useCallback(
    async (keepCurrent: boolean = true) => {
      if (!session) {
        throw new Error("User is not signed in");
      }

      setLoading(true);
      setError(null);

      try {
        const token = session.session?.token;
        if (!token) {
          throw new Error("No authentication token");
        }

        const response = await fetch(
          `/api/v1/sessions/logout-all?keep_current=${keepCurrent}`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(
            `Failed to logout all sessions: ${response.statusText}`
          );
        }

        if (!keepCurrent) {
          setSessionStatus(null);
        }

        return await response.json();
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [session]
  );

  // Fetch session status on mount and at regular intervals
  useEffect(() => {
    if (!session) {
      setSessionStatus(null);
      return;
    }

    // Initial fetch
    fetchSessionStatus();

    // Set up periodic status check
    const interval = setInterval(fetchSessionStatus, statusCheckInterval);

    return () => clearInterval(interval);
  }, [session, fetchSessionStatus, statusCheckInterval]);

  // Auto-refresh session before expiry
  useEffect(() => {
    if (
      !autoRefresh ||
      !sessionStatus ||
      sessionStatus.time_until_expiry_seconds === null
    ) {
      return;
    }

    // Refresh when 10 minutes remaining
    const refreshThreshold = 600; // 10 minutes in seconds

    if (
      sessionStatus.time_until_expiry_seconds < refreshThreshold &&
      sessionStatus.time_until_expiry_seconds > 0
    ) {
      refreshSession().catch((err) => {
        console.error("Auto-refresh failed:", err);
      });
    }
  }, [autoRefresh, sessionStatus, refreshSession]);

  return {
    sessionStatus,
    loading,
    error,
    refreshSession,
    logout,
    logoutAll,
    fetchSessionStatus,
  };
}

export default useSession;
