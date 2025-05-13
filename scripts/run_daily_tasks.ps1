# PowerShell script to run daily email marketing tasks
# Recommended to run this via Windows Task Scheduler daily

# Set environment variables if needed
# $env:DJANGO_SETTINGS_MODULE="email_marketing_platform.settings"

# Get the directory of the script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Navigate to project root
Set-Location "$scriptDir\.."

# Activate virtual environment if using one
# & .\venv\Scripts\Activate.ps1

Write-Host "Starting daily email marketing tasks..."

# Send scheduled campaigns
Write-Host "Sending scheduled campaigns..."
python manage.py send_scheduled_campaigns

# Process automations
Write-Host "Processing automations..."
python manage.py process_automations

Write-Host "Daily tasks completed." 