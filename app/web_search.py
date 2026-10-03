try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover - deployment installs the dependency
    TavilyClient = None

from app.config import TAVILY_API_KEY


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(query: str, num_results: int = 5):
    """
    Search the internet using Tavily.

    Args:
        query: Search query.
        num_results: Maximum number of results.

    Returns:
        Dictionary containing search results.
    """

    # --------------------------------------------------------
    # CHECK QUERY
    # --------------------------------------------------------

    if not query or not query.strip():

        return {
            "error": "Search query cannot be empty."
        }

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    if not TAVILY_API_KEY or TavilyClient is None:

        return {
            "error": (
                "Tavily API key is not configured."
            )
        }

    try:

        # ----------------------------------------------------
        # CREATE TAVILY CLIENT
        # ----------------------------------------------------

        tavily = TavilyClient(
            api_key=TAVILY_API_KEY
        )

        # ----------------------------------------------------
        # SEARCH WEB
        # ----------------------------------------------------

        response = tavily.search(
            query=query,
            max_results=num_results,
            search_depth="basic"
        )

        # ----------------------------------------------------
        # FORMAT RESULTS
        # ----------------------------------------------------

        results = []

        for item in response.get(
            "results",
            []
        ):

            results.append(
                {
                    "title": item.get(
                        "title",
                        ""
                    ),
                    "url": item.get(
                        "url",
                        ""
                    ),
                    "content": item.get(
                        "content",
                        ""
                    )
                }
            )

        # ----------------------------------------------------
        # RETURN RESULTS
        # ----------------------------------------------------

        return {
            "query": query,
            "results": results
        }

    except Exception as e:

        return {
            "error": (
                f"Web search failed: {str(e)}"
            )
        }
