# Use a dedicated Python environment for Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy all files from the current directory to the container
COPY . /app

# Install dependencies including fpdf2 for reports
RUN pip install --no-cache-dir \
    beautifulsoup4 \
    playwright \
    duckduckgo_search \
    httpx \
    dnspython \
    pytz \
    fpdf2

# Ensure Playwright browsers are installed within the container
RUN playwright install chromium

# The command to run your automated lead generation engine
# Run unbuffered so logs appear instantly
CMD ["python", "-u", "global_lead_engine.py"]
