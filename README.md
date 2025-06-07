# Orchids SWE Intern Challenge

This project consists of a backend built with FastAPI and a frontend built with Next.js and TypeScript. The application uses LLMs to clone websites as part of the Orchids SWE Intern challenge.

## Prerequisites

- Python 3.11
- Node.js 18 or higher
- Git
- uv (Python package installer and resolver)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment using uv:
   ```bash
   # Create virtual environment
   uv venv

   # Activate virtual environment
   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

4. Set up your environment variables:
   - Create a `.env` file in the `backend` directory with the following content:
     ```env
     # Choose either 'gemini' or 'claude'
     LLM_CHOICE=claude
     GEMINI_API_KEY=your_gemini_api_key_here
     CLAUDE_API_KEY=your_claude_api_key_here
     ```
   - Get your API keys:
     - [Gemini API key](https://aistudio.google.com/app/apikey)
     - [Claude API key](https://console.anthropic.com/settings/keys)

5. Start the backend server using uv:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Features

- Uses an LLM to make clones of websites
- A history to see previous cloned websites
- A way to easily copy or modify the cloned website

## License

This project is licensed under the MIT License.
