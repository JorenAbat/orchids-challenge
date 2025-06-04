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

async def scrape_website(url: str) -> dict:
    """
    Scrapes website content and styling.
    Uses Playwright for JavaScript rendering support.
    """
    try:
        async with async_playwright() as p:
            # Initialize browser
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to target URL
            await page.goto(url)
            
            # Extract page content
            content = await page.content()
            
            # Extract styling information
            styles = await page.evaluate("""() => {
                const styles = {};
                // Extract computed styles
                const bodyStyles = window.getComputedStyle(document.body);
                styles.backgroundColor = bodyStyles.backgroundColor;
                styles.color = bodyStyles.color;
                styles.fontFamily = bodyStyles.fontFamily;
                return styles;
            }""")
            
            await browser.close()
            return {
                "content": content,
                "styles": styles
            }
    except Exception as e:
        # Handle scraping errors
        raise HTTPException(status_code=500, detail=f"Error scraping website: {str(e)}")

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
        # Return result
        return {"html": clone}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in /clone: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")

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
