#!/usr/bin/env bash
# Print the address the staging workflows should SSH to.
#
# Usage: find-staging-box.sh <configured host>
#
# The configured host is the STAGING_TS_HOST secret (or HOST): normally the
# box's full MagicDNS name, <machine>.<tailnet>.ts.net. On 2026-11-06 the
# deploy failed with "Could not resolve hostname" on every attempt: the box was
# online in the tailnet under the same machine name, but the tailnet's MagicDNS
# suffix no longer matched the one stored in the secret, so the old full name
# had no DNS record. A tailnet rename should not take the deploy down.
#
# So: if the configured host resolves, print it unchanged. If it does not,
# look the machine name (its first label) up in this node's netmap
# (`tailscale status --json`) and print that peer's tailnet IPv4 address, with
# a warning to update the secret. Exactly one online peer must match.
#
# Picking the box by name is safe because every ssh/scp in the workflows runs
# with StrictHostKeyChecking=yes against a pinned host key (#859): a different
# machine answering under that name is refused before authentication.
#
# For tests: RESOLVE (default "getent hosts") and TAILSCALE_STATUS_JSON (a
# file read instead of running `tailscale status --json`) can be overridden.
set -euo pipefail

host="${1:-}"
if [ -z "$host" ]; then
  echo "::error::no staging host configured (STAGING_TS_HOST / HOST)" >&2
  exit 1
fi

resolve=${RESOLVE:-getent hosts}
# shellcheck disable=SC2086  # $resolve is a command plus its arguments
if $resolve "$host" >/dev/null 2>&1; then
  printf '%s\n' "$host"
  exit 0
fi

if [ -n "${TAILSCALE_STATUS_JSON:-}" ]; then
  status=$(cat "$TAILSCALE_STATUS_JSON")
else
  status=$(tailscale status --json)
fi

name=$(printf '%s' "${host%%.*}" | tr 'A-Z' 'a-z')
ips=$(jq -r --arg name "$name" '
  [ (.Peer // {})[]
    | select(.Online == true)
    | select((.DNSName // "" | split(".")[0] | ascii_downcase) == $name)
    | (.TailscaleIPs // [])[]
    | select(test("^[0-9]+(\\.[0-9]+){3}$")) ]
  | unique | .[]' <<<"$status")

count=$(printf '%s' "$ips" | grep -c . || true)
if [ "$count" != 1 ]; then
  echo "::error::the configured staging host does not resolve, and $count online tailnet peers carry its machine name (need exactly 1)" >&2
  exit 1
fi

echo "::warning::the configured staging host has no DNS record (the tailnet's MagicDNS name may have changed); reaching the box by its machine name in the tailnet instead. Update the STAGING_TS_HOST secret to the box's current MagicDNS name." >&2
printf '%s\n' "$ips"
