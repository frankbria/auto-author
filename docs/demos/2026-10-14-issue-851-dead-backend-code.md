# Issue #851: dead and Clerk-era backend code is gone

*2026-10-14T22:59:21Z by Showboat 0.6.1*
<!-- showboat-id: 0ffe6f0f-9e77-461f-90de-35a969a082f3 -->

`$DEMO/run.sh` starts a checkout's backend for real (bypass auth, a scratch local database) and calls the two routes this issue removes, plus PATCH /users/me, which stays. Then it counts the removed symbols still named anywhere in that checkout's backend code, tests and config (`git grep -w`, Markdown excluded), and checks for the seed script under `backend/app/`, the directory the Dockerfile copies into the image.

main:

```bash
"$DEMO/run.sh" "$MAIN" 8147 demo851-main
```

```output
PUT  /users/test-auth-id       -> 200
POST /webhooks/better-auth     -> 200
PATCH /users/me (still there)  -> 200
removed symbols left in backend (code, tests, config): 51
seed script in the image's app/ : yes
```

this branch:

```bash
"$DEMO/run.sh" "$PWD" 8148 demo851-branch
```

```output
PUT  /users/test-auth-id       -> 405
POST /webhooks/better-auth     -> 404
PATCH /users/me (still there)  -> 200
removed symbols left in backend (code, tests, config): 0
seed script in the image's app/ : no
```

DELETE /users/{auth_id} stays: since #954 it is how support erases a deactivated account early (docs/api-profile-endpoints.md), a decision made after the review that listed it.
