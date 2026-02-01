#!/usr/bin/env python3
"""
Demonstration of two-step search + content extraction workflow
"""
import asyncio
import json
import sys
import os

sys.path.append('/Users/qasim/Documents/ai/mcp/backend')
from server_search import web_search

async def demo_two_step_workflow():
    """Demonstrate search + content extraction workflow"""
    
    print("🔍 STEP 1: Search for relevant pages")
    print("=" * 50)
    
    # Step 1: Search
    search_result = await web_search("zapier mcp ai", num_results=2)
    
    if search_result["status"] != "success":
        print("Search failed:", search_result["message"])
        return
    
    # Extract URLs from search results
    urls_to_fetch = []
    for result in search_result["organic_results"]:
        urls_to_fetch.append({
            "url": result["link"],
            "title": result["title"],
            "snippet": result["snippet"]
        })
    
    print(f"Found {len(urls_to_fetch)} URLs to extract content from:")
    for i, item in enumerate(urls_to_fetch, 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Snippet: {item['snippet'][:100]}...")
        print()
    
    print("🌐 STEP 2: Extract full content from discovered pages")
    print("=" * 50)
    
    # Step 2: Content extraction workflow
    extraction_plan = {
        "workflow": "search_then_extract",
        "search_results": len(urls_to_fetch),
        "extraction_targets": [
            {
                "url": item["url"],
                "title": item["title"],
                "extraction_method": "web_fetch with selective mode",
                "search_terms": "MCP model context protocol zapier integration",
                "expected_content": "Setup instructions, API documentation, integration examples"
            }
            for item in urls_to_fetch
        ]
    }
    
    print("Content Extraction Plan:")
    print(json.dumps(extraction_plan, indent=2))
    
    return extraction_plan

if __name__ == "__main__":
    asyncio.run(demo_two_step_workflow())
