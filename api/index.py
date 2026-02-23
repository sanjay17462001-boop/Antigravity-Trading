"""
Vercel Python Serverless Function Entry Point
Exposes the FastAPI app via Mangum ASGI adapter for AWS Lambda / Vercel.
"""

import sys
from pathlib import Path

# Add project root to Python path so all imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI app
from dashboard.api.main import app

# Vercel uses the ASGI app directly when using @vercel/python runtime
# The app variable is detected automatically by Vercel
