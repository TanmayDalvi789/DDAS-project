#!/usr/bin/env python3
"""
DDAS End-to-End System Validation - Final Status Check

This script validates that all three components are running and operational.
"""

import requests
import json
from datetime import datetime

def check_backend():
    """Check backend status."""
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "✅ RUNNING",
                "port": 8001,
                "version": data.get("version", "unknown"),
                "endpoints": data.get("endpoints", {})
            }
        return {"status": "❌ NOT RESPONDING", "port": 8001}
    except Exception as e:
        return {"status": "❌ UNAVAILABLE", "port": 8001, "error": str(e)}

def check_dashboard():
    """Check dashboard status."""
    try:
        response = requests.get("http://localhost:3000/", timeout=5)
        if response.status_code == 200:
            return {
                "status": "✅ RUNNING",
                "port": 3000,
                "serving": "Next.js Dashboard"
            }
        return {"status": "❌ NOT RESPONDING", "port": 3000}
    except Exception as e:
        return {"status": "❌ UNAVAILABLE", "port": 3000, "error": str(e)}

def check_event_endpoint():
    """Check if events endpoint is working."""
    try:
        response = requests.get("http://localhost:8001/api/v1/events", timeout=5)
        # Should be 405 (method not allowed) for GET on POST-only endpoint
        # or 200 if a GET endpoint exists
        if response.status_code in [200, 405, 401]:
            return {
                "status": "✅ ACCESSIBLE",
                "endpoint": "/api/v1/events",
                "response_code": response.status_code
            }
        return {"status": "❌ INACCESSIBLE", "endpoint": "/api/v1/events"}
    except Exception as e:
        return {"status": "❌ ERROR", "endpoint": "/api/v1/events", "error": str(e)}

def main():
    """Run validation checks."""
    print("\n" + "="*70)
    print("DDAS END-TO-END SYSTEM VALIDATION")
    print("="*70)
    print(f"Check Time: {datetime.now().isoformat()}\n")
    
    print("🔍 COMPONENT STATUS CHECK\n")
    
    # Check backend
    print("1. Backend API (FastAPI)")
    backend = check_backend()
    print(f"   Status: {backend.get('status', 'Unknown')}")
    if "port" in backend:
        print(f"   Port: {backend['port']}")
    if "version" in backend:
        print(f"   Version: {backend['version']}")
    
    # Check dashboard
    print("\n2. Dashboard (Next.js)")
    dashboard = check_dashboard()
    print(f"   Status: {dashboard.get('status', 'Unknown')}")
    if "port" in dashboard:
        print(f"   Port: {dashboard['port']}")
    
    # Check event endpoint
    print("\n3. Event Endpoint")
    event_api = check_event_endpoint()
    print(f"   Status: {event_api.get('status', 'Unknown')}")
    if "endpoint" in event_api:
        print(f"   Endpoint: {event_api['endpoint']}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_running = (
        backend.get("status", "").startswith("✅") and
        dashboard.get("status", "").startswith("✅") and
        event_api.get("status", "").startswith("✅")
    )
    
    if all_running:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
        print("\nYou can now:")
        print("  1. Open dashboard at: http://localhost:3000")
        print("  2. Run simulator: python agent/tests/simulate_event.py")
        print("  3. View API docs: http://localhost:8001/docs")
    else:
        print("\n⚠️  SOME SYSTEMS NOT AVAILABLE")
        print("\nMissing components:")
        if not backend.get("status", "").startswith("✅"):
            print("  • Backend API on port 8001")
        if not dashboard.get("status", "").startswith("✅"):
            print("  • Dashboard on port 3000")
        if not event_api.get("status", "").startswith("✅"):
            print("  • Event API endpoint")
    
    print("\n" + "="*70)
    print(f"Generated: {datetime.now().isoformat()}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
