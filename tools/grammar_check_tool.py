"""
Calls the free public LanguageTool REST API to grammar-check report text without API key.
"""
import requests

LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"


def grammar_check(text: str, language: str = "en-US") -> dict[str, any]:
    """
    Run grammar and spell-check on the given text using the free LanguageTool API.

    Args:
        text: The text to check (reasoning sentences from Agent 2).
        language: Language code (default: en-US).

    Returns:
        A dict with:
            - 'corrected_text' (str): Text with corrections applied.
            - 'issues_found' (int): Total number of grammar issues detected.
            - 'matches' (list): Raw match objects from the API.

    Raises:
        RuntimeError: If the API request fails due to network or HTTP error.
    """
    try:
        response = requests.post(
            LANGUAGETOOL_URL,
            data={"text": text, "language": language},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"LanguageTool API call failed: {e}")

    matches = data.get("matches", [])
    corrected = text

    # Apply replacements in REVERSE order to preserve string offsets
    for match in reversed(matches):
        if match.get("replacements"):
            replacement = match["replacements"][0]["value"]
            start = match["offset"]
            end = start + match["length"]
            corrected = corrected[:start] + replacement + corrected[end:]

    return {
        "corrected_text": corrected,
        "issues_found": len(matches),
        "matches": matches,
    }