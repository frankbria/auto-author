# Issue #795: the backend verifies the session cookie's signature

*2026-10-12T01:35:38Z by Showboat 0.6.1*
<!-- showboat-id: 9bf48202-14a7-4f9d-a5f6-49294601aead -->

The backend took the part of the cookie before the dot and looked it up, ignoring the signature, so the bare session token was a working credential, and that token is readable by any script on the page from better-auth's own responses. This demo runs the branch: real better-auth on $WEB, the FastAPI backend on $API, and a throwaway local MongoDB database ($DB). `new_account` is a small curl wrapper defined for this demo. Nothing here touches staging. The library that signs the cookie, at the version the lockfile pins:

```bash
cd "$WT/frontend" && node -e "console.log(\"better-auth\", require(\"./node_modules/better-auth/package.json\").version, \"| better-call\", require(\"./node_modules/better-call/package.json\").version)"
```

```output
better-auth 1.7.7 | better-call 1.4.0
```

**Criterion: a real library-signed cookie validates; unsigned and forged cookies do not.** A member signs up and opens the emailed link, so the cookie jar holds a cookie that real better-auth signed. Its shape, and what the backend answers to it:

```bash
new_account member@example.com "$D/member"
COOKIE=$(awk "\$6==\"better-auth.session_token\"{print \$7}" "$D/member"); echo "$COOKIE" > "$D/cookie"
TOKEN=${COOKIE%%.*}
echo "cookie: ${#COOKIE} characters, of which the token is the first ${#TOKEN} and the rest is a url-encoded signature"
curl -s -o /dev/null -w "the cookie as better-auth set it: backend GET /users/me HTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$COOKIE" "$API/users/me"
```

```output
cookie: 81 characters, of which the token is the first 32 and the rest is a url-encoded signature
the cookie as better-auth set it: backend GET /users/me HTTP 200
```

The same request with the signature removed, replaced, or borrowed. The bare token is what `/api/auth/get-session` returns in its body, which a script on the page can read. A second member's cookie supplies a genuine signature for a different token.

```bash
COOKIE=$(cat "$D/cookie"); TOKEN=${COOKIE%%.*}
try() { curl -s -o /dev/null -w "$1: HTTP %{http_code}\n" -H "Cookie: better-auth.session_token=$2" "$API/users/me"; }
echo "get-session responses that carry the bare token in their body: $(curl -s -b "$D/member" "$WEB/api/auth/get-session" | grep -c "\"token\":\"$TOKEN\"")"
try "the bare token" "$TOKEN"
try "the token with a made-up signature" "$TOKEN.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA%3D"
new_account other@example.com "$D/other"
OTHER=$(awk "\$6==\"better-auth.session_token\"{print \$7}" "$D/other")
try "this token with another member's genuine signature" "$TOKEN.${OTHER#*.}"
try "the untouched cookie, again" "$COOKIE"
```

```output
get-session responses that carry the bare token in their body: 1
the bare token: HTTP 401
the token with a made-up signature: HTTP 401
this token with another member's genuine signature: HTTP 401
the untouched cookie, again: HTTP 200
```

**Criterion: a deployed environment accepts only the `__Secure-` cookie name.** A second backend runs the same code against the same database with `ENVIRONMENT=staging`. The genuine signed cookie is sent to it under each name, and to the development backend under each name.

```bash
COOKIE=$(cat "$D/cookie")
for env in "development http://localhost:8100" "staging http://localhost:8101"; do set -- $env
  for name in better-auth.session_token __Secure-better-auth.session_token; do
    curl -s -o /dev/null -w "$1 backend, cookie named $name: HTTP %{http_code}\n" -H "Cookie: $name=$COOKIE" "$2/api/v1/users/me"
  done
done
```

```output
development backend, cookie named better-auth.session_token: HTTP 200
development backend, cookie named __Secure-better-auth.session_token: HTTP 200
staging backend, cookie named better-auth.session_token: HTTP 401
staging backend, cookie named __Secure-better-auth.session_token: HTTP 200
```

**Tests.** The backend's own tests, which include two cookies signed by the real library with a fixed secret, the forged and unsigned forms, the constant-time comparison and the cookie-name rule:

```bash
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s795demo uv run pytest -p no:cacheprovider --no-cov -o addopts="" -v "tests/test_core/test_better_auth_session.py::TestGetSessionTokenFromCookies" 2>&1 | grep -E "PASSED|FAILED|ERROR" | sed "s/ *\[ *[0-9]*%\]//; s/.*TestGetSessionTokenFromCookies:://" | sed "s/\[.*\]/[...]/" | sort | uniq -c
```

```output
      2 test_a_cookie_signed_by_the_real_library_is_accepted[...] PASSED
      1 test_a_cookie_signed_with_another_secret_is_refused PASSED
      3 test_a_deployed_environment_accepts_only_the_secure_name[...] PASSED
      1 test_a_forged_secure_cookie_does_not_fall_back_to_the_other_name PASSED
      1 test_a_non_ascii_signature_is_refused_without_raising PASSED
      8 test_an_unsigned_or_forged_cookie_is_refused[...] PASSED
      1 test_no_cookie_returns_none PASSED
      1 test_secure_prefixed_cookie PASSED
      1 test_the_decoded_form_is_accepted_too PASSED
      1 test_the_signature_is_compared_in_constant_time PASSED
```

Not shown: staging itself. There the browser holds the `__Secure-` cookie, and whether the backend and the frontend share one `BETTER_AUTH_SECRET` is only proven by deploying: if they did not, every request would be refused and the post-deploy E2E run would fail.
