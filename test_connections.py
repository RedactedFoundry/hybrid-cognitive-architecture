# test_connections.py
# Test script to verify Sprint 1 database clients work correctly
# Run this AFTER starting docker-compose services

from clients.redis_client import get_redis_connection
from clients.tigervector_client import get_tigergraph_connection
from core.logging_config import setup_logging
import structlog

def test_sprint1_deliverables():
    """
    Test all Sprint 1 deliverables to ensure they work correctly.
    
    This function tests:
    1. Structured logging (logging_config.py)
    2. Redis connection (redis_client.py)  
    3. TigerGraph connection (tigervector_client.py)
    """
    
    # Test 1: Setup structured logging
    print("🧪 Testing Sprint 1 Deliverables...")
    print("=" * 50)
    
    try:
        setup_logging("DEBUG")
        logger = structlog.get_logger()
        logger.info("Structured logging is working!", test="sprint1")
        print("✅ Structured logging: PASS")
    except Exception as e:
        print(f"❌ Structured logging: FAIL - {e}")
        return False

    # Test 2: Redis connection
    try:
        redis_conn = get_redis_connection()
        if redis_conn:
            # Test basic Redis operation
            redis_conn.set("test_key", "Hello Sprint 1!")
            value = redis_conn.get("test_key")
            assert value == "Hello Sprint 1!"
            redis_conn.delete("test_key")
            print("✅ Redis connection: PASS")
            logger.info("Redis connection successful", test="sprint1")
        else:
            print("❌ Redis connection: FAIL - No connection returned")
            return False
    except Exception as e:
        print(f"❌ Redis connection: FAIL - {e}")
        print("💡 Make sure Redis is running: docker-compose up redis")
        return False

    # Test 3: TigerGraph connection  
    try:
        tg_conn = get_tigergraph_connection()
        if tg_conn:
            # Test basic TigerGraph operation
            version = tg_conn.getVersion()
            print("✅ TigerGraph connection: PASS")
            logger.info("TigerGraph connection successful", version=version, test="sprint1")
        else:
            print("❌ TigerGraph connection: FAIL - No connection returned")
            return False
    except Exception as e:
        print(f"❌ TigerGraph connection: FAIL - {e}")
        print("💡 Make sure TigerGraph is running: docker-compose up tigervector")
        return False

    print("=" * 50)
    print("🎉 All Sprint 1 deliverables working correctly!")
    logger.info("Sprint 1 testing complete", status="success", test="sprint1")
    return True

if __name__ == "__main__":
    test_sprint1_deliverables() 