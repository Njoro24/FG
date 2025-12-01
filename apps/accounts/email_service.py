import os
from django.core.mail import send_mail
from django.conf import settings

# Initialize Brevo (Sendinblue) API - optional
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
FROM_EMAIL = os.environ.get('BREVO_FROM_EMAIL', 'fundigo.noreply@gmail.com')
FROM_NAME = os.environ.get('BREVO_FROM_NAME', 'FundiGO')

# Try to import Brevo SDK
try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False


def send_email_via_django(to_email, subject, html_content, text_content=None):
    """Send email using Django's built-in SMTP (Gmail)"""
    try:
        send_mail(
            subject=subject,
            message=text_content or '',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_content,
            fail_silently=False,
        )
        print(f"✅ Email sent to {to_email} via Django SMTP")
        return True
    except Exception as e:
        print(f"❌ Django SMTP email failed: {e}")
        return False


def send_email_via_brevo(to_email, to_name, subject, html_content, text_content=None):
    """Send email using Brevo (Sendinblue) API, fallback to Django SMTP"""
    
    # Try Brevo first if available and configured
    if BREVO_AVAILABLE and BREVO_API_KEY:
        try:
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email, "name": to_name or to_email}],
                sender={"email": FROM_EMAIL, "name": FROM_NAME},
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            response = api_instance.send_transac_email(send_smtp_email)
            print(f"✅ Email sent to {to_email} via Brevo (ID: {response.message_id})")
            return True
        except Exception as e:
            print(f"⚠️ Brevo failed: {e}, falling back to Django SMTP")
    
    # Fallback to Django SMTP (Gmail)
    return send_email_via_django(to_email, subject, html_content, text_content)


def send_otp_email(email, otp):
    """Send OTP email using Brevo"""
    # Always log OTP to console for debugging
    print(f"📧 OTP for {email}: {otp}")
    
    subject = 'Your FundiGO OTP Verification Code'
    
    html_content = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">FundiGO</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2 style="color: #333;">Your Verification Code</h2>
            <p style="color: #666; font-size: 16px;">Use this code to verify your email address:</p>
            <div style="background: #667eea; color: white; font-size: 32px; font-weight: bold; padding: 20px; text-align: center; border-radius: 10px; letter-spacing: 8px; margin: 20px 0;">
                {otp}
            </div>
            <p style="color: #999; font-size: 14px;">This code expires in 10 minutes.</p>
            <p style="color: #999; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
        </div>
        <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
            © 2024 FundiGO. All rights reserved.
        </div>
    </div>
    '''
    
    text_content = f'''
Your FundiGO OTP is: {otp}

This code will expire in 10 minutes.
If you didn't request this code, please ignore this email.

Best regards,
The FundiGO Team
'''
    
    return send_email_via_brevo(email, None, subject, html_content, text_content)


def send_welcome_email(email, full_name):
    """Send welcome email to new user"""
    subject = 'Welcome to FundiGO!'
    
    html_content = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to FundiGO!</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2 style="color: #333;">Hi {full_name}! 👋</h2>
            <p style="color: #666; font-size: 16px;">Your account has been successfully created.</p>
            <p style="color: #666; font-size: 16px;">You can now:</p>
            <ul style="color: #666; font-size: 16px;">
                <li>Book verified technicians for your device repairs</li>
                <li>Track your bookings in real-time</li>
                <li>Pay securely via M-Pesa or cash</li>
            </ul>
            <a href="https://fundigo25.netlify.app/dashboard" style="display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin-top: 20px;">Go to Dashboard</a>
        </div>
    </div>
    '''
    
    return send_email_via_brevo(email, full_name, subject, html_content)


def send_verification_status_email(email, status, reason=''):
    """Send technician verification status email"""
    if status == 'approved':
        subject = 'Your Technician Profile Has Been Approved! ✅'
        html_content = '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Congratulations! 🎉</h1>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <h2 style="color: #333;">Your Profile is Approved!</h2>
                <p style="color: #666; font-size: 16px;">You can now start accepting booking requests from customers.</p>
                <a href="https://fundigo25.netlify.app/technician/dashboard" style="display: inline-block; background: #10b981; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin-top: 20px;">View Dashboard</a>
            </div>
        </div>
        '''
    else:
        subject = 'Technician Profile Verification Update'
        html_content = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #ef4444; padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Verification Update</h1>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <p style="color: #666; font-size: 16px;">Unfortunately, your profile verification was not successful.</p>
                <p style="color: #666; font-size: 16px;"><strong>Reason:</strong> {reason}</p>
                <p style="color: #666; font-size: 16px;">Please update your profile and resubmit for verification.</p>
            </div>
        </div>
        '''
    
    return send_email_via_brevo(email, None, subject, html_content)


def send_booking_notification(email, booking_id, event):
    """Send booking notification email"""
    subject = f'Booking Update - #{booking_id}'
    
    html_content = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Booking Update</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2 style="color: #333;">Booking #{booking_id}</h2>
            <p style="color: #666; font-size: 16px;">Your booking has been <strong>{event}</strong>.</p>
            <a href="https://fundigo25.netlify.app/dashboard" style="display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin-top: 20px;">View Details</a>
        </div>
    </div>
    '''
    
    return send_email_via_brevo(email, None, subject, html_content)
