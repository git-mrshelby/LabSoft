"""Sends a single LabSoft test email. Usage: python send_test.py <recipient>"""
import sys
import os
from automated_cold_mailer import send_gen_corders_offer

if __name__ == "__main__":
    recipient = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEST_RECIPIENT", "")
    if not recipient:
        print("Usage: python send_test.py <recipient> (or set TEST_RECIPIENT)")
        sys.exit(1)
    print(f"Sending LabSoft TEST email to {recipient}...")
    ok = send_gen_corders_offer("City Diagnostics", recipient, "Diagnostic Center")
    print("SENT OK" if ok else "SEND FAILED")
