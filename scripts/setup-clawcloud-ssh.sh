#!/bin/bash
# Setup SSH access to ClawCloud server
# Run this script interactively to copy SSH keys

set -euo pipefail

SERVER="47.88.89.175"
USER="root"
SSH_KEY="$HOME/.ssh/id_ed25519"

echo "Setting up SSH access to ClawCloud ($SERVER)..."
echo

# Copy SSH key to server
echo "Copying SSH key to server..."
echo "You will be prompted for the server password"
ssh-copy-id -i "$SSH_KEY.pub" -o StrictHostKeyChecking=no "$USER@$SERVER"

echo
echo "Testing SSH connection..."
if ssh -i "$SSH_KEY" -o BatchMode=yes "$USER@$SERVER" "echo 'SSH connection successful!'" 2>/dev/null; then
    echo "✅ SSH key setup complete!"
    echo "You can now connect with: ssh root@$SERVER"
else
    echo "❌ SSH connection failed. Please check your credentials."
    exit 1
fi
