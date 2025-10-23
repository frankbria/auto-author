#!/bin/bash
# SSH Hardening Script for ClawCloud Production Server
# Run this via console access after firewall lockout recovery
#
# Usage: bash harden-ssh.sh
#
# What this script does:
# 1. Re-enables SSH access from anywhere (0.0.0.0/0)
# 2. Hardens SSH configuration (key-only auth)
# 3. Installs and configures fail2ban
# 4. Sets up automatic brute-force protection

set -euo pipefail

echo "=== SSH Hardening Script for ClawCloud ==="
echo "This script will:"
echo "  1. Re-enable SSH access (port 22 from anywhere)"
echo "  2. Configure SSH for key-only authentication"
echo "  3. Install and configure fail2ban"
echo "  4. Verify configuration"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Re-enable SSH access via UFW
echo ""
echo "Step 1: Re-enabling SSH access..."
ufw allow 22/tcp
ufw reload
echo "✅ SSH port 22 enabled from anywhere"

# Step 2: Backup SSH config
echo ""
echo "Step 2: Backing up SSH configuration..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"

# Step 3: Harden SSH configuration
echo ""
echo "Step 3: Hardening SSH configuration..."

# Disable password authentication
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Enable public key authentication
sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# Disable root password login (keys only)
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# Disable empty passwords
sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# Disable X11 forwarding (security)
sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' /etc/ssh/sshd_config

# Set login grace time
sed -i 's/^#*LoginGraceTime.*/LoginGraceTime 30/' /etc/ssh/sshd_config

# Max auth tries
sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config

echo "✅ SSH configuration hardened"

# Step 4: Verify SSH config
echo ""
echo "Step 4: Verifying SSH configuration..."
if sshd -t; then
    echo "✅ SSH configuration valid"
else
    echo "❌ SSH configuration error - restoring backup"
    mv /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config
    exit 1
fi

# Step 5: Restart SSH service
echo ""
echo "Step 5: Restarting SSH service..."
systemctl restart sshd
echo "✅ SSH service restarted"

# Step 6: Install fail2ban
echo ""
echo "Step 6: Installing fail2ban..."
apt update -qq
apt install -y fail2ban

# Step 7: Configure fail2ban for SSH
echo ""
echo "Step 7: Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<'EOF'
# Auto-Author Production Server - fail2ban configuration
# Generated: $(date)

[DEFAULT]
# Ban IP for 1 hour after 3 failed attempts within 10 minutes
bantime = 3600
findtime = 600
maxretry = 3

# Email alerts (optional - configure if needed)
# destemail = your-email@example.com
# sendername = Fail2Ban-ClawCloud
# action = %(action_mwl)s

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600

[sshd-ddos]
enabled = true
port = 22
filter = sshd-ddos
logpath = /var/log/auth.log
maxretry = 6
bantime = 600
findtime = 60
EOF

echo "✅ fail2ban configured"

# Step 8: Enable and start fail2ban
echo ""
echo "Step 8: Starting fail2ban..."
systemctl enable fail2ban
systemctl restart fail2ban
echo "✅ fail2ban enabled and started"

# Step 9: Verify fail2ban status
echo ""
echo "Step 9: Verifying fail2ban status..."
if systemctl is-active --quiet fail2ban; then
    echo "✅ fail2ban is running"
    fail2ban-client status sshd
else
    echo "❌ fail2ban failed to start"
    exit 1
fi

# Step 10: Display final configuration
echo ""
echo "=== SSH Hardening Complete ==="
echo ""
echo "Current SSH Configuration:"
echo "  - Password Authentication: DISABLED"
echo "  - Public Key Authentication: ENABLED"
echo "  - Root Login: Keys only (no password)"
echo "  - Max Auth Tries: 3"
echo "  - Login Grace Time: 30 seconds"
echo ""
echo "fail2ban Protection:"
echo "  - Ban after 3 failed attempts within 10 minutes"
echo "  - Ban duration: 1 hour"
echo "  - Protected services: SSH (port 22)"
echo ""
echo "UFW Firewall Status:"
ufw status numbered
echo ""
echo "✅ Server is now hardened and accessible"
echo ""
echo "IMPORTANT: Verify you can SSH with your key before closing this session!"
echo "  Test command: ssh root@47.88.89.175"
echo ""
echo "To monitor fail2ban:"
echo "  fail2ban-client status sshd"
echo "  tail -f /var/log/fail2ban.log"
echo ""
echo "To view banned IPs:"
echo "  fail2ban-client status sshd | grep 'Banned IP'"
echo ""
