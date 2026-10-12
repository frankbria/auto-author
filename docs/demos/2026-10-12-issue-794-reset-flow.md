# Issue #794: the password reset flow is hardened

*2026-10-12T01:06:01Z by Showboat 0.6.1*
<!-- showboat-id: 72c2a738-d22b-4dd5-8397-32e5630c5a92 -->

Four defects in the reset flow: a weak password was refused only by the browser, the forgot-password page could say whether an account exists, the address was written to the log on every reset, and the reset email put the user-chosen name into its HTML unescaped. This demo runs the branch: real better-auth on $WEB, the FastAPI backend on $API, and a throwaway local MongoDB database ($DB). `post`, `new_account` and `sign_in` are small curl wrappers defined for this demo. Nothing here touches staging. The library version the server is running, which is the one the lockfile pins:

```bash
cd "$WT/frontend" && node -e "console.log(\"better-auth\", require(\"./node_modules/better-auth/package.json\").version)" && grep -A1 "\"node_modules/better-auth\": {" package-lock.json | tail -1 | tr -d " ,"
```

```output
better-auth 1.7.7
"version":"1.7.7"
```

**Criterion: a server hook rejects a password like `aaaaaaaa` with 400.** Requests sent straight to the server, with no page in between. First sign-up: the weak password is refused and no account is created; a password that meets the rule is accepted.

```bash
post sign-up/email "{\"email\":\"weak@example.com\",\"password\":\"aaaaaaaa\",\"name\":\"Weak\"}" -w " <- HTTP %{http_code}\n"
mongosh --quiet "$DATABASE_URL/$DB" --eval "print(\"accounts created for weak@example.com:\", db.user.countDocuments({email:\"weak@example.com\"}))"
new_account member@example.com "$D/member"
echo "sign-up with a password that meets the rule, then the emailed link: backend GET /users/me HTTP $(curl -s -o /dev/null -w "%{http_code}" -b "$D/member" "$API/users/me")"
```

```output
{"message":"Password must be at least 8 characters and include an uppercase letter, a lowercase letter and a number."} <- HTTP 400
accounts created for weak@example.com: 0
sign-up with a password that meets the rule, then the emailed link: backend GET /users/me HTTP 200
```

The same rule on the two other ways to set a password: a reset with the emailed token, and a change by the signed-in member. In each, the weak password is refused and the strong one accepted.

```bash
post request-password-reset "{\"email\":\"member@example.com\",\"redirectTo\":\"/auth/reset-password\"}" -o /dev/null; sleep 2
TOKEN=$(grep -o "reset-password/[A-Za-z0-9]*" "$FRONTEND_LOG" | tail -1 | cut -d/ -f2)
post reset-password "{\"newPassword\":\"aaaaaaaa\",\"token\":\"$TOKEN\"}" -o /dev/null -w "reset to aaaaaaaa: HTTP %{http_code}\n"
post reset-password "{\"newPassword\":\"$NEW_PW\",\"token\":\"$TOKEN\"}" -o /dev/null -w "reset to a password that meets the rule: HTTP %{http_code}\n"
echo "sign-in with the new password: HTTP $(sign_in member@example.com "$NEW_PW" "$D/member")"
post change-password "{\"currentPassword\":\"$NEW_PW\",\"newPassword\":\"aaaaaaaa\"}" -b "$D/member" -o /dev/null -w "change to aaaaaaaa: HTTP %{http_code}\n"
post change-password "{\"currentPassword\":\"$NEW_PW\",\"newPassword\":\"$DEMO_PW\"}" -b "$D/member" -o /dev/null -w "change to a password that meets the rule: HTTP %{http_code}\n"
echo "sign-in with a wrong password is still a 401, not a 400: HTTP $(sign_in member@example.com aaaaaaaa "$D/scratch")"
```

```output
reset to aaaaaaaa: HTTP 400
reset to a password that meets the rule: HTTP 200
sign-in with the new password: HTTP 200
change to aaaaaaaa: HTTP 400
change to a password that meets the rule: HTTP 200
sign-in with a wrong password is still a 401, not a 400: HTTP 401
```

**Criterion: the forgot-password response is generic.** In a real browser the form is submitted twice: for an address that has an account, and for one that has none. The page text is compared with the address removed, and the server's own two answers are compared as well.

