import csv
import os
import datetime
import smtplib
from fpdf import FPDF

# --- Configuration ---
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SUMMARY_RECIPIENT = os.environ.get("SUMMARY_RECIPIENT")
LOG_FILE = "sent_log.csv"
MASTER_DB = "leads.csv"


def generate_pdf():
    """Generates a PDF report from the current cycle's sent_log.csv entries."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(200, 10, txt="Gen Coders Pvt Ltd - Hourly Outreach Report", ln=True, align='C')
    pdf.set_font("Helvetica", size=10)
    pdf.cell(200, 10, txt=f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(5)

    # Count total leads in master DB
    total_leads = 0
    if os.path.exists(MASTER_DB):
        with open(MASTER_DB, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            total_leads = sum(1 for _ in reader)

    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(200, 8, txt=f"Total Leads in Database: {total_leads}", ln=True, align='C')
    pdf.ln(5)

    # --- THIS CYCLE'S EMAILS ---
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(200, 8, txt="Emails Sent This Cycle:", ln=True, align='L')
    pdf.ln(2)

    # Table Header
    pdf.set_fill_color(0, 149, 246)  # Meta Blue
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(30, 8, "Time", 1, 0, 'C', True)
    pdf.cell(45, 8, "Business", 1, 0, 'C', True)
    pdf.cell(55, 8, "Email", 1, 0, 'C', True)
    pdf.cell(30, 8, "Niche", 1, 0, 'C', True)
    pdf.cell(30, 8, "Location", 1, 1, 'C', True)

    # Table Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=8)

    cycle_count = 0
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    safe_time = row[0].encode('latin-1', 'replace').decode('latin-1')
                    safe_name = row[1][:25].encode('latin-1', 'replace').decode('latin-1')
                    safe_email = row[2][:30].encode('latin-1', 'replace').decode('latin-1')
                    safe_niche = (row[3][:15] if len(row) > 3 else "").encode('latin-1', 'replace').decode('latin-1')
                    safe_loc = (row[4][:15] if len(row) > 4 else "").encode('latin-1', 'replace').decode('latin-1')

                    pdf.cell(30, 7, safe_time[-8:], 1)  # Just show HH:MM:SS
                    pdf.cell(45, 7, safe_name, 1)
                    pdf.cell(55, 7, safe_email, 1)
                    pdf.cell(30, 7, safe_niche, 1)
                    pdf.cell(30, 7, safe_loc, 1, 1)
                    cycle_count += 1

    if cycle_count == 0:
        pdf.ln(5)
        pdf.set_font("Helvetica", 'I', 10)
        pdf.cell(200, 10, txt="No new leads matched the filter criteria this cycle.", ln=True, align='C')

    # Summary footer
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(200, 8, txt=f"Fresh Emails Sent This Hour: {cycle_count}", ln=True, align='C')
    pdf.cell(200, 8, txt=f"Lifetime Total Leads: {total_leads}", ln=True, align='C')

    pdf_name = f"Gen_Coders_Report_{datetime.datetime.now().strftime('%Y_%m_%d_%H%M')}.pdf"
    pdf.output(pdf_name)
    print(f"PDF generated: {pdf_name}")
    return pdf_name


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_summary_email(pdf_path, cycle_count=0):
    """Emails the PDF report to SUMMARY_RECIPIENT, then clears the cycle log."""
    if not SMTP_USER or not SMTP_PASS or not SUMMARY_RECIPIENT:
        print("Error: SMTP_USER, SMTP_PASS or SUMMARY_RECIPIENT not set in environment.")
        return

    now = datetime.datetime.now()
    msg = MIMEMultipart()
    msg['Subject'] = f"Gen Coders Report - {now.strftime('%Y-%m-%d %H:%M')} | {cycle_count} Fresh Leads"
    msg['From'] = f"Gen Coders System <{SMTP_USER}>"
    msg['To'] = SUMMARY_RECIPIENT

    body = (
        f"Hourly Outreach Report\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Fresh emails sent this cycle: {cycle_count}\n\n"
        f"See attached PDF for details."
    )
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(pdf_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(pdf_path)}',
            )
            msg.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, SUMMARY_RECIPIENT, msg.as_string())
            print(f"Report sent to {SUMMARY_RECIPIENT}")

            # Clear the cycle log AFTER successful send so next hour starts fresh
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                print("Cycle log cleared for next run.")

            # Clean up the PDF file
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    except Exception as e:
        print(f"Failed to send summary report: {e}")


if __name__ == "__main__":
    report_file = generate_pdf()
    if report_file:
        send_summary_email(report_file)
