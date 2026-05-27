#!/usr/bin/env python3
"""
KINYO AI Video Generation Platform - Startup Script
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
STREAMLIT_APP_DIR = PROJECT_ROOT / "streamlit_app"

def main():
    """Start Streamlit application"""
    
    print("=" * 70)
    print("KINYO AI Video Generation Platform")
    print("=" * 70)
    print("App directory:", STREAMLIT_APP_DIR)
    print("=" * 70)
    print()
    
    try:
        # Directly call streamlit command (not through python -m)
        cmd = [
            "streamlit",
            "run",
            str(STREAMLIT_APP_DIR / "app.py"),
            "--server.address=127.0.0.1",
            "--server.port=8501",
        ]
        
        subprocess.run(cmd, check=True)
        
    except FileNotFoundError:
        print("\n" + "=" * 70)
        print("ERROR: 'streamlit' command not found!")
        print("=" * 70)
        print("\nPlease install streamlit first:")
        print()
        print("  pip install streamlit")
        print()
        print("Or if you have multiple Python environments, activate the correct one first.")
        print("=" * 70)
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        print("\nError starting Streamlit:", e)
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nShutting down Streamlit server...")
        sys.exit(0)

if __name__ == "__main__":
    main()
