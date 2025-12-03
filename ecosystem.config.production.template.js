// PM2 Ecosystem Configuration Template - PRODUCTION
// This file is populated by the deployment script with actual values
// DO NOT edit the __PLACEHOLDER__ values - they are replaced during deployment

module.exports = {
  apps: [
    {
      name: 'auto-author-api-prod',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8001',
      cwd: '__BACKEND_CWD__', // Will be replaced with actual release path
      interpreter: 'none', // Don't use Node.js interpreter
      env: {
        ENVIRONMENT: 'production',
        DATABASE_URI: '__MONGODB_URI__',
        DATABASE_NAME: '__DATABASE_NAME__',
        BACKEND_CORS_ORIGINS: '["__FRONTEND_URL__","__API_URL__"]',
        OPENAI_AUTOAUTHOR_API_KEY: '__OPENAI_API_KEY__',
        CLERK_API_KEY: '__CLERK_API_KEY__',
        CLERK_SECRET_KEY: '__CLERK_SECRET_KEY__',
        CLERK_FRONTEND_API: '__CLERK_FRONTEND_API__',
        CLERK_BACKEND_API: '__CLERK_BACKEND_API__',
        CLERK_WEBHOOK_SECRET: '__CLERK_WEBHOOK_SECRET__',
        CLERK_JWT_ALGORITHM: 'RS256',
        API_V1_PREFIX: '/api/v1',
      },
      error_file: '~/.pm2/logs/auto-author-api-prod-error.log',
      out_file: '~/.pm2/logs/auto-author-api-prod-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
      max_memory_restart: '1G', // Restart if memory exceeds 1GB
    },
    {
      name: 'auto-author-web-prod',
      script: 'npm',
      args: 'start',
      cwd: '__FRONTEND_CWD__', // Will be replaced with actual release path
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: '3001',
        NEXT_PUBLIC_API_URL: '__API_URL__',
        NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: '__CLERK_PUBLISHABLE_KEY__',
        CLERK_SECRET_KEY: '__CLERK_SECRET_KEY__',
        NEXT_PUBLIC_ENVIRONMENT: 'production',
      },
      error_file: '~/.pm2/logs/auto-author-web-prod-error.log',
      out_file: '~/.pm2/logs/auto-author-web-prod-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
      max_memory_restart: '1G', // Restart if memory exceeds 1GB
    },
  ],
};
