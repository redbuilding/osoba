#!/usr/bin/env python3
"""
Comprehensive test of smart search extract with different configurations
"""
import asyncio
import json
import sys

sys.path.append('/Users/qasim/Documents/ai/mcp/backend')

async def test_comprehensive_smart_extract():
    from server_search import smart_search_extract
    
    print("🧠 COMPREHENSIVE SMART SEARCH + EXTRACT TEST")
    print("=" * 60)
    
    # Test 1: Default configuration
    print("\n📋 TEST 1: Default Configuration")
    print("-" * 30)
    result1 = await smart_search_extract("python web scraping tutorial")
    
    print(f"Query: {result1['query']}")
    print(f"URLs processed: {result1['extraction_stats']['urls_processed']}")
    print(f"Successful extractions: {result1['extraction_stats']['successful_extractions']}")
    print(f"Total chars extracted: {result1['extraction_stats']['total_chars_extracted']}")
    
    print("\nPrioritized URLs:")
    for i, url in enumerate(result1['prioritized_urls'], 1):
        print(f"{i}. {url['title']} (Score: {url['priority_score']})")
    
    print("\nExtracted Content Preview:")
    for content in result1['extracted_content']:
        if content['status'] == 'success' and content['content']:
            preview = content['content'][:200] + "..." if len(content['content']) > 200 else content['content']
            print(f"• {content['title']}: {preview}")
    
    # Test 2: Limited configuration
    print("\n\n📋 TEST 2: Limited Configuration (1 URL, 500 chars)")
    print("-" * 50)
    result2 = await smart_search_extract(
        query="openai api documentation",
        max_urls=1,
        max_chars_per_url=500,
        max_total_chars=500
    )
    
    print(f"Query: {result2['query']}")
    print(f"URLs processed: {result2['extraction_stats']['urls_processed']}")
    print(f"Total chars extracted: {result2['extraction_stats']['total_chars_extracted']}")
    
    if result2['extracted_content'] and result2['extracted_content'][0]['content']:
        print(f"Content length: {len(result2['extracted_content'][0]['content'])} chars")
        print(f"Content preview: {result2['extracted_content'][0]['content'][:100]}...")
    
    return result1, result2

if __name__ == "__main__":
    asyncio.run(test_comprehensive_smart_extract())
