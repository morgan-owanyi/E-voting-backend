"""
Clean OTP Service for E-Voting System
Handles OTP generation, email sending with timeout, and verification
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from accounts.models import EmailOTP
import threading
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """Service class to handle all OTP-related operations"""
    
    EMAIL_TIMEOUT = 5  # seconds
    OTP_LENGTH = 6
    OTP_EXPIRY = 600  # 10 minutes
    
    @classmethod
    def generate_otp(cls, email: str) -> EmailOTP:
        """
        Generate a new OTP for the given email.
        Marks all previous unused OTPs for this email as used.
        
        Args:
            email: The email address to generate OTP for
            
        Returns:
            EmailOTP: The newly created OTP object
        """
        # Invalidate all previous unused OTPs for this email
        EmailOTP.objects.filter(email=email, used=False).update(used=True)
        
        # Create new OTP
        otp_obj = EmailOTP.create_otp(
            email=email,
            length=cls.OTP_LENGTH,
            expiry_seconds=cls.OTP_EXPIRY
        )
        
        logger.info(f"Generated OTP for {email}: {otp_obj.code}")
        return otp_obj
    
    @classmethod
    def send_otp_email(cls, email: str, otp_code: str, election_title: str, reg_no: str) -> dict:
        """
        Send OTP via email with timeout protection.
        
        Args:
            email: Recipient email address
            otp_code: The OTP code to send
            election_title: Title of the election
            reg_no: Voter registration number
            
        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        result = {'success': False, 'error': None}
        
        def send_email():
            try:
                email_body = f"""Hello,

Your One-Time Password (OTP) for voting is: {otp_code}

IMPORTANT INFORMATION:
• This OTP can only be used once
• It will expire in 10 minutes
• Election: {election_title}
• Registration Number: {reg_no}

Please do not share this OTP with anyone.

Thank you for participating in the election!
KuraVote Team"""

                send_mail(
                    subject=f'Your Voting OTP - {election_title}',
                    message=email_body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kuravote.com'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                result['success'] = True
                logger.info(f"OTP email sent successfully to {email}")
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        
        # Start email sending in daemon thread with timeout
        email_thread = threading.Thread(target=send_email, daemon=True)
        email_thread.start()
        email_thread.join(timeout=cls.EMAIL_TIMEOUT)
        
        if email_thread.is_alive():
            # Timeout occurred
            result['error'] = 'Email service timeout'
            logger.warning(f"Email sending timed out for {email}")
        
        return result
    
    @classmethod
    def verify_otp(cls, email: str, otp_code: str) -> dict:
        """
        Verify an OTP code for the given email.
        
        Args:
            email: The email address
            otp_code: The OTP code to verify
            
        Returns:
            dict: {'valid': bool, 'message': str, 'otp_obj': EmailOTP or None}
        """
        try:
            otp_obj = EmailOTP.objects.get(email=email, code=otp_code, used=False)
            
            if not otp_obj.is_valid():
                logger.warning(f"Expired OTP attempted for {email}")
                return {
                    'valid': False,
                    'message': 'OTP has expired. Please request a new one.',
                    'otp_obj': None
                }
            
            # Mark OTP as used
            otp_obj.mark_used()
            logger.info(f"OTP verified successfully for {email}")
            
            return {
                'valid': True,
                'message': 'OTP verified successfully',
                'otp_obj': otp_obj
            }
            
        except EmailOTP.DoesNotExist:
            logger.warning(f"Invalid OTP attempted for {email}")
            return {
                'valid': False,
                'message': 'Invalid OTP code. Please check and try again.',
                'otp_obj': None
            }
    
    @classmethod
    def get_masked_email(cls, email: str) -> str:
        """
        Return a masked version of the email for display.
        Example: user@example.com -> use***@example.com
        
        Args:
            email: The email to mask
            
        Returns:
            str: Masked email address
        """
        try:
            local, domain = email.split('@')
            if len(local) <= 3:
                masked_local = local[0] + '***'
            else:
                masked_local = local[:3] + '***'
            return f"{masked_local}@{domain}"
        except Exception:
            return "***@***.***"
