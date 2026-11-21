from unittest.mock import patch, MagicMock
from app.services.ip_resolver import get_client_ip, is_private_ip, parse_user_agent
from app.services.geolocation import lookup_ip_geolocation

def test_is_private_ip():
    """Verify detection of loopback, private, and public IPs."""
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("::1") is True
    assert is_private_ip("192.168.1.50") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("1.1.1.1") is False


def test_ip_resolution_direct(app):
    """When proxy headers are disabled, ignore X-Forwarded-For to prevent spoofing."""
    with app.test_request_context(
        "/", 
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
        headers={"X-Forwarded-For": "203.0.113.199"}
    ) as ctx:
        app.config["USE_PROXY_HEADERS"] = False
        client_ip = get_client_ip(ctx.request)
        assert client_ip == "198.51.100.10"


def test_ip_resolution_trusted_proxy(app):
    """When behind a trusted proxy, parse real client from X-Forwarded-For."""
    with app.test_request_context(
        "/",
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
        headers={"X-Forwarded-For": "198.51.100.55, 127.0.0.1"}
    ) as ctx:
        app.config["USE_PROXY_HEADERS"] = True
        app.config["TRUSTED_PROXIES"] = ["127.0.0.1"]
        client_ip = get_client_ip(ctx.request)
        assert client_ip == "198.51.100.55"


def test_parse_user_agent():
    """Verify parsing user agent strings."""
    chrome_win = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    browser, os = parse_user_agent(chrome_win)
    assert "Chrome" in browser
    assert "Windows" in os

    empty_browser, empty_os = parse_user_agent("")
    assert empty_browser == "Unknown Browser"
    assert empty_os == "Unknown OS"


@patch("requests.get")
def test_geo_lookup_ipinfo_success(mock_get, app):
    """Test successful IPinfo response parsing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ip": "8.8.8.8",
        "city": "Mountain View",
        "region": "California",
        "country": "US",
        "loc": "37.3860,-122.0838",
        "org": "AS15169 Google LLC",
        "postal": "94035",
        "timezone": "America/Los_Angeles"
    }
    mock_get.return_value = mock_resp

    with app.app_context():
        res = lookup_ip_geolocation("8.8.8.8")
        assert res["success"] is True
        assert res["city"] == "Mountain View"
        assert res["country"] == "US"
        assert res["latitude"] == 37.3860
        assert res["longitude"] == -122.0838
        assert res["postal_code"] == "94035"
        assert res["asn"] == "AS15169"
        assert res["isp"] == "Google LLC"


@patch("requests.get")
def test_geo_lookup_fallback_on_primary_failure(mock_get, app):
    """Test fallback to ip-api when primary provider fails."""
    def mock_dispatch(url, *args, **kwargs):
        if "ipinfo.io" in url:
            return MagicMock(status_code=500)
        elif "ip-api.com" in url:
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "country": "Germany",
                    "countryCode": "DE",
                    "regionName": "Bavaria",
                    "city": "Munich",
                    "zip": "80331",
                    "lat": 48.1351,
                    "lon": 11.5820,
                    "timezone": "Europe/Berlin",
                    "isp": "Deutsche Telekom AG",
                    "as": "AS3320 Deutsche Telekom AG",
                    "query": "194.25.0.1"
                }
            )
        return MagicMock(status_code=500)

    mock_get.side_effect = mock_dispatch

    with app.app_context():
        res = lookup_ip_geolocation("194.25.0.1")
        assert res["success"] is True
        assert res["provider"] == "ip-api"
        assert res["city"] == "Munich"
        assert res["country"] == "Germany"
        assert res["latitude"] == 48.1351


@patch("requests.get")
def test_geo_lookup_missing_postal_code(mock_get, app):
    """Test that missing postal code is stored as None without inventing fake data."""
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "ip": "93.184.216.34",
            "city": "Norwell",
            "region": "Massachusetts",
            "country": "US",
            "loc": "42.1615,-70.7937",
            "org": "AS15133 Edgecast",
            "postal": None  # Missing postal
        }
    )
    mock_get.return_value = mock_resp

    with app.app_context():
        res = lookup_ip_geolocation("93.184.216.34")
        assert res["success"] is True
        assert res["postal_code"] is None
        assert res["city"] == "Norwell"


@patch("requests.get")
def test_geo_lookup_total_outage(mock_get, app):
    """Test total provider outage handled gracefully returning None fields."""
    mock_get.side_effect = Exception("Connection refused / timeout")

    with app.app_context():
        res = lookup_ip_geolocation("93.184.216.35")
        assert res["success"] is False
        assert res["city"] is None
        assert res["country"] is None
        assert res["latitude"] is None
        assert res["longitude"] is None
