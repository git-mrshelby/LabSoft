import csv
import re
import time
import random
import urllib.parse
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        # Fallback if neither works, though unlikely
        DDGS = None
import httpx
from bs4 import BeautifulSoup

# Standard generic directories to exclude when looking for independent websites
EXCLUSIONS = [
    'yelp.com', 'angi.com', 'homeadvisor.com', 'bbb.org', 'thumbtack.com',
    'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com', 'youtube.com',
    'yellowpages.com', 'superpages.com', 'porch.com', 'expertise.com', 'houzz.com',
    'mapquest.com', 'localyahoo.com', 'chamberofcommerce.com', 'local.yahoo.com',
    'chamber.com', 'forbes.com', 'chicagotribune.com', 'chicagoreader.com',
    'chicagomag.com', 'timeout.com', 'wikipedia.org', 'gov', 'yell.com', 'yellowpages.ca',
    'truelocal.com.au', 'yellow.co.nz', 'goldenpages.ie', 'yellowpages.com.sg', 'brabys.com',
    'tripadvisor.com', 'bing.com', 'google.com', 'apple.com', 'amazon.com',
    'nextdoor.com', 'bark.com', 'fresha.com', 'trustpilot.com', 'glassdoor.com',
    'indeed.com', 'craigslist.org', 'reddit.com', 'quora.com'
]

def extract_emails(text):
    """Extract valid business emails from text, filtering out garbage."""
    if not text: return []
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    valid_emails = []

    garbage_keywords = [
        'sentry.io', 'wixpress', 'wix.com', 'example.com', 'domain.com',
        'yourwebsite.com', 'yell.com', 'yelp', 'yellowpages', 'bbb.org',
        'manta.com', 'apple.com', 'google.com', 'amazon.com', 'sentry', '@12x', '@3x',
        'bytescraper.com', 'teco.com.ar', 'enacom.gob.ar', 'bark.com', 'fresha.com',
        'cloudflare.com', 'wordpress.com', 'squarespace.com', 'godaddy.com',
        'microsoft.com', 'outlook.com/signup', 'github.com', 'sitedomain.com'
    ]

    dummy_patterns = [
        'example', 'sample', 'test', 'yourname', 'email@', 'domain', 'contact@website',
        'user@', 'admin@address', 'info@address', 'someone@', 'name@', 'mail@mail',
        'placeholder', 'changeme', 'noreply', 'no-reply', 'donotreply', 'admin@example'
    ]

    for e in emails:
        e = e.lower().strip()
        if e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.svg', '.webp', '.pdf', '.woff', '.woff2', '.ttf')):
            continue
        if e.endswith(('.gov', '.gov.za', '.edu', '.edu.za', '.ac.za', '.mil', '.org', '.org.za', '.za.com', '.za.net')):
            continue
        if any(bad in e for bad in garbage_keywords) or any(dummy in e for dummy in dummy_patterns):
            continue
        if '@' in e:
            domain_part = e.split('@')[1]
            if '.' not in domain_part or len(domain_part) < 4:
                continue
        valid_emails.append(e)
    return list(set(valid_emails))

def find_email_for_business(company_name, location_hint, phone_fallback=""):
    """Exhaustive search to find a contact email for a lab."""
    # ADVANCED CLEANING: Ampersands and special chars can break queries
    clean_name = re.sub(r' - .*$|\(.*?\)| (Ltd|LLC|Inc|Co|SIA|PTY)\.?$', '', company_name, flags=re.IGNORECASE).strip()
    clean_name = clean_name.replace('&', 'and').replace('+', 'plus')
    
    search_templates = [
        f'"{clean_name}" {location_hint} "yelp" email',
        f'"{clean_name}" {location_hint} "linkedin" email',
        f'"{clean_name}" {phone_fallback} email' if phone_fallback else f'"{clean_name}" {location_hint} email',
        f'"{clean_name}" {location_hint} "contact" "@gmail.com"',
        f'"{clean_name}" {location_hint} "about" contact email',
        f'"{clean_name}" {location_hint} "@gmail.com" OR "@yahoo.com" OR "@outlook.com"',
        f'"{clean_name}" {location_hint} "directory" email',
        f'"{clean_name}" {location_hint} "chamber of commerce" email'
    ]
    
    with DDGS() as ddgs:
        for query in search_templates:
            if not query: continue
            try:
                time.sleep(1.2)
                results = list(ddgs.text(query, max_results=6))
                for req in results:
                    snippet = req.get('body', '') if isinstance(req, dict) else getattr(req, 'body', '')
                    emails = extract_emails(snippet)
                    if emails:
                        return emails[0]
            except Exception:
                continue
    return None

