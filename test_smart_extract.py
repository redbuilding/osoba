#!/usr/bin/env python3
"""
Test the new smart_search_extract tool
"""
import asyncio
import json
import sys

sys.path.append('/Users/qasim/Documents/ai/mcp/backend')

async def test_smart_search_extract():
    from server_search import smart_search_extract
    
    print("🧠 Testing Smart Search + Extract Tool")
    print("=" * 50)
    
    result = await smart_search_extract(
        query="zapier mcp ai setup",
        max_urls=2,
        max_chars_per_url=1500,
        max_total_chars=3000
    )
    
    print("SMART EXTRACTION RESULTS:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result

if __name__ == "__main__":
    asyncio.run(test_smart_search_extract())
