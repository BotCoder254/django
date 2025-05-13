# EmailPro - Modern Email Marketing Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green)](https://www.djangoproject.com/)

EmailPro is a powerful, self-hosted email marketing platform built with Django. It provides all the essential features for effective email marketing campaigns, audience segmentation, and automated workflows.

![EmailPro Dashboard](https://via.placeholder.com/800x400?text=EmailPro+Dashboard)

## ✨ Features

- 📧 **Campaign Management**: Create, schedule, and track email campaigns
- 👥 **Subscriber Management**: Import, segment, and organize your audience
- 📊 **Analytics Dashboard**: Track opens, clicks, and conversions
- 🔄 **Automation Workflows**: Create multi-step email sequences triggered by user actions
- 🧪 **A/B Testing**: Compare subject lines, content, and timing to optimize your campaigns
- 📱 **Responsive Templates**: Built-in templates that work across all devices
- 🔌 **SMTP Integration**: Use your own SMTP server or third-party services
- 💰 **Stripe Integration**: Accept payments and manage subscriptions

## 🚀 Deployment Options

### Quick Start (Local Development)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/emailpro.git
   cd emailpro
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file (use `.env.example` as a template)

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the server:
   ```bash
   python manage.py runserver
   ```

8. Visit `http://127.0.0.1:8000/` in your browser

### Docker Deployment

1. Clone the repository
2. Create a `.env` file based on `.env.example`
3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository
2. Connect your Render account to GitHub
3. Create a new Web Service from your fork
4. Use the settings from `render.yaml`
5. Deploy!

### Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyourusername%2Femailpro)

*Note: For full functionality on Vercel, you'll need to set up a database provider separately.*

## 📋 Environment Variables

Copy `.env.example` to `.env` and update the values according to your environment:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: Database connection URL
- `EMAIL_HOST`, `EMAIL_PORT`, etc.: SMTP server configuration
- `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`: Stripe API keys

## 🛠️ Scheduled Tasks

To enable automated campaign sending and workflow processing:

### Using Cron (Linux/Mac)

Add to crontab:
```bash
0 0 * * * /path/to/project/scripts/run_daily_tasks.sh
```

### Using Task Scheduler (Windows)

- Create a new task in Windows Task Scheduler
- Set the program/script to: `powershell.exe`
- Set arguments to: `-ExecutionPolicy Bypass -File "C:\path\to\scripts\run_daily_tasks.ps1"`
- Set daily trigger

## 📱 API Access

EmailPro provides a RESTful API to integrate with other services:

- Authentication: API key-based
- Documentation: `/api/docs/` endpoint
- Rate limits: 100 requests/minute

## 💡 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Django Framework
- Bootstrap 5
- Stripe API
- Chart.js
- FontAwesome 