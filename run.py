#!/usr/bin/env python
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory as this script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from api.index import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
