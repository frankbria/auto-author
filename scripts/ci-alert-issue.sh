#!/bin/sh
# Open/update/close ONE labelled GitHub issue for a CI signal (#776). Reusable:
# any workflow sets ALERT_LABEL + ALERT_TITLE and calls `failure` or `recovery`
# (P1.29 reuses it). Dedupe key is the label, so a retitled issue is still found.
# Needs GH_TOKEN with `issues: write` and GH_REPO (owner/name).
# DRY_RUN=1 runs the real read-only lookup but only prints the writes.
# ALERT_QUIET_HOURS=N (#811): a repeat failure comments only when the open issue
# has had no activity for N hours, so a probe that runs every few minutes does
# not add a comment every time. Unset or 0: every failing run comments.
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
    if [ "${ALERT_QUIET_HOURS:-0}" -gt 0 ]; then
      updated=$(gh api "repos/$GH_REPO/issues/$open" --jq .updated_at)
      cutoff=$(date -u -d "$ALERT_QUIET_HOURS hours ago" +%Y-%m-%dT%H:%M:%SZ)
      # Both are UTC ISO timestamps, so the later one sorts last.
      if [ "$(printf '%s\n%s\n' "$updated" "$cutoff" | sort | tail -1)" = "$updated" ]; then
        echo "Still failing; #$open last changed at $updated, inside the $ALERT_QUIET_HOURS-hour quiet period. No comment."
        exit 0
      fi
    fi
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
