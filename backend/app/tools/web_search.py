"""
Web Search Tool — uses DuckDuckGo (free, no API key needed).
"""

from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool
def web_search(query: str) -> str:
    """Search the web for current information. Use this when the user asks about
    something you don't have knowledge about, or when you need up-to-date info."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No search results found."
        # Format results concisely
        formatted = []
        for r in results:
            formatted.append(f"- {r['title']}: {r['body']}")
        return "\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}"
