# Issue #793: a password reset or a two-factor change ends other sessions

*2026-10-12T00:48:34Z by Showboat 0.6.1*
<!-- showboat-id: b39c7402-29a0-4bbb-be9d-17a9e2a8216d -->

A session someone else already held survived the password reset or the 2FA change meant to lock them out. This demo runs the branch: real better-auth on $WEB, the FastAPI backend on $API, and a throwaway local MongoDB database ($DB). `post`, `new_account`, `sign_in`, `state` and `totp` are small wrappers around curl and the one-time-code library, defined for this demo. Nothing here touches staging. The library version the server is running, which is the one the lockfile pins:

```bash
cd "$WT/frontend" && node -e "console.log(\"better-auth\", require(\"./node_modules/better-auth/package.json\").version)" && grep -A1 "\"node_modules/better-auth\": {" package-lock.json | tail -1 | tr -d " ,"
```

```output
better-auth 1.7.7
"version":"1.7.7"
```

**Criterion 1: after a reset, the old session is refused by get-session and by the backend.** One account is signed in twice, as two cookie jars: "phone" and "laptop". Both work.

```bash
new_account reset@example.com "$D/phone"
echo "laptop sign-in: HTTP $(sign_in reset@example.com "$DEMO_PW" "$D/laptop")"
state phone "$D/phone"; state laptop "$D/laptop"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"reset@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}))"
```

```output
laptop sign-in: HTTP 200
phone: get-session answers {"session":{, backend GET /users/me answers HTTP 200
laptop: get-session answers {"session":{, backend GET /users/me answers HTTP 200
sessions for this account: 2
```

The password is reset with the token from the emailed link (printed by the development server). Then each of the two sessions is tried again, and a sign-in with each password is checked.

```bash
post request-password-reset "{\"email\":\"reset@example.com\",\"redirectTo\":\"/auth/reset-password\"}" -o /dev/null; sleep 2
TOKEN=$(grep -o "reset-password/[A-Za-z0-9]*" "$FRONTEND_LOG" | tail -1 | cut -d/ -f2)
post reset-password "{\"newPassword\":\"$NEW_PW\",\"token\":\"$TOKEN\"}" -w " <- reset-password HTTP %{http_code}\n"
state phone "$D/phone"; state laptop "$D/laptop"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"reset@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}))"
echo "sign-in with the old password: HTTP $(sign_in reset@example.com "$DEMO_PW" "$D/scratch")"
echo "sign-in with the new password: HTTP $(sign_in reset@example.com "$NEW_PW" "$D/scratch")"
```

```output
{"status":true} <- reset-password HTTP 200
phone: get-session answers null, backend GET /users/me answers HTTP 401
laptop: get-session answers null, backend GET /users/me answers HTTP 401
sessions for this account: 0
sign-in with the old password: HTTP 401
sign-in with the new password: HTTP 200
```

**Criterion 2: after 2FA is enabled or disabled, the second session is deleted and the current one is kept.** A second account is signed in twice: in a real browser, and as a "laptop" cookie jar. In the browser, on Settings, Security, 2FA setup has been started with the account password and the page shows the secret. Before the change, the laptop session works:

```bash
state laptop "$D/laptop2"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"factor@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}), \"| twoFactorEnabled:\", u.twoFactorEnabled)"
```

```output
laptop: get-session answers {"session":{, backend GET /users/me answers HTTP 200
sessions for this account: 3 | twoFactorEnabled: false
```

The current code is computed from the secret on the page, typed in, the backup-codes box is ticked and "Verify & Enable" is pressed. Then: what the page shows, whether the browser is still signed in, and what the laptop session can do.

