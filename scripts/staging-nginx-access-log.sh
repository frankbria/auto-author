#!/usr/bin/env bash
# Give the dev.autoauthor.app nginx vhost on the staging box its own access log
# (#1223), and check that a request reached it.
#
# Usage (on the box, normally piped over ssh by staging-nginx-access-log.yml):
#   staging-nginx-access-log.sh dry-run          report what apply would change
#   staging-nginx-access-log.sh apply            back up, edit, nginx -t, reload
#   staging-nginx-access-log.sh verify <marker>  the log holds a line with <marker>
#
# Why: twice on 2026-10-23 the post-deploy E2E timed out loading the sign-in
# page, and nobody could tell whether the runner's requests reached the box,
# because the vhost names no access_log and the default log had no lines for it.
#
# The box is shared with other apps, so the edit is as narrow as it can be:
# - exactly one enabled config file may name the site, or nothing is touched;
# - one line, `access_log <file>;`, goes after each `server_name` line that
#   names the site (not api.dev.autoauthor.app), in that file only;
# - a file that already has any access_log line is left for a human, since an
#   `access_log off;` in the same block would silently cancel the new one;
# - the file is backed up outside every directory nginx includes, `nginx -t`
#   must pass before the reload, and a failed test puts the backup back.
#
# The log goes in /var/log/nginx, which the stock logrotate rule
# (/var/log/nginx/*.log) already rotates.
#
# Overridable for scripts/test_staging_nginx_access_log.py: NGINX_DIR, SITE,
# LOG_FILE, BACKUP_DIR, NGINX (the nginx command), NO_SUDO=1.
set -euo pipefail

main() {
  local mode=${1:-}
  case "$mode" in
    dry-run|apply|verify) ;;
    *) echo "usage: $0 dry-run|apply|verify <marker>" >&2; return 2 ;;
  esac

  NGINX_DIR=${NGINX_DIR:-/etc/nginx}
  SITE=${SITE:-dev.autoauthor.app}
  LOG_FILE=${LOG_FILE:-/var/log/nginx/$SITE.access.log}
  BACKUP_DIR=${BACKUP_DIR:-$NGINX_DIR/auto-author-backups}
  NGINX=${NGINX:-nginx}

  if [ "$mode" = verify ]; then
    verify "${2:-}"
    return
  fi

  run true || { echo "::error::this account can't run commands as root without a password (sudo -n)"; return 1; }

  local target
  target=$(find_vhost) || return 1
  echo "vhost file: $target"
  echo "--- server_name / access_log / error_log lines in it ---"
  run grep -nE '^[[:space:]]*(server_name|access_log|error_log)[[:space:]]' "$target" || true

  if run grep -Eq '^[[:space:]]*access_log[[:space:]]' "$target"; then
    if run grep -Eq "^[[:space:]]*access_log[[:space:]]+$(escape "$LOG_FILE")[[:space:];]" "$target"; then
      echo "Already enabled: $LOG_FILE"
      return 0
    fi
    echo "::error::$target already has an access_log line that is not $LOG_FILE; left for a human to look at"
    return 1
  fi

  local candidate
  candidate=$(mktemp)
  # shellcheck disable=SC2064  # expand now: the path is fixed
  trap "rm -f '$candidate'" EXIT
  local added
  run cat "$target" | insert_access_log > "$candidate"
  added=$(grep -c -F "access_log $LOG_FILE;" "$candidate" || true)
  if [ "${added:-0}" -lt 1 ]; then
    echo "::error::no server_name line naming $SITE ends on its own line; left for a human to look at"
    return 1
  fi
  echo "--- change ($added line(s) added) ---"
  run cat "$target" | diff -u --label "$target" --label "$target (new)" - "$candidate" || true

  echo "--- nginx -t on the current config ---"
  run "$NGINX" -t 2>&1

  if [ "$mode" = dry-run ]; then
    echo "--- what apply also needs ---"
    echo "log directory: $(dirname "$LOG_FILE") $( [ -d "$(dirname "$LOG_FILE")" ] && echo exists || echo MISSING)"
    df -h "$(dirname "$LOG_FILE")" 2>/dev/null | tail -n 1 || true
    if grep -qs "$(dirname "$LOG_FILE")/\*\.log" /etc/logrotate.d/nginx; then
      echo "logrotate: /etc/logrotate.d/nginx rotates $(dirname "$LOG_FILE")/*.log"
    else
      echo "logrotate: no rule for $(dirname "$LOG_FILE")/*.log found"
    fi
    echo "Dry run: nothing changed."
    return 0
  fi

  local backup
  backup="$BACKUP_DIR/$(basename "$target").$(date -u +%Y%m%dT%H%M%SZ)"
  run mkdir -p "$BACKUP_DIR"
  run cp -a "$target" "$backup"
  echo "backup: $backup"
  # tee writes into the existing file, so its owner, mode and any symlink to it stay as they were.
  run tee "$target" < "$candidate" > /dev/null

  if ! run "$NGINX" -t 2>&1; then
    run tee "$target" < "$backup" > /dev/null
    echo "::error::nginx -t failed with the change; the backup is back in place and nginx was not reloaded"
    return 1
  fi
  run "$NGINX" -s reload
  # Keep enough backups to roll back, not an archive.
  run sh -c 'ls -1t "$1"/* 2>/dev/null | tail -n +6 | xargs -r rm -f' sh "$BACKUP_DIR"
  echo "Applied: $SITE now logs to $LOG_FILE (nginx reloaded)."
}

