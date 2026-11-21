import ipaddress
from typing import Tuple
from flask import Request, current_app
from user_agents import parse as parse_ua

def get_client_ip(request: Request) -> str:
    """
    Extract client public IP address safely according to security configuration.
    
    If USE_PROXY_HEADERS is False, this function strictly uses request.remote_addr.
    If USE_PROXY_HEADERS is True, it validates that request.remote_addr is among
    TRUSTED_PROXIES before inspecting X-Forwarded-For headers.
    """
    remote_addr = request.remote_addr or "127.0.0.1"
    use_proxy = current_app.config.get("USE_PROXY_HEADERS", False)
    trusted_proxies = current_app.config.get("TRUSTED_PROXIES", ["127.0.0.1", "::1"])

    if not use_proxy:
        # Standard direct connection or non-proxy deployment
        return remote_addr

    # Only process headers if incoming socket connection is from a trusted proxy
    if remote_addr not in trusted_proxies:
        return remote_addr

    # Check X-Forwarded-For header
    forwarded_for = request.headers.get("X-Forwarded-For")
    if not forwarded_for:
        return remote_addr

    # Parse X-Forwarded-For list from right to left
    # The first untrusted IP from the right is the real client IP
    ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
    if not ips:
        return remote_addr

    for ip in reversed(ips):
        if ip not in trusted_proxies:
            # Validate IP syntax before returning
            try:
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue

    return ips[0]


def is_private_ip(ip_str: str) -> bool:
    """Check if the given IP address is private, loopback, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or 
            ip.is_loopback or 
            ip.is_link_local or 
            ip.is_reserved or 
            ip.is_multicast
        )
    except ValueError:
        return False


def parse_user_agent(user_agent_str: str) -> Tuple[str, str]:
    """Parse HTTP User-Agent string to extract human-readable Browser and OS."""
    if not user_agent_str or not user_agent_str.strip():
        return ("Unknown Browser", "Unknown OS")
    
    try:
        ua = parse_ua(user_agent_str)
        # Format browser name and version
        browser_family = ua.browser.family
        browser_version = ua.browser.version_string
        browser = f"{browser_family} {browser_version}".strip() if browser_version else browser_family
        if not browser or browser.lower() == "other":
            browser = "Other / Unknown"

        # Format OS name and version
        os_family = ua.os.family
        os_version = ua.os.version_string
        os = f"{os_family} {os_version}".strip() if os_version else os_family
        if not os or os.lower() == "other":
            os = "Other / Unknown"

        return (browser, os)
    except Exception:
        return ("Unknown Browser", "Unknown OS")
