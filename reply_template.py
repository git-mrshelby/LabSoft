"""Reply email format (NOT automated). Run: python reply_template.py
Generates reply_preview.html with the same header/footer as the cold email.
Copy-paste the rendered look manually, or send via Gmail when someone replies.
"""

WEBSITE_URL = "https://gencoderssolutions.qzz.io/"
PRICE_PER_MONTH = "$199"

# --- Same branding as automated_cold_mailer.py ---
blue_badge = """
<span style="background-color: #0095f6; color: #fff; border-radius: 50%; display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 10px; font-weight: bold; margin-left: 2px; vertical-align: middle;">&#10003;</span>
"""

custom_logo = """
<div style="background-color: transparent; border: 1px solid #0095f6; border-radius: 50%; width: 65px; height: 65px; display: table; float: right; margin-left: 20px;">
    <div style="display: table-cell; vertical-align: middle; text-align: center; font-family: 'Arial Black', Gadget, sans-serif; line-height: 1.1;">
        <span style="color: #000000; font-size: 9px; letter-spacing: 1px; font-weight: bold;">GEN</span><br>
        <span style="color: #0095f6; font-size: 9px; letter-spacing: 1px; font-weight: bold;">CODERS</span>
    </div>
</div>
"""

header_badge = """
<span style="background-color: #0095f6; color: #fff; border-radius: 50%; display: inline-block; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 10px; font-weight: bold; margin-left: 2px; vertical-align: 2px;">&#10003;</span>
"""

brand_header = f"""
<div style="background-color: transparent; padding: 10px; border-bottom: 2px solid #0095f6; margin-bottom: 15px; text-align: center;">
    <span style="font-family: 'Arial Black', Gadget, sans-serif; font-weight: bold; font-size: 1.2em; letter-spacing: 2px; color: #0095f6;">GEN CODERS {header_badge}</span>
</div>
"""

website_link = f'<a href="{WEBSITE_URL}" style="color: #0095f6; text-decoration: none; font-weight: bold;">{WEBSITE_URL.replace("https://", "").rstrip("/")}</a>'
email_link = '<a href="mailto:gencoderssolutions@gmail.com" style="color: #0095f6; text-decoration: none; font-weight: bold;">gencoderssolutions@gmail.com</a>'

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


def build_reply(business_name, demo_link="https://labsoft-demo.netlify.app/"):
    """Returns the full reply HTML. Same header/footer, LabSoft-adapted body."""
    body_content = f"""
    <p style="margin: 6px 0;">Hi {business_name},</p>
    <p style="margin: 13px 0;">Great to hear from you! As promised, I have prepared a <strong>2-minute LabSoft demo video</strong> showing a full patient-to-report workflow with sample patients, tests and reports.</p>
    <p style="margin: 13px 0;">You can watch the demo video here: <a href="{demo_link}" style="color: #0095f6; text-decoration: none; font-weight: bold;">{demo_link}</a></p>
    <p style="margin: 13px 0;"><strong>Note:</strong> The demo uses placeholder lab name, address and logo - all of it is replaced with your actual business details, free of cost, once we go live.</p>
    <p style="margin: 13px 0;"><strong>The Offer:</strong> <strong>{PRICE_PER_MONTH} per month, flat</strong> - free setup, 30-day trial.</p>
    <p style="margin: 13px 0;"><strong>Next Steps:</strong> Reply me with <strong>"yes"</strong> so that we can schedule a meeting and discuss further about the trial setup.</p>
    <p style="margin: 13px 0;">Looking forward to hearing your thoughts!</p>
    """
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333; font-size: 16px;">
    {brand_header}
    {body_content}
    {signature}
    </body>
    </html>
    """


if __name__ == "__main__":
    html = build_reply("City Diagnostics")
    out = "reply_preview.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Reply format written to {out} - open it in a browser to preview.")
