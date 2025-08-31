#!/usr/bin/env python3
"""
Simple test script to verify the Flask application starts correctly
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    print("✅ Flask app imported successfully")
    
    # Test basic route
    with app.test_client() as client:
        response = client.get('/')
        if response.status_code == 200:
            print("✅ Homepage route works")
        else:
            print(f"❌ Homepage returned status {response.status_code}")
    
    print("✅ Application is ready to run")
    print("\nTo start the server:")
    print("1. Set up your .env file with Discord OAuth credentials")
    print("2. Run: python app.py")
    print("3. Visit: http://localhost:5000")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Install dependencies with: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Error: {e}")
