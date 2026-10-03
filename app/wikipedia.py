import requests


def wikipedia_search(query: str):
    """
    Search Wikipedia for a topic.
    """

    url = "https://en.wikipedia.org/w/rest.php/v1/search/page"

    headers = {
        "User-Agent": (
            "AdvancedChatbot/1.0 "
            "(personal learning project)"
        )
    }

    params = {
        "q": query,
        "limit": 5
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        pages = data.get("pages", [])

        if not pages:

            return {
                "query": query,
                "results": []
            }

        results = []

        for page in pages:

            results.append({
                "title": page.get("title"),
                "description": page.get("description"),
                "key": page.get("key")
            })

        return {
            "query": query,
            "results": results
        }

    except requests.RequestException as e:

        return {
            "error": f"Wikipedia search failed: {str(e)}"
        }