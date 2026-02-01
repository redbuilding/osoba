#!/usr/bin/env python3
"""
Smart Content Prioritization Algorithm
"""

def calculate_url_priority(search_result, query_terms):
    """
    Calculate priority score for each discovered URL
    """
    priorities = []
    
    for result in search_result.get("organic_results", []):
        score = 0
        
        # Base score from search position (higher position = higher score)
        position_score = max(0, 10 - result.get("position", 10))
        score += position_score
        
        # Title relevance (exact query terms in title)
        title = result.get("title", "").lower()
        title_matches = sum(1 for term in query_terms if term.lower() in title)
        score += title_matches * 3
        
        # Snippet relevance
        snippet = result.get("snippet", "").lower()
        snippet_matches = sum(1 for term in query_terms if term.lower() in snippet)
        score += snippet_matches * 2
        
        # Sitelinks bonus (indicates comprehensive content)
        sitelinks_count = len(result.get("sitelinks", []))
        score += min(sitelinks_count, 3) * 1.5
        
        # Domain authority heuristics
        url = result.get("link", "")
        if any(domain in url for domain in ["docs.", "help.", "guide.", "tutorial."]):
            score += 2
        if url.endswith(".pdf"):
            score -= 1  # PDFs are harder to extract from
            
        priorities.append({
            "url": url,
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "priority_score": score,
            "reasoning": {
                "position_score": position_score,
                "title_matches": title_matches,
                "snippet_matches": snippet_matches,
                "sitelinks_bonus": sitelinks_count,
                "domain_bonus": 2 if any(domain in url for domain in ["docs.", "help.", "guide."]) else 0
            }
        })
    
    # Sort by priority score (highest first)
    return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

def demo_prioritization():
    # Simulate search results
    mock_search_result = {
        "organic_results": [
            {
                "title": "Zapier MCP Setup Guide - Complete Tutorial",
                "link": "https://docs.zapier.com/mcp/setup",
                "snippet": "Step-by-step guide to setup Zapier MCP with AI tools",
                "position": 1,
                "sitelinks": [{"title": "Quick Start"}, {"title": "Advanced Config"}]
            },
            {
                "title": "Connect AI tools to 8,000 apps with Zapier MCP",
                "link": "https://zapier.com/mcp",
                "snippet": "One connection point, 8,000 apps, 30,000+ actions",
                "position": 2,
                "sitelinks": []
            },
            {
                "title": "Zapier MCP Review - Third Party Blog",
                "link": "https://techblog.com/zapier-mcp-review",
                "snippet": "Our thoughts on the new Zapier MCP integration",
                "position": 3,
                "sitelinks": []
            }
        ]
    }
    
    query_terms = ["zapier", "mcp", "setup", "ai"]
    priorities = calculate_url_priority(mock_search_result, query_terms)
    
    print("🎯 URL PRIORITIZATION RESULTS:")
    print("=" * 50)
    
    for i, item in enumerate(priorities, 1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Priority Score: {item['priority_score']}")
        print(f"   Reasoning: {item['reasoning']}")
        print()

if __name__ == "__main__":
    demo_prioritization()
