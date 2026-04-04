#!/usr/bin/env python3
"""
Setup script for Content Automation System
Guides users through initial configuration
"""
import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_step(step_num, text):
    print(f"[{step_num}] {text}")

def ask_question(question, default=""):
    """Ask user a question with optional default"""
    if default:
        answer = input(f"    {question} [{default}]: ").strip()
        return answer if answer else default
    else:
        return input(f"    {question}: ").strip()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def create_venv():
    """Create virtual environment"""
    print_step(1, "Creating virtual environment...")
    if not os.path.exists("venv"):
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("   ✅ Virtual environment created")
    else:
        print("   ✅ Virtual environment already exists")

def install_dependencies():
    """Install Python dependencies"""
    print_step(2, "Installing dependencies...")
    pip_path = "venv\\Scripts\\pip.exe" if os.name == "nt" else "venv/bin/pip"
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    print("   ✅ Dependencies installed")

def create_env_file():
    """Create .env file from example"""
    print_step(3, "Creating configuration file...")
    if os.path.exists(".env"):
        print("   ⚠️  .env file already exists")
        if ask_question("    Overwrite? (y/n)", "n").lower() != "y":
            print("   ⏭️  Skipping .env creation")
            return
    
    # Copy example file
    if os.path.exists(".env.example"):
        with open(".env.example", "r") as f:
            content = f.read()
        with open(".env", "w") as f:
            f.write(content)
        print("   ✅ .env file created from template")
        print("   📝 Edit .env to add your API keys (optional)")
    else:
        print("   ❌ .env.example not found")

def initialize_database():
    """Initialize the database"""
    print_step(4, "Initializing database...")
    try:
        from src.core.database import init_db
        init_db()
        print("   ✅ Database initialized")
    except Exception as e:
        print(f"   ⚠️  Database initialization will happen on first run: {e}")

def print_next_steps():
    """Print next steps for the user"""
    print_header("🎉 Setup Complete!")
    
    print("Next steps:")
    print()
    print("1. (Optional) Edit .env file to add API keys:")
    print("   - OPENAI_API_KEY or ANTHROPIC_API_KEY for AI content generation")
    print("   - Social media API keys for auto-posting")
    print()
    print("2. Start the application:")
    if os.name == "nt":
        print("   venv\\Scripts\\activate")
        print("   uvicorn src.main:app --reload")
    else:
        print("   source venv/bin/activate")
        print("   uvicorn src.main:app --reload")
    print()
    print("3. Open your browser to:")
    print("   - Dashboard: http://localhost:8000/")
    print("   - API Docs:  http://localhost:8000/docs")
    print()
    print("The system will start collecting data and generating content automatically!")
    print("You can monitor everything from the dashboard.")

def main():
    print_header("🤖 Content Automation System - Setup Wizard")
    
    print("This wizard will guide you through the setup process.")
    print("All configuration is optional - the system works out of the box!")
    print()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    create_venv()
    
    # Install dependencies
    install_dependencies()
    
    # Create .env file
    create_env_file()
    
    # Initialize database
    initialize_database()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()