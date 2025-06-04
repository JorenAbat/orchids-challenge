# Import necessary libraries
from fastapi import FastAPI, HTTPException  # FastAPI for creating the API, HTTPException for error handling
from fastapi.middleware.cors import CORSMiddleware  # For handling cross-origin requests
from pydantic import BaseModel  # For data validation
from playwright.async_api import async_playwright  # For website scraping
import google.generativeai as genai  # For AI website generation
import os  # For accessing environment variables
from dotenv import load_dotenv  # For loading environment variables from .env file

# Load environment variables from .env file
# This is where we store our API key securely
load_dotenv()

# Set up the Gemini AI model
# We configure it with our API key from the .env file
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
# Create a model instance that we'll use to generate website clones
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Create our FastAPI application
app = FastAPI()

# Add CORS middleware to allow our frontend to communicate with the backend
# This is necessary because our frontend and backend run on different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Our frontend will run on port 3000
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Define the structure of our input data
# This ensures that when someone sends a URL to our API, it's in the correct format
class URLInput(BaseModel):
    url: str  # The URL should be a string

async def scrape_website(url: str) -> dict:
    """
    Scrapes a website and returns its content and styling information.
    Uses Playwright to handle JavaScript-rendered content.
    """
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to URL
            await page.goto(url)
            
            # Get page content
            content = await page.content()
            
            # Extract styling information
            styles = await page.evaluate("""() => {
                const styles = {};
                // Get computed styles for body
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
        # If anything goes wrong, raise an error
        raise HTTPException(status_code=500, detail=f"Error scraping website: {str(e)}")

def generate_clone(content: dict) -> str:
    """
    Generate a clone of the website using Gemini AI.
    This function:
    1. Takes the scraped content and styles
    2. Creates a prompt for the AI
    3. Gets the AI to generate a similar website
    """
    try:
        # Create a prompt that tells the AI what to do
        prompt = f"""
        Create a similar-looking website based on this content and styling:
        Content: {content['content']}
        Styles: {content['styles']}
        
        Generate only the HTML code that recreates this website's look and feel.
        Keep the same color scheme, layout, and overall design.
        """
        
        # Ask the AI to generate the clone
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # If anything goes wrong, raise an error
        raise HTTPException(status_code=500, detail=f"Error generating clone: {str(e)}")

@app.post("/clone")
async def clone_website(url_input: URLInput):
    """
    This is our main API endpoint that:
    1. Takes a URL from the user
    2. Scrapes the website
    3. Generates a clone
    4. Returns the cloned HTML
    """
    try:
        # First, scrape the website
        content = await scrape_website(url_input.url)
        
        # Then, generate the clone
        clone = generate_clone(content)
        
        # Return the cloned HTML
        return {"html": clone}
    except Exception as e:
        # If anything goes wrong, raise an error
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_root():
    """Simple endpoint to check if our API is running"""
    return {"message": "Website Cloning API is running"}

# This allows us to run the file directly with Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