```bash
agent-browser eval "[...document.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => e.textContent.trim()).find(t => /^[A-Z2-7]{16,}$/.test(t))" | tr -d '"' > "$D/totp-secret"
agent-browser fill '#two-factor-code' "$(totp "$(cat "$D/totp-secret")")" >/dev/null
agent-browser eval "document.querySelector('[role=checkbox]').click()" >/dev/null
agent-browser eval "[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Verify & Enable').click()" >/dev/null
agent-browser wait 4000 >/dev/null
agent-browser eval "fetch('/api/auth/get-session', { credentials: 'include' }).then(r => r.json()).then(s => ({ pageShows2FA: [...document.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => e.textContent.trim()).find(t => t === 'Enabled' || t === 'Disabled'), browserSignedInAs: s && s.user.email }))"
state laptop "$D/laptop2"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"factor@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}), \"| twoFactorEnabled:\", u.twoFactorEnabled)"

```

```output
{
  "browserSignedInAs": "factor@example.com",
  "pageShows2FA": "Enabled"
}
laptop: get-session answers null, backend GET /users/me answers HTTP 401
sessions for this account: 1 | twoFactorEnabled: true
```

Three sessions existed before: the browser, the laptop, and the one the verification link created at sign-up. Only the browser's is left.

**Disabling.** A "tablet" signs in to the same account, now with the account password and a one-time code, and works.

```bash
post sign-in/email "{\"email\":\"factor@example.com\",\"password\":\"$DEMO_PW\"}" -c "$D/tablet" | cut -c1-25; echo
post two-factor/verify-totp "{\"code\":\"$(totp "$(cat "$D/totp-secret")")\"}" -b "$D/tablet" -c "$D/tablet" -o /dev/null -w "one-time code accepted: HTTP %{http_code}\n"
state tablet "$D/tablet"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"factor@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}))"
```

```output
{"twoFactorRedirect":true

one-time code accepted: HTTP 200
tablet: get-session answers {"session":{, backend GET /users/me answers HTTP 200
sessions for this account: 2
```

In the browser, "Disable 2FA" is pressed, the account password is entered and the change is confirmed. Then the same three checks.

```bash
press() { agent-browser eval "[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '$1').click()" >/dev/null; agent-browser wait 1500 >/dev/null; }
press 'Disable 2FA'
agent-browser fill '#two-factor-password' "$DEMO_PW" >/dev/null
press 'Disable 2FA'
agent-browser wait 2500 >/dev/null
agent-browser eval "fetch('/api/auth/get-session', { credentials: 'include' }).then(r => r.json()).then(s => ({ pageShows2FA: [...document.querySelectorAll('*')].filter(e => e.children.length === 0).map(e => e.textContent.trim()).find(t => t === 'Enabled' || t === 'Disabled'), browserSignedInAs: s && s.user.email }))"
state tablet "$D/tablet"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const u = db.user.findOne({email:\"factor@example.com\"}); print(\"sessions for this account:\", db.session.countDocuments({userId:u._id}), \"| twoFactorEnabled:\", u.twoFactorEnabled)"

```

```output
{
  "browserSignedInAs": "factor@example.com",
  "pageShows2FA": "Disabled"
}
tablet: get-session answers null, backend GET /users/me answers HTTP 401
sessions for this account: 1 | twoFactorEnabled: false
```

**Tests.** The named tests for this change:

```bash
cd "$WT/frontend" && npx jest src/lib/__tests__/auth-session-revocation.test.ts src/components/settings/__tests__/SecuritySettings.test.tsx -t "793|walks through enable|disables 2FA after" --verbose --reporters=default 2>&1 | grep -E "✓|✕" | sed "s/ ([0-9]* ms)//" | sort
```

```output
    ✓ disables 2FA after password confirmation
    ✓ does not cache sessions in a cookie
    ✓ leaves other sessions alone when the disable password is wrong (#793)
    ✓ leaves other sessions alone when the verification code is wrong (#793)
    ✓ says so when 2FA changed but the request never arrives and other devices stay signed in (#793)
    ✓ says so when 2FA changed but the server refuses and other devices stay signed in (#793)
    ✓ tells better-auth to revoke sessions when a password is reset
    ✓ walks through enable: password → QR + backup codes → verify
```

Not shown: a client that calls the two-factor endpoints directly and skips the page. The page is what ends the other sessions after a 2FA change, so such a client leaves them alive, and so does a page that is closed between the change and the follow-up request. For a revoked session get-session answers null with HTTP 200, not 401; the backend answers 401.
