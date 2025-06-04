# Required imports for the application
from fastapi import FastAPI, HTTPException  # FastAPI for API framework, HTTPException for error handling
from fastapi.middleware.cors import CORSMiddleware  # Enable cross-origin requests
from pydantic import BaseModel  # Data validation
from playwright.async_api import async_playwright  # Website scraping
import google.generativeai as genai  # AI model integration
import os  # Environment variables
from dotenv import load_dotenv  # Load environment variables
import logging
from urllib.parse import urlparse
import re
import json
from datetime import datetime
import uuid
from pathlib import Path
import asyncio

# Initialize environment variables
load_dotenv()

# Configure Gemini AI model
# Using the latest model for optimal performance
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Initialize FastAPI application
app = FastAPI()

# Configure CORS for frontend communication
# Frontend runs on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Create clones directory if it doesn't exist
CLONES_DIR = Path("clones")
CLONES_DIR.mkdir(exist_ok=True)

# Input validation model
class URLInput(BaseModel):
    url: str  # URL string validation

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Helper to validate URLs
PRIVATE_IP_PREFIXES = (
    '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.', '127.', '169.254.'
)
def is_valid_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    if not parsed.hostname:
        return False
    # Block localhost and private IPs
    if parsed.hostname == 'localhost' or any(parsed.hostname.startswith(prefix) for prefix in PRIVATE_IP_PREFIXES):
        return False
    return True

SCRAPING_ERROR_LOG = Path("scraping_errors.log")

async def scrape_website(url: str, max_retries: int = 3, timeout: int = 20) -> dict:
    """
    Scrapes website content and styling with retry and timeout logic.
    Uses Playwright for JavaScript rendering support.
    Logs errors to a file.
    """
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            async def do_scrape():
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()
                    await page.goto(url)
                    content = await page.content()
                    styles = await page.evaluate("""() => {
                        const styles = {};
                        const bodyStyles = window.getComputedStyle(document.body);
                        styles.backgroundColor = bodyStyles.backgroundColor;
                        styles.color = bodyStyles.color;
                        styles.fontFamily = bodyStyles.fontFamily;
                        return styles;
                    }""")
                    await browser.close()
                    return {"content": content, "styles": styles}
            # Add timeout
            return await asyncio.wait_for(do_scrape(), timeout=timeout)
        except Exception as e:
            last_exception = e
            # Log error
            with open(SCRAPING_ERROR_LOG, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.now().isoformat()}] Attempt {attempt} failed for {url}: {str(e)}\n")
            if attempt < max_retries:
                await asyncio.sleep(1)  # brief pause before retry
    # If all retries failed
    raise HTTPException(status_code=502, detail="Failed to scrape the website after several attempts. The site may be blocking bots, too slow, or unavailable.")

# Robust HTML extraction from AI response
def extract_html_from_ai_response(text):
    # Try to extract from a markdown code block first
    code_block = re.search(r"```(?:html)?\s*([\s\S]+?)```", text)
    if code_block:
        html = code_block.group(1)
    else:
        # Try to extract the first <html>...</html> block
        html_block = re.search(r"(<html[\s\S]+?</html>)", text, re.IGNORECASE)
        if html_block:
            html = html_block.group(1)
        else:
            # Fallback: return the whole text
            html = text
    return html.strip()

def generate_clone(content: dict) -> str:
    """
    Generates website clone using Gemini AI.
    Processes scraped content and styles to create a similar website.
    """
    try:
        # Prepare AI prompt
        prompt = f"""
        Create a similar-looking website based on this content and styling:
        Content: {content['content']}
        Styles: {content['styles']}
        
        Generate only the HTML code that recreates this website's look and feel.
        Keep the same color scheme, layout, and overall design.
        """
        # Generate clone using AI
        response = model.generate_content(prompt)
        html = extract_html_from_ai_response(response.text)
        return html
    except Exception as e:
        # Handle AI generation errors
        raise HTTPException(status_code=500, detail=f"Error generating clone: {str(e)}")

def save_clone(url: str, html: str) -> dict:
    """Save the cloned website to a file and return metadata"""
    try:
        # Generate unique ID and filename
        clone_id = str(uuid.uuid4())
        filename = f"{clone_id}.html"
        filepath = CLONES_DIR / filename
        
        # Save HTML file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        
        # Create metadata
        metadata = {
            "id": clone_id,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "filename": filename
        }
        
        # Save metadata
        metadata_path = CLONES_DIR / f"{clone_id}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        
        return metadata
    except Exception as e:
        logging.error(f"Error saving clone: {e}")
        raise HTTPException(status_code=500, detail="Failed to save clone")

@app.post("/clone")
async def clone_website(url_input: URLInput):
    if not is_valid_url(url_input.url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe URL")
    try:
        logging.info(f"Cloning website: {url_input.url}")
        # Scrape website content
        content = await scrape_website(url_input.url)
        # Generate clone
        clone = generate_clone(content)
        # Limit HTML size (e.g., 1MB)
        if len(clone.encode('utf-8')) > 1_000_000:
            raise HTTPException(status_code=413, detail="Generated HTML is too large.")
        
        # Save clone and get metadata
        metadata = save_clone(url_input.url, clone)
        
        # Return result with metadata
        return {"html": clone, "metadata": metadata}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in /clone: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")

@app.get("/history")
async def get_history():
    """Get list of all cloned websites"""
    try:
        history = []
        # Read all JSON metadata files
        for metadata_file in CLONES_DIR.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    history.append(metadata)
            except Exception as e:
                logging.error(f"Error reading metadata file {metadata_file}: {e}")
                continue
        
        # Sort by timestamp, newest first
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history
    except Exception as e:
        logging.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get history")

@app.get("/preview/{filename}")
async def preview_clone(filename: str):
    """Get the HTML content of a cloned website"""
    try:
        filepath = CLONES_DIR / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Clone not found")
        
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
        
        return {"html": html}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error previewing clone: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview clone")

@app.get("/download/{filename}")
async def download_clone(filename: str):
    """Download a cloned website"""
    try:
        filepath = CLONES_DIR / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Clone not found")
        
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
        
        return {"html": html}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error downloading clone: {e}")
        raise HTTPException(status_code=500, detail="Failed to download clone")

@app.get("/")
async def read_root():
    """Health check endpoint"""
    return {"message": "Website Cloning API is running"}

# Development server configuration
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Placeholder for Playwright browser reuse (advanced):
# browser = None
# @app.on_event("startup")
# async def startup_event():
#     global browser
#     playwright = await async_playwright().start()
#     browser = await playwright.chromium.launch()
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     global browser
#     if browser:
#         await browser.close()
