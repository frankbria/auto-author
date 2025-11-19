---
id: doc-1
title: Backend Deployment
type: other
created_date: '2025-07-17'
---



---


# Backend Deployment Plan for VPS (Port 8001)

## 🎯 Deployment Overview
Deploy the FastAPI backend to a remote VPS on port 8001 with Nginx reverse proxy at api.autoauthor.net

## 📋 Pre-Deployment Checklist

### VPS Requirements
- **OS**: Ubuntu 22.04 LTS (recommended)
- **RAM**: Minimum 2GB (4GB recommended)
- **CPU**: 2+ cores
- **Storage**: 20GB+ SSD
- **Python**: 3.11+ 
- **Open Ports**: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- **Note**: Port 8000 already in use, will use 8001

### Required Credentials
```bash
# Ensure you have these ready:
✓ VPS root/sudo access
✓ Domain configured: api.autoauthor.net
✓ All API keys from .env file
✓ MongoDB connection string
✓ SSL certificate (or use Let's Encrypt)
```

## 🚀 Deployment Steps

### Step 1: Initial VPS Setup (30 mins)

```bash
# 1. SSH into your VPS
ssh root@your-vps-ip

# 2. Update system (if not already done)
apt update && apt upgrade -y

# 3. Create deploy user (if not exists)
id -u deploy &>/dev/null || adduser deploy
usermod -aG sudo deploy

# 4. Check firewall (ports should already be open)
ufw status

# 5. Install required packages (skip if already installed)
apt install -y python3.11 python3.11-venv python3-pip nginx supervisor git curl

# 6. Install UV (if not already installed)
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Setup Application Directory (15 mins)

```bash
# Switch to deploy user
su - deploy

# Create application directory
sudo mkdir -p /var/www/auto-author-backend
sudo chown deploy:deploy /var/www/auto-author-backend
cd /var/www/auto-author-backend

# Clone repository (or upload files)
git clone https://github.com/yourusername/auto-author.git .
# OR use SCP/SFTP to upload files

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Step 3: Configure Environment Variables (10 mins)

```bash
# Create production .env file
cd /var/www/auto-author-backend/backend
sudo nano .env
```

Add your production environment variables:
```env
# Database
DATABASE_URI=mongodb+srv://your-production-mongodb-uri
DATABASE_NAME=auto_author_prod

# CORS - Update with your frontend domain AND the API domain
BACKEND_CORS_ORIGINS=["https://autoauthor.net","https://www.autoauthor.net","https://api.autoauthor.net"]

# API Keys (use your real keys)
OPENAI_API_KEY=your-openai-key
CLERK_API_KEY=your-clerk-key
CLERK_JWT_PUBLIC_KEY="your-clerk-public-key"
CLERK_FRONTEND_API=your-clerk-frontend
CLERK_BACKEND_API=api.clerk.com
CLERK_JWT_ALGORITHM=RS256
CLERK_WEBHOOK_SECRET=your-webhook-secret

# AWS (if using)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket

# Cloudinary (if using)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### Step 4: Setup Gunicorn with Supervisor (20 mins)

Create Gunicorn configuration for **port 8001**:
```bash
sudo nano /etc/supervisor/conf.d/auto-author-backend.conf
```

```ini
[program:auto-author-backend]
command=/var/www/auto-author-backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001
directory=/var/www/auto-author-backend/backend
user=deploy
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
redirect_stderr=true
stdout_logfile=/var/log/auto-author-backend/gunicorn.log
environment=PATH="/var/www/auto-author-backend/venv/bin",PYTHONPATH="/var/www/auto-author-backend/backend"
```

Create log directory and start service:
```bash
sudo mkdir -p /var/log/auto-author-backend
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start auto-author-backend
```

### Step 5: Configure Nginx for api.autoauthor.net (20 mins)

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/api.autoauthor.net
```

