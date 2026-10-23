"use client";

import { useEffect, useState } from "react";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";

// better-auth allows 3 sends per 60s per IP on /send-verification-email
// (getDefaultSpecialRules, rate limiting on in production); this keeps a user
// from spending them all in one burst of clicks.
const COOLDOWN_MS = 60_000;

/** Sends another verification link to an address the page already knows (#969). */
export function ResendVerificationButton({
  email,
  callbackURL,
}: {
  email: string;
  callbackURL: string;
}) {
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [now, setNow] = useState(0);

  useEffect(() => {
    if (!cooldownUntil) return;
    const id = setInterval(() => {
      const t = Date.now();
      setNow(t);
      if (t >= cooldownUntil) clearInterval(id);
    }, 1000);
    return () => clearInterval(id);
  }, [cooldownUntil]);

  const secondsLeft = Math.max(0, Math.ceil((cooldownUntil - now) / 1000));
  const blocked = sending || secondsLeft > 0;

  function startCooldown() {
    const t = Date.now();
    setNow(t);
    setCooldownUntil(t + COOLDOWN_MS);
  }

  async function resend() {
    if (blocked) return;
    setSending(true);
    setMessage("");
    try {
      const { error } = await authClient.sendVerificationEmail({ email, callbackURL });
      if (!error) {
        setMessage(`We sent a new link to ${email}.`);
        startCooldown();
      } else if (error.status === 429) {
        setMessage("Too many requests. Wait a minute, then try again.");
        startCooldown();
      } else {
        setMessage("We could not send a new link. Please try again.");
      }
    } catch {
      setMessage("Connection error. Please check your internet and try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="space-y-2">
      {/* aria-disabled, not disabled: the button keeps keyboard focus while it
          waits, and is not dimmed, so the countdown in its label stays legible. */}
      <Button
        type="button"
        variant="outline"
        className="w-full"
        busy={sending}
        disabled={false}
        aria-disabled={blocked}
        onClick={resend}
      >
        {sending
          ? "Sending..."
          : secondsLeft > 0
            ? `Resend verification email (${secondsLeft}s)`
            : "Resend verification email"}
      </Button>
      <p role="status" className="text-sm text-muted-foreground">
        {message}
      </p>
    </div>
  );
}
