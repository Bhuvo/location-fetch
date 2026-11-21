import logging
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from flask import current_app
from app.services.confidence import haversine_distance_km

logger = logging.getLogger(__name__)

def query_ipinfo_provider(ip: str, token: str = "") -> Dict[str, Any]:
    """Query IPinfo API."""
    start_time = time.time()
    url = f"https://ipinfo.io/{ip}/json"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, timeout=4)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        if resp.status_code != 200:
            return {
                "provider": "ipinfo",
                "display_name": "IPinfo",
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "response_time_ms": duration_ms,
            }

        data = resp.json()
        lat, lon = None, None
        loc = data.get("loc")
        if loc and "," in loc:
            try:
                parts = loc.split(",")
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
            except (ValueError, IndexError):
                pass

        org_field = data.get("org") or ""
        asn, isp = None, org_field
        if org_field.startswith("AS"):
            parts = org_field.split(" ", 1)
            asn = parts[0]
            isp = parts[1] if len(parts) > 1 else org_field

        return {
            "provider": "ipinfo",
            "display_name": "IPinfo",
            "success": True,
            "ip_address": data.get("ip") or ip,
            "country": data.get("country"),
            "country_code": data.get("country"),
            "region": data.get("region"),
            "city": data.get("city"),
            "postal_code": data.get("postal"),
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone"),
            "isp": isp or None,
            "organization": org_field or None,
            "asn": asn,
            "accuracy_radius": None, # IPinfo basic tier does not specify radius
            "response_time_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "provider": "ipinfo",
            "display_name": "IPinfo",
            "success": False,
            "error": str(e),
            "response_time_ms": duration_ms,
        }


def query_ip_api_provider(ip: str, api_key: str = "") -> Dict[str, Any]:
    """Query ip-api.com provider."""
    start_time = time.time()
    fields = "status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
    url = f"http://ip-api.com/json/{ip}?fields={fields}"
    if api_key:
        url = f"https://pro.ip-api.com/json/{ip}?key={api_key}&fields={fields}"

    try:
        resp = requests.get(url, timeout=4)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        if resp.status_code != 200:
            return {
                "provider": "ip-api",
                "display_name": "ip-api",
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "response_time_ms": duration_ms,
            }

        data = resp.json()
        if data.get("status") != "success":
            return {
                "provider": "ip-api",
                "display_name": "ip-api",
                "success": False,
                "error": data.get("message", "Provider returned error status"),
                "response_time_ms": duration_ms,
            }

        lat, lon = None, None
        if data.get("lat") is not None and data.get("lon") is not None:
            try:
                lat = float(data["lat"])
                lon = float(data["lon"])
            except (ValueError, TypeError):
                pass

        as_field = data.get("as") or ""
        asn = as_field.split(" ")[0].strip() if as_field.startswith("AS") else None

        return {
            "provider": "ip-api",
            "display_name": "ip-api",
            "success": True,
            "ip_address": data.get("query") or ip,
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "region": data.get("regionName"),
            "city": data.get("city"),
            "postal_code": data.get("zip") if data.get("zip") else None,
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone"),
            "isp": data.get("isp"),
            "organization": data.get("org") or data.get("isp"),
            "asn": asn,
            "accuracy_radius": None,
            "response_time_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "provider": "ip-api",
            "display_name": "ip-api",
            "success": False,
            "error": str(e),
            "response_time_ms": duration_ms,
        }


