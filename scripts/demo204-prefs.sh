#!/usr/bin/env bash
# Print the stored preferences subdocument + bio for the demo user (issue #204 demo).
# Same database the running backend uses (app.core.config: local Mongo, DB auto_author).
set -euo pipefail
mongosh "mongodb://localhost:27017/auto_author" --quiet --eval '
const u = db.users.findOne({email: "demo204@example.com"}, {preferences: 1, bio: 1, _id: 0});
print(JSON.stringify(u, null, 2));
'
