# EmailPro Deployment Guide

This guide provides detailed instructions for deploying the EmailPro email marketing platform to different environments.

## Table of Contents

- [Environment Preparation](#environment-preparation)
- [Database Setup](#database-setup)
- [Local Deployment](#local-deployment)
- [Docker Deployment](#docker-deployment)
- [Render Deployment](#render-deployment)
- [Vercel Deployment](#vercel-deployment)
- [Scheduled Tasks](#scheduled-tasks)
- [Troubleshooting](#troubleshooting)

## Environment Preparation

### Create Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

The file should include:

```
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database settings
DATABASE_URL=postgres://username:password@host:port/database

# Email settings
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=your-email@example.com

# Stripe settings
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret
```

### Generate a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Database Setup

### PostgreSQL Setup

1. Install PostgreSQL:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   ```

2. Create a database and user:
   ```bash
   sudo -u postgres psql
   ```
   
   ```sql
   CREATE DATABASE emailpro;
   CREATE USER emailprouser WITH PASSWORD 'your-secure-password';
   ALTER ROLE emailprouser SET client_encoding TO 'utf8';
   ALTER ROLE emailprouser SET default_transaction_isolation TO 'read committed';
   ALTER ROLE emailprouser SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE emailpro TO emailprouser;
   \q
   ```

3. Update your `.env` file with the database credentials.

## Local Deployment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Apply migrations:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

6. Run the server:
   ```bash
   python manage.py runserver
   ```

## Docker Deployment

### Using Docker Compose

1. Make sure Docker and Docker Compose are installed.

2. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

3. Create a superuser:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. Access your application at `http://localhost:80`

### Customizing the Docker Setup

- Modify `Dockerfile` for additional packages or settings
- Adjust `docker-compose.yml` for additional services
- Update `nginx/nginx.conf` for custom Nginx configurations

## Render Deployment

1. Create a Render account at [render.com](https://render.com)

2. Connect your GitHub or GitLab repository

3. Create a new Web Service and select your repository

4. Configure settings:
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - Start Command: `gunicorn email_marketing_platform.wsgi:application --bind 0.0.0.0:$PORT`
   - Environment Variables: Add all variables from `.env.example`

5. Create a PostgreSQL database service and link it to your web service

6. Deploy your service!

### Using render.yaml

Alternatively, use the included `render.yaml` file:

1. Push your code to GitHub
2. Go to Render Dashboard and click "Blueprint"
3. Connect your repository and Render will set up the services defined in `render.yaml`

## Vercel Deployment

Vercel works well for frontend applications but requires some adaptation for Django. The included `vercel.json` file configures your project for Vercel deployment.

1. Install the Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy your project:
   ```bash
   vercel
   ```

3. Set all required environment variables in the Vercel dashboard.

4. **Note**: You'll need a separate database service, as Vercel doesn't provide PostgreSQL. Consider using:
   - [Neon](https://neon.tech)
   - [Supabase](https://supabase.com)
   - [Render PostgreSQL](https://render.com/docs/databases)
   - [Railway](https://railway.app)

## Scheduled Tasks

For automations and scheduled campaigns to work, you need to set up the task scheduler:

### On Linux/macOS with Cron

Edit your crontab:
```bash
crontab -e
```

Add:
```
0 0 * * * /path/to/project/scripts/run_daily_tasks.sh
```

### On Windows with Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set Trigger to Daily
4. Action: Start a program
5. Program/script: `powershell.exe`
6. Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\scripts\run_daily_tasks.ps1"`

## Troubleshooting

### Database Connectivity Issues

1. Check your DATABASE_URL format
2. Ensure database server is accessible from your deployment environment
3. Check database user permissions

### Static Files Not Loading

1. Verify `STATIC_ROOT` is set correctly
2. Run `python manage.py collectstatic --noinput`
3. Ensure your webserver is configured to serve static files
4. For Vercel: Check your vercel.json routes configuration

### Email Sending Failures

1. Verify SMTP server settings
2. Check username and password
3. If using Gmail, ensure "Less secure app access" is enabled or use an App Password
4. Check for rate limiting on your email provider

### Server 500 Errors

1. Check your deployment logs
2. Temporarily set `DEBUG=True` to see detailed error messages
3. Verify all environment variables are set correctly

For additional help, please open an issue on the GitHub repository. 