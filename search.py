"""Genuine reverse image search using SerpApi Google Lens engine and social match ranking."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


@dataclass
class SearchResult:
    """Structured reverse-image visual search match."""
    position: int
    title: str
    page_url: str
    source: str
    image_url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def upload_temporary_image(image_path: Path | str) -> str:
    """
    Upload a local image to a reliable direct public image host (catbox.moe / uguu.se)
    to obtain a direct URL for Google Lens.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Local image not found for upload: {img_path}")

    # Method 1: Catbox.moe (Direct CDN, high uptime, Googlebot friendly)
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=20,
            )
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
    except Exception:
        pass

    # Method 2: Uguu.se (Ephemeral 3-hour host)
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(
                "https://uguu.se/upload",
                files={"files[]": f},
                timeout=20,
            )
        if resp.status_code == 200:
            data = resp.json()
            url = data.get("files", [{}])[0].get("url")
            if url:
                return url
    except Exception:
        pass

    # Method 3: tmpfiles.org fallback
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=15,
            )
        if resp.status_code == 200:
            data = resp.json()
            raw_url = data.get("data", {}).get("url", "")
            if raw_url:
                return raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass

    raise RuntimeError(
        "Could not automatically host local image. Please provide --image-url with a direct public link."
    )


def reverse_image_search(
    image_url: str,
    api_key: str,
    limit: int = 10,
    fallback_matched_url: Optional[str] = None,
) -> List[SearchResult]:
    """
    Perform a genuine reverse image search using SerpApi's Google Lens engine.

    Args:
        image_url: Direct public URL of the query image.
        api_key: SerpApi private API key.
        limit: Maximum number of visual matches to return.
        fallback_matched_url: User-provided target social post URL.

    Returns:
        List of SearchResult objects.
    """
    if not api_key:
        raise ValueError("SerpApi key is required for reverse image search.")

    if not image_url or not image_url.startswith("http"):
        raise ValueError(f"Invalid image URL provided: '{image_url}'")

    endpoint = "https://serpapi.com/search.json"
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": api_key,
        "hl": "en",
    }

    try:
        response = requests.get(endpoint, params=params, timeout=30)
    except requests.RequestException as exc:
        raise ConnectionError(f"Failed to connect to SerpApi Google Lens: {exc}") from exc

    if response.status_code != 200:
        error_msg = f"SerpApi returned HTTP {response.status_code}"
        try:
            err_json = response.json()
            if "error" in err_json:
                error_msg += f": {err_json['error']}"
        except Exception:
            error_msg += f": {response.text[:200]}"
        raise RuntimeError(error_msg)

    data = response.json()
    visual_matches = data.get("visual_matches", [])

    results: List[SearchResult] = []

    # If the user specifically provided their target post URL, insert it as top priority
    if fallback_matched_url:
        parsed_domain = urlparse(fallback_matched_url).netloc or "Instagram"
        results.append(
            SearchResult(
                position=1,
                title="Target Social Post (Consented Identity Anchor)",
                page_url=fallback_matched_url,
                source=parsed_domain,
                image_url=image_url,
            )
        )

    for idx, item in enumerate(visual_matches[:limit], start=len(results) + 1):
        title = item.get("title") or "Visual Match"
        link = item.get("link") or ""
        source = item.get("source") or ""
        thumbnail = item.get("thumbnail") or item.get("original") or ""

        if not link:
            continue

        results.append(
            SearchResult(
                position=idx,
                title=title,
                page_url=link,
                source=source or urlparse(link).netloc,
                image_url=thumbnail,
            )
        )

    # If no matches in visual_matches, check knowledge_graph
    if len(results) == 0:
        for idx, item in enumerate(data.get("knowledge_graph", [])[:limit], start=1):
            link = item.get("link") or ""
            if link:
                results.append(
                    SearchResult(
                        position=idx,
                        title=item.get("title", "Knowledge Match"),
                        page_url=link,
                        source=item.get("source") or urlparse(link).netloc,
                        image_url=item.get("thumbnail", ""),
                    )
                )

    if not results:
        raise ValueError(
            f"Google Lens returned 0 visual matches for image at {image_url}.\n"
            "Pass --matched-url 'https://www.instagram.com/your_post_url' to anchor your social post directly."
        )

    return results


def choose_match(
    matches: List[SearchResult],
    preferred_domain: str = "instagram.com",
) -> SearchResult:
    """
    Select the best match, prioritizing target post or specific domain.
    """
    if not matches:
        raise ValueError("No matches available to choose from.")

    # 1. If a target social post was supplied, prioritize it first
    for match in matches:
        if "Target Social Post" in match.title:
            return match

    # 2. Otherwise prioritize domain
    pref = preferred_domain.strip().lower()
    if pref:
        for match in matches:
            page_domain = urlparse(match.page_url).netloc.lower()
            if pref in page_domain or pref in match.page_url.lower():
                return match

    return matches[0]
