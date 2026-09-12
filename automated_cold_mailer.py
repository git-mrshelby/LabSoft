import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# --- Configuration (Gen Coders Brand - LabSoft Offer) ---
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

WEBSITE_URL = "https://gencoderssolutions.qzz.io/"
PRICE_PER_MONTH = "$199"


def send_gen_corders_offer(business_name, owner_email, niche, competitor_site="", is_active_search=False):
    """Sends the LabSoft closing cold email from Gen Coders."""
    business_name = str(business_name).strip()
    owner_email = str(owner_email).strip()

    if not SMTP_USER or not SMTP_PASS:
        print("Error: SMTP_USER or SMTP_PASS not set in environment.")
        return False

    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Urgent !! run your whole lab from one simple screen"
    msg['From'] = f"Gen Coders Solutions <{SMTP_USER}>"
    msg['To'] = owner_email

    # Official Meta-Style Verification Badge (Pure CSS, tuned to not stretch text lines)
    blue_badge = """
    <span style="background-color: #0095f6; color: #fff; border-radius: 50%; display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 10px; font-weight: bold; margin-left: 2px; vertical-align: middle;">&#10003;</span>
    """

    # High-End Professional Digital Logo (Transparent Background)
    custom_logo = """
    <div style="background-color: transparent; border: 1px solid #0095f6; border-radius: 50%; width: 65px; height: 65px; display: table; float: right; margin-left: 20px;">
        <div style="display: table-cell; vertical-align: middle; text-align: center; font-family: 'Arial Black', Gadget, sans-serif; line-height: 1.1;">
            <span style="color: #000000; font-size: 9px; letter-spacing: 1px; font-weight: bold;">GEN</span><br>
            <span style="color: #0095f6; font-size: 9px; letter-spacing: 1px; font-weight: bold;">CODERS</span>
        </div>
    </div>
    """

    # Header badge — standalone span nudged up 2px to center against Arial Black caps
    header_badge = """
    <span style="background-color: #0095f6; color: #fff; border-radius: 50%; display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 10px; font-weight: bold; margin-left: 2px; vertical-align: 2px;">&#10003;</span>
    """

    # Premium Brand Header (Transparent Background)
    brand_header = f"""
    <div style="background-color: transparent; padding: 10px; border-bottom: 2px solid #0095f6; margin-bottom: 15px; text-align: center;">
        <span style="font-family: 'Arial Black', Gadget, sans-serif; font-weight: bold; font-size: 1.2em; letter-spacing: 2px; color: #0095f6;">GEN CODERS {header_badge}</span>
    </div>
    """

    # Clickable links (Website + Email only for a clean, professional footer)
    website_link = f'<a href="{WEBSITE_URL}" style="color: #0095f6; text-decoration: none; font-weight: bold;">{WEBSITE_URL.replace("https://", "").rstrip("/")}</a>'
    email_link = f'<a href="mailto:gencoderssolutions@gmail.com" style="color: #0095f6; text-decoration: none; font-weight: bold;">gencoderssolutions@gmail.com</a>'

    signature = f"""
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.3; color: #444; border-top: 1px solid #0095f6; padding-top: 10px; margin-top: 15px;">
        {custom_logo}
        <div style="float: left;">
            <div style="font-size: 1.0em; color: #333;">Best Regards,</div>
            <div style="font-size: 1.2em; font-weight: bold; color: #000;">S . Mohsin {blue_badge}</div>
            <div style="font-size: 0.85em; color: #7f8c8d;">Lead Automation Engineer</div>
            <div style="color: #1a1a1a; font-size: 1.0em;"><strong>Gen Coders Solutions {blue_badge}</strong></div>
        </div>
        <div style="clear: both;"></div>
        <div style="font-size: 0.75em; color: #bdc3c7; font-style: italic; margin-top: 15px; border-top: 1px solid #eee; padding-top: 5px;">
            Website: {website_link}<br>
            Email: {email_link}
        </div>
    </div>
    """

    body_content = f"""
    <p style="margin: 6px 0;">Hi {business_name},</p>
    <p style="margin: 13px 0;">I was reviewing diagnostic labs in your area and <strong>noticed something critical</strong>: every lab software costs $3,000+ and needs weeks of setup. Nothing runs out-of-the-box.</p>
    <p style="margin: 13px 0;">We built <strong>LabSoft</strong> - everything pre-loaded, zero setup:</p>
    <ul style="margin: 10px 0; padding-left: 18px;">
        <li>Registration + test &amp; rate master with ranges &amp; flags</li>
        <li>Single &amp; multi-parameter result entry</li>
        <li>Culture &amp; sensitivity with antibiotic panels (S/I/R)</li>
        <li>Profiles/panels + role logins (Admin, Reception, Tech, Results)</li>
        <li>Billing, refunds + PDF reports on your letterhead</li>
    </ul>
    <p style="margin: 13px 0;"><strong>The Offer:</strong> <strong>{PRICE_PER_MONTH} per month, flat</strong> - free setup, 30-day trial. If your team doesn't report faster, pay nothing.</p>
    <p style="margin: 13px 0;"><strong>Want to see a 2-minute demo video</strong> of a full patient-to-report? Reply "yes" - no call, no pitch.</p>
    """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333; font-size: 16px;">
    {brand_header}
    {body_content}
    {signature}
    </body>
    </html>
    """

    part2 = MIMEText(html, 'html')
    msg.attach(part2)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, owner_email, msg.as_string())
            print(f"LabSoft offer sent to {owner_email}")
            return True
    except Exception as e:
        print(f"Failed to send email to {owner_email}: {e}")
        return False


if __name__ == "__main__":
    recipient = os.environ.get("TEST_RECIPIENT", "")
    if not recipient:
        print("Set TEST_RECIPIENT env var to a target address.")
    else:
        print(f"Sending LabSoft cold email to {recipient}...")
        send_gen_corders_offer("City Diagnostics", recipient, "Diagnostic Center")
