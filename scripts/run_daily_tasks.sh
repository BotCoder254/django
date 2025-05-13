#!/bin/bash

# Script to run daily email marketing tasks
# Recommended to run this via cron job daily

# Set environment variables if needed
# export DJANGO_SETTINGS_MODULE=email_marketing_platform.settings

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to project root
cd "$DIR/.."

# Activate virtual environment if using one
# source venv/bin/activate

echo "Starting daily email marketing tasks..."

# Send scheduled campaigns
echo "Sending scheduled campaigns..."
python manage.py send_scheduled_campaigns

# Process automations
echo "Processing automations..."
python manage.py process_automations

echo "Daily tasks completed." 