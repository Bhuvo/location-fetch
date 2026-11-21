import logging
import json
import time
from typing import Dict, Any, Optional
import requests
from flask import current_app
from app.services.ip_resolver import is_private_ip
from app.services.provider_comparator import compare_all_providers
from app.services.confidence import is_city_centre_fallback, evaluate_confidence
from app.models import db

logger = logging.getLogger(__name__)

# In-memory geolocation cache: {ip: (timestamp, data_dict)}
_geo_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}

def lookup_ip_geolocation(ip_address: str) -> Dict[str, Any]:
    """
    Query IP geolocation provider and compute accuracy & confidence rating.
    
    Adheres strictly to the guidelines:
    - Never averages coordinates across providers.
    - Accurately detects generic city-center centroid fallbacks (e.g. Chennai 13.0878, 80.2785).
    - Computes confidence (HIGH, MEDIUM, LOW, UNKNOWN).
    - Captures accuracy radius when available.
    - Never fabricates fake coordinates.
    """
    clean_ip = ip_address.strip()

    # 1. Check in-memory cache
    cache_ttl = current_app.config.get("GEO_CACHE_TTL_SECONDS", 3600)
    now = time.time()
    if clean_ip in _geo_cache:
        cached_time, cached_data = _geo_cache[clean_ip]
        if now - cached_time < cache_ttl:
            logger.debug(f"Geolocation cache hit for {clean_ip}")
            return cached_data.copy()

    # 2. Handle private / loopback IP addresses
    if is_private_ip(clean_ip):
        dev_resolve_server_ip = current_app.config.get("DEV_RESOLVE_SERVER_PUBLIC_IP", False)
        if dev_resolve_server_ip:
            try:
                res = requests.get("https://api.ipify.org?format=json", timeout=3)
                if res.status_code == 200:
                    public_ip = res.json().get("ip")
                    if public_ip and not is_private_ip(public_ip):
                        logger.info(f"Dev mode: Resolved local IP {clean_ip} to server public IP {public_ip}")
                        data = _resolve_and_compare(public_ip)
                        data["ip_address"] = clean_ip  # Preserve original client IP
                        data["organization"] = f"{data.get('organization') or ''} (Dev Public IP Test)".strip()
                        _geo_cache[clean_ip] = (now, data)
                        return data
            except Exception as e:
                logger.warning(f"Dev public IP resolution failed: {e}")

        # Standard private network response
        local_result = {
            "ip_address": clean_ip,
            "country": "Localhost / Private Network",
            "country_code": "LOCAL",
            "region": "Local Network",
            "city": "Localhost",
            "postal_code": None,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "isp": "Private Loopback / RFC 1918",
            "organization": "Local Development",
            "asn": None,
            "accuracy_radius": None,
            "confidence": "UNKNOWN",
            "confidence_reasons": ["Private / loopback network interface without public geolocation coordinates."],
            "is_city_centre": False,
            "city_centre_reason": None,
            "provider": "local_private_network",
            "provider_comparison": "{}",
            "success": True,
        }
        _geo_cache[clean_ip] = (now, local_result)
        return local_result

    # 3. Resolve public IP with multi-provider comparison
    result = _resolve_and_compare(clean_ip)
    _geo_cache[clean_ip] = (now, result)
    return result


def _resolve_and_compare(ip: str) -> Dict[str, Any]:
    """Execute multi-provider comparison and determine confidence."""
    comparison = compare_all_providers(ip)
    providers = comparison.get("providers", [])

    # Filter successful provider responses
    successful = [p for p in providers if p.get("success") and p.get("latitude") is not None]

    if not successful:
        # All providers failed
        return {
            "ip_address": ip,
            "country": None,
            "country_code": None,
            "region": None,
            "city": None,
            "postal_code": None,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "isp": None,
            "organization": None,
            "asn": None,
            "accuracy_radius": None,
            "confidence": "UNKNOWN",
            "confidence_reasons": ["All geolocation providers failed to return coordinates."],
            "is_city_centre": False,
            "city_centre_reason": None,
            "provider": "none",
            "provider_comparison": json.dumps(comparison),
            "success": False,
        }

    # CRITICAL: Select a single primary provider's coordinates. NEVER average coordinates!
    # Preference: IPinfo -> ip-api -> MaxMind/ipapi_co
    primary = None
    for preferred_name in ("ipinfo", "ip-api", "maxmind", "ipapi_co"):
        match = next((p for p in successful if p.get("provider") == preferred_name), None)
        if match:
            primary = match
            break
    if not primary:
        primary = successful[0]

    lat = primary.get("latitude")
    lon = primary.get("longitude")
    city = primary.get("city")

    # Detect city-centre fallback
    is_centroid, centroid_reason = is_city_centre_fallback(
        lat=lat,
        lon=lon,
        city=city,
        db_session=db.session,
        current_ip=ip
    )

    # Evaluate confidence level
    confidence_level, confidence_reasons = evaluate_confidence(
        providers_results=providers,
        is_city_centre=is_centroid,
        city_centre_reason=centroid_reason
    )

    # If accuracy_radius is available on primary or any successful provider, record it
    accuracy_radius = primary.get("accuracy_radius")
    if accuracy_radius is None:
        for p in successful:
            if p.get("accuracy_radius") is not None:
                accuracy_radius = p.get("accuracy_radius")
                break

    comparison["confidence"] = confidence_level
    comparison["confidence_reasons"] = confidence_reasons
    comparison["is_city_centre"] = is_centroid
    comparison["city_centre_reason"] = centroid_reason
    comparison["selected_provider"] = primary.get("provider")

    return {
        "ip_address": primary.get("ip_address") or ip,
        "country": primary.get("country"),
        "country_code": primary.get("country_code"),
        "region": primary.get("region"),
        "city": primary.get("city"),
        "postal_code": primary.get("postal_code"),
        "latitude": lat,
        "longitude": lon,
        "timezone": primary.get("timezone"),
        "isp": primary.get("isp"),
        "organization": primary.get("organization"),
        "asn": primary.get("asn"),
        "accuracy_radius": accuracy_radius,
        "confidence": confidence_level,
        "confidence_reasons": confidence_reasons,
        "is_city_centre": is_centroid,
        "city_centre_reason": centroid_reason,
        "provider": primary.get("provider"),
        "provider_comparison": json.dumps(comparison),
        "success": True,
    }