```bash
ask() {
  agent-browser open "$WEB/auth/forgot-password" >/dev/null 2>&1; agent-browser wait 1500 >/dev/null
  agent-browser fill '#email' "$1" >/dev/null
  agent-browser eval "[...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Send Reset Link').click()" >/dev/null
  agent-browser wait 3000 >/dev/null
  agent-browser eval "document.querySelector('[data-slot=card]').textContent.replace(/\s+/g, ' ').trim()" | tr -d '"'
}
ask member@example.com | tee "$D/page-known"
ask nobody@example.com | tee "$D/page-unknown"
[ "$(sed 's/member@example.com//' "$D/page-known")" = "$(sed 's/nobody@example.com//' "$D/page-unknown")" ] && echo "the two pages are identical apart from the address typed"
post request-password-reset '{"email":"member@example.com","redirectTo":"/auth/reset-password"}' > "$D/api-known"
post request-password-reset '{"email":"nobody@example.com","redirectTo":"/auth/reset-password"}' > "$D/api-unknown"
cmp -s "$D/api-known" "$D/api-unknown" && echo "the two server responses are byte-identical: $(cat "$D/api-known")"

```

```output
Check Your EmailIf an account exists for member@example.com, we have sent it a password reset link.The link will expire in 1 hour. If you don't see the email, check your spam folder.Send another linkBack to sign in
Check Your EmailIf an account exists for nobody@example.com, we have sent it a password reset link.The link will expire in 1 hour. If you don't see the email, check your spam folder.Send another linkBack to sign in
the two pages are identical apart from the address typed
the two server responses are byte-identical: {"status":true,"message":"If this email exists in our system, check your email for the reset link"}
```

**Criterion: no email address appears in logs.** Three resets were requested for member@example.com above. The line the server writes for each, and the backend's line for creating the member's record. (The development server also prints each whole email, address included, because no provider is configured here; that dump does not exist outside development.)

```bash
grep "Password reset email sent" "$FRONTEND_LOG" | sed "s/^ *//" | sort | uniq -c
echo "reset lines that name an address: $(grep -c "Password reset email sent to" "$FRONTEND_LOG")"
grep -o "Successfully created backend user record[^\"]*" "$BACKEND_LOG" | sed "s/auth_id: [0-9a-f]*/auth_id: <id>/" | sort -u
echo "backend log lines containing member@example.com: $(grep -c "member@example.com" "$BACKEND_LOG")"
```

```output
      3 Password reset email sent
reset lines that name an address: 0
Successfully created backend user record (auth_id: <id>)
backend log lines containing member@example.com: 0
```

**Criterion: a name containing `<a href=x>` renders escaped in the email.** The HTML part only exists in the request to the email provider, so it is shown by the test that captures that request: the name `<a href=x>Click</a> & "friends"` must arrive as `&lt;a href=x&gt;Click&lt;/a&gt; &amp; &quot;friends&quot;`, and the plain-text part must keep it as typed. That test, with the others for this change:

```bash
cd "$WT/frontend" && npx jest src/lib/__tests__/auth-reset-flow.test.ts src/lib/__tests__/email.test.ts src/__tests__/ForgotPassword.test.tsx -t "794|escapes the name|server enforces|without logging|shows error message on API failure|shows success" --verbose --reporters=default 2>&1 | grep -E "✓|✕" | sed "s/ ([0-9]* ms)//" | sort
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s794demo uv run pytest -p no:cacheprovider --no-cov -o addopts="" -v tests/test_api/test_routes/test_email_verification.py -k log 2>&1 | grep -E "PASSED|FAILED|ERROR" | sed "s/ *\[ *[0-9]*%\]//"
```

```output
    ✓ accepts a password that meets every requirement
    ✓ does not echo a thrown error's text (#794)
    ✓ does not judge the password of an existing account at sign-in
    ✓ escapes the name in the HTML part and leaves the text part as typed
    ✓ keeps the address out of the log when the email is not sent
    ✓ keeps the address out of the log when the email is sent
    ✓ rejects /change-password when the password is missing or not a string
    ✓ rejects /reset-password when the password is missing or not a string
    ✓ rejects /sign-up/email when the password is missing or not a string
    ✓ rejects a weak password sent to /change-password with a 400
    ✓ rejects a weak password sent to /reset-password with a 400
    ✓ rejects a weak password sent to /sign-up/email with a 400
    ✓ runs before every better-auth request
    ✓ shows error message on API failure
    ✓ submits form with valid email and shows success
tests/test_api/test_routes/test_email_verification.py::test_creating_the_record_does_not_log_the_email_address PASSED
```

Not shown: the reset email arriving in a real mailbox with the name escaped (no provider is configured here). An account that already has a weak password keeps it until it is next changed: sign-in does not apply the rule.
