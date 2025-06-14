# Required imports for the application
from fastapi import FastAPI, HTTPException  # FastAPI for API framework, HTTPException for error handling
from fastapi.middleware.cors import CORSMiddleware  # Enable cross-origin requests
from pydantic import BaseModel  # Data validation
import os  # Environment variables
from dotenv import load_dotenv  # Load environment variables
import logging
from urllib.parse import urlparse, urljoin
import re
import json
from datetime import datetime
import uuid
from pathlib import Path
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from .llm_providers import get_llm_provider

# Initialize environment variables
load_dotenv()

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize LLM provider
llm_provider = get_llm_provider()

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
    Scrapes website content and CSS using requests and BeautifulSoup.
    Preserves real <img src> links as absolute URLs in the HTML.
    """
    logger.info(f"Starting website scraping for URL: {url}")
    last_exception = None
    MAX_CSS_LENGTH = 10000  # Sensible default for CSS length
    DEFAULT_IMG_CSS = 'img { max-width: 100%; height: auto; }\n'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Scraping attempt {attempt}/{max_retries}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail=f"Failed to fetch website: {response.status}")
                    
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract CSS from style tags
                    css = DEFAULT_IMG_CSS
                    for style in soup.find_all('style'):
                        css += style.string + '\n' if style.string else ''
                    
                    # Extract CSS from link tags
                    for link in soup.find_all('link', rel='stylesheet'):
                        if link.get('href'):
                            css_url = urljoin(url, link['href'])
                            try:
                                async with session.get(css_url, headers=headers) as css_response:
                                    if css_response.status == 200:
                                        css += await css_response.text() + '\n'
                            except Exception as e:
                                logger.warning(f"Failed to fetch CSS from {css_url}: {e}")
                    
                    # Update image URLs to absolute paths
                    for img in soup.find_all('img'):
                        src = img.get('src')
                        if src:
                            img['src'] = urljoin(url, src)
                    
                    # Get only the visible content (above the fold)
                    body = soup.find('body')
                    if body:
                        # Remove elements that are likely below the fold
                        for element in body.find_all(['script', 'style', 'noscript']):
                            element.decompose()
                        
                        # Keep only the first few sections
                        sections = body.find_all(['div', 'section', 'article'], recursive=False)
                        for section in sections[3:]:  # Keep only first 3 major sections
                            section.decompose()
                    
                    # Truncate CSS to sensible length
                    if len(css) > MAX_CSS_LENGTH:
                        logger.info(f"Truncating CSS from {len(css)} to {MAX_CSS_LENGTH} characters.")
                        css = css[:MAX_CSS_LENGTH]
                    
                    return {"content": str(soup), "styles": css}
                    
        except Exception as e:
            last_exception = e
            logger.error(f"Scraping attempt {attempt} failed: {str(e)}")
            # Log error
            with open(SCRAPING_ERROR_LOG, "a", encoding="utf-8") as logf:
                logf.write(f"[{datetime.now().isoformat()}] Attempt {attempt} failed for {url}: {str(e)}\n")
            if attempt < max_retries:
                logger.info(f"Waiting before retry...")
                await asyncio.sleep(1)  # brief pause before retry
    
    # If all retries failed
    logger.error("All scraping attempts failed")
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

def truncate_css(css: str, max_length: int = 10000) -> str:
    """Truncate CSS to a sensible length if needed."""
    if len(css) > max_length:
        logger.info(f"Truncating CSS from {len(css)} to {max_length} characters.")
        return css[:max_length]
    return css

def truncate_content(content: str, max_length: int = 10000) -> str:
    """Truncate HTML/content to a sensible length if needed."""
    if len(content) > max_length:
        logger.info(f"Truncating content from {len(content)} to {max_length} characters.")
        return content[:max_length]
    return content

def generate_clone(content: dict, truncate_css_flag: bool = False, truncate_content_flag: bool = False) -> str:
    """
    Generates website clone using the configured LLM provider.
    Processes scraped content and styles to create a similar website.
    Tries with full CSS/content first, and on quota/token error, retries with truncated CSS/content.
    """
    try:
        logger.info("Starting AI clone generation...")
        css = content['styles']
        html_content = content['content']
        if truncate_css_flag:
            css = truncate_css(css)
        if truncate_content_flag:
            html_content = truncate_content(html_content)
        # Prepare AI prompt with specific instructions about styling
        prompt = f"""
        Create a similar-looking website based on this content and styling:
        Content: {html_content}
        Styles: {css}
        
        Generate only the HTML code that recreates this website's look and feel.
        Follow these specific guidelines:
        1. Keep the same color scheme, layout, and overall design
        2. PRESERVE ALL ORIGINAL IMAGE URLs - do not replace them with placeholders
        3. Use standard web-safe fonts if the original font is not available
        4. Keep CSS simple and avoid complex transformations
        5. Use semantic HTML elements where possible
        6. Ensure all styles are properly closed and valid
        7. Keep the HTML structure clean and well-formatted
        8. Avoid inline styles where possible - use a style tag instead
        9. Make sure all CSS properties are valid and properly formatted
        10. Maintain all original image dimensions (width/height attributes)
        11. Do NOT use placeholder comments or generic content such as <!-- Original navigation items --> or <!-- Original slider/hero content -->. If you cannot reconstruct a section, OMIT IT entirely rather than using a placeholder.
        
        Return only the HTML code with embedded CSS.
        """
        logger.info(f"Sending request to {os.getenv('LLM_CHOICE', 'gemini').upper()} AI...")
        # Generate clone using AI
        response = llm_provider.generate_content(prompt)
        logger.info("Received response from AI")
        html = extract_html_from_ai_response(response)
        
        # Validate and clean up the HTML
        html = clean_generated_html(html)
        
        logger.info("Successfully extracted and cleaned HTML from AI response")
        return html
    except Exception as e:
        # Check for quota/token error and retry with truncated CSS/content
        error_message = str(e)
        if (not truncate_css_flag or not truncate_content_flag) and ("quota" in error_message.lower() or "token" in error_message.lower() or "429" in error_message):
            logger.warning("Quota/token error detected. Retrying with truncated CSS and content.")
            return generate_clone(content, truncate_css_flag=True, truncate_content_flag=True)
        logger.error(f"Error in AI clone generation: {error_message}")
        # Handle AI generation errors
        raise HTTPException(status_code=500, detail=f"Error generating clone: {error_message}")

def clean_generated_html(html: str) -> str:
    """
    Cleans and validates the generated HTML to ensure it's properly formatted
    and doesn't contain broken elements.
    """
    try:
        # Remove any broken base64 images
        html = re.sub(r'url\([\'"]?data:image[^)]+\)', '', html)
        
        # Remove any extremely long strings (likely broken base64)
        html = re.sub(r'[A-Za-z0-9+/]{1000,}', '', html)
        
        # Ensure style tags are properly closed
        html = re.sub(r'<style[^>]*>(?!.*</style>)', '<style>', html)
        
        # Remove any invalid CSS properties
        invalid_props = [
            r'background-image:\s*url\([^)]{1000,}\)',
            r'content:\s*url\([^)]{1000,}\)',
            r'url\([^)]{1000,}\)'
        ]
        for prop in invalid_props:
            html = re.sub(prop, '', html)
        
        # Ensure all quotes are properly closed
        html = re.sub(r'([^\\])"([^"]*?)(?<!\\)"', r'\1"\2"', html)
        html = re.sub(r"([^\\])'([^']*?)(?<!\\)'", r"\1'\2'", html)
        
        return html
    except Exception as e:
        logger.error(f"Error cleaning HTML: {str(e)}")
        return html  # Return original HTML if cleaning fails

def save_clone(url: str, html: str) -> dict:
    """Save the cloned website to a file and return metadata"""
    try:
        logger.info("Starting clone save process...")
        # Generate unique ID and filename
        clone_id = str(uuid.uuid4())
        filename = f"{clone_id}.html"
        filepath = CLONES_DIR / filename
        
        logger.info(f"Saving HTML file: {filename}")
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
        
        logger.info("Saving metadata...")
        # Save metadata
        metadata_path = CLONES_DIR / f"{clone_id}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        
        logger.info("Clone saved successfully")
        return metadata
    except Exception as e:
        logger.error(f"Error saving clone: {e}")
        raise HTTPException(status_code=500, detail="Failed to save clone")

@app.post("/clone")
async def clone_website(url_input: URLInput):
    logger.info(f"Received clone request for URL: {url_input.url}")
    if not is_valid_url(url_input.url):
        logger.warning(f"Invalid URL provided: {url_input.url}")
        raise HTTPException(status_code=400, detail="Invalid or unsafe URL")
    try:
        # Scrape website content
        logger.info("Starting website scraping phase...")
        content = await scrape_website(url_input.url)
        
        # Generate clone
        logger.info("Starting clone generation phase...")
        clone = generate_clone(content)
        
        # Limit HTML size (e.g., 1MB)
        if len(clone.encode('utf-8')) > 1_000_000:
            logger.warning("Generated HTML exceeds size limit")
            raise HTTPException(status_code=413, detail="Generated HTML is too large.")
        
        # Save clone and get metadata
        logger.info("Starting clone save phase...")
        metadata = save_clone(url_input.url, clone)
        
        logger.info("Clone process completed successfully")
        # Return result with metadata
        return {"html": clone, "metadata": metadata}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /clone: {e}")
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
