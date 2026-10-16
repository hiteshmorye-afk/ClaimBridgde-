import os
import smtplib
import ssl
from email.message import EmailMessage


class OtpDeliveryError(Exception):
    pass


def send_email_otp(recipient: str, code: str, purpose: str) -> None:
    host = os.environ.get("CLAIMBRIDGE_SMTP_HOST")
    sender = os.environ.get("CLAIMBRIDGE_SMTP_FROM")
    if not host or not sender:
        raise OtpDeliveryError(
            "Email OTP delivery is not configured. Configure a real SMTP provider."
        )

    try:
        port = int(os.environ.get("CLAIMBRIDGE_SMTP_PORT", "587"))
    except ValueError as exc:
        raise OtpDeliveryError("SMTP port configuration is invalid.") from exc

    username = os.environ.get("CLAIMBRIDGE_SMTP_USER")
    password = os.environ.get("CLAIMBRIDGE_SMTP_PASSWORD")
    if bool(username) != bool(password):
        raise OtpDeliveryError("SMTP authentication configuration is incomplete.")

    use_tls = os.environ.get("CLAIMBRIDGE_SMTP_STARTTLS", "true").lower() == "true"
    if not use_tls and not (
        os.environ.get("CLAIMBRIDGE_ENV") == "development"
        and host.lower() in {"localhost", "127.0.0.1", "::1"}
    ):
        raise OtpDeliveryError(
            "Unencrypted SMTP is permitted only for a local development inbox."
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
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if username and password:
                smtp.login(username, password)
            refused = smtp.send_message(message)
            if refused:
                raise OtpDeliveryError("The email provider rejected the message.")
    except OtpDeliveryError:
        raise
    except (OSError, smtplib.SMTPException) as exc:
        raise OtpDeliveryError(
            "The configured email provider could not accept the verification message."
        ) from exc
