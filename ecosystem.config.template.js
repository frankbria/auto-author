// PM2 Ecosystem Configuration Template
// This file is populated by the deployment script with actual values

module.exports = {
  apps: [
    {
      name: 'auto-author-backend',
      script: '.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      cwd: '__BACKEND_CWD__', // Will be replaced with actual release path
      interpreter: 'none', // Don't use Node.js interpreter
      env: {
        ENVIRONMENT: '__ENVIRONMENT__',
      },
      error_file: '~/.pm2/logs/auto-author-backend-error.log',
      out_file: '~/.pm2/logs/auto-author-backend-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
    },
    {
      name: 'auto-author-frontend',
      script: 'npm',
      args: 'start',
      cwd: '__FRONTEND_CWD__', // Will be replaced with actual release path
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: '3002',
        NEXT_PUBLIC_API_URL: '__API_URL__',
        NEXT_PUBLIC_ENVIRONMENT: '__ENVIRONMENT__',
        DATABASE_URL: '__DATABASE_URL__',
        DATABASE_NAME: '__DATABASE_NAME__',
        BETTER_AUTH_SECRET: '__BETTER_AUTH_SECRET__',
        NEXT_PUBLIC_BETTER_AUTH_URL: '__BETTER_AUTH_URL__',
      },
      error_file: '~/.pm2/logs/auto-author-frontend-error.log',
      out_file: '~/.pm2/logs/auto-author-frontend-out.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      watch: false,
    },
  ],
};
