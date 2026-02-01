#!/usr/bin/env python3
"""
Enhanced MCP tool that combines search + content extraction
"""
import asyncio
import json
import sys
import os
import httpx

sys.path.append('/Users/qasim/Documents/ai/mcp/backend')

async def search_and_extract_content(query: str, num_results: int = 2):
    """
    Combined search and content extraction workflow
    """
    from server_search import web_search
    
    print(f"🔍 Searching for: {query}")
    
    # Step 1: Search
    search_result = await web_search(query, num_results)
    
    if search_result["status"] != "success":
        return {"error": "Search failed", "details": search_result}
    
    # Step 2: Extract content from top results
    extracted_results = []
    
    for result in search_result["organic_results"]:
        url = result["link"]
        title = result["title"]
        snippet = result["snippet"]
        
        print(f"\n📄 Extracting content from: {title}")
        print(f"URL: {url}")
        
        # Simulate web_fetch extraction (in real implementation, would call web_fetch)
        extraction_summary = {
            "url": url,
            "title": title,
            "original_snippet": snippet,
            "extraction_method": "web_fetch selective mode",
            "search_terms": query,
            "content_preview": "Full webpage content would be extracted here...",
            "content_length": "~2000-5000 characters of relevant content",
            "key_sections": [
                "Setup instructions",
                "Integration examples", 
                "API documentation",
                "Pricing information",
                "Use cases and examples"
            ]
        }
        
        extracted_results.append(extraction_summary)
    
    return {
        "search_summary": {
            "query": query,
            "results_found": len(search_result["organic_results"]),
            "related_searches": search_result.get("related_searches", [])
        },
        "extracted_content": extracted_results,
        "workflow": "search_then_extract",
        "total_content_sources": len(extracted_results)
    }

async def demo_combined_workflow():
    result = await search_and_extract_content("zapier mcp ai setup", 2)
    print("\n" + "="*60)
    print("COMBINED SEARCH + EXTRACT RESULTS:")
    print("="*60)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(demo_combined_workflow())
