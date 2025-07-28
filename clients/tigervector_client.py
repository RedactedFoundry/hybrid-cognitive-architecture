# clients/tigervector_client.py
import pyTigerGraph as tg
import os

def get_tigergraph_connection():
    """
    Establishes a connection to the TigerGraph server.

    Reads connection details from environment variables.
    Includes basic error handling for connection failures.

    Returns:
        A TigerGraph connection object if successful, otherwise None.
    """
    try:
        host = os.getenv("TIGERGRAPH_HOST", "http://localhost")
        # The default password is set in our docker-compose.yaml
        password = os.getenv("TIGERGRAPH_PASSWORD", "tigergraph")

        # pyTigerGraph uses a specific port for the REST API
        conn = tg.TigerGraphConnection(host=host, restppPort="14240", password=password)

        # Get a token to verify the connection is successful
        conn.getToken()
        print("Successfully connected to TigerGraph.")
        return conn
    except Exception as e:
        print(f"Error connecting to TigerGraph: {e}")
        return None 