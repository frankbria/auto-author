# The frontend reports errors to Sentry without the reset token, the request body or what the user wrote (#809)

*2026-10-12T17:35:15Z by Showboat 0.6.1*
<!-- showboat-id: 469d171f-80a4-4756-bf74-40902393e6b2 -->

The frontend has shipped the Sentry SDK since #334 and no image has ever had an address to send to, so nothing has been sent. This demo builds the real frontend image from main and from this branch with a placeholder Sentry address on this machine, runs it, and reads what the SDK posts there when something fails. Nothing reaches Sentry. What a user would have typed is in typed.json, so each value can be looked for in everything posted.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo809/env.sh; echo "main:   $(git -C $MAIN log --oneline -1 | cut -c1-7)"; echo "branch: $(git -C $WT rev-parse --abbrev-ref HEAD)"; echo "Sentry address built in: $DSN"; cat $D/typed.json
```

```output
main:   22b7d20
branch: feature/issue-809-frontend-sentry
Sentry address built in: http://publickey@localhost:9809/1
{
 "token": "RESET-TOKEN-VALUE",
 "sign_in_value": "SIGN-IN-VALUE",
 "cookie": "SESSION-COOKIE-VALUE",
 "body": "MANUSCRIPT: the chapter the server sent back",
 "title": "TITLE: The Lighthouse",
 "console": "CONSOLE: a draft the page logged"
}```
```

The build. Both images are built with the four build arguments the workflow passes. The address is already in the static files of both: the build arguments were wired by #779, after this issue was written. And the page's CSP allows the browser to post there, with no Sentry setting given at run time, because the address is built in.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo809/env.sh; image main; image branch; for t in main branch; do echo "$t: files under .next/static that name the Sentry host: $(docker run --rm aa-demo-809-$t sh -c 'grep -rl localhost:9809 .next/static | wc -l')"; done; echo "branch, CSP of a page: $(csp branch)"
```

```output
main image built
branch image built
main: files under .next/static that name the Sentry host: 1
branch: files under .next/static that name the Sentry host: 1
branch, CSP of a page: connect-src 'self' http://localhost:8109 http://localhost:9809
```

The browser, before. A real Chromium opens the reset-password page with a token in its address, the page logs a line and makes a request, the user clicks an element titled like a book card, and an error is thrown with the message shape the API client uses (the status followed by the response body). From main's image the one report carries all four values.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo809/browser-probe.sh main show
```

```output
error reports the browser posted: 1
  FOUND   the reset token (page address, request made)
  FOUND   the response body in the error message
  FOUND   what the page logged to the console
  FOUND   the title of the element clicked
what the report still says:
  error:   Error: Failed to save chapter content: 500 {"detail":"MANUSCRIPT: the chapter the server sent back"}
  page:    http://localhost:3109/auth/reset-password?token=RESET-TOKEN-VALUE
  crumb:   navigation | {"from": "/auth/reset-password?token=RESET-TOKEN-VALUE", "to": "/auth/reset-password?token=RESET-TOKEN-VALUE"}
  crumb:   fetch | {"method": "GET", "url": "http://localhost:3109/auth/sign-in?_rsc=EvxfPg76gC__plC3", "status_code": 200}
  crumb:   fetch | {"method": "GET", "url": "http://localhost:3109/auth/sign-in?_rsc=2A_u_KXhTfuopk5j", "status_code": 200}
  crumb:   console | CONSOLE: a draft the page logged
  crumb:   fetch | {"method": "GET", "url": "/api/health?search=RESET-TOKEN-VALUE", "status_code": 200}
  crumb:   ui.click | button#probe[title="TITLE: The Lighthouse"]
```

The browser, after. One report still arrives, which also shows the CSP lets it through. It names the error, its status and the page, and none of the four values.

```bash
bash /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo809/browser-probe.sh branch show
```

```output
error reports the browser posted: 1
  absent  the reset token (page address, request made)
  absent  the response body in the error message
  absent  what the page logged to the console
  absent  the title of the element clicked
what the report still says:
  error:   Error: Failed to save chapter content: 500
  page:    http://localhost:3109/auth/reset-password
  crumb:   navigation | {"from": "/auth/reset-password", "to": "/auth/reset-password"}
  crumb:   fetch | {"method": "GET", "url": "http://localhost:3109/auth/sign-in", "status_code": 200}
  crumb:   fetch | {"method": "GET", "url": "http://localhost:3109/auth/sign-in", "status_code": 200}
  crumb:   fetch | {"method": "GET", "url": "/api/health", "status_code": 200}
  crumb:   ui.click | button#probe
```

The server. The same SDK runs in the Next server and attaches the request to a report. This runs the server-side SDK the frontend uses, with a list for a transport, and sends it a sign-in request that fails. Without the scrubbers the report holds the password from the request body, the session cookie, the token and the response body. With this branch's scrubbers it holds none.

```bash
source /tmp/claude-1000/-home-frankbria-projects-auto-author/37b63b79-18ca-4958-9013-d3974f437927/scratchpad/demo809/env.sh; cd $D; echo 'without the scrubbers (main):'; node server-probe.cjs $WT/frontend 2>/dev/null; echo 'with them (branch):'; node server-probe.cjs $WT/frontend scrub 2>/dev/null | sed -E 's/127\.0\.0\.1:[0-9]+/127.0.0.1:PORT/'
```

```output
without the scrubbers (main):
error reports sent: 1
  FOUND   the password in the request body
  FOUND   the session cookie
  FOUND   the token in the query string and the referer
  FOUND   the response body in the error message
with them (branch):
error reports sent: 1
  absent  the password in the request body
  absent  the session cookie
  absent  the token in the query string and the referer
  absent  the response body in the error message
  what is left of the request: {"headers":"accept,accept-encoding,accept-language,baggage,connection,content-length,content-type,host,referer,sec-fetch-mode,sentry-trace,user-agent","method":"POST","url":"http://127.0.0.1:PORT/api/auth/sign-in/email"}
  the error: Failed to save chapter content: 500
```

Staging today. Its image is built without a Sentry address (the staging environment has no NEXT_PUBLIC_SENTRY_DSN variable), so its CSP names no Sentry host and the SDK stays off. Setting that variable is what turns this on.

```bash
curl -sI -m 15 https://dev.autoauthor.app/auth/sign-in | grep -i '^content-security-policy' | sed -E 's/.*(connect-src[^;]*).*/\1/'
```

```output
connect-src 'self' https://api.dev.autoauthor.app
```

The same behaviour as unit tests.

```bash
cd /home/frankbria/projects/worktrees/issue-809-frontend-sentry/frontend && npx jest src/lib/__tests__/sentry-scrub.test.ts src/lib/__tests__/csp.test.ts 2>&1 | grep -E '^Tests:' | sed -E 's/ +/ /g'
```

```output
Tests: 33 passed, 33 total
```
