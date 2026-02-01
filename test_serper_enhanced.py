#!/usr/bin/env python3
"""
Test script to demonstrate enhanced Serper API response
"""
import asyncio
import json
import sys
import os

# Add backend to path
sys.path.append('/Users/qasim/Documents/ai/mcp/backend')

from server_search import web_search

async def test_enhanced_search():
    """Test enhanced web search with single result"""
    print("Testing enhanced Serper API with query: 'zapier mcp ai'")
    print("=" * 60)
    
    result = await web_search(
        query="zapier mcp ai",
        num_results=1,
        location="us",
        language="en"
    )
    
    print("COMPLETE API RESPONSE:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result

if __name__ == "__main__":
    asyncio.run(test_enhanced_search())
