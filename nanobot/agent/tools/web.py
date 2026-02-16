"""Web tools: web_search and web_fetch."""

import html
import ipaddress
import json
import os
import re
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from nanobot.agent.tools.base import Tool

# Shared constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
MAX_REDIRECTS = 5  # Limit redirects to prevent DoS attacks

# Private IP ranges for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("0.0.0.0/8"),  # "This" network
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::/128"),  # IPv6 unspecified
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "169.254.169.254",
}


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _normalize(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _is_private_ip(ip_str: str) -> bool:
    """
    Determine whether the given IP address string refers to a private/internal network.
    
    Parameters:
        ip_str (str): IP address in textual form (IPv4 or IPv6).
    
    Returns:
        bool: `True` if `ip_str` parses as an IP address that is contained in the module's PRIVATE_IP_RANGES; `False` if it is not contained or if `ip_str` is not a valid IP address.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def _resolve_hostname(hostname: str) -> list[str]:
    """
    Resolve a hostname to all associated IP address strings.
    
    Parameters:
        hostname (str): The hostname or domain name to resolve.
    
    Returns:
        list[str]: A list of unique IP address strings (IPv4/IPv6) associated with the hostname.
                   Returns an empty list if the hostname cannot be resolved or an error occurs.
    """
    try:
        result = socket.getaddrinfo(hostname, None)
        ips = []
        for r in result:
            ip = r[4][0]
            if ip not in ips:
                ips.append(ip)
        return ips
    except (socket.gaierror, socket.herror, OSError):
        return []


def _validate_url(url: str) -> tuple[bool, str]:
    """
    Validate that a URL is permitted for fetching.
    
    Performs these checks: the scheme is "http" or "https"; a hostname is present; the hostname is not in the blocked hostnames set; the hostname resolves to one or more IP addresses; and none of the resolved IPs are in configured private/internal ranges. On unexpected errors during validation, returns the error message.
    
    Returns:
        (bool, str): `(True, "")` if the URL passes all checks; otherwise `(False, "<error message>")`.
    """
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}"
        if not p.netloc:
            return False, "Missing domain"

        hostname = p.hostname
        if not hostname:
            return False, "Missing hostname"

        hostname = hostname.lower()

        if hostname in BLOCKED_HOSTNAMES:
            return False, f"Access to {hostname} is blocked"

        ips = _resolve_hostname(hostname)
        if not ips:
            return False, "Could not resolve hostname"

        for ip in ips:
            if _is_private_ip(ip):
                return False, f"Access to private/internal addresses is blocked"

        return True, ""
    except Exception as e:
        return False, str(e)


class WebSearchTool(Tool):
    """Search the web using Brave Search API."""

    name = "web_search"
    description = "Search the web. Returns titles, URLs, and snippets."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {
                "type": "integer",
                "description": "Results (1-10)",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    }

    def __init__(self, api_key: str | None = None, max_results: int = 5):
        self.api_key = api_key or os.environ.get("BRAVE_API_KEY", "")
        self.max_results = max_results

    async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
        if not self.api_key:
            return "Error: BRAVE_API_KEY not configured"

        try:
            n = min(max(count or self.max_results, 1), 10)
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": n},
                    headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
                    timeout=10.0,
                )
                r.raise_for_status()

            results = r.json().get("web", {}).get("results", [])
            if not results:
                return f"No results for: {query}"

            lines = [f"Results for: {query}\n"]
            for i, item in enumerate(results[:n], 1):
                lines.append(f"{i}. {item.get('title', '')}\n   {item.get('url', '')}")
                if desc := item.get("description"):
                    lines.append(f"   {desc}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"


class WebFetchTool(Tool):
    """Fetch and extract content from a URL using Readability."""

    name = "web_fetch"
    description = "Fetch URL and extract readable content (HTML → markdown/text)."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "extractMode": {"type": "string", "enum": ["markdown", "text"], "default": "markdown"},
            "maxChars": {"type": "integer", "minimum": 100},
        },
        "required": ["url"],
    }

    def __init__(self, max_chars: int = 50000):
        self.max_chars = max_chars

    async def execute(
        self, url: str, extractMode: str = "markdown", maxChars: int | None = None, **kwargs: Any
    ) -> str:
        """
        Fetches a URL, extracts readable content according to the requested mode, and returns a JSON-formatted string with metadata and the extracted text.
        
        Parameters:
            url (str): The URL to fetch; validated against host/IP policies before fetching.
            extractMode (str): "markdown" to convert HTML to Markdown via readability + internal converter, "text" to extract plain text. Defaults to "markdown".
            maxChars (int | None): Maximum number of characters to include in the returned text; if None, the tool's default max is used.
        
        Returns:
            str: A JSON string containing:
                - url: the original requested URL
                - finalUrl: the final location after validated redirects
                - status: HTTP status code of the final response
                - extractor: one of "readability", "json", or "raw" indicating how content was extracted
                - truncated: `true` if the returned text was cut to fit `maxChars`, `false` otherwise
                - length: length of the returned text in characters
                - text: the extracted content (Markdown/plain/JSON/raw)
            If URL validation fails or an exception occurs, returns a JSON string with keys:
                - error: error message
                - url: the original requested URL
        """
        from readability import Document

        max_chars = maxChars or self.max_chars

        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return json.dumps({"error": f"URL validation failed: {error_msg}", "url": url})

        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
                r = await self._fetch_with_redirect_validation(client, url)
                r.raise_for_status()

            ctype = r.headers.get("content-type", "")

            # JSON
            if "application/json" in ctype:
                text, extractor = json.dumps(r.json(), indent=2), "json"
            # HTML
            elif "text/html" in ctype or r.text[:256].lower().startswith(("<!doctype", "<html")):
                doc = Document(r.text)
                content = (
                    self._to_markdown(doc.summary())
                    if extractMode == "markdown"
                    else _strip_tags(doc.summary())
                )
                text = f"# {doc.title()}\n\n{content}" if doc.title() else content
                extractor = "readability"
            else:
                text, extractor = r.text, "raw"

            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]

            return json.dumps(
                {
                    "url": url,
                    "finalUrl": str(r.url),
                    "status": r.status_code,
                    "extractor": extractor,
                    "truncated": truncated,
                    "length": len(text),
                    "text": text,
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e), "url": url})

    async def _fetch_with_redirect_validation(
        self, client: httpx.AsyncClient, url: str, redirect_count: int = 0
    ) -> httpx.Response:
        """
        Follow redirects for the given URL up to MAX_REDIRECTS while validating each redirect target.
        
        Performs a GET using the provided httpx.AsyncClient and, if a redirect status is returned (301, 302, 303, 307, 308),
        validates the Location header with _validate_url and recursively follows the redirect. Returns the final httpx.Response
        for a non-redirect response.
        
        Parameters:
            client (httpx.AsyncClient): Async HTTP client used to perform requests.
            url (str): Initial URL to fetch.
            redirect_count (int): Current redirect depth (used internally).
        
        Returns:
            httpx.Response: The response for the final (non-redirect) URL.
        
        Raises:
            Exception: If the redirect depth exceeds MAX_REDIRECTS.
            Exception: If a redirect response is missing a Location header.
            Exception: If _validate_url rejects a redirect target (includes validation error message).
        """
        if redirect_count > MAX_REDIRECTS:
            raise Exception(f"Too many redirects (max {MAX_REDIRECTS})")

        r = await client.get(url, headers={"User-Agent": USER_AGENT})

        if r.status_code in (301, 302, 303, 307, 308):
            redirect_url = r.headers.get("location")
            if not redirect_url:
                raise Exception("Redirect response missing Location header")

            is_valid, error_msg = _validate_url(redirect_url)
            if not is_valid:
                raise Exception(f"Redirect target validation failed: {error_msg}")

            return await self._fetch_with_redirect_validation(
                client, redirect_url, redirect_count + 1
            )

        return r

    def _to_markdown(self, html: str) -> str:
        """
        Convert HTML to a lightweight Markdown-like plain text representation.
        
        Performs targeted conversions for links, headings, list items, paragraph/div breaks, and line breaks, then strips remaining HTML and normalizes whitespace.
        
        Parameters:
            html (str): HTML content to convert.
        
        Returns:
            markdown_text (str): Plain-text string with simple Markdown-style constructs (e.g., `[text](url)`, `#` headings, `-` list items) and normalized whitespace.
        """
        # Convert links, headings, lists before stripping tags
        text = re.sub(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
            lambda m: f"[{_strip_tags(m[2])}]({m[1]})",
            html,
            flags=re.I,
        )
        text = re.sub(
            r"<h([1-6])[^>]*>([\s\S]*?)</h\1>",
            lambda m: f"\n{'#' * int(m[1])} {_strip_tags(m[2])}\n",
            text,
            flags=re.I,
        )
        text = re.sub(
            r"<li[^>]*>([\s\S]*?)</li>", lambda m: f"\n- {_strip_tags(m[1])}", text, flags=re.I
        )
        text = re.sub(r"</(p|div|section|article)>", "\n\n", text, flags=re.I)
        text = re.sub(r"<(br|hr)\s*/?>", "\n", text, flags=re.I)
        return _normalize(_strip_tags(text))