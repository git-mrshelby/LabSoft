import datetime
import pytz
import os
import random
import csv
import time
import hashlib
import socket
import smtplib
import dns.resolver
from automated_cold_mailer import send_gen_corders_offer
from leads_scraper import scrape_leads
from generate_pdf_summary import generate_pdf, send_summary_email
from urllib.parse import urlparse
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import httpx

# --- Ultimate Global Strategy (24/7 Automation) ---
# Free Gmail: 500/day via web UI but ~100/day via SMTP (what this bot uses).
# 3 outreach + 1 report per cycle = max 96/day, under the SMTP cap.
# Watch logs for "TooManyRecipients" / "Exceeded message limit" - if seen, drop to 2.
EMAILS_PER_HOUR = 3
LOG_FILE = "sent_log.csv"
MASTER_DB = "leads.csv"

NICHES = [
    "Diagnostic Center", "Pathology Lab", "Medical Laboratory", "Clinical Laboratory",
    "Diagnostic Lab", "Medical Diagnostic Center", "Pathology Center", "Blood Test Lab",
    "Radiology & Diagnostic Center", "Diagnostic Imaging Center", "Clinical Pathology Lab",
    "Molecular Diagnostics Lab", "Microbiology Lab", "Biochemistry Lab", "Histopathology Lab",
    "Health Screening Center", "Medical Testing Laboratory", "Reference Laboratory"
]

# Mapping each country to its major official business directories
COUNTRIES = {
    "USA": {
        "tz": "US/Eastern",
        "cities": ["New York", "Chicago", "Houston", "Dallas", "Miami", "Los Angeles", "Atlanta", "Phoenix",
                   "Philadelphia", "San Antonio", "San Diego", "Denver", "Seattle", "Boston", "Nashville",
                   "Portland", "Austin", "Charlotte", "Indianapolis", "Columbus", "San Jose", "Jacksonville",
                   "Fort Worth", "Memphis", "Baltimore", "Milwaukee", "Tucson", "Fresno", "Sacramento", "Mesa"],
        "directories": ["yellowpages.com", "yelp.com", "manta.com", "bbb.org", "angi.com", "homeadvisor.com", "superpages.com", "chamberofcommerce.com"]
    },
    "UK": {
        "tz": "Europe/London",
        "cities": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Sheffield", "Bristol",
                   "Edinburgh", "Leicester", "Coventry", "Nottingham", "Newcastle", "Brighton", "Cardiff",
                   "Belfast", "Southampton", "Plymouth", "Reading", "Derby"],
        "directories": ["yell.com", "yelp.co.uk", "thomsonlocal.com", "118.com", "scoop.co.uk", "cylex-uk.co.uk"]
    },
    "Canada": {
        "tz": "Canada/Eastern",
        "cities": ["Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City",
                   "Hamilton", "Kitchener", "London", "Victoria", "Halifax", "Saskatoon", "Regina",
                   "Kelowna", "Barrie", "Windsor", "Sudbury", "Thunder Bay"],
        "directories": ["yellowpages.ca", "yelp.ca", "411.ca", "canpages.ca", "bbb.org", "goldbook.ca", "n49.com"]
    },
    "Australia": {
        "tz": "Australia/Sydney",
        "cities": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Newcastle",
                   "Wollongong", "Hobart", "Geelong", "Townsville", "Cairns", "Darwin", "Toowoomba",
                   "Ballarat", "Bendigo", "Launceston", "Mackay", "Rockhampton"],
        "directories": ["yellowpages.com.au", "truelocal.com.au", "yelp.com.au", "whitepages.com.au", "hotfrog.com.au", "startlocal.com.au"]
    },
    "New Zealand": {
        "tz": "Pacific/Auckland",
        "cities": ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Palmerston North",
                   "Napier", "Nelson", "Rotorua", "New Plymouth", "Whangarei", "Invercargill", "Hastings"],
        "directories": ["yellow.co.nz", "finda.co.nz", "yelp.co.nz", "localist.co.nz", "nzpages.co.nz"]
    },
    "Ireland": {
        "tz": "Europe/Dublin",
        "cities": ["Dublin", "Cork", "Galway", "Limerick", "Waterford", "Drogheda", "Dundalk", "Swords",
                   "Bray", "Navan", "Kilkenny", "Ennis", "Tralee", "Carlow", "Athlone"],
        "directories": ["goldenpages.ie", "yelp.ie", "yourlocal.ie", "bizlocate.ie", "inform.ie"]
    },
    "Singapore": {
        "tz": "Asia/Singapore",
        "cities": ["Singapore City", "Jurong", "Tampines", "Woodlands", "Bedok", "Ang Mo Kio"],
        "directories": ["yellowpages.com.sg", "yelp.com.sg", "streetdirectory.com", "thesmartlocal.com"]
    },
    "South Africa": {
        "tz": "Africa/Johannesburg",
        "cities": ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein",
                   "East London", "Pietermaritzburg", "Nelspruit", "Polokwane", "Kimberley", "Rustenburg"],
        "directories": ["brabys.com", "yellowpages.co.za", "snupit.co.za", "sayellow.com", "activeweb.co.za"]
    }
}


