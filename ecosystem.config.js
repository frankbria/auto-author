module.exports = {
  apps: [
    {
      name: 'auto-author-backend',
      script: '.venv/bin/python',
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: '/opt/auto-author/current/backend',
      interpreter: 'none', // Don't use Node.js interpreter
      env: {
        ENVIRONMENT: 'staging',
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
      cwd: '/opt/auto-author/current/frontend',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: '3002',
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
