"""
Email service for sending verification and password reset emails.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from app.models import EmailVerificationToken, PasswordResetToken

User = get_user_model()


class EmailService:
    """Service class for handling email operations"""

    @staticmethod
    def send_verification_email(user):
        """
        Send email verification link to user

        Args:
            user: User instance

        Returns:
            EmailVerificationToken instance
        """
        # Create token (expires in 24 hours)
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24)
        )

        # Generate verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token.token}/"

        # Render email
        subject = "Verify your TerminalTunes account"
        html_message = render_to_string('email/verification_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        plain_message = render_to_string('email/verification_email.txt', {
            'user': user,
            'verification_url': verification_url,
        })

        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return token

    @staticmethod
    def verify_email_token(token_str):
        """
        Verify email token and activate user

        Args:
            token_str: Token string

        Returns:
            dict with 'valid' (bool) and 'user' or 'message'
        """
        try:
            verification_token = EmailVerificationToken.objects.get(
                token=token_str,
                is_used=False
            )

            if not verification_token.is_valid():
                return {'valid': False, 'message': 'Token expired'}

            # Activate user and mark email as verified
            user = verification_token.user
            user.is_active = True

            # Create or update profile
            from app.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.email_verified = True
            profile.save()

            user.save()

            # Mark token as used
            verification_token.is_used = True
            verification_token.save()

            return {'valid': True, 'user': user}

        except EmailVerificationToken.DoesNotExist:
            return {'valid': False, 'message': 'Invalid token'}

    @staticmethod
    def send_password_reset_email(user):
        """
        Send password reset link to user

        Args:
            user: User instance

        Returns:
            PasswordResetToken instance
        """
        # Create token (expires in 1 hour)
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=1)
        )

        # Generate reset URL
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token.token}/"

        # Render email
        subject = "Reset your TerminalTunes password"
        html_message = render_to_string('email/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
        })
        plain_message = render_to_string('email/password_reset_email.txt', {
            'user': user,
            'reset_url': reset_url,
        })

        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return token

    @staticmethod
    def verify_password_reset_token(token_str):
        """
        Verify password reset token

        Args:
            token_str: Token string

        Returns:
            dict with 'valid' (bool) and 'user' or 'message'
        """
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token_str,
                is_used=False
            )

            if not reset_token.is_valid():
                return {'valid': False, 'message': 'Token expired'}

            return {'valid': True, 'user': reset_token.user}

        except PasswordResetToken.DoesNotExist:
            return {'valid': False, 'message': 'Invalid token'}

    @staticmethod
    def mark_password_reset_token_used(token_str):
        """
        Mark password reset token as used

        Args:
            token_str: Token string

        Returns:
            bool: True if successful
        """
        try:
            reset_token = PasswordResetToken.objects.get(token=token_str)
            reset_token.is_used = True
            reset_token.save()
            return True
        except PasswordResetToken.DoesNotExist:
            return False
