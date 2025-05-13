import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from users.models import SmtpSettings

def send_email_with_settings(user, subject, message, to_emails, html_content=None, reply_to=None, from_name=None, from_email=None, headers=None):
    """
    Send an email using user's SMTP settings if available, otherwise use default Django settings.
    
    Args:
        user: The CustomUser object whose SMTP settings to use
        subject: Email subject
        message: Plain text message
        to_emails: List of recipient email addresses
        html_content: Optional HTML content
        reply_to: Optional reply-to email address
        from_name: Optional sender name (default: user full name or username)
        from_email: Optional sender email (default: user email or DEFAULT_FROM_EMAIL)
        headers: Optional email headers dict
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not to_emails:
        return False
    
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    # Check if user has custom SMTP settings
    use_custom_smtp = False
    smtp_settings = None
    
    try:
        smtp_settings = SmtpSettings.objects.get(user=user, is_active=True)
        use_custom_smtp = True
    except SmtpSettings.DoesNotExist:
        use_custom_smtp = False
    
    # Set from_name and from_email if not provided
    if not from_name:
        from_name = user.get_full_name() if hasattr(user, 'get_full_name') and user.get_full_name() else user.username
    
    if not from_email:
        from_email = smtp_settings.from_email if use_custom_smtp else settings.DEFAULT_FROM_EMAIL
    
    # Format sender
    sender = f"{from_name} <{from_email}>"
    
    try:
        if use_custom_smtp:
            # Create the email message
            if html_content:
                # Create multipart email with both HTML and text versions
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = ', '.join(to_emails)
                
                if reply_to:
                    msg['Reply-To'] = reply_to
                
                # Attach plain text and HTML parts
                text_part = MIMEText(message, 'plain')
                html_part = MIMEText(html_content, 'html')
                msg.attach(text_part)
                msg.attach(html_part)
                
                # Add custom headers if provided
                if headers:
                    for key, value in headers.items():
                        msg[key] = value
                
                # Create SMTP connection
                connection = smtplib.SMTP(smtp_settings.host, smtp_settings.port)
                connection.ehlo()
                
                if smtp_settings.use_tls:
                    connection.starttls()
                    connection.ehlo()
                
                # Login and send
                connection.login(smtp_settings.username, smtp_settings.password)
                connection.sendmail(from_email, to_emails, msg.as_string())
                connection.quit()
            else:
                # Plain text email
                msg = MIMEMultipart()
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = ', '.join(to_emails)
                
                if reply_to:
                    msg['Reply-To'] = reply_to
                
                # Add custom headers if provided
                if headers:
                    for key, value in headers.items():
                        msg[key] = value
                
                # Attach message
                msg.attach(MIMEText(message, 'plain'))
                
                # Create SMTP connection
                connection = smtplib.SMTP(smtp_settings.host, smtp_settings.port)
                connection.ehlo()
                
                if smtp_settings.use_tls:
                    connection.starttls()
                    connection.ehlo()
                
                # Login and send
                connection.login(smtp_settings.username, smtp_settings.password)
                connection.sendmail(from_email, to_emails, msg.as_string())
                connection.quit()
        else:
            # Use Django's built-in email system with default settings
            if html_content:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=sender,
                    to=to_emails,
                    reply_to=[reply_to] if reply_to else None,
                    headers=headers,
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)
            else:
                msg = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=sender,
                    to=to_emails,
                    reply_to=[reply_to] if reply_to else None,
                    headers=headers,
                )
                msg.send(fail_silently=False)
        
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False 