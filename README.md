# RBC Wealth Assistant

AI-powered chatbot that helps users discover and invest in RBC mutual funds.

## Setup

```bash
# Install dependencies
pip install gradio google-generativeai google-cloud-firestore python-dotenv

# Create .env file
GEMINI_API_KEY=your_key_here
PROJECT_ID=your_gcp_project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Run
python app.py
```

App runs on http://localhost:7860

## What It Does

- Search for mutual funds
- Get fund details and performance
- Compare funds side-by-side
- Generate personalized portfolios
- Capture lead information

## Example Queries

- "I want to invest $50,000 for retirement"
- "Show me low-risk Canadian equity funds"
- "Compare RBF460 and RBF559"
- "Create a conservative portfolio for 20 years"

## System Flow

```
User Message
    ↓
Gradio Interface
    ↓
Gemini AI (decides what to do)
    ↓
Execute Function (search, compare, etc.)
    ↓
Query Firestore Database
    ↓
Format & Display Results
```

## Files

- `app.py` - Main application
- `wealth_server.py` - Business logic functions
- `utils/common.py` - Embedding utilities
- `.env` - Configuration (you create this)

## Troubleshooting

**Functions not working?**
- Check Gemini API key is valid
- Verify Firestore credentials
- Ensure wealth_server.py exists

**Connection errors?**
- Check .env file paths
- Verify GCP project ID
- Confirm Firestore is enabled

## Requirements

- Python 3.8+
- Google Cloud Project with Firestore
- Gemini API key
- Fund data in Firestore 'funds' collection