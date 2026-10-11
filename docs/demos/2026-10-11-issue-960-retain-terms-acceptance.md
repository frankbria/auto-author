# Issue #960: a deactivated account keeps its Terms acceptance record

*2026-10-11T20:54:38Z by Showboat 0.6.1*
<!-- showboat-id: 98bef203-c3b4-4247-a211-cf27967eb693 -->

The owner decided on 2026-10-11 that the Terms acceptance record (#789) is kept with the 18-month record of a deactivated account (#954). This demo runs against the branch: real better-auth on $WEB, the FastAPI backend on $API, and a throwaway local MongoDB database ($DB). Nothing here touches staging.

**Criterion 1: the owner's answer is recorded on the issue.**

```bash
gh issue view 960 --repo frankbria/auto-author --json comments -q ".comments[0].body"
```

```output
Owner decision (2026-10-11): **keep it**. The Terms acceptance record (`terms_version`, `terms_accepted_at`) joins the fields a deactivated account keeps for 18 months. Implementation follows in a PR.
```

**Criterion 2: both fields are in the retained record.** Sign up through real better-auth, make the first backend request so the users doc is created, and read what sign-up recorded.

```bash
curl -s -o /dev/null -w "sign-up HTTP %{http_code}\n" -c "$D/jarA" -X POST "$WEB/api/auth/sign-up/email" -H "Origin: $WEB" -H "Content-Type: application/json" -d "{\"email\":\"keeps-terms@example.com\",\"password\":\"$DEMO_PW\",\"name\":\"Keeps Terms\"}"
curl -s -o /dev/null -w "GET /users/me HTTP %{http_code}\n" -b "$D/jarA" "$API/users/me"
mongosh --quiet "$DATABASE_URL/$DB" --eval "printjson(db.users.findOne({email:\"keeps-terms@example.com\"},{_id:0,email:1,terms_version:1,terms_accepted_at:1}))"
```

```output
sign-up HTTP 200
GET /users/me HTTP 200
{
  email: 'keeps-terms@example.com',
  terms_version: '2026-10-10',
  terms_accepted_at: ISODate('2026-10-11T20:54:46.866Z')
}
```

Delete the account through the API and read the record that is left.

```bash
curl -s -o /dev/null -w "DELETE /users/me HTTP %{http_code}\n" -b "$D/jarA" -X DELETE "$API/users/me"
mongosh --quiet "$DATABASE_URL/$DB" --eval "const d=db.users.findOne({\"retained.email\":\"keeps-terms@example.com\"}); printjson({top_level_keys:Object.keys(d).sort(), retained:d.retained, kept_for_days:(d.purge_at-d.deleted_at)/86400000})"
```

```output
DELETE /users/me HTTP 200
{
  top_level_keys: [
    '_id',
    'auth_id',
    'deleted_at',
    'purge_at',
    'retained'
  ],
  retained: {
    email: 'keeps-terms@example.com',
    first_name: 'Keeps',
    last_name: 'Terms',
    created_at: ISODate('2026-10-11T20:54:47.024Z'),
    plan: 'free',
    terms_version: '2026-10-10',
    terms_accepted_at: ISODate('2026-10-11T20:54:46.866Z')
  },
  kept_for_days: 548
}
```

The retained record carries `terms_version` and `terms_accepted_at`, the same values sign-up recorded.

**An account with no Terms record keeps no empty entry.** A second account signs up, and its better-auth row has the two fields removed before the first backend request, which is what an account created before #789 looks like. The backend then writes null for both.

```bash
curl -s -o /dev/null -w "sign-up HTTP %{http_code}\n" -c "$D/jarB" -X POST "$WEB/api/auth/sign-up/email" -H "Origin: $WEB" -H "Content-Type: application/json" -d "{\"email\":\"before-789@example.com\",\"password\":\"$DEMO_PW\",\"name\":\"Before Record\"}"
mongosh --quiet "$DATABASE_URL/$DB" --eval "print(\"better-auth rows changed:\", db.user.updateOne({email:\"before-789@example.com\"},{\$unset:{termsVersion:1,termsAcceptedAt:1}}).modifiedCount)"
curl -s -o /dev/null -w "GET /users/me HTTP %{http_code}\n" -b "$D/jarB" "$API/users/me"
mongosh --quiet "$DATABASE_URL/$DB" --eval "printjson(db.users.findOne({email:\"before-789@example.com\"},{_id:0,terms_version:1,terms_accepted_at:1}))"
curl -s -o /dev/null -w "DELETE /users/me HTTP %{http_code}\n" -b "$D/jarB" -X DELETE "$API/users/me"
mongosh --quiet "$DATABASE_URL/$DB" --eval "printjson({retained_keys:Object.keys(db.users.findOne({\"retained.email\":\"before-789@example.com\"}).retained).sort()})"
```

```output
sign-up HTTP 200
better-auth rows changed: 1
GET /users/me HTTP 200
{
  terms_version: null,
  terms_accepted_at: null
}
DELETE /users/me HTTP 200
{
  retained_keys: [
    'created_at',
    'email',
    'first_name',
    'last_name',
    'plan'
  ]
}
```

**Criterion 3: `/privacy` section 8 lists the record.** The sentence as the browser renders it:

```bash
agent-browser eval "[...document.querySelectorAll('h2')].find(h => /Data Retention/.test(h.textContent)).closest('section').querySelectorAll('p')[1].textContent.replace(/\s+/g,' ').split('. ').slice(1,2).join()"

```

```output
"We keep a record of it for 18 months so that we can answer a complaint or a payment dispute: an internal account identifier, your name, your email address, the dates the account was created and deleted, which version of our Terms of Service you accepted and when, your plan, the reference that links the account to our payment processor, and the reference, plan and status of any subscription that was cancelled when you deleted the account"
```

**Criterion 4: the deactivation tests assert the fields.** The named tests, against a private test database:

```bash
cd "$WT/backend" && ENVIRONMENT=test TEST_MONGO_URI=mongodb://localhost:27017/auto-author-test-s960 uv run pytest -p no:cacheprovider --no-cov -o addopts="" -v tests/test_db/test_user.py::TestDeleteUser::test_soft_delete_keeps_only_the_account_and_billing_record tests/test_api/test_routes/test_terms_acceptance.py::test_deactivation_keeps_the_terms_acceptance_record tests/test_api/test_routes/test_account_deletion_real_session.py::test_deactivation_keeps_the_account_record_until_an_admin_erases_it 2>&1 | grep -E "PASSED|FAILED|ERROR" | sed "s/ *\[.*//" | sort
cd "$WT/frontend" && npx jest src/app/privacy -t "keeps its record for 18 months" --verbose --reporters=default 2>&1 | grep -E "✓|✕" | sed "s/ ([0-9]* ms)//" | sort
```

```output
tests/test_api/test_routes/test_account_deletion_real_session.py::test_deactivation_keeps_the_account_record_until_an_admin_erases_it PASSED
tests/test_api/test_routes/test_terms_acceptance.py::test_deactivation_keeps_the_terms_acceptance_record PASSED
tests/test_db/test_user.py::TestDeleteUser::test_soft_delete_keeps_only_the_account_and_billing_record PASSED
    ✓ says deletion deactivates the account and keeps its record for 18 months (#954)
```

**Criterion 5: counsel sees the sentence with #791.** Recorded as a comment on #791 when this merges. Not shown here: an account deactivated between #789 and this change has already lost its record, and nothing restores it.