def scrape_google_maps_leads(niche, location, max_leads=10):
    """Scrape lab leads from Google Maps and resolve a contact email for each."""
    maps_query = f"{niche} in {location}"
    maps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(maps_query)}"
    print(f"  [Maps] Searching: {maps_query}")
    
    leads = []
    seen_names = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            try:
                page.goto(maps_url, wait_until='load', timeout=60000)
                time.sleep(5)  
                
                # More robust scrolling to load more results
                for _ in range(5):
                    page.mouse.move(300, 500)
                    page.mouse.wheel(0, 5000)
                    time.sleep(1.5)
                
                # More specific selector for business cards
                cards_locator = page.locator('div[role="article"] a[href*="/maps/place/"]')
                if cards_locator.count() == 0:
                    cards_locator = page.locator('a[href*="/maps/place/"]')
                
                cards_count = min(cards_locator.count(), 30)
                print(f"     [Maps] Found {cards_locator.count()} potential results, checking up to 30...")
                
                for i in range(cards_count):
                    card = cards_locator.nth(i)
                    name = card.get_attribute('aria-label')
                    if not name or name in seen_names: continue
                    seen_names.add(name)
                    
                    try:
                        card.click(timeout=5000)
                        time.sleep(2.5) 
                        sidebar = page.locator('div[role="main"]').last
                        sidebar_html = sidebar.inner_html()
                        
                        # More precise website detection
                        has_website = False
                        website_url = ""
                        if 'data-item-id="authority"' in sidebar_html or 'aria-label="Website"' in sidebar_html:
                            has_website = True
                            ws_match = re.search(r'data-item-id="authority"[^>]*href="(https?://[^"]+)"', sidebar_html)
                            if not ws_match:
                                ws_match = re.search(r'href="(https?://[^"]+)"[^>]*data-item-id="authority"', sidebar_html)
                            if ws_match:
                                website_url = ws_match.group(1)
                        elif 'www.' in sidebar_html:
                            # Check if it's actually a website link or just text containing www.
                            # We look for common website link structures in the sidebar
                            if 'href="http' in sidebar_html and 'www.' in sidebar_html:
                                # Still might be a directory link, check against EXCLUSIONS
                                website_match = re.search(r'href="(https?://[^"]+)"', sidebar_html)
                                if website_match:
                                    ws_url = website_match.group(1).lower()
                                    if not any(ex in ws_url for ex in EXCLUSIONS):
                                        has_website = True
                                        website_url = website_match.group(1)

                        # LabSoft is sold to all labs, whether or not they already
                        # have a website, so we no longer skip leads with sites.

                        email = ""                        
                        # Try to find email in sidebar text first
                        sidebar_text = sidebar.inner_text()
                        candidate_emails = extract_emails(sidebar_text)
                        if candidate_emails: 
                            email = candidate_emails[0]
                        
                        if not email:
                            # Look for mailto links specifically
                            mail_match = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', sidebar_html)
                            if mail_match: email = mail_match.group(1)
                        
                        if not email:
                            phone = ""
                            try:
                                # Try multiple ways to find phone
                                phone_loc = sidebar.locator('button[aria-label*="Phone"]').first
                                if phone_loc.count() > 0:
                                    phone = phone_loc.get_attribute('aria-label').replace('Phone: ', '').strip()
                                else:
                                    # Fallback phone search in text
                                    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', sidebar_text)
                                    if phone_match: phone = phone_match.group(0)
                            except: pass
                            
                            print(f"     [Maps] No email in sidebar for {name}, searching web...")
                            email = find_email_for_business(name, location, phone)
                        
                        if email:
                            leads.append({'Company': name, 'Website': website_url or "No Website (Maps Verified)", 'Emails': email})
                            print(f"     + Found: {name} ({email})")
                            if len(leads) >= max_leads: break
                    except Exception as e: 
                        print(f"     [Maps] Error processing {name}: {e}")
                        continue
            finally: browser.close()
    except Exception as e: print(f"  [Maps Error] {e}")
    return leads