```nginx
# Rate limiting zone (add to /etc/nginx/nginx.conf in http block if not exists)
# limit_req_zone $binary_remote_addr zone=autoauthor_api:10m rate=10r/s;

server {
    listen 80;
    server_name api.autoauthor.net;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.autoauthor.net;

    # SSL Configuration - Let's Encrypt will update these
    ssl_certificate /etc/letsencrypt/live/api.autoauthor.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.autoauthor.net/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Logging
    access_log /var/log/nginx/api.autoauthor.net.access.log;
    error_log /var/log/nginx/api.autoauthor.net.error.log;
    
    # Rate limiting (uncomment if zone is defined)
    # limit_req zone=autoauthor_api burst=20 nodelay;
    
    # Proxy settings to port 8001
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts for long-running AI requests
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    # File upload size limit
    client_max_body_size 50M;
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/api.autoauthor.net /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 6: Setup SSL with Let's Encrypt (15 mins)

```bash
# Install Certbot (if not already installed)
which certbot || sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate for api.autoauthor.net
sudo certbot --nginx -d api.autoauthor.net

# Auto-renewal is set up automatically
# Test renewal
sudo certbot renew --dry-run
```

### Step 7: Update Frontend Configuration (5 mins)

**Important**: Update your frontend `.env` file to point to the new API URL:

```env
NEXT_PUBLIC_API_URL=https://api.autoauthor.net
```

### Step 8: Create Deployment Script (10 mins)

Create a deployment script for future updates:
```bash
nano /home/deploy/deploy-auto-author-backend.sh
```

```bash
#!/bin/bash
echo "Deploying Auto Author Backend..."
cd /var/www/auto-author-backend

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
cd backend
pip install -r requirements.txt

# Restart the service
sudo supervisorctl restart auto-author-backend

# Check status
sleep 2
sudo supervisorctl status auto-author-backend

# Test the API
echo "Testing API endpoint..."
curl -s https://api.autoauthor.net/health || echo "API health check failed!"

echo "Deployment complete!"
```

```bash
chmod +x /home/deploy/deploy-auto-author-backend.sh
```

### Step 9: Setup Monitoring and Logs (15 mins)

Create log monitoring script:
```bash
nano /home/deploy/monitor-auto-author.sh
```

```bash
#!/bin/bash
echo "=== Auto Author Backend Status ==="
echo "Service Status:"
sudo supervisorctl status auto-author-backend
echo ""
echo "Port Check:"
sudo netstat -tlnp | grep 8001
echo ""
echo "Recent Logs:"
sudo tail -20 /var/log/auto-author-backend/gunicorn.log
echo ""
echo "Nginx Access (last 10 requests):"
sudo tail -10 /var/log/nginx/api.autoauthor.net.access.log
```

```bash
chmod +x /home/deploy/monitor-auto-author.sh
```

Setup log rotation:
```bash
sudo nano /etc/logrotate.d/auto-author-backend
```

```
/var/log/auto-author-backend/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        supervisorctl restart auto-author-backend
    endscript
}

/var/log/nginx/api.autoauthor.net*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        /usr/bin/systemctl reload nginx
    endscript
}
```

### Step 10: Test Deployment (10 mins)

```bash
# 1. Check service is running on port 8001
sudo supervisorctl status auto-author-backend
sudo netstat -tlnp | grep 8001

# 2. Test local connection
curl http://127.0.0.1:8001/health

# 3. Test through Nginx
curl https://api.autoauthor.net/health

# 4. Check API documentation
echo "Visit: https://api.autoauthor.net/docs"

# 5. Test a real endpoint (adjust the token)
curl -H "Authorization: Bearer YOUR_CLERK_TOKEN" https://api.autoauthor.net/api/v1/users/me

