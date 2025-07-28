# clients/redis_client.py
import redis
import os

def get_redis_connection():
    """
    Establishes a connection to the Redis server.

    Reads connection details from environment variables.
    Includes basic error handling for connection failures.

    Returns:
        A Redis connection object if successful, otherwise None.
    """
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))

        # The decode_responses=True argument ensures that Redis returns strings, not bytes.
        r = redis.Redis(host=host, port=port, decode_responses=True)

        # Ping the server to confirm the connection is alive.
        r.ping()
        print("Successfully connected to Redis.")
        return r
    except redis.exceptions.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        return None 