run() {
  if [ "$(id -u)" -eq 0 ] || [ -n "${NO_SUDO:-}" ]; then "$@"; else sudo -n "$@"; fi
}

escape() { printf '%s' "$1" | sed 's/[][\.*^$/]/\\&/g'; }

# A server_name line naming the site exactly: not api.<site>, not <site>.example.
site_pattern() {
  printf '^[[:space:]]*server_name([[:space:]]+[^;#[:space:]]+)*[[:space:]]+%s([[:space:]]|;)' "$(escape "$SITE")"
}

find_vhost() {
  local files=() f
  for f in "$NGINX_DIR"/sites-enabled/* "$NGINX_DIR"/conf.d/*.conf; do
    [ -e "$f" ] || continue
    if run grep -Eq "$(site_pattern)" "$f"; then files+=("$(readlink -f "$f")"); fi
  done
  mapfile -t files < <(printf '%s\n' "${files[@]+"${files[@]}"}" | sed '/^$/d' | sort -u)
  if [ "${#files[@]}" -ne 1 ]; then
    echo "::error::expected exactly one enabled nginx file naming $SITE, found ${#files[@]}: ${files[*]-}" >&2
    return 1
  fi
  printf '%s\n' "${files[0]}"
}

# After each complete `server_name ... <site> ...;` line, the same indent plus access_log.
insert_access_log() {
  # ENVIRON, not -v: awk would read the backslashes in the pattern as escapes.
  PAT="$(site_pattern)" LOG="$LOG_FILE" awk '
    { print }
    $0 ~ ENVIRON["PAT"] {
      line = $0; sub(/#.*/, "", line)
      if (line ~ /;[[:space:]]*$/) {
        match($0, /^[[:space:]]*/)
        print substr($0, 1, RLENGTH) "access_log " ENVIRON["LOG"] ";"
      }
    }'
}

verify() {
  local marker=$1
  if [[ ! "$marker" =~ ^auto-author-1223-check-[0-9]+$ ]]; then
    echo "::error::verify needs a marker like auto-author-1223-check-<run id>" >&2
    return 2
  fi
  local n
  n=$(run grep -c -F "$marker" "$LOG_FILE" 2>/dev/null || true)
  if [ "${n:-0}" -ge 1 ]; then
    echo "$LOG_FILE has $n line(s) for this run's request."
    return 0
  fi
  echo "::error::$LOG_FILE has no line for this run's request"
  return 1
}

# Everything runs from inside main, so a command that reads stdin can't swallow
# the rest of this script when it arrives over `ssh ... bash -s`.
main "$@" < /dev/null
