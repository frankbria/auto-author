"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Clock, Shield } from "lucide-react";
import useSession from "@/hooks/useSession";

export interface SessionWarningProps {
  /** Show warning when session will expire in this many seconds (default: 300 = 5 minutes) */
  expiryWarningThreshold?: number;
  /** Auto-refresh on user activity (default: true) */
  autoRefreshOnActivity?: boolean;
}

export function SessionWarning({
  expiryWarningThreshold = 300,
  autoRefreshOnActivity = true,
}: SessionWarningProps) {
  const [showExpiryWarning, setShowExpiryWarning] = useState(false);
  const [showIdleWarning, setShowIdleWarning] = useState(false);
  const [showSuspiciousWarning, setShowSuspiciousWarning] = useState(false);

  const { sessionStatus, refreshSession, logout } = useSession({
    onSessionExpiring: () => setShowExpiryWarning(true),
    onSessionIdle: () => setShowIdleWarning(true),
    onSuspiciousActivity: () => setShowSuspiciousWarning(true),
  });

  // Handle user activity to refresh session
  useEffect(() => {
    if (!autoRefreshOnActivity) return;

    const handleActivity = () => {
      if (sessionStatus?.idle_warning) {
        refreshSession().catch(console.error);
        setShowIdleWarning(false);
      }
    };

    // Listen for user activity
    window.addEventListener("mousemove", handleActivity);
    window.addEventListener("keydown", handleActivity);
    window.addEventListener("click", handleActivity);

    return () => {
      window.removeEventListener("mousemove", handleActivity);
      window.removeEventListener("keydown", handleActivity);
      window.removeEventListener("click", handleActivity);
    };
  }, [autoRefreshOnActivity, sessionStatus, refreshSession]);

  // Format time remaining
  const formatTimeRemaining = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  const handleRefresh = async () => {
    try {
      await refreshSession();
      setShowExpiryWarning(false);
      setShowIdleWarning(false);
    } catch (error) {
      console.error("Failed to refresh session:", error);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      // Redirect to login or home page
      window.location.href = "/";
    } catch (error) {
      console.error("Failed to logout:", error);
    }
  };

  // Don't render anything if no warnings
  if (!showExpiryWarning && !showIdleWarning && !showSuspiciousWarning) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {/* Session Expiry Warning */}
      {showExpiryWarning && sessionStatus?.time_until_expiry_seconds !== null && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 shadow-lg max-w-md">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900 mb-1">
                Session Expiring Soon
              </h3>
              <p className="text-sm text-amber-700 mb-3">
                Your session will expire in{" "}
                <strong>
                  {formatTimeRemaining(sessionStatus.time_until_expiry_seconds)}
                </strong>
                . Click "Stay Signed In" to continue your session.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleRefresh}
                  className="px-3 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 transition-colors"
                >
                  Stay Signed In
                </button>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 bg-white text-amber-900 text-sm rounded border border-amber-300 hover:bg-amber-50 transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
            <button
              onClick={() => setShowExpiryWarning(false)}
              className="text-amber-400 hover:text-amber-600 transition-colors"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Idle Warning */}
      {showIdleWarning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 shadow-lg max-w-md">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-blue-900 mb-1">
                Session Idle
              </h3>
              <p className="text-sm text-blue-700 mb-3">
                You've been inactive for a while. Move your mouse or press a key to
                keep your session active.
              </p>
              <button
                onClick={handleRefresh}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
              >
                I'm Still Here
              </button>
            </div>
            <button
              onClick={() => setShowIdleWarning(false)}
              className="text-blue-400 hover:text-blue-600 transition-colors"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Suspicious Activity Warning */}
      {showSuspiciousWarning && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg max-w-md">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-red-900 mb-1">
                Suspicious Activity Detected
              </h3>
              <p className="text-sm text-red-700 mb-3">
                We detected unusual activity on your account. For your security,
                please verify your identity or logout from all sessions.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleRefresh}
                  className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                >
                  Verify Identity
                </button>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 bg-white text-red-900 text-sm rounded border border-red-300 hover:bg-red-50 transition-colors"
                >
                  Logout All Sessions
                </button>
              </div>
            </div>
            <button
              onClick={() => setShowSuspiciousWarning(false)}
              className="text-red-400 hover:text-red-600 transition-colors"
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default SessionWarning;