def scrape_yelp_leads(niche, location, max_leads=5):
    """Scrape lab leads from Yelp/directories."""
    # Simpler, more robust query
    queries = [
        f'site:yelp.com/biz/ "{niche}" {location} email',
        f'site:yelp.com/biz/ "{niche}" {location} contact',
        f'"{niche}" {location} "yelp" email'
    ]
    
    leads = []
    try:
        with DDGS() as ddgs:
            for yelp_query in queries:
                print(f"  [Yelp] Searching: {yelp_query}")
                results = list(ddgs.text(yelp_query, max_results=15))
                for r in results:
                    snippet = r.get('body', '')
                    emails = extract_emails(snippet)
                    if emails:
                        title = r.get('title', '').split(' - ')[0].replace(' | Yelp', '').replace(' - Yelp', '')
                        # Dedup by company name
                        if not any(l['Company'] == title for l in leads):
                            leads.append({'Company': title, 'Website': r.get('href', 'Yelp Listing'), 'Emails': emails[0]})
                            if len(leads) >= max_leads: break
                if len(leads) >= max_leads: break
    except Exception as e: print(f"  [Yelp Error] {e}")
    return leads

def scrape_social_leads(max_leads=5):
    """Scrape active 'need lab management software' leads from top social platforms (Twitter, LinkedIn, Reddit, etc)."""
    platforms = [
        'twitter.com', 'linkedin.com', 'facebook.com', 'reddit.com', 'instagram.com', 
        'quora.com', 'youtube.com', 'tiktok.com'
    ]
    
    intent_phrases = [
        '"need lab management software"',
        '"looking for lab management software"',
        '"recommend laboratory software"',
        '"need a LIS system"',
        '"looking for pathology software"',
        '"recommend diagnostic center software"',
        '"lab reporting software recommendations"'
    ]
    
    leads = []
    try:
        with DDGS() as ddgs:
            # Randomly pick a few platform + intent combinations to avoid footprinting
            random.shuffle(platforms)
            random.shuffle(intent_phrases)
            
            for platform in platforms[:4]:
                for intent in intent_phrases[:3]:
                    query = f'site:{platform} {intent} "@gmail.com" OR "@yahoo.com" OR "@outlook.com"'
                    print(f"  [SOCIAL] Hunting: {query}")
                    
                    # Use timelimit='d' for last 24 hours
                    results = list(ddgs.text(query, max_results=10, timelimit='d'))
                    for r in results:
                        snippet = r.get('body', '')
                        emails = extract_emails(snippet)
                        if emails:
                            title = r.get('title', '').split(' - ')[0].replace(' | ' + platform.capitalize(), '')
                            # Clean up title
                            title = re.sub(r' on (Twitter|LinkedIn|Facebook|Instagram|Reddit)', '', title, flags=re.IGNORECASE)
                            
                            if not any(l['Emails'] == emails[0] for l in leads):
                                leads.append({
                                    'Company': title if len(title) < 50 else "Active Lead",
                                    'Website': r.get('href', platform),
                                    'Emails': emails[0],
                                    'Source': 'Social Media'
                                })
                                print(f"     + Social Lead Found: {emails[0]}")
                                if len(leads) >= max_leads: break
                    if len(leads) >= max_leads: break
                if len(leads) >= max_leads: break
    except Exception as e:
        print(f"  [Social Error] {e}")
    
    return leads

def scrape_leads(query, max_leads=10):
    """Master Multi-Source Lead Generator (Maps, Yelp, Social)."""
    # 1. Social Media "Active" Leads (Priority)
    print(f"  [SOCIAL] Checking for active 'need lab software' posts from the last 24 hours...")
    social_leads = scrape_social_leads(max_leads=3) # Target 3 active leads per batch
    
    # 2. Local Lab Leads (Maps/Yelp)
    match = re.findall(r'"([^"]+)"', query)
    if len(match) >= 2:
        niche, location = match[0], match[1]
    else:
        niche, location = query, "Global"

    sources = ['maps', 'yelp']
    random.shuffle(sources)
    
    all_leads = social_leads
    remaining = max_leads - len(all_leads)
    
    if remaining > 0:
        for source in sources:
            print(f"  [{source.upper()}] Hunting leads for {niche} in {location}...")
            if source == 'yelp': batch = scrape_yelp_leads(niche, location, max_leads=remaining)
            else: batch = scrape_google_maps_leads(niche, location, max_leads=remaining)
            
            if batch:
                all_leads.extend(batch)
                if len(all_leads) >= max_leads: break

    return all_leads[:max_leads]

if __name__ == "__main__":
    # Test Yelp specifically
    print("Testing Yelp leads...")
    print(scrape_yelp_leads("Diagnostic Center", "Chicago", max_leads=1))
    
    # Test Maps specifically
    print("\nTesting Maps leads...")
    print(scrape_google_maps_leads("Pathology Lab", "Chicago", max_leads=1))