def get_all_sent_emails():
    """Loads ALL previously contacted emails from both leads.csv and sent_log.csv into a set.
    This is the SINGLE SOURCE OF TRUTH for deduplication."""
    sent = set()

    # 1. Load from master leads database
    if os.path.exists(MASTER_DB):
        with open(MASTER_DB, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_email = row.get('Email')
                if raw_email:
                    email = str(raw_email).strip().lower()
                    if email:
                        sent.add(email)

    # 2. Load from session log (covers current run + any unsent reports)
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    sent.add(row[2].strip().lower())

    return sent


def verify_email_exists(email):
    """Verify that an email address can receive mail by checking DNS MX records.
    Returns True if the domain has valid MX records, False otherwise."""
    try:
        domain = email.split('@')[1]
        # Check if domain has MX records (can receive email)
        mx_records = dns.resolver.resolve(domain, 'MX')
        if mx_records:
            print(f"  [MX OK] {domain} has {len(mx_records)} mail server(s)")
            return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        print(f"  [MX FAIL] {domain} - domain does not exist or has no MX records")
        return False
    except dns.resolver.NoNameservers:
        print(f"  [MX FAIL] {domain} - no nameservers responding")
        return False
    except Exception as e:
        print(f"  [MX WARN] Could not verify {domain}: {e}")
        # If DNS check fails due to network issues, allow it through (benefit of the doubt)
        return True
    return False


def verify_no_website(company_name, found_url):
    """Verify that the target company does NOT have their own independent website.
    Returns True if the company has NO website (good lead), False if they DO have one (skip).
    
    Our email pitch says 'you have no online presence' — we must verify this is true."""
    
    # If the scraper already tagged it as a directory listing, that's a good sign
    if 'No Website' in found_url or 'Directory' in found_url:
        print(f"  [SITE CHECK] {company_name} - Found via directory (no own website) [OK]")
        return True
    
    # If found_url is from a known directory/aggregator, the business likely has no website
    directory_indicators = [
        'yelp.com', 'yellowpages', 'yell.com', 'manta.com', 'bbb.org', 'angi.com',
        'homeadvisor.com', 'thumbtack.com', 'bark.com', 'cybo.com', 'hotfrog.com',
        'truelocal.com', 'finda.co.nz', 'goldenpages.ie', 'superpages.com',
        'yellowpages.ca', 'yellowpages.com.au', 'brabys.com', 'snupit.co.za',
        'n49.com', 'chamberofcommerce.com', 'porch.com', '118.com', 'thomsonlocal.com'
    ]
    found_domain = urlparse(found_url).netloc.lower() if found_url.startswith('http') else ''
    if any(d in found_domain for d in directory_indicators):
        print(f"  [SITE CHECK] {company_name} - Listed on directory only [OK]")
        return True
    
    # The URL is an actual website — this business HAS a website, skip them
    if found_url.startswith('http') and found_domain:
        # Check if the website is actually reachable (not a dead link)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
            }
            resp = httpx.head(found_url, timeout=5, headers=headers, follow_redirects=True)
            if resp.status_code < 400:
                print(f"  [SITE CHECK] {company_name} - HAS a live website at {found_domain} [X]")
                return False  # They have a website, skip this lead
            else:
                print(f"  [SITE CHECK] {company_name} - Website returned {resp.status_code} (dead) [OK]")
                return True  # Website is dead/down, treat as no website
        except Exception:
            # Can't reach the site — might be down, treat as no website
            print(f"  [SITE CHECK] {company_name} - Website unreachable (dead link) [OK]")
            return True
    
    # No URL at all — definitely no website
    print(f"  [SITE CHECK] {company_name} - No website found [OK]")
    return True


