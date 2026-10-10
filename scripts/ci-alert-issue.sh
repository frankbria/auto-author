#!/bin/sh
# Open/update/close ONE labelled GitHub issue for a CI signal (#776). Reusable:
# any workflow sets ALERT_LABEL + ALERT_TITLE and calls `failure` or `recovery`
# (P1.29 reuses it). Dedupe key is the label, so a retitled issue is still found.
# Needs GH_TOKEN with `issues: write` and GH_REPO (owner/name).
# DRY_RUN=1 runs the real read-only lookup but only prints the writes.
set -eu
mode="${1:?usage: ci-alert-issue.sh failure|recovery}"
: "${GH_REPO:?}" "${ALERT_LABEL:?}" "${ALERT_TITLE:?}" "${RUN_URL:?}"

w() { if [ -n "${DRY_RUN:-}" ]; then echo "DRY-RUN gh $*"; else gh "$@"; fi; }

# REST list by label. A just-created issue can take a second or two to show up here,
# so two calls back to back can both create; scheduled runs are hours apart, so that
# only matters for manual demos (sleep between calls).
open=$(gh api "repos/$GH_REPO/issues?labels=$ALERT_LABEL&state=open&per_page=1" --jq '.[0].number // empty')

case "$mode" in
failure)
  if [ -n "$open" ]; then
    w issue comment "$open" --body "Still failing: $RUN_URL"
  else
    w label create "$ALERT_LABEL" --force --color B60205 --description "Automated CI alert (one open issue at a time)"
    w issue create --title "$ALERT_TITLE" --label "$ALERT_LABEL" --body "Failing run: $RUN_URL

This issue is opened and closed automatically by the workflow. It gets a comment while the failure persists and is closed on the next green run."
  fi ;;
recovery)
  if [ -n "$open" ]; then
    w issue comment "$open" --body "Recovered on a green run: $RUN_URL"
    w issue close "$open"
  fi ;;
*) echo "unknown mode: $mode" >&2; exit 2 ;;
esac
