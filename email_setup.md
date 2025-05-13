# Email Marketing Platform: Email Setup Guide

This guide provides instructions on how to set up and use the email sending features of the Email Marketing Platform.

## Table of Contents
1. [SMTP Settings Configuration](#smtp-settings-configuration)
2. [Gmail App Password Setup](#gmail-app-password-setup)
3. [Using Your Own SMTP Server](#using-your-own-smtp-server)
4. [Testing Email Functionality](#testing-email-functionality)
5. [Scheduled Emails](#scheduled-emails)
6. [Automations](#automations)
7. [Troubleshooting](#troubleshooting)

## SMTP Settings Configuration

Each user on the platform can configure their own SMTP settings for sending emails:

1. Log in to your account
2. Navigate to your Profile (click on your name in the top-right corner)
3. Select "SMTP Settings" from the dropdown menu
4. Fill out the SMTP server details:
   - Host: Your SMTP server address (e.g., smtp.gmail.com)
   - Port: The SMTP port (e.g., 587 for TLS, 465 for SSL)
   - Username: Your email address
   - Password: Your email password or app password (for Gmail, see next section)
   - Use TLS: Check this if your SMTP server requires TLS
   - Use SSL: Check this if your SMTP server requires SSL
   - From Email: The email address to appear in the "From" field
   - From Name: The name to appear in the "From" field
5. Click "Save Settings"
6. Test your configuration by clicking the "Test Connection" button

## Gmail App Password Setup

For Gmail users, you'll need to use an "App Password" instead of your regular password:

1. Visit your [Google Account](https://myaccount.google.com/)
2. Select "Security" from the left menu
3. Under "Signing in to Google," select "2-Step Verification" (turn it on if not already enabled)
4. At the bottom of the page, click on "App passwords"
5. Select "Mail" for the app and "Other" for the device
6. Enter a name (e.g., "Email Marketing Platform")
7. Click "Generate"
8. Use the generated 16-character password in your SMTP settings

## Using Your Own SMTP Server

If you're running your own SMTP server, make sure:

1. Your server allows connections from your application
2. You've correctly set up SPF, DKIM, and DMARC records to improve deliverability
3. Your server IP is not on any spam blacklists
4. You've configured appropriate rate limits to avoid being flagged as spam

## Testing Email Functionality

Before sending actual campaigns, test your email configuration:

1. Create a test campaign with a small group of test subscribers
2. Use the "Test Campaign" button to send a test email to yourself
3. Check that the email is properly formatted and delivered to your inbox (check spam folder too)
4. For automations, use the "Test Automation" button to verify email steps

## Scheduled Emails

Scheduled emails are sent automatically at the specified date and time:

1. The server runs a daily task to check for scheduled campaigns
2. To set up scheduled sending, use the "Schedule" button on the campaign detail page
3. Enter the date and time when you want the campaign to be sent
4. The system will automatically send the campaign at the specified time
5. You'll receive a notification when the campaign is sent

## Automations

Automations allow you to send emails based on triggers like new subscriptions:

1. Create an automation from the Automations dashboard
2. Define the trigger type (e.g., subscription, inactivity, etc.)
3. Add email steps and wait periods as needed
4. Activate the automation using the toggle switch
5. The system will automatically process active automations daily
6. You'll receive notifications when automation emails are sent

## Troubleshooting

If you encounter issues with email sending:

1. **Emails not sending**:
   - Check your SMTP settings are correct
   - Verify your username and password
   - Ensure your SMTP server is accessible from the application
   - Check if your email account has sending limits

2. **Emails going to spam**:
   - Improve your email subject and content (avoid spam triggers)
   - Set up proper SPF, DKIM, and DMARC records
   - Gradually increase your sending volume to build reputation
   - Use a dedicated IP address if possible

3. **Authentication errors**:
   - For Gmail, ensure you're using an App Password, not your regular password
   - Check if your email service requires additional security settings
   - Verify that TLS/SSL settings match your provider's requirements

4. **Error logs**:
   - Check the application logs for detailed error messages
   - Review SMTP server logs if accessible
   - Look for any rate limiting or policy violations in the logs

For additional assistance or to report issues, please contact support. 