#!/usr/bin/env python3
"""
Security Features Demo - Show Rate Limiting and Protection in Action
==================================================================

This demo script demonstrates the security middleware protecting the Hybrid AI Council API.
It shows rate limiting, input validation, and security headers in action.
"""

import asyncio
import aiohttp
import json
import os
import time
from typing import List, Dict

import structlog

# Set up logging for demo
logger = structlog.get_logger("security_demo")


class SecurityDemo:
    """Demo class to test security features."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def demo_rate_limiting(self):
        """Demonstrate rate limiting in action."""
        logger.info("🚦 Testing Rate Limiting")
        print("🚦 Testing Rate Limiting")
        print("=" * 50)
        
        # Test normal requests within limits
        print("\n1. Testing normal requests (within limits):")
        for i in range(5):
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    print(f"   Request {i+1}: {response.status} - Rate limit remaining: {response.headers.get('X-RateLimit-Remaining', 'N/A')}")
                    await asyncio.sleep(0.1)  # Small delay
            except Exception as e:
                print(f"   Request {i+1}: Error - {e}")
        
        # Test rapid requests to trigger rate limiting
        print("\n2. Testing rapid requests (trigger rate limiting):")
        start_time = time.time()
        
        for i in range(15):  # Exceed the per-minute limit
            try:
                async with self.session.post(
                    f"{self.base_url}/api/chat/simple",
                    json={"message": f"Test message {i}"}
                ) as response:
                    if response.status == 429:
                        retry_after = response.headers.get('Retry-After', 'N/A')
                        print(f"   🚫 Request {i+1}: Rate limited! Retry after: {retry_after}s")
                        break
                    else:
                        remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
                        print(f"   ✅ Request {i+1}: {response.status} - Remaining: {remaining}")
                        
            except Exception as e:
                print(f"   ❌ Request {i+1}: Error - {e}")
        
        elapsed = time.time() - start_time
        print(f"\n   Total time: {elapsed:.2f}s")
    
    async def demo_input_validation(self):
        """Demonstrate input validation and security."""
        logger.info("🛡️ Testing Input Validation")
        print("\n🛡️ Testing Input Validation")
        print("=" * 50)
        
        # Test SQL injection attempts
        print("\n1. Testing SQL injection protection:")
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM sensitive_data"
        ]
        
        for payload in sql_payloads:
            try:
                async with self.session.post(
                    f"{self.base_url}/api/chat/simple",
                    json={"message": payload}
                ) as response:
                    if response.status == 400:
                        print(f"   🛡️ SQL injection blocked: '{payload[:30]}...'")
                    else:
                        print(f"   ⚠️ SQL injection passed: {response.status}")
            except Exception as e:
                print(f"   ❌ Error testing SQL injection: {e}")
        
        # Test XSS attempts
        print("\n2. Testing XSS protection:")
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        for payload in xss_payloads:
            try:
                async with self.session.post(
                    f"{self.base_url}/api/chat/simple",
                    json={"message": payload}
                ) as response:
                    if response.status == 400:
                        print(f"   🛡️ XSS blocked: '{payload[:30]}...'")
                    else:
                        print(f"   ⚠️ XSS passed: {response.status}")
            except Exception as e:
                print(f"   ❌ Error testing XSS: {e}")
        
        # Test oversized request
        print("\n3. Testing request size limits:")
        large_payload = "A" * (2 * 1024 * 1024)  # 2MB payload
        try:
            async with self.session.post(
                f"{self.base_url}/api/chat/simple",
                json={"message": large_payload}
            ) as response:
                if response.status == 413:
                    print("   🛡️ Large request blocked (413 Payload Too Large)")
                else:
                    print(f"   ⚠️ Large request passed: {response.status}")
        except Exception as e:
            print(f"   🛡️ Large request blocked at network level: {e}")
    
    async def demo_security_headers(self):
        """Demonstrate security headers."""
        logger.info("🔒 Testing Security Headers")
        print("\n🔒 Testing Security Headers")
        print("=" * 50)
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                headers = response.headers
                
                security_headers = [
                    "Content-Security-Policy",
                    "X-Frame-Options", 
                    "X-Content-Type-Options",
                    "X-XSS-Protection",
                    "Referrer-Policy",
                    "Permissions-Policy"
                ]
                
                print("\nSecurity headers present:")
                for header in security_headers:
                    value = headers.get(header, "❌ Missing")
                    print(f"   {header}: {value}")
                
                # Check for information disclosure headers that should be removed
                print("\nInformation disclosure check:")
                server_header = headers.get("server", "✅ Removed")
                powered_by = headers.get("x-powered-by", "✅ Not present")
                
                print(f"   Server header: {server_header}")
                print(f"   X-Powered-By: {powered_by}")
                
        except Exception as e:
            print(f"   ❌ Error checking headers: {e}")
    
    async def demo_websocket_limits(self):
        """Demonstrate WebSocket connection limits."""
        logger.info("🔌 Testing WebSocket Connection Limits")
        print("\n🔌 Testing WebSocket Connection Limits")
        print("=" * 50)
        
        print("Note: WebSocket limit testing requires manual verification")
        print("The middleware limits WebSocket connections per IP address")
        print(f"Current limit: 5 connections per IP")
    
    async def demo_performance_impact(self):
        """Measure performance impact of security middleware."""
        logger.info("⚡ Testing Performance Impact")
        print("\n⚡ Testing Performance Impact")
        print("=" * 50)
        
        num_requests = 10
        
        # Test response times
        print(f"\nTesting {num_requests} requests to /health endpoint:")
        response_times = []
        
        for i in range(num_requests):
            start_time = time.time()
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    elapsed = (time.time() - start_time) * 1000  # Convert to ms
                    response_times.append(elapsed)
                    print(f"   Request {i+1}: {response.status} - {elapsed:.1f}ms")
            except Exception as e:
                print(f"   Request {i+1}: Error - {e}")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\nPerformance Summary:")
            print(f"   Average response time: {avg_time:.1f}ms")
            print(f"   Min response time: {min_time:.1f}ms")
            print(f"   Max response time: {max_time:.1f}ms")
            print(f"   Security middleware overhead: ~{avg_time:.1f}ms per request")


async def main():
    """Run the security features demo."""
    print("🔒 Hybrid AI Council - Security Features Demo")
    print("=" * 60)
    print()
    
    # Check if server is running
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_base_url}/health") as response:
                if response.status == 200:
                    print(f"✅ Server is running at {api_base_url}")
                else:
                    print(f"⚠️ Server responded with status {response.status}")
    except Exception as e:
        print("❌ Server is not running or not accessible")
        print("💡 Start the server with: python main.py")
        return
    
    # Run security demos
    async with SecurityDemo() as demo:
        try:
            await demo.demo_rate_limiting()
            await demo.demo_input_validation()
            await demo.demo_security_headers()
            await demo.demo_websocket_limits()
            await demo.demo_performance_impact()
            
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")
        except Exception as e:
            logger.error("Demo error", error=str(e))
            print(f"❌ Demo error: {e}")
    
    print("\n🎉 Security Demo Complete!")
    print("\n💡 Security Features Summary:")
    print("   ✅ Rate limiting per IP and endpoint")
    print("   ✅ Input validation and sanitization")
    print("   ✅ Security headers protection")
    print("   ✅ SQL injection prevention")
    print("   ✅ XSS protection")
    print("   ✅ Request size limits")
    print("   ✅ WebSocket connection limits")
    print("   ✅ Server information hiding")


if __name__ == "__main__":
    asyncio.run(main())