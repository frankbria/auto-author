# SSH Key Deployment Troubleshooting

## Current Issue

Deployment failing with:
```
Load key "/home/runner/.ssh/staging_key": error in libcrypto
```

This error indicates the `SSH_KEY` secret in GitHub is corrupted or incorrectly formatted.

## Diagnosis Steps

### 1. Verify Local SSH Key Format

On your local machine, check the SSH private key:

```bash
# View the key content (be careful - this is sensitive!)
cat ~/.ssh/id_rsa  # or your key path

# It should look like this:
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
... (many lines of base64)
-----END OPENSSH PRIVATE KEY-----
```

### 2. Validate Key Format

```bash
# Test if OpenSSL can read the key
ssh-keygen -l -f ~/.ssh/id_rsa

# Should output something like:
# 2048 SHA256:... user@host (RSA)
```

### 3. Check Key Permissions

```bash
# Ensure correct permissions
chmod 600 ~/.ssh/id_rsa
```

## Fixing the GitHub Secret

### Option 1: Re-copy the Existing Key

1. **Display the key content:**
   ```bash
   cat ~/.ssh/id_rsa
   ```

2. **Copy the ENTIRE output** including:
   - `-----BEGIN OPENSSH PRIVATE KEY-----`
   - All base64 content
   - `-----END OPENSSH PRIVATE KEY-----`

3. **Update GitHub Secret:**
   - Go to: https://github.com/frankbria/auto-author/settings/secrets/actions
   - Click `SSH_KEY` → Update
   - Paste the key **exactly as displayed** (no extra spaces/newlines)

### Option 2: Generate a New Key (Recommended)

```bash
# Generate a new ED25519 key (more secure than RSA)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy_key

# Display the private key
cat ~/.ssh/github_deploy_key

# Display the public key (to add to staging server)
cat ~/.ssh/github_deploy_key.pub
```

**Then:**

1. **Add public key to staging server:**
   ```bash
   ssh root@47.88.89.175
   echo "ssh-ed25519 AAAA... github-actions-deploy" >> ~/.ssh/authorized_keys
   ```

2. **Add private key to GitHub Secrets:**
   - Copy entire output of `cat ~/.ssh/github_deploy_key`
   - Go to GitHub → Settings → Secrets → Actions
   - Update `SSH_KEY` with the new private key

## Validation After Update

### Test Locally First

```bash
# Save the key to a test file
cat << 'EOF' > /tmp/test_key
<paste your key here>
EOF

# Set permissions
chmod 600 /tmp/test_key

# Test SSH connection
ssh -i /tmp/test_key root@47.88.89.175 "echo 'SSH works!'"

# Clean up
rm /tmp/test_key
```

### Trigger New Deployment

```bash
# Push a small change to trigger deployment
git commit --allow-empty -m "test: trigger deployment after SSH key fix"
git push origin develop
```

## Common Mistakes to Avoid

❌ **Don't copy from terminal with line wrapping** - this breaks the base64 encoding
❌ **Don't add extra newlines** at the beginning or end
❌ **Don't copy the public key** (`.pub` file) - you need the private key
❌ **Don't paste into a word processor** first - it might add formatting
❌ **Don't manually format/reformat** the base64 content

✅ **Do use `cat` to display the key** and copy directly
✅ **Do include the BEGIN/END markers** exactly as shown
✅ **Do preserve all newlines** in the base64 content
✅ **Do test locally first** before updating GitHub Secrets

## Expected Key Format

An OpenSSH private key should have:
- **Line 1:** `-----BEGIN OPENSSH PRIVATE KEY-----`
- **Lines 2-N:** Base64-encoded content (70 chars per line)
- **Last line:** `-----END OPENSSH PRIVATE KEY-----`

**Total:** Usually 20-40 lines for ED25519, 25-50 lines for RSA keys

## Next Steps After Fix

1. Update `SSH_KEY` secret in GitHub
2. Push a commit to trigger deployment
3. Monitor workflow: https://github.com/frankbria/auto-author/actions
4. Verify health checks pass