def query_maxmind_or_ipapi_provider(ip: str, account_id: str = "", license_key: str = "") -> Dict[str, Any]:
    """
    Query MaxMind GeoIP Precision Web Service if credentials configured,
    or fallback to ipapi.co (which supplies accuracy radius).
    """
    start_time = time.time()

    # If MaxMind GeoIP web service credentials exist
    if account_id and license_key:
        url = f"https://geoip.maxmind.com/geoip/v2.1/city/{ip}"
        try:
            resp = requests.get(url, auth=(account_id, license_key), timeout=4)
            duration_ms = round((time.time() - start_time) * 1000, 1)
            if resp.status_code == 200:
                data = resp.json()
                location = data.get("location", {})
                lat = location.get("latitude")
                lon = location.get("longitude")
                radius = location.get("accuracy_radius")

                city = data.get("city", {}).get("names", {}).get("en")
                country = data.get("country", {}).get("names", {}).get("en")
                country_code = data.get("country", {}).get("iso_code")
                postal = data.get("postal", {}).get("code")
                subdivisions = data.get("subdivisions", [])
                region = subdivisions[0].get("names", {}).get("en") if subdivisions else None

                traits = data.get("traits", {})
                isp = traits.get("isp")
                org = traits.get("organization") or isp
                asn = f"AS{traits.get('autonomous_system_number')}" if traits.get("autonomous_system_number") else None

                return {
                    "provider": "maxmind",
                    "display_name": "MaxMind GeoIP2",
                    "success": True,
                    "ip_address": ip,
                    "country": country,
                    "country_code": country_code,
                    "region": region,
                    "city": city,
                    "postal_code": postal,
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": location.get("time_zone"),
                    "isp": isp,
                    "organization": org,
                    "asn": asn,
                    "accuracy_radius": radius,
                    "response_time_ms": duration_ms,
                }
            else:
                return {
                    "provider": "maxmind",
                    "display_name": "MaxMind GeoIP2",
                    "success": False,
                    "error": f"MaxMind HTTP {resp.status_code}",
                    "response_time_ms": duration_ms,
                }
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "provider": "maxmind",
                "display_name": "MaxMind GeoIP2",
                "success": False,
                "error": str(e),
                "response_time_ms": duration_ms,
            }

    # Third provider fallback: ipapi.co (provides accuracy radius in km)
    url = f"https://ipapi.co/{ip}/json/"
    headers = {"User-Agent": "IPTrace/2.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=4)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        if resp.status_code != 200:
            return {
                "provider": "ipapi_co",
                "display_name": "ipapi.co",
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "response_time_ms": duration_ms,
            }

        data = resp.json()
        if data.get("error"):
            return {
                "provider": "ipapi_co",
                "display_name": "ipapi.co",
                "success": False,
                "error": data.get("reason", "API Error"),
                "response_time_ms": duration_ms,
            }

        lat, lon = None, None
        if data.get("latitude") is not None and data.get("longitude") is not None:
            try:
                lat = float(data["latitude"])
                lon = float(data["longitude"])
            except (ValueError, TypeError):
                pass

        radius = None
        if data.get("accuracy"):
            try:
                radius = float(data["accuracy"])
            except (ValueError, TypeError):
                pass

        return {
            "provider": "ipapi_co",
            "display_name": "ipapi.co",
            "success": True,
            "ip_address": data.get("ip") or ip,
            "country": data.get("country_name"),
            "country_code": data.get("country_code"),
            "region": data.get("region"),
            "city": data.get("city"),
            "postal_code": data.get("postal"),
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone"),
            "isp": data.get("org"),
            "organization": data.get("org"),
            "asn": data.get("asn"),
            "accuracy_radius": radius,
            "response_time_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "provider": "ipapi_co",
            "display_name": "ipapi.co",
            "success": False,
            "error": str(e),
            "response_time_ms": duration_ms,
        }


def compare_all_providers(ip: str) -> Dict[str, Any]:
    """
    Run multi-provider comparison concurrently.
    
    CRITICAL RULE: Never average coordinates from different providers!
    Each provider's coordinates and metadata are preserved independently.
    """
    ipinfo_token = current_app.config.get("IPINFO_API_TOKEN", "")
    ip_api_key = current_app.config.get("IP_API_KEY", "")
    maxmind_account = current_app.config.get("MAXMIND_ACCOUNT_ID", "")
    maxmind_key = current_app.config.get("MAXMIND_LICENSE_KEY", "")

    providers_results: List[Dict[str, Any]] = []

    # Query providers in parallel using thread pool
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(query_ipinfo_provider, ip, ipinfo_token): "ipinfo",
            executor.submit(query_ip_api_provider, ip, ip_api_key): "ip-api",
            executor.submit(query_maxmind_or_ipapi_provider, ip, maxmind_account, maxmind_key): "maxmind_or_ipapi",
        }

        for future in as_completed(futures):
            try:
                res = future.result()
                providers_results.append(res)
            except Exception as e:
                p_name = futures[future]
                providers_results.append({
                    "provider": p_name,
                    "display_name": p_name.title(),
                    "success": False,
                    "error": str(e),
                    "response_time_ms": 0.0,
                })

    # Sort results in consistent order: IPinfo, ip-api, MaxMind/ipapi.co
    order = {"ipinfo": 0, "ip-api": 1, "maxmind": 2, "ipapi_co": 2}
    providers_results.sort(key=lambda x: order.get(x.get("provider", ""), 99))

    # Calculate pairwise differences without averaging
    successful = [p for p in providers_results if p.get("success") and p.get("latitude") is not None]
    variances: List[Dict[str, Any]] = []
    max_variance_km = 0.0

    for i in range(len(successful)):
        for j in range(i + 1, len(successful)):
            p1 = successful[i]
            p2 = successful[j]
            dist = round(haversine_distance_km(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"]), 2)
            if dist > max_variance_km:
                max_variance_km = dist
            variances.append({
                "provider_a": p1["display_name"],
                "provider_b": p2["display_name"],
                "distance_km": dist,
                "city_a": p1.get("city"),
                "city_b": p2.get("city"),
                "agrees_on_city": str(p1.get("city", "")).lower() == str(p2.get("city", "")).lower()
            })

    return {
        "ip_address": ip,
        "providers": providers_results,
        "total_providers_queried": len(providers_results),
        "successful_providers": len(successful),
        "pairwise_variances": variances,
        "max_variance_km": max_variance_km,
    }
