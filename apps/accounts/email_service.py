from django.core.mail import send_mail, get_connection
from django.conf import settings
import socket


def send_otp_email(email, otp):
    """Send OTP email with timeout handling for Render"""
    subject = 'Your FundiGO OTP Verification Code'
    message = f'''
    Your FundiGO OTP is: {otp}
    
    This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    The FundiGO Team
    '''
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fundigo.com')
    
    # Always log OTP to console (useful for debugging and when email fails)
    print(f"📧 OTP for {email}: {otp}")
    
    # Check if email is properly configured
    email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
    if not email_host_user:
        print("⚠️ EMAIL_HOST_USER not configured, skipping email send")
        return True  # Return True so signup continues
    
    try:
        # Set a short timeout to prevent worker from hanging
        socket.setdefaulttimeout(10)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=True,  # Don't raise exceptions
        )
        print(f"✅ OTP Email sent to {email}")
        return True
    except socket.timeout:
        print(f"⚠️ Email timeout for {email}, OTP logged above")
        return True  # Return True so signup continues
    except Exception as e:
        print(f"⚠️ Email failed for {email}: {type(e).__name__}")
        return True  # Return True so signup continues
    finally:
        socket.setdefaulttimeout(None)  # Reset timeout


def send_welcome_email(email, full_name):
    """Send welcome email to new user"""
    subject = 'Welcome to FundiGO!'
    message = f'''
    Hi {full_name},
    
    Welcome to FundiGO! Your account has been successfully created.
    
    You can now book technicians for your device repairs or register as a technician to offer your services.
    
    Best regards,
    The FundiGO Team
    '''
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fundigo.com')
    try:
        send_mail(subject, message, from_email, [email], fail_silently=True)
        print(f"✅ Welcome email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send welcome email: {e}")
    return True


def send_verification_status_email(email, status, reason=''):
    """Send technician verification status email"""
    if status == 'approved':
        subject = 'Your Technician Profile Has Been Approved!'
        message = '''
        Congratulations! Your technician profile has been approved.
        
        You can now start accepting booking requests from customers.
        
        Best regards,
        Fundigo Team
        '''
    else:
        subject = 'Your Technician Profile Verification Status'
        message = f'''
        Unfortunately, your technician profile has been rejected.
        
        Reason: {reason}
        
        Please update your profile and resubmit for verification.
        
        Best regards,
        Fundigo Team
        '''
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fundigo.com')
    try:
        send_mail(subject, message, from_email, [email], fail_silently=True)
        print(f"✅ Verification status email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send verification email: {e}")
    return True


def send_booking_notification(email, booking_id, event):
    """Send booking notification email"""
    subject = f'Booking Update - #{booking_id}'
    message = f'''
    Your booking #{booking_id} has been {event}.
    
    Please check your app for more details.
    
    Best regards,
    Fundigo Team
    '''
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fundigo.com')
    try:
        send_mail(subject, message, from_email, [email], fail_silently=True)
        print(f"✅ Booking notification sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send booking notification: {e}")
    return True
