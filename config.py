# config.py
# Configuration file for Hybrid AI Council
# This shows how environment variables work with our database clients

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

TIGERGRAPH_HOST = os.getenv("TIGERGRAPH_HOST", "http://localhost")
TIGERGRAPH_PASSWORD = os.getenv("TIGERGRAPH_PASSWORD", "tigergraph")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Print current config (for testing)
if __name__ == "__main__":
    print("🔧 Current Configuration:")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"TigerGraph: {TIGERGRAPH_HOST}")
    print(f"Log Level: {LOG_LEVEL}") 