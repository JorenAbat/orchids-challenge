# Orchids SWE Intern Challenge Template

This project consists of a backend built with FastAPI and a frontend built with Next.js and TypeScript.

## Backend

The backend uses `uv` for package management.

### Installation

To install the backend dependencies, run the following command in the backend project directory:

```bash
uv sync
```

### Running the Backend

To run the backend development server, use the following command:

```bash
uv run fastapi dev
```

## Frontend

The frontend is built with Next.js and TypeScript.

### Installation

To install the frontend dependencies, navigate to the frontend project directory and run:

```bash
npm install
```

### Running the Frontend

To start the frontend development server, run:

```bash
npm run dev
```

## Environment Variables & LLM Setup

The backend requires a `.env` file in the `backend` directory to configure your Large Language Model (LLM) provider and API keys.

### 1. Create a `.env` file in `backend/`

Add the following variables:

```
# Choose either 'gemini' or 'claude'
LLM_CHOICE=claude

# Your API keys (add at least the one for your chosen provider)
GEMINI_API_KEY=your_gemini_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

- `LLM_CHOICE`: Set to `gemini` (Google Gemini) or `claude` (Anthropic Claude) depending on which provider you want to use.
- `GEMINI_API_KEY`: Your Google Gemini API key (required if using Gemini).
- `CLAUDE_API_KEY`: Your Anthropic Claude API key (required if using Claude).

### 2. Get Your API Keys
- **Gemini**: [Get a Gemini API key](https://aistudio.google.com/app/apikey)
- **Claude**: [Get a Claude API key](https://console.anthropic.com/settings/keys)

### 3. Switching Providers
- Change the value of `LLM_CHOICE` in your `.env` file to switch between Gemini and Claude.
- Make sure the corresponding API key is present in your `.env` file.

### 4. Restart the Backend
After updating your `.env` file, restart the backend server for changes to take effect.