def generate_unique_query(sent_emails):
    """Generates a search query designed to find NEW leads not already in our database.
    Uses timestamp-seeded randomization to avoid repeating the same combos."""

    # Seed with current time to ensure different picks each run
    random.seed(time.time())

    country = random.choice(list(COUNTRIES.keys()))
    city = random.choice(COUNTRIES[country]['cities'])
    niche = random.choice(NICHES)

    # Vary the query format to get different DuckDuckGo results each time
    query_templates = [
        f'"{niche}" "{city}" email contact',
        f'"{niche}" near "{city}" "@gmail.com"',
        f'"{niche}" "{city}" phone email site:yelp.com',
        f'"{niche}" in "{city}" contact us email',
        f'"{city}" "{niche}" laboratory email',
        f'best "{niche}" "{city}" contact email address',
        f'"{niche}" services "{city}" email',
        f'top "{niche}" companies "{city}" contact',
        f'"{niche}" "{city}" directory listing email',
        f'"{niche}" "{city}" lab manager email contact',
        f'"{niche}" near me "{city}" reviews email',
        f'local "{niche}" "{city}" phone email address',
    ]

    query = random.choice(query_templates)

    return country, city, niche, query


def run_global_outreach_cycle():
    """Performs Live Directory Scrape, Email Outreach, Database Append, and Immediate PDF Reporting.
    
    FLOW:
    1. Load ALL previously sent emails (leads.csv + sent_log.csv)
    2. Scrape fresh leads using randomized queries
    3. Filter out ANY email we've ever contacted before
    4. Send exactly 4 new emails
    5. Log each to sent_log.csv AND append to leads.csv
    6. Generate PDF with ONLY this cycle's leads
    7. Email the PDF report
    """
    print(f"\n{'='*70}")
    print(f"--- Gen Coders Global Outreach: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    print(f"{'='*70}")

    # 1. Load the COMPLETE history of emails we've ever sent
    already_sent = get_all_sent_emails()
    print(f"[DEDUP] Loaded {len(already_sent)} previously contacted emails from database.")

    # 2. Track what we send THIS cycle (for the PDF report)
    cycle_leads = []
    sent_this_cycle = 0
    attempts = 0
    max_attempts = EMAILS_PER_HOUR * 15  # Give plenty of room to find 4 fresh ones

    while sent_this_cycle < EMAILS_PER_HOUR and attempts < max_attempts:
        attempts += 1
        country, city, niche, query = generate_unique_query(already_sent)

        print(f"\n[ATTEMPT {attempts}] Searching: {niche} in {city}, {country}")
        print(f"[QUERY] {query}")

        # Scrape leads from DuckDuckGo
        new_leads = scrape_leads(query, max_leads=10)

        if not new_leads:
            print(f"  -> No leads found. Trying different parameters...")
            time.sleep(1)
            continue

        for lead in new_leads:
            if sent_this_cycle >= EMAILS_PER_HOUR:
                break

            email_list = lead.get('Emails', '').split(',')
            if not email_list or not email_list[0]:
                continue

            email = email_list[0].strip().lower()

            # --- STRICT DUPLICATE CHECK against entire history ---
            if email in already_sent:
                print(f"  [SKIP] Already contacted: {email}")
                continue

            email_domain = email.split('@')[1] if '@' in email else ""
            
            # --- ALLOW PUBLIC PROVIDERS AND BUSINESS DOMAINS ---
            # Labs often use their own domain (info@citylabs.com), so we accept
            # both public providers and custom domains. MX + cross-confirmation
            # checks below still protect against junk.
            allowed_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'ymail.com', 'live.com', 'msn.com', 'proton.me', 'protonmail.com']
            is_public = any(email_domain == provider for provider in allowed_providers)
            if not is_public and len(email_domain) > 40:
                print(f"  [SKIP] Suspicious domain email: {email}")
                continue

            # --- ENHANCED TRASH FILTER ---
            spam_platforms = [
                '@sentry', 'wix.', 'domain.', 'example.', 'test@', 'support@',
                'info@fresha', 'team@bark', '@tiktok', '@google', '@facebook',
                'noreply', 'no-reply', 'notifications', 'mailer-daemon', 'dev@',
                '@bytescraper', 'kalathiya', '@apple.com', '@amazon.com',
                'admin@', 'webmaster@', 'postmaster@', 'hostmaster@',
                'sales@hubspot', '@cloudflare', '@wordpress', '@squarespace'
            ]
            if any(spam in email for spam in spam_platforms) or len(email) > 40:
                print(f"  [SKIP] Spam/platform email: {email}")
                continue

            # --- BLOCK NON-ENGLISH TLDs (we only target English-speaking countries) ---
            email_domain = email.split('@')[1] if '@' in email else ""
            blocked_tlds = ['.ru', '.cn', '.jp', '.kr', '.ar', '.br', '.mx', '.in', '.pk',
                            '.bd', '.vn', '.th', '.id', '.tr', '.ir', '.sa', '.eg', '.pl',
                            '.cz', '.hu', '.ro', '.bg', '.ua', '.by', '.kz', '.tw']
            if any(email_domain.endswith(tld) for tld in blocked_tlds):
                print(f"  [SKIP] Non-English TLD: {email}")
                continue

            # --- BLOCK LISTICLE/AGGREGATOR COMPANY NAMES ---
            company_name = lead['Company'].lower()
            junk_patterns = ['best ', 'top ', 'list of', ' vs ', 'review', 'how to',
                             'guide', 'tips', 'comparison', 'ranking', 'rated',
                             'directory', 'conference', 'summit', 'expo', 'awards', 'forum',
                             'available on', 'for sale', 'buy ', 'sell ']
            if any(junk in company_name for junk in junk_patterns):
                print(f"  [SKIP] Junk/aggregator name: {lead['Company']}")
                continue

            # --- CROSS-CONFIRMATION (STRICT) ---
            company_words = [w.lower() for w in lead['Company'].replace(',', '').replace('.', '').split() if len(w) > 2]

            is_confirmed = False
            generic_handles = ['enquiries', 'sales', 'info', 'contact', 'admin', 'office', 'support', 'hello', 'mail', 'team']
            email_handle = email.split('@')[0].lower()
            
            # Generic handles (highly reliable when found via directory/social)
            if any(handle in email_handle for handle in generic_handles):
                is_confirmed = True

            # Public email providers: email handle should contain part of company name
            else:
                for word in company_words:
                    if word in email_handle:
                        is_confirmed = True
                        break

            if not is_confirmed:
                print(f"  [SKIP] Unconfirmed: {email} vs '{lead['Company']}'")
                continue

            # --- VERIFY EMAIL EXISTS (MX Record Check) ---
            if not verify_email_exists(email):
                print(f"  [SKIP] Email domain has no MX records: {email}")
                continue

            # Note: LabSoft is sold to labs regardless of whether they already
            # have a website, so the old "no website" requirement is skipped.

            # --- SEND THE EMAIL ---
            is_active = (lead.get('Source') == 'Social Media')
            print(f"\n  >>> SENDING {'[ACTIVE SEARCH]' if is_active else ''} to: {lead['Company']} ({email})")
            
            success = send_gen_corders_offer(
                lead['Company'], 
                email, 
                niche, 
                lead.get('Website', 'your website'),
                is_active_search=is_active
            )

            if success:
                # Add to sent set IMMEDIATELY so we don't send again this cycle
                already_sent.add(email)

                # Log to sent_log.csv (for PDF report)
                log_sent_email(lead['Company'], email, niche, city, country, source=lead.get('Source', 'Search'))

                # Append to master leads.csv (for cross-run dedup)
                save_to_master_db(lead['Company'], lead.get('Website', 'No Website'), email)

                cycle_leads.append({
                    'company': lead['Company'],
                    'email': email,
                    'niche': niche,
                    'city': city,
                    'country': country,
                    'source': lead.get('Source', 'Search')
                })

                sent_this_cycle += 1
                print(f"  [OK] {sent_this_cycle}/{EMAILS_PER_HOUR} emails sent this cycle.")

            time.sleep(2)  # Rate limiting

        time.sleep(1)  # Pause between search attempts

    # --- GENERATE & SEND REPORT ---
    print(f"\n{'='*70}")
    print(f"Cycle complete: {sent_this_cycle}/{EMAILS_PER_HOUR} fresh emails sent.")
    print(f"Total attempts: {attempts}")
    print(f"{'='*70}")

    # Generate PDF report for THIS cycle only
    report_file = generate_pdf()
    if report_file:
        send_summary_email(report_file, sent_this_cycle)
        print("PDF Report emailed to configured SUMMARY_RECIPIENT.")
    else:
        print("No report generated.")


def log_sent_email(company_name, email, niche="", city="", country="", source="Search"):
    """Logs sent emails to sent_log.csv for the hourly PDF report."""
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, company_name, email, niche, city, country, source])


def save_to_master_db(company, website, email):
    """Appends lead to Master leads.csv. This file persists across runs via git."""
    file_exists = os.path.exists(MASTER_DB) and os.path.getsize(MASTER_DB) > 0

    # Check if file has header
    has_header = False
    if file_exists:
        with open(MASTER_DB, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('Company'):
                has_header = True

    with open(MASTER_DB, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists or not has_header:
            writer.writerow(['Company', 'Website', 'Email'])
        writer.writerow([company, website, email])


if __name__ == "__main__":
    run_global_outreach_cycle()
