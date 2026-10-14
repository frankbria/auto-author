# Issue #848: PATCH changes what it is sent and nothing else

*2026-10-14T21:18:33Z by Showboat 0.6.1*
<!-- showboat-id: 1f3a32c4-27a9-4d3a-82a1-36be70f7b425 -->

Each checkout's backend is started for real (bypass auth, a scratch local database). A user is seeded with preferences {theme: dark, email_notifications: false, marketing_emails: false}; false is not email_notifications' default. Then one preference is PATCHed, a book's subtitle is cleared by a PATCH that sends no title, and a PATCH tries to null the title. `$DEMO/run.sh` prints what MongoDB holds after each step.

main:

```bash
"$DEMO/run.sh" "$MAIN/backend" 8147 demo848-main
```

```output
stored preferences: {"theme":"dark","email_notifications":false,"marketing_emails":false}
PATCH preferences {theme: system}                          -> 200
stored preferences: {"theme":"system"}
PATCH book {subtitle: null}, no title -> 422
PATCH book {title: null}              -> 200
stored book: {"title":"Kept","subtitle":"Going"}
```

this branch:

```bash
"$DEMO/run.sh" "$PWD/backend" 8148 demo848-branch
```

```output
stored preferences: {"theme":"dark","email_notifications":false,"marketing_emails":false}
PATCH preferences {theme: system}                          -> 200
stored preferences: {"theme":"system","email_notifications":false,"marketing_emails":false}
PATCH book {subtitle: null}, no title -> 200
PATCH book {title: null}              -> 422
stored book: {"title":"Kept","subtitle":null}
```

On main the partial PATCH left only the theme stored, so email_notifications went back to its default of true. The subtitle PATCH was refused for want of a title. A null title was accepted with 200 and silently dropped. On this branch the untouched preferences stay, the subtitle clears without resending the title, and a null title is a 422.
