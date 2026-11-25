# Issue #965: the account export holds the account's activity records

*2026-11-25T22:35:29Z by Showboat 0.6.1*
<!-- showboat-id: 61da00aa-0d2b-4d33-a94c-4308cd50768f -->

Backend from this branch on port 8965 (uvicorn, ENVIRONMENT=development) over the scratch Mongo database `aa_demo_965`; frontend from this branch (`next dev`) on port 3965. `$DEMO/bin/seed.py` drops that database and creates two accounts, Alice and Bob, with signed session cookies, then writes each one's activity through the app's own writers: a Stripe-webhook-style `user_update` audit row (actor `stripe:evt_<who>`, target the account) via `create_audit_log`, a usage counter via `increment_usage`, and a chapter `edit` access via `ChapterAccessService.log_access`. It also writes two cross-account rows: the one an admin erasure leaves (actor Alice, target Bob, `resource_type: user`, with an IP address and user-agent) and a chapter row of Alice's whose request-supplied target id happens to equal Bob's id. `$DEMO/bin/export.sh <who>` POSTs for a download token and GETs `/users/me/export` with that account's session, saving the file. Cookies and tokens are never printed.

```bash
uv run python -I $DEMO/bin/seed.py $DEMO/ids.json
```

```output
{'alice': '6b0763658d4db7b444c8197e', 'bob': '6b0763658d4db7b444c81983'}
```

## Each account downloads its export through the real route

```bash
$DEMO/bin/export.sh alice && $DEMO/bin/export.sh bob
```

```output
GET /users/me/export -> 200
GET /users/me/export -> 200
```

## (1) Alice's file: audit rows she wrote or that are about her, her chapter access and usage counters

Her Stripe row (matched by target), her chapter row (matched by actor; its target is the id she sent, which here equals Bob's), the erasure she performed as admin (the erased account shown only as `another account`), her own `account_export` row (written before the file, so it is in it), her chapter access, and her usage counters (the AI count and the export-token rate-limit counter, which share `usage_counters`).

```bash
python3 -I - $DEMO/alice.json $DEMO/ids.json <<"EOF"
import json, sys
d = json.load(open(sys.argv[1])); ids = json.load(open(sys.argv[2]))
name = {ids["alice"]["auth_id"]: "<alice>", ids["bob"]["auth_id"]: "<bob id>"}
for r in d["audit_logs"]:
    print("audit:", r["action"], "| actor:", name.get(r["actor_id"], r["actor_id"]), "| target:", name.get(r["target_id"], r["target_id"]), "|", r["resource_type"])
print("chapter_access_logs:", [(a["access_type"], a["metadata"]) for a in d["chapter_access_logs"]])
print("usage_counters:", [(u["_id"].replace(ids["alice"]["auth_id"], "<alice>"), u["count"]) for u in d["usage_counters"]])
EOF
```

```output
audit: user_update | actor: stripe:evt_alice | target: <alice> | user
audit: user_erase | actor: <alice> | target: another account | user
audit: batch_save_failed | actor: <alice> | target: <bob id> | chapter
audit: account_export | actor: <alice> | target: <alice> | user
chapter_access_logs: [('edit', {'chapter_title': "alice's chapter"})]
usage_counters: [('<alice>:day:2026-11-25', 1), ('<alice>:rl:POST /me/export/token:1795644000', 1)]
```

## (2) Bob's file: what someone else did to him, not who or from where; nothing of Alice's

The erasure row about him has its actor replaced by `another account` and no IP address, user-agent or request id. Alice's chapter row, whose target id equals Bob's id, is not in it. Alice's id, both of her IP addresses and the admin user-agent appear nowhere in it.

```bash
python3 -I - $DEMO/bob.json $DEMO/ids.json <<"EOF"
import json, sys
d = json.load(open(sys.argv[1])); ids = json.load(open(sys.argv[2])); raw = open(sys.argv[1]).read()
me = ids["bob"]["auth_id"]
for r in d["audit_logs"]:
    print("audit:", r["action"], "| actor:", "<bob>" if r["actor_id"] == me else r["actor_id"], "| details keys:", sorted(r["details"]))
for needle in (ids["alice"]["auth_id"], "203.0.113.7", "198.51.100.9", "AdminBrowser", "batch_save_failed"):
    print(needle.replace(ids["alice"]["auth_id"], "<alice id>"), "in Bob file:", needle in raw)
EOF
```

```output
audit: user_update | actor: stripe:evt_bob | details keys: ['updated_fields']
audit: user_erase | actor: another account | details keys: []
audit: account_export | actor: <bob> | details keys: ['ip_address', 'method', 'path', 'request_id', 'user_agent']
<alice id> in Bob file: False
203.0.113.7 in Bob file: False
198.51.100.9 in Bob file: False
AdminBrowser in Bob file: False
batch_save_failed in Bob file: False
```

## (3) Every activity row in each file is that account's

An audit row is when the account wrote it or it is an account-level row (user, billing, books) about the account; access and usage rows when their `user_id` is the account.

```bash
python3 -I - $DEMO/ids.json $DEMO/alice.json $DEMO/bob.json <<"EOF"
import json, sys
ids = json.load(open(sys.argv[1])); ACCOUNT = {"user", "billing", "books"}
for who, path in (("alice", sys.argv[2]), ("bob", sys.argv[3])):
    me = ids[who]["auth_id"]; d = json.load(open(path))
    ok = all(r["actor_id"] == me or (r["resource_type"] in ACCOUNT and r["target_id"] == me) for r in d["audit_logs"])
    ok &= all(r["user_id"] == me for r in d["chapter_access_logs"] + d["usage_counters"])
    print(who, "| rows:", {k: len(d[k]) for k in ("audit_logs", "chapter_access_logs", "usage_counters")}, "| every row the account s own:", ok)
EOF
```

```output
alice | rows: {'audit_logs': 4, 'chapter_access_logs': 1, 'usage_counters': 2} | every row the account s own: True
bob | rows: {'audit_logs': 3, 'chapter_access_logs': 1, 'usage_counters': 2} | every row the account s own: True
```

## (4) /privacy section 9 says what the download holds

The page served by `next dev` from this branch, section 9's paragraph as text.

```bash
curl -s localhost:3965/privacy | python3 -I -c "
import html, re, sys
t = re.sub(r\"<[^>]+>\", \" \", sys.stdin.read()); t = re.sub(r\"\\s+\", \" \", html.unescape(t))
start = t.index(\"You can download a copy\"); print(t[start:t.index(\"making one.\", start) + 11])
"
```

```output
You can download a copy of your profile, your books and the questions, answers and ratings in them as a JSON file (Download my data), delete your content and close your account directly from your profile page. The download also holds your account’s activity records: the security log of actions taken by or on your account (which can include the IP address and browser user-agent of your requests), the log of your chapter edits, status changes, exports and open tabs, and your usage counters (AI generations and request rate limits). Where someone else acted on your account, such as our support team, the record says what was done but not who or from where. It does not include uploaded image files (it lists their addresses) or payment records held by our payment processor. To get those, to have the account record we keep for 18 months (section 8) erased sooner, or for any other request, contact us using the details below. We do not charge for a request and will not treat you differently for making one.
```