# 6. Monitor logs
./monitor-auto-author.sh
```

## 📊 Post-Deployment Checklist

- [ ] API responds at https://api.autoauthor.net
- [ ] FastAPI docs accessible at https://api.autoauthor.net/docs
- [ ] SSL certificate is valid for api.autoauthor.net
- [ ] Service running on port 8001 (not conflicting with 8000)
- [ ] All environment variables are set
- [ ] MongoDB connection works
- [ ] OpenAI API calls succeed
- [ ] Clerk authentication works
- [ ] CORS includes frontend domain
- [ ] File uploads work
- [ ] Logs are being written
- [ ] Frontend can connect to new API URL

## 🔧 Quick Reference Commands

```bash
# View service status
sudo supervisorctl status auto-author-backend

# View logs
sudo supervisorctl tail -f auto-author-backend

# Restart service
sudo supervisorctl restart auto-author-backend

# Update and deploy
./deploy-auto-author-backend.sh

# Monitor everything
./monitor-auto-author.sh

# Check what's running on ports
sudo netstat -tlnp | grep -E '8000|8001'
```

## 🚨 Troubleshooting

### Port Conflicts
```bash
# Check what's using port 8001
sudo lsof -i :8001

# Verify our service is on 8001, not 8000
ps aux | grep gunicorn
```

### Domain/SSL Issues
```bash
# Test DNS resolution
nslookup api.autoauthor.net

# Check SSL certificate
openssl s_client -connect api.autoauthor.net:443 -servername api.autoauthor.net
```

### Common Issues:

1. **502 Bad Gateway**
   - Service might be trying to use port 8000 instead of 8001
   - Check supervisor config has correct port
   - Verify Nginx proxy_pass points to 8001

2. **CORS Errors**
   - Ensure BACKEND_CORS_ORIGINS includes your frontend domain
   - Check that api.autoauthor.net is also in CORS origins

3. **Connection Refused**
   - Service might not be running on 8001
   - Check: `sudo netstat -tlnp | grep 8001`

4. **Module Import Errors**
   - Ensure PYTHONPATH is set in supervisor config
   - Check virtual environment activation

5. **MongoDB Connection Issues**
   - Verify connection string
   - Check firewall rules on MongoDB
   - Ensure IP is whitelisted in MongoDB Atlas

## 🔐 Security Hardening (Optional)

### Additional Security Steps
```bash
# 1. Disable root SSH login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart ssh

# 2. Install fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 3. Setup automatic security updates
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades

# 4. Create API rate limiting with Nginx
# Add to nginx http block:
# limit_req_zone $binary_remote_addr zone=autoauthor_api:10m rate=10r/s;
# Then uncomment the limit_req line in the server block
```

## 🚀 Future Enhancements

1. **Setup CI/CD**
   - GitHub Actions for automated deployment
   - Webhook for auto-deploy on push

2. **Advanced Monitoring**
   - Setup Prometheus + Grafana
   - Or use cloud monitoring (DataDog, New Relic)
   - Setup alerts for errors or downtime

3. **Backup Strategy**
   - Automated MongoDB backups
   - VPS snapshots
   - Configuration backups

4. **Performance Optimization**
   - Redis for caching
   - CDN for static files
   - Database query optimization

5. **Load Balancing** (For scale)
   - Multiple VPS instances
   - Nginx load balancing
   - Or use cloud load balancer

## 📝 Maintenance Notes

### Regular Maintenance Tasks
- Check logs weekly: `./monitor-auto-author.sh`
- Update dependencies monthly: `pip list --outdated`
- Review security updates: `sudo apt update && sudo apt list --upgradable`
- Monitor disk space: `df -h`
- Check SSL renewal: `sudo certbot certificates`

### Backup Commands
```bash
# Backup .env file
cp /var/www/auto-author-backend/backend/.env ~/backups/auto-author-env-$(date +%Y%m%d).bak

# Backup nginx config
sudo cp /etc/nginx/sites-available/api.autoauthor.net ~/backups/

# Backup supervisor config
sudo cp /etc/supervisor/conf.d/auto-author-backend.conf ~/backups/
```

## Total Deployment Time: ~2.5 hours

This deployment plan ensures your Auto Author backend runs smoothly on port 8001 without conflicting with existing services!

---
*Document Created: January 29, 2025*  
*Last Updated: January 29, 2025*