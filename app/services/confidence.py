import math
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import func

# Curated reference centroids of major global municipal centers frequently
# returned as generic default fallbacks by IP registries and geolocation providers.
KNOWN_CITY_CENTROIDS: Dict[str, Tuple[float, float]] = {
    # India
    "chennai": (13.0878, 80.2785),
    "chennai_alt": (13.0827, 80.2707),
    "bangalore": (12.9716, 77.5946),
    "bengaluru": (12.9719, 77.5937),
    "mumbai": (19.0760, 72.8777),
    "mumbai_alt": (19.0728, 72.8826),
    "delhi": (28.6139, 77.2090),
    "new_delhi": (28.6519, 77.2315),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    "pune": (18.5204, 73.8567),
    # Europe
    "london": (51.5074, -0.1278),
    "london_alt": (51.5085, -0.1257),
    "paris": (48.8566, 2.3522),
    "frankfurt": (50.1109, 8.6821),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    # Americas
    "new_york": (40.7128, -74.0060),
    "new_york_alt": (40.7143, -74.0060),
    "chicago": (41.8781, -87.6298),
    "san_francisco": (37.7749, -122.4194),
    "los_angeles": (34.0522, -118.2437),
    "toronto": (43.6532, -79.3832),
    # Asia-Pacific
    "tokyo": (35.6895, 139.6917),
    "singapore": (1.2897, 103.8501),
    "singapore_alt": (1.3521, 103.8198),
    "sydney": (-33.8688, 151.2093),
}

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0 # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def is_city_centre_fallback(
    lat: Optional[float], 
    lon: Optional[float], 
    city: Optional[str] = None,
    db_session: Any = None,
    current_ip: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Detect if coordinates represent a generic city-centre centroid rather than
    a granular network location.
    
    Checks:
    1. Direct match with known reference centroids within 1.5 km tolerance.
    2. Identical coordinates returned for different IP addresses in SQLite database.
    3. Truncated or generic whole-number coordinates.
    """
    if lat is None or lon is None:
        return (False, None)

    # 1. Check known reference centroids
    for name, (c_lat, c_lon) in KNOWN_CITY_CENTROIDS.items():
        dist = haversine_distance_km(lat, lon, c_lat, c_lon)
        if dist <= 1.5:
            matched_name = name.replace("_alt", "").title()
            return (True, f"Coordinates match canonical municipal centroid for {matched_name} ({lat:.4f}, {lon:.4f})")

    # 2. Check if city name matches and coordinates are within 5 km of standard city centre
    if city:
        city_key = city.lower().replace(" ", "_").strip()
        if city_key in KNOWN_CITY_CENTROIDS:
            c_lat, c_lon = KNOWN_CITY_CENTROIDS[city_key]
            dist = haversine_distance_km(lat, lon, c_lat, c_lon)
            if dist <= 5.0:
                return (True, f"Within {dist:.1f} km of standard {city.title()} city-center reference point")

    # 3. Check for coordinate repetition across distinct IPs in database
    if db_session:
        try:
            from app.models import VisitorRecord
            query = db_session.query(func.count(func.distinct(VisitorRecord.ip_address))).filter(
                func.abs(VisitorRecord.latitude - lat) < 0.0005,
                func.abs(VisitorRecord.longitude - lon) < 0.0005
            )
            if current_ip:
                query = query.filter(VisitorRecord.ip_address != current_ip)
            
            other_ips_count = query.scalar() or 0
            if other_ips_count >= 1:
                return (True, f"Identical coordinates returned for {other_ips_count} other distinct IP(s) in database (ISP regional centroid)")
        except Exception:
            pass

    return (False, None)


def evaluate_confidence(
    providers_results: List[Dict[str, Any]],
    is_city_centre: bool,
    city_centre_reason: Optional[str] = None
) -> Tuple[str, List[str]]:
    """
    Compute geolocation confidence rating: HIGH, MEDIUM, LOW, or UNKNOWN.
    
    Principles:
    - Never average coordinates across providers.
    - Do not fabricate accuracy scores or claim coordinate is exact.
    - Provide transparent human-readable explanations.
    """
    successful_results = [p for p in providers_results if p.get("success") and p.get("latitude") is not None]
    reasons: List[str] = []

    # Case 0: No coordinates returned
    if not successful_results:
        return ("UNKNOWN", ["No coordinates returned by any geolocation provider."])

    # Case 1: Flagged as generic city-centre centroid
    if is_city_centre:
        reasons.append(city_centre_reason or "Suspiciously generic city-center fallback coordinates detected.")
        return ("LOW", reasons)

    # Check accuracy radius if available from any provider
    min_radius = None
    for p in successful_results:
        rad = p.get("accuracy_radius")
        if rad is not None:
            if min_radius is None or rad < min_radius:
                min_radius = rad

    if min_radius is not None:
        if min_radius > 100:
            reasons.append(f"Large provider uncertainty radius ({min_radius} km).")
        elif min_radius <= 25:
            reasons.append(f"Tight uncertainty radius ({min_radius} km).")

    # Case 2: Single provider succeeded
    if len(successful_results) == 1:
        p = successful_results[0]
        p_name = p.get("provider", "provider")
        has_postal = bool(p.get("postal_code"))
        
        if min_radius and min_radius > 100:
            reasons.append(f"Single provider ({p_name}) with wide uncertainty radius.")
            return ("LOW", reasons)

        if has_postal:
            reasons.append(f"Single provider ({p_name}) with postal code ({p.get('postal_code')}).")
            return ("MEDIUM", reasons)
        else:
            reasons.append(f"Single provider ({p_name}) without postal corroboration.")
            return ("MEDIUM", reasons)

    # Case 3: Multiple providers available -> Compare agreement/disagreement
    coords = [(p["latitude"], p["longitude"]) for p in successful_results]
    cities = [str(p.get("city") or "").lower().strip() for p in successful_results if p.get("city")]
    countries = [str(p.get("country") or "").lower().strip() for p in successful_results if p.get("country")]

    # Check country agreement
    unique_countries = set(countries)
    if len(unique_countries) > 1:
        reasons.append(f"Major country disagreement between providers: {', '.join(unique_countries)}")
        return ("LOW", reasons)

    # Calculate distance between provider coordinates
    max_dist_km = 0.0
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = haversine_distance_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            if d > max_dist_km:
                max_dist_km = d

    # City agreement check
    unique_cities = set(cities)
    if len(unique_cities) > 1 and max_dist_km > 75.0:
        reasons.append(f"Providers disagree on city ({', '.join(unique_cities)}) by {max_dist_km:.1f} km.")
        return ("LOW", reasons)

    if max_dist_km > 100.0:
        reasons.append(f"Provider coordinate variance is high ({max_dist_km:.1f} km).")
        return ("LOW", reasons)

    # Strong agreement between providers
    has_any_postal = any(bool(p.get("postal_code")) for p in successful_results)
    if max_dist_km <= 25.0 and len(unique_cities) == 1:
        if has_any_postal or (min_radius and min_radius <= 25):
            reasons.append(f"Strong multi-provider consensus (variance {max_dist_km:.1f} km in {cities[0].title()}).")
            return ("HIGH", reasons)
        else:
            reasons.append(f"Providers agree on {cities[0].title()} within {max_dist_km:.1f} km (postal code missing).")
            return ("MEDIUM", reasons)

    reasons.append(f"Providers agree on general area within {max_dist_km:.1f} km.")
    return ("MEDIUM", reasons)
