# Incident Report: ClawCloud Firewall Lockout

**Date**: 2025-10-19
**Severity**: Critical
**Status**: Awaiting Console Recovery
**Affected System**: ClawCloud Production Server (47.88.89.175)

---

## Summary

Attempted to restrict SSH access via UFW firewall rules, but deleted all existing SSH rules before new restricted rules could be applied, resulting in complete SSH lockout.

---

## Timeline

1. **19:55** - Started firewall security task (bd-13)
2. **19:56** - Backed up UFW rules successfully
3. **19:57** - Deleted unrestricted SSH rules (1, 3, 2, 4) sequentially
4. **19:58** - Attempted to add restricted rule: `ufw allow from 70.172.64.0/24 to any port 22`
5. **19:58** - Connection lost mid-command
6. **20:01** - Confirmed lockout - unable to reconnect via SSH

---

## Root Cause

**Non-atomic firewall modification**: Deleted all SSH access rules before confirming new restricted rule was active.

The command sequence should have been:
```bash
# WRONG (what we did):
ufw delete [old rules]  # Removed all SSH access
ufw allow from X.X.X.X  # Never completed

# RIGHT (atomic approach):
ufw allow from X.X.X.X  # Add new rule FIRST
ufw delete [old rules]  # Remove old rules AFTER
```

---

## Additional Contributing Factors

1. **Dynamic IP Address**: Attempted to use Cox dynamic IP (70.172.64.212) - not a stable long-term solution
2. **DDNS Limitations**: User has DDNS (uf06b2c.glddns.com) but UFW doesn't reliably support hostnames
3. **No VPN Alternative**: Tailscale considered but rejected for production environments

---

## Current Impact

### Services Still Running ✅
- Auto-author frontend (port 3002) - ONLINE
- Auto-author backend (port 8000) - ONLINE
- Nginx reverse proxy - ONLINE
- Bear Adventures Travel - ONLINE
- Strapi CMS - ONLINE

### Administrative Access ❌
- SSH access completely blocked
- Cannot manage server remotely
- Cannot deploy updates

---

## Recovery Steps (Console Access Required)

### Option 1: Quick Recovery (Re-enable SSH from anywhere)
```bash
# Access via ClawCloud web console/VNC
ufw allow 22/tcp
# OR
ufw disable  # Temporary - not recommended for production
```

### Option 2: Restore with Hardening (RECOMMENDED)
```bash
# 1. Re-enable SSH from anywhere
ufw allow 22/tcp

# 2. Harden SSH configuration
# Disable password authentication (key-only)
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# 3. Restart SSH service
systemctl restart sshd

# 4. Install and configure fail2ban
apt update && apt install fail2ban -y

# Create jail configuration for SSH
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

# 5. Enable and start fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# 6. Verify firewall rules
ufw status numbered
```

---

## Prevention Strategies

### 1. Authentication Hardening (RECOMMENDED for Production)
Instead of IP-based restrictions, use strong authentication:

**✅ Implemented**:
- SSH key-only authentication (no passwords)
- fail2ban automatic ban after 3 failed attempts
- Rate limiting via fail2ban

**🔄 Optional Enhancements**:
- Change SSH to non-standard port (e.g., 2222)
- Two-factor authentication (Google Authenticator)
- SSH certificate authority

### 2. Atomic Firewall Changes
Always add new rules BEFORE deleting old ones:
```bash
# Template for safe firewall changes:
ufw allow [NEW_RULE]     # Add new rule first
ufw status numbered      # Verify new rule exists
ufw delete [OLD_RULE]    # Remove old rule last
```

### 3. Testing Methodology
For critical firewall changes:
```bash
# Option A: Use at command for auto-rollback
at now + 5 minutes <<< "ufw disable && ufw enable"
# Make changes - if locked out, auto-reverts in 5 min

# Option B: Secondary connection
# Keep existing SSH session open while testing new rules
```

### 4. VPN for Dev/Staging (Not Production)
- Use Tailscale on dev machine for staging server access
- Keep production servers with hardened SSH from 0.0.0.0/0

---

## Lessons Learned

1. ❌ **Don't use dynamic IPs for firewall rules** - Cox assigns dynamic IPs that change
2. ❌ **Don't rely on DDNS for UFW** - Hostname resolution is unreliable in firewalls
3. ❌ **Don't delete before adding** - Always add new rules before removing old ones
4. ✅ **Do use authentication hardening** - More reliable than IP restrictions for production
5. ✅ **Do keep a console backup** - Always have out-of-band access method
6. ✅ **Do test incrementally** - Test each rule before proceeding to next

---

## Updated Security Approach

### New bd-13 Strategy
**FROM**: IP-based firewall restrictions
**TO**: Authentication-hardening approach

**Rationale**:
- Dynamic IP addresses are unstable
- UFW hostname support is unreliable
- VPN inappropriate for production
- Authentication hardening is industry standard

**Implementation**:
1. Allow SSH from 0.0.0.0/0 (anywhere)
2. Disable password authentication (key-only)
3. Install fail2ban (auto-ban brute force)
4. Rate limit connections
5. Monitor auth logs

---

## Related Tasks

- **bd-13**: Update to reflect authentication-hardening approach
- **New**: Create automated SSH hardening script
- **New**: Document console access procedures for ClawCloud

---

## Sign-off

**Incident Type**: Self-inflicted (firewall misconfiguration)
**Data Loss**: None
**Service Downtime**: None (services still running)
**Recovery ETA**: Awaiting user console access

**Next Actions**:
1. User accesses ClawCloud web console
2. User runs recovery script (Option 2 recommended)
3. Verify SSH access restored
4. Update bd-13 task with new approach
5. Create SSH hardening automation script
