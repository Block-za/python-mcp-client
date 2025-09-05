#!/usr/bin/env python3
"""
Setup script for the Chat Application
This script helps initialize the PostgreSQL database and set up the environment.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_requirements():
    """Install required Python packages"""
    print("Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
    except subprocess.CalledProcessError:
        print("Error: Failed to install requirements")
        sys.exit(1)

def create_env_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_example = Path("env_config.txt")
    
    if env_file.exists():
        print("✓ .env file already exists")
        return
    
    if env_example.exists():
        print("Creating .env file from template...")
        with open(env_example, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        print("✓ .env file created. Please update the values in .env")
    else:
        print("Warning: env_config.txt not found. Please create .env file manually")

def check_postgresql():
    """Check if PostgreSQL is available"""
    print("Checking PostgreSQL availability...")
    try:
        import psycopg2
        print("✓ psycopg2 is available")
    except ImportError:
        print("Error: psycopg2 not installed. Please install PostgreSQL client libraries")
        return False
    
    # Try to connect to PostgreSQL
    try:
        # This will use environment variables from .env
        from dotenv import load_dotenv
        load_dotenv()
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'chat_app')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.close()
        print("✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"Warning: Could not connect to PostgreSQL: {e}")
        print("Please ensure PostgreSQL is running and update .env with correct credentials")
        return False

def setup_database():
    """Initialize the database schema"""
    print("Setting up database schema...")
    schema_file = Path("database_schema.sql")
    
    if not schema_file.exists():
        print("Error: database_schema.sql not found")
        return False
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'chat_app')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        
        import psycopg2
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        # Read and execute schema
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(schema_sql)
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Database schema created successfully")
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def main():
    """Main setup function"""
    print("=== Chat Application Setup ===")
    print()
    
    # Check Python version
    check_python_version()
    
    # Install requirements
    install_requirements()
    
    # Create .env file
    create_env_file()
    
    # Check PostgreSQL
    postgres_ok = check_postgresql()
    
    # Setup database if PostgreSQL is available
    if postgres_ok:
        setup_database()
    
    print()
    print("=== Setup Complete ===")
    print()
    print("Next steps:")
    print("1. Update the .env file with your actual configuration")
    print("2. Ensure PostgreSQL is running")
    print("3. Run the application: python app.py")
    print()
    print("Required environment variables:")
    print("- OPENAI_API_KEY: Your OpenAI API key")
    print("- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD: PostgreSQL connection details")
    print("- SECRET_KEY: Flask secret key for sessions")

if __name__ == "__main__":
    main()
