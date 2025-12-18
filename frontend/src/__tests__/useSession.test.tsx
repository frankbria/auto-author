/**
 * Tests for useSession hook
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useSession, SessionStatus } from "@/hooks/useSession";
import { useSession as useAuthSession } from "@/lib/auth-client";

// Mock better-auth's useSession hook
jest.mock("@/lib/auth-client", () => ({
  useSession: jest.fn(),
  authClient: {
    signIn: { email: jest.fn() },
    signUp: { email: jest.fn() },
    signOut: jest.fn(),
  },
}));

// Mock fetch
global.fetch = jest.fn();

const mockGetToken = jest.fn();
const mockSessionStatus: SessionStatus = {
  session_id: "sess_test123",
  is_active: true,
  is_suspicious: false,
  created_at: "2025-01-01T00:00:00Z",
  last_activity: "2025-01-01T00:30:00Z",
  expires_at: "2025-01-01T12:00:00Z",
  idle_seconds: 0,
  idle_warning: false,
  time_until_expiry_seconds: 3600,
  request_count: 42,
  device_type: "desktop",
  browser: "Chrome",
};

describe("useSession", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthSession as jest.Mock).mockReturnValue({
      data: {
        user: {
          id: "test-user-123",
          email: "test@example.com",
          name: "Test User",
        },
        session: {
          token: "test-token",
          id: "session-123",
        },
      },
      isPending: false,
      error: null,
    });
    mockGetToken.mockResolvedValue("test-token");
  });

  it("should fetch session status on mount", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessionStatus,
    });

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.sessionStatus).toEqual(mockSessionStatus);
    });

    expect(global.fetch).toHaveBeenCalledWith("/api/v1/sessions/current", {
      headers: {
        Authorization: "Bearer test-token",
      },
    });
  });

  it("should handle session not found (404)", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.sessionStatus).toBeNull();
    });
  });

  it("should refresh session successfully", async () => {
    // Initial fetch
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessionStatus,
    });

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.sessionStatus).toEqual(mockSessionStatus);
    });

    // Refresh session
    const refreshedExpiry = "2025-01-02T00:00:00Z";
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ expires_at: refreshedExpiry }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockSessionStatus, expires_at: refreshedExpiry }),
      });

    await act(async () => {
      await result.current.refreshSession();
    });

    expect(global.fetch).toHaveBeenCalledWith("/api/v1/sessions/refresh", {
      method: "POST",
      headers: {
        Authorization: "Bearer test-token",
      },
    });
  });

  it("should logout successfully", async () => {
    // Initial fetch
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessionStatus,
    });

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.sessionStatus).toEqual(mockSessionStatus);
    });

    // Logout
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: "Logged out successfully" }),
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(global.fetch).toHaveBeenCalledWith("/api/v1/sessions/logout", {
      method: "POST",
      headers: {
        Authorization: "Bearer test-token",
      },
    });

    expect(result.current.sessionStatus).toBeNull();
  });

  it("should logout all sessions", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessionStatus,
    });

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.sessionStatus).toEqual(mockSessionStatus);
    });

    // Logout all sessions
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sessions_ended: 3, current_session_kept: true }),
    });

    await act(async () => {
      await result.current.logoutAll(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/v1/sessions/logout-all?keep_current=true",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer test-token",
        },
      }
    );
  });

  it("should call onSessionExpiring callback when session is expiring", async () => {
    const onSessionExpiring = jest.fn();

    const expiringSessionStatus = {
      ...mockSessionStatus,
      time_until_expiry_seconds: 240, // 4 minutes - less than 5 minute threshold
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => expiringSessionStatus,
    });

    renderHook(() => useSession({ onSessionExpiring }));

    await waitFor(() => {
      expect(onSessionExpiring).toHaveBeenCalled();
    });
  });

  it("should call onSessionIdle callback when session is idle", async () => {
    const onSessionIdle = jest.fn();

    const idleSessionStatus = {
      ...mockSessionStatus,
      idle_warning: true,
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => idleSessionStatus,
    });

    renderHook(() => useSession({ onSessionIdle }));

    await waitFor(() => {
      expect(onSessionIdle).toHaveBeenCalled();
    });
  });

  it("should call onSuspiciousActivity callback when session is suspicious", async () => {
    const onSuspiciousActivity = jest.fn();

    const suspiciousSessionStatus = {
      ...mockSessionStatus,
      is_suspicious: true,
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => suspiciousSessionStatus,
    });

    renderHook(() => useSession({ onSuspiciousActivity }));

    await waitFor(() => {
      expect(onSuspiciousActivity).toHaveBeenCalled();
    });
  });

  it("should not fetch status when user is not signed in", async () => {
    (useAuthSession as jest.Mock).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
    });

    renderHook(() => useSession());

    // Wait a bit to ensure no fetch is made
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("should handle fetch errors gracefully", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
      expect(result.current.error?.message).toBe("Network error");
    });
  });

  it("should auto-refresh session when expiry is near", async () => {
    const sessionNearExpiry = {
      ...mockSessionStatus,
      time_until_expiry_seconds: 500, // 8.3 minutes - less than 10 minute refresh threshold
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => sessionNearExpiry,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ expires_at: "2025-01-02T00:00:00Z" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockSessionStatus, expires_at: "2025-01-02T00:00:00Z" }),
      });

    renderHook(() => useSession({ autoRefresh: true }));

    await waitFor(() => {
      // Should have called refresh endpoint
      expect(global.fetch).toHaveBeenCalledWith("/api/v1/sessions/refresh", expect.any(Object));
    });
  });
});
