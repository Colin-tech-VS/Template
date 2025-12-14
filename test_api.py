#!/usr/bin/env python3
"""
Test script pour vérifier la connexion API au Template

Usage:
    python test_api.py <template_url> <api_key>

Exemple:
    python test_api.py https://example.artworksdigital.fr "sk-abc123def456"
"""

import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

class TemplateAPITester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key}
        self.results = []
    
    def test_endpoint(self, endpoint: str, method: str = 'GET', 
                      params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Teste un endpoint et retourne les résultats"""
        url = f"{self.base_url}/api/export/{endpoint}"
        
        print(f"\n📍 Testing: {method} {endpoint}")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
            elif method == 'PUT':
                response = requests.put(
                    url,
                    headers=self.headers,
                    json=data,
                    timeout=10
                )
            else:
                return {"success": False, "error": f"Unknown method: {method}"}
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                json_data = response.json()
                result["response"] = json_data
                
                if response.status_code == 200:
                    print(f"   ✅ {response.status_code} OK")
                    if "count" in json_data:
                        print(f"   📦 {json_data['count']} items returned")
                else:
                    print(f"   ❌ {response.status_code} {json_data.get('error', 'Error')}")
            except:
                result["response_text"] = response.text[:200]
                print(f"   ⚠️  {response.status_code} (non-JSON response)")
            
            self.results.append(result)
            return result
        
        except requests.exceptions.Timeout:
            result = {
                "endpoint": endpoint,
                "success": False,
                "error": "Timeout (10s) - Server not responding",
                "timestamp": datetime.now().isoformat()
            }
            print(f"   ⏱️  Timeout!")
            self.results.append(result)
            return result
        
        except requests.exceptions.ConnectionError as e:
            result = {
                "endpoint": endpoint,
                "success": False,
                "error": f"Connection error: {str(e)[:100]}",
                "timestamp": datetime.now().isoformat()
            }
            print(f"   🔌 Connection error!")
            self.results.append(result)
            return result
        
        except Exception as e:
            result = {
                "endpoint": endpoint,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"   ❌ Error: {e}")
            self.results.append(result)
            return result
    
    def run_full_test_suite(self):
        """Lance la suite complète de tests"""
        print("=" * 70)
        print("🧪 Template API Test Suite")
        print("=" * 70)
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().isoformat()}")
        print("=" * 70)
        
        # 1. Test Settings
        print("\n[1/7] Testing Settings Endpoint...")
        self.test_endpoint("settings")
        
        # 2. Test Users
        print("\n[2/7] Testing Users Endpoint...")
        self.test_endpoint("users")
        
        # 3. Test Paintings
        print("\n[3/7] Testing Paintings Endpoint...")
        self.test_endpoint("paintings")
        
        # 4. Test Orders (with limit)
        print("\n[4/7] Testing Orders Endpoint...")
        self.test_endpoint("orders", params={"limit": 10})
        
        # 5. Test Exhibitions
        print("\n[5/7] Testing Exhibitions Endpoint...")
        self.test_endpoint("exhibitions")
        
        # 6. Test Custom Requests
        print("\n[6/7] Testing Custom Requests Endpoint...")
        self.test_endpoint("custom-requests")
        
        # 7. Test Stats
        print("\n[7/7] Testing Stats Endpoint...")
        self.test_endpoint("stats")
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Affiche un résumé des tests"""
        print("\n" + "=" * 70)
        print("📊 Test Summary")
        print("=" * 70)
        
        successful = sum(1 for r in self.results if r.get("success", False))
        failed = len(self.results) - successful
        
        print(f"✅ Successful: {successful}/{len(self.results)}")
        print(f"❌ Failed: {failed}/{len(self.results)}")
        
        if failed > 0:
            print("\nFailed endpoints:")
            for result in self.results:
                if not result.get("success", False):
                    error = result.get("error") or result.get("response", {}).get("error", "Unknown")
                    print(f"  ❌ {result['endpoint']}: {error}")
        
        print("\n" + "=" * 70)
        
        # Recommendations
        if failed > 0:
            print("\n💡 Troubleshooting:")
            
            if any(r.get("status_code") == 401 for r in self.results):
                print("  • 401 Unauthorized: API key is invalid or missing")
                print("    - Verify TEMPLATE_MASTER_API_KEY is set on the server")
                print("    - Check that X-API-Key header is being sent correctly")
                print("    - Try regenerating the API key")
            
            if any("Timeout" in str(r.get("error", "")) for r in self.results):
                print("  • Timeout: Server is not responding")
                print("    - Check if the server is running")
                print("    - Verify network connectivity")
                print("    - Check firewall/security rules")
            
            if any("Connection" in str(r.get("error", "")) for r in self.results):
                print("  • Connection Error: Cannot reach the server")
                print("    - Verify the base URL is correct")
                print("    - Check DNS resolution")
                print("    - Ensure HTTPS certificates are valid (if using HTTPS)")
    
    def export_results(self, filename: str = "test_results.json"):
        """Exporte les résultats en JSON"""
        with open(filename, 'w') as f:
            json.dump({
                "base_url": self.base_url,
                "timestamp": datetime.now().isoformat(),
                "results": self.results
            }, f, indent=2)
        print(f"\n📄 Results saved to: {filename}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_api.py <template_url> <api_key>")
        print("\nExample:")
        print('  python test_api.py "https://example.artworksdigital.fr" "sk-1234567890abcdef"')
        sys.exit(1)
    
    base_url = sys.argv[1]
    api_key = sys.argv[2]
    
    tester = TemplateAPITester(base_url, api_key)
    tester.run_full_test_suite()
    tester.export_results()


if __name__ == "__main__":
    main()
