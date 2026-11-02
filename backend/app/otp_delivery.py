import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class OtpDeliveryError(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


def is_demo_email_mode_enabled() -> bool:
    value = os.environ.get("CLAIMBRIDGE_EMAIL_DEMO_MODE", "false")
    return value.strip().lower() in {"1", "true", "yes", "on", "demo"}


def send_email_otp(recipient: str, code: str, purpose: str) -> None:
    env_name = (os.environ.get("CLAIMBRIDGE_ENV") or "production").lower()
    if is_demo_email_mode_enabled():
        if env_name == "production":
            raise OtpDeliveryError(
                "Development demo mode is disabled in production.",
                code="demo_email_disabled",
            )

        logger.warning(
            "CLAIMBRIDGE DEMO EMAIL OTP :: recipient=%s purpose=%s code=%s",
            recipient,
            purpose,
            code,
        )
        print(
            f"[ClaimBridge Development Demo Email] {purpose} verification code for {recipient}: {code} "
            "(valid for 10 minutes)"
        )
        return

    host = os.environ.get("CLAIMBRIDGE_SMTP_HOST")
    sender = os.environ.get("CLAIMBRIDGE_SMTP_FROM")
    if not host or not sender:
        raise OtpDeliveryError(
            "Email service is not configured. Please contact the system administrator.",
            code="smtp_not_configured",
        )

    try:
        port = int(os.environ.get("CLAIMBRIDGE_SMTP_PORT", "587"))
    except ValueError as exc:
        raise OtpDeliveryError(
            "Email service is not configured. Please contact the system administrator.",
            code="smtp_not_configured",
        ) from exc

    username = os.environ.get("CLAIMBRIDGE_SMTP_USER")
    password = os.environ.get("CLAIMBRIDGE_SMTP_PASSWORD")
    if not username or not password:
        raise OtpDeliveryError(
            "Email authentication failed. Please check the email service configuration.",
            code="smtp_credentials_invalid",
        )

    use_tls = os.environ.get("CLAIMBRIDGE_SMTP_STARTTLS", "true").lower() == "true"
    if not use_tls and not (
        env_name == "development" and host.lower() in {"localhost", "127.0.0.1", "::1"}
    ):
        raise OtpDeliveryError(
            "Email service is not configured. Please contact the system administrator.",
            code="smtp_not_configured",
        )

    message = EmailMessage()
    message["Subject"] = "ClaimBridge verification code"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Your ClaimBridge {purpose} verification code is {code}. "
        "It expires in 10 minutes and can be used once."
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            if use_tls:
                try:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                except smtplib.SMTPNotSupportedError as exc:
                    raise OtpDeliveryError(
                        "Email sender is not verified for this provider. Please check the email service configuration.",
                        code="sender_not_verified",
                    ) from exc
            try:
                smtp.login(username, password)
            except smtplib.SMTPAuthenticationError as exc:
                raise OtpDeliveryError(
                    "Email authentication failed. Please check the email service configuration.",
                    code="smtp_credentials_invalid",
                ) from exc
            try:
                refused = smtp.send_message(message)
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError) as exc:
                raise OtpDeliveryError(
                    "Email delivery was rejected by the provider. Please try again later.",
                    code="email_delivery_rejected",
                ) from exc
            if refused:
                raise OtpDeliveryError(
                    "Email delivery was rejected by the provider. Please try again later.",
                    code="email_delivery_rejected",
                )
    except OtpDeliveryError:
        raise
    except smtplib.SMTPConnectError as exc:
        raise OtpDeliveryError(
            "Unable to send verification email right now. Please try again later.",
            code="email_provider_unavailable",
        ) from exc
    except (OSError, TimeoutError, smtplib.SMTPException) as exc:
        message_text = str(exc).lower()
        if "sender" in message_text or "mail from" in message_text:
            raise OtpDeliveryError(
                "Email sender is not verified for this provider. Please check the email service configuration.",
                code="sender_not_verified",
            ) from exc
        raise OtpDeliveryError(
            "Unable to send verification email right now. Please try again later.",
            code="email_verification_unavailable",
        ) from exc
