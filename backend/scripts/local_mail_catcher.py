"""
ClaimBridge Local Development SMTP Mail Catcher
===============================================
A lightweight, zero-dependency SMTP server for Windows local development on port 1025.
Captures real emails sent by ClaimBridge OTP delivery without external cloud services.
Saves received messages to `backend/dev_inbox.json` for real-time inspection.
"""

import asyncio
import email
from email import policy
import json
import os
from datetime import datetime
from pathlib import Path

INBOX_FILE = Path(__file__).resolve().parent.parent / "dev_inbox.json"


class SMTPDevServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.transport = None
        self.buffer = ""
        self.in_data = False
        self.data_lines = []
        self.mail_from = ""
        self.rcpt_to = []

    def connection_made(self, transport):
        self.transport = transport
        self.transport.write(b"220 ClaimBridge Dev Mail Catcher Ready\r\n")

    def data_received(self, data):
        self.buffer += data.decode("utf-8", errors="replace")
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            self._handle_line(line)

    def _handle_line(self, line):
        if self.in_data:
            if line == ".":
                self.in_data = False
                raw_email = "\r\n".join(self.data_lines)
                self._save_message(raw_email)
                self.data_lines = []
                self.transport.write(b"250 OK: message received\r\n")
            else:
                self.data_lines.append(line)
            return

        upper = line.upper().strip()
        if upper.startswith("EHLO") or upper.startswith("HELO"):
            self.transport.write(b"250-localhost\r\n250 8BITMIME\r\n")
        elif upper.startswith("MAIL FROM:"):
            self.mail_from = line[10:].strip("<> ")
            self.transport.write(b"250 OK\r\n")
        elif upper.startswith("RCPT TO:"):
            recipient = line[8:].strip("<> ")
            self.rcpt_to.append(recipient)
            self.transport.write(b"250 OK\r\n")
        elif upper == "DATA":
            self.in_data = True
            self.data_lines = []
            self.transport.write(b"354 Start mail input; end with <CR><LF>.<CR><LF>\r\n")
        elif upper == "RSET":
            self.mail_from = ""
            self.rcpt_to = []
            self.in_data = False
            self.data_lines = []
            self.transport.write(b"250 OK\r\n")
        elif upper == "NOOP":
            self.transport.write(b"250 OK\r\n")
        elif upper == "QUIT":
            self.transport.write(b"221 2.0.0 Service closing transmission channel\r\n")
            self.transport.close()
        else:
            self.transport.write(b"500 Command unrecognized\r\n")

    def _save_message(self, raw_email: str):
        msg = email.message_from_string(raw_email, policy=policy.default)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()

        entry = {
            "id": datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f"),
            "received_at": datetime.utcnow().isoformat(),
            "from": self.mail_from or msg.get("From", ""),
            "to": self.rcpt_to or [msg.get("To", "")],
            "subject": msg.get("Subject", ""),
            "body": body.strip() if isinstance(body, str) else str(body),
        }

        # Load existing inbox
        inbox = []
        if INBOX_FILE.exists():
            try:
                with open(INBOX_FILE, "r", encoding="utf-8") as f:
                    inbox = json.load(f)
            except Exception:
                inbox = []

        inbox.insert(0, entry)
        # Keep last 100 messages
        inbox = inbox[:100]

        with open(INBOX_FILE, "w", encoding="utf-8") as f:
            json.dump(inbox, f, indent=2)

        print(f"[MailCatcher] Received email To={entry['to']} Subject='{entry['subject']}'")


async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(SMTPDevServerProtocol, "127.0.0.1", 1025)
    print("ClaimBridge Local Dev Mail Catcher listening on 127.0.0.1:1025...")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
