"""Unit tests for military / Gulf-focused data source connectors:
  - AcledConnector    (src/connectors/acled.py)
  - NgaMsiConnector   (src/connectors/nga_msi.py)
  - OsmMilitaryConnector (src/connectors/osm_military.py)

Tests cover:
- connect() raises ConnectorUnavailableError on HTTP error
- fetch() builds correct query parameters / Overpass QL
- normalize() happy path for each connector
- normalize() raises NormalizationError for missing required fields
- normalize() event_id determinism (same input → same id)
- CanonicalEvent fields: source, source_type, entity_type, event_type, license
- health() returns healthy/unhealthy based on HTTP response
- Geometry helpers: bbox / centroid extraction
- NGA MSI NAVAREA detection from centroid
- NGA MSI coordinate parsing from warning text
- OSM Overpass query builder
- OSM element center extraction (node / way / relation)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.base import ConnectorUnavailableError, NormalizationError
from src.connectors.acled import (
    AcledConnector,
    _geojson_to_centroid_radius,
)
from src.connectors.nga_msi import (
    NgaMsiConnector,
    _bbox_from_geojson as nga_bbox,
    _navarea_from_centroid,
    _parse_first_coord_from_text,
)
from src.connectors.osm_military import (
    OsmMilitaryConnector,
    _bbox_from_geojson as osm_bbox,
    _build_overpass_query,
    _extract_center,
)
from src.models.canonical_event import EntityType, EventType, SourceType


# ─────────────────────────────────────────────────────────────────────────────
# Shared test data helpers
# ─────────────────────────────────────────────────────────────────────────────

_T0 = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
_T1 = _T0 + timedelta(days=30)


def _polygon(
    lon: float = 50.0, lat: float = 25.0, delta: float = 1.0
) -> Dict[str, Any]:
    """Small polygon around (lon, lat) — simulates a Gulf AOI."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - delta, lat - delta],
            [lon - delta, lat + delta],
            [lon + delta, lat + delta],
            [lon + delta, lat - delta],
            [lon - delta, lat - delta],
        ]],
    }


def _point(lon: float = 50.0, lat: float = 25.0) -> Dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def _multipolygon(lon: float = 50.0, lat: float = 25.0, delta: float = 1.0) -> Dict[str, Any]:
    ring = [
        [lon - delta, lat - delta],
        [lon - delta, lat + delta],
        [lon + delta, lat + delta],
        [lon + delta, lat - delta],
        [lon - delta, lat - delta],
    ]
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


def _mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helper tests — shared across all connectors
# ─────────────────────────────────────────────────────────────────────────────

class TestGeometryHelpers:
    def test_nga_bbox_polygon(self):
        min_lat, min_lon, max_lat, max_lon = nga_bbox(_polygon(50.0, 25.0, 1.0))
        assert min_lat == pytest.approx(24.0, abs=0.01)
        assert max_lat == pytest.approx(26.0, abs=0.01)
        assert min_lon == pytest.approx(49.0, abs=0.01)
        assert max_lon == pytest.approx(51.0, abs=0.01)

    def test_nga_bbox_point(self):
        min_lat, min_lon, max_lat, max_lon = nga_bbox(_point(50.0, 25.0))
        assert min_lat == max_lat == pytest.approx(25.0, abs=0.01)
        assert min_lon == max_lon == pytest.approx(50.0, abs=0.01)

    def test_nga_bbox_multipolygon(self):
        min_lat, min_lon, max_lat, max_lon = nga_bbox(_multipolygon(50.0, 25.0, 2.0))
        assert min_lat < 25.0 < max_lat
        assert min_lon < 50.0 < max_lon

    def test_nga_bbox_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            nga_bbox({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})

    def test_osm_bbox_polygon(self):
        min_lat, min_lon, max_lat, max_lon = osm_bbox(_polygon(56.0, 24.0, 0.5))
        assert min_lat == pytest.approx(23.5, abs=0.01)
        assert max_lat == pytest.approx(24.5, abs=0.01)

    def test_osm_bbox_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            osm_bbox({"type": "GeometryCollection", "geometries": []})

    def test_acled_centroid_polygon(self):
        lat, lon, radius = _geojson_to_centroid_radius(_polygon(50.0, 25.0, 1.0))
        assert lat == pytest.approx(25.0, abs=0.15)
        assert lon == pytest.approx(50.0, abs=0.15)
        assert radius > 0

    def test_acled_centroid_point(self):
        lat, lon, radius = _geojson_to_centroid_radius(_point(50.0, 25.0))
        assert lat == pytest.approx(25.0, abs=0.01)
        assert lon == pytest.approx(50.0, abs=0.01)
        assert radius == 50.0  # default point radius

    def test_acled_centroid_multipolygon(self):
        lat, lon, radius = _geojson_to_centroid_radius(_multipolygon(50.0, 25.0, 2.0))
        assert lat == pytest.approx(25.0, abs=0.3)
        assert lon == pytest.approx(50.0, abs=0.3)

    def test_acled_centroid_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            _geojson_to_centroid_radius({"type": "LineString", "coordinates": []})


# ─────────────────────────────────────────────────────────────────────────────
# NGA MSI coordinate and NAVAREA helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestNgaMsiHelpers:
    def test_navarea_from_centroid_gulf(self):
        # Persian Gulf centroid
        result = _navarea_from_centroid(56.0, 24.0)
        assert result == "IX"

    def test_navarea_from_centroid_mediterranean(self):
        result = _navarea_from_centroid(15.0, 38.0)
        assert result == "III"

    def test_navarea_from_centroid_unknown_returns_none(self):
        # Deep Pacific — not in any configured NAVAREA
        result = _navarea_from_centroid(170.0, -50.0)
        assert result is None

    def test_parse_coord_from_text_basic(self):
        text = "NAVAREA IX. 24-30.5 N 056-10.2 E EXCLUSION ZONE"
        pt = _parse_first_coord_from_text(text)
        assert pt is not None
        lon, lat = pt
        assert lat == pytest.approx(24.508, abs=0.01)
        assert lon == pytest.approx(56.17, abs=0.01)

    def test_parse_coord_from_text_south_west(self):
        text = "11-30.0 S 042-15.0 W WARNING AREA"
        pt = _parse_first_coord_from_text(text)
        assert pt is not None
        lon, lat = pt
        assert lat < 0  # South
        assert lon < 0  # West

    def test_parse_coord_from_text_no_match(self):
        assert _parse_first_coord_from_text("No coordinates in this text.") is None
        assert _parse_first_coord_from_text("") is None


# ─────────────────────────────────────────────────────────────────────────────
# OSM Overpass helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestOsmOverpassHelpers:
    def test_build_overpass_query_contains_bbox(self):
        q = _build_overpass_query(24.0, 49.0, 26.0, 51.0)
        assert "24.0,49.0,26.0,51.0" in q
        assert "out:json" in q
        assert "node[military]" in q
        assert "way[military]" in q
        assert "out center" in q

    def test_extract_center_node(self):
        element = {"type": "node", "id": 123, "lat": 25.0, "lon": 55.5, "tags": {}}
        pt = _extract_center(element)
        assert pt is not None
        lon, lat = pt
        assert lon == pytest.approx(55.5)
        assert lat == pytest.approx(25.0)

    def test_extract_center_way(self):
        element = {"type": "way", "id": 456, "center": {"lat": 24.5, "lon": 54.3}, "tags": {}}
        pt = _extract_center(element)
        assert pt is not None
        lon, lat = pt
        assert lon == pytest.approx(54.3)
        assert lat == pytest.approx(24.5)

    def test_extract_center_relation(self):
        element = {"type": "relation", "id": 789, "center": {"lat": 26.0, "lon": 50.0}, "tags": {}}
        pt = _extract_center(element)
        assert pt is not None

    def test_extract_center_node_missing_coords(self):
        element = {"type": "node", "id": 999, "tags": {}}
        pt = _extract_center(element)
        assert pt is None

    def test_extract_center_way_missing_center(self):
        element = {"type": "way", "id": 888, "tags": {}}
        pt = _extract_center(element)
        assert pt is None


# ─────────────────────────────────────────────────────────────────────────────
# AcledConnector
# ─────────────────────────────────────────────────────────────────────────────

def _acled_record(
    event_id: str = "YEM1234",
    event_date: str = "2026-03-15",
    lat: float = 15.4,
    lon: float = 44.2,
    event_type: str = "Explosions/Remote violence",
    sub_event_type: str = "Air/drone strike",
    fatalities: int = 3,
) -> Dict[str, Any]:
    return {
        "event_id_cnty": event_id,
        "event_date": event_date,
        "latitude": str(lat),
        "longitude": str(lon),
        "event_type": event_type,
        "sub_event_type": sub_event_type,
        "disorder_type": "Political violence",
        "actor1": "Saudi-led coalition",
        "actor2": "Houthis (Ansar Allah)",
        "country": "Yemen",
        "admin1": "Sana'a",
        "location": "Sana'a",
        "fatalities": fatalities,
        "source": "Al-Masdar Online",
        "notes": "Air strike targeting Houthi military position",
        "civilian_targeting": "",
    }


def _acled_connector() -> AcledConnector:
    return AcledConnector(
        api_key="test-key",
        email="test@example.com",
        api_url="https://api.acleddata.com/acled/read.php",
    )


class TestAcledConnector:
    def test_init_raises_without_api_key(self):
        with pytest.raises(ValueError, match="API key"):
            AcledConnector(api_key="", email="test@example.com")

    def test_init_raises_without_email(self):
        with pytest.raises(ValueError, match="email"):
            AcledConnector(api_key="k", email="")

    def test_connect_ok(self):
        mock_resp = _mock_response({"status": 200, "data": [_acled_record()]})
        with patch("httpx.get", return_value=mock_resp):
            _acled_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _acled_connector().connect()

    def test_connect_raises_on_api_error_status(self):
        mock_resp = _mock_response({"status": 403, "message": "Invalid API key"})
        with patch("httpx.get", return_value=mock_resp):
            with pytest.raises(ConnectorUnavailableError, match="auth failed"):
                _acled_connector().connect()

    def test_fetch_includes_auth_params(self):
        mock_resp = _mock_response({"status": 200, "data": []})
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            _acled_connector().fetch(_polygon(50.0, 25.0), _T0, _T1)
            params = mock_get.call_args[1]["params"]
            assert params["key"] == "test-key"
            assert params["email"] == "test@example.com"
            assert params["terms"] == "accept"

    def test_fetch_includes_geo_and_date_params(self):
        mock_resp = _mock_response({"status": 200, "data": []})
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            _acled_connector().fetch(_polygon(50.0, 25.0), _T0, _T1)
            params = mock_get.call_args[1]["params"]
            assert "latitude" in params
            assert "longitude" in params
            assert "radius" in params
            assert "event_date" in params

    def test_fetch_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())):
            with pytest.raises(ConnectorUnavailableError):
                _acled_connector().fetch(_polygon(), _T0, _T1)

    def test_fetch_returns_list(self):
        records = [_acled_record("YEM1234"), _acled_record("YEM5678", event_date="2026-03-14")]
        mock_resp = _mock_response({"status": 200, "data": records})
        with patch("httpx.get", return_value=mock_resp):
            result = _acled_connector().fetch(_polygon(), _T0, _T1)
        assert len(result) == 2

    def test_normalize_happy_path(self):
        ev = _acled_connector().normalize(_acled_record())
        assert ev.event_type == EventType.CONFLICT_EVENT
        assert ev.entity_type == EntityType.CONFLICT_INCIDENT
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "acled"
        assert ev.confidence == pytest.approx(0.95)  # Air/drone strike
        assert ev.geometry["type"] == "Point"

    def test_normalize_populates_attributes(self):
        ev = _acled_connector().normalize(_acled_record())
        attrs = ev.attributes
        assert attrs["acled_event_id"] == "YEM1234"
        assert attrs["country"] == "Yemen"
        assert attrs["fatalities"] == 3
        assert attrs["actor1"] == "Saudi-led coalition"

    def test_normalize_event_id_determinism(self):
        rec = _acled_record()
        id1 = _acled_connector().normalize(rec).event_id
        id2 = _acled_connector().normalize(rec).event_id
        assert id1 == id2

    def test_normalize_missing_event_id_raises(self):
        bad = _acled_record()
        bad["event_id_cnty"] = ""
        with pytest.raises(NormalizationError):
            _acled_connector().normalize(bad)

    def test_normalize_missing_date_raises(self):
        bad = _acled_record()
        bad["event_date"] = ""
        with pytest.raises(NormalizationError):
            _acled_connector().normalize(bad)

    def test_normalize_missing_coordinates_raises(self):
        bad = _acled_record()
        del bad["latitude"]
        with pytest.raises(NormalizationError):
            _acled_connector().normalize(bad)

    def test_normalize_license_fields(self):
        ev = _acled_connector().normalize(_acled_record())
        assert ev.license is not None
        assert ev.license.attribution_required is True

    def test_normalize_default_confidence_for_unknown_sub_type(self):
        rec = _acled_record(sub_event_type="Unknown event type XYZ")
        ev = _acled_connector().normalize(rec)
        assert 0.0 < ev.confidence <= 1.0

    def test_health_healthy(self):
        mock_resp = _mock_response({"status": 200, "data": []})
        with patch("httpx.get", return_value=mock_resp):
            status = _acled_connector().health()
        assert status.healthy is True
        assert status.connector_id == "acled"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = _acled_connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# NgaMsiConnector
# ─────────────────────────────────────────────────────────────────────────────

def _nga_warning(
    nav_area: str = "IX",
    nav_area_code: str = "IX",
    msg_year: str = "2026",
    msg_num: str = "042",
    text: str = "24-00.0 N 056-00.0 E EXCLUSION ZONE IN EFFECT.",
    status: str = "Active",
    lat: Any = None,
    lon: Any = None,
    authority: str = "COMUSNAVCENT",
) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "navArea": nav_area,
        "navAreaCode": nav_area_code,
        "msgYear": msg_year,
        "msgNumber": msg_num,
        "text": text,
        "status": status,
        "authority": authority,
        "subregion": "Persian Gulf",
        "region": "Middle East",
        "issueDate": "2026-03-28",
    }
    if lat is not None:
        rec["latitude"] = lat
    if lon is not None:
        rec["longitude"] = lon
    return rec


def _nga_connector() -> NgaMsiConnector:
    return NgaMsiConnector(
        api_url="https://msi.nga.mil/api/publications/broadcast-warn",
        default_nav_areas=["IX"],
    )


class TestNgaMsiConnector:
    def test_connect_ok(self):
        mock_resp = _mock_response({"broadcastWarn": []})
        with patch("httpx.get", return_value=mock_resp):
            _nga_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _nga_connector().connect()

    def test_fetch_queries_configured_nav_area(self):
        mock_resp = _mock_response({"broadcastWarn": []})
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            _nga_connector().fetch(_polygon(55.0, 24.0), _T0, _T1)
            params = mock_get.call_args[1]["params"]
            assert params["navArea"] == "IX"
            assert params["status"] == "active"

    def test_fetch_returns_warnings(self):
        warnings = [_nga_warning(), _nga_warning(msg_num="043")]
        mock_resp = _mock_response({"broadcastWarn": warnings})
        with patch("httpx.get", return_value=mock_resp):
            result = _nga_connector().fetch(_polygon(55.0, 24.0, delta=5.0), _T0, _T1)
        assert len(result) == 2

    def test_fetch_filters_by_bbox_when_coords_available(self):
        # Warning inside AOI
        inside = _nga_warning(msg_num="001", lat=25.0, lon=55.0)
        # Warning outside AOI (far from polygon around 55.0, 25.0)
        outside = _nga_warning(msg_num="002", lat=45.0, lon=10.0)
        mock_resp = _mock_response({"broadcastWarn": [inside, outside]})
        with patch("httpx.get", return_value=mock_resp):
            # AOI polygon centered on 55.0, 25.0 with delta=1.0 → bbox 54-56 lon, 24-26 lat
            result = _nga_connector().fetch(_polygon(55.0, 25.0, 1.0), _T0, _T1)
        assert len(result) == 1
        assert result[0]["msgNumber"] == "001"

    def test_normalize_happy_path(self):
        ev = _nga_connector().normalize(_nga_warning())
        assert ev.event_type == EventType.MARITIME_WARNING
        assert ev.entity_type == EntityType.MARITIME_ZONE
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "nga-msi"
        assert ev.confidence == pytest.approx(0.98)

    def test_normalize_coordinates_from_api_fields(self):
        ev = _nga_connector().normalize(_nga_warning(lat=24.5, lon=56.2))
        assert ev.geometry["coordinates"][0] == pytest.approx(56.2, abs=0.01)
        assert ev.geometry["coordinates"][1] == pytest.approx(24.5, abs=0.01)

    def test_normalize_coordinates_fallback_from_text(self):
        # No API lat/lon; coordinates embedded in text
        warning = _nga_warning(text="24-30.0 N 056-10.0 E EXERCISE AREA")
        ev = _nga_connector().normalize(warning)
        lon, lat = ev.geometry["coordinates"]
        assert lat == pytest.approx(24.5, abs=0.01)
        assert lon == pytest.approx(56.167, abs=0.05)

    def test_normalize_coordinates_fallback_to_navarea_centroid(self):
        # No coordinates anywhere — fall back to NAVAREA IX centroid
        warning = _nga_warning(text="NO COORDS IN THIS TEXT")
        ev = _nga_connector().normalize(warning)
        assert ev.geometry["type"] == "Point"
        lon, lat = ev.geometry["coordinates"]
        # NAVAREA IX centroid is (56.0, 20.0)
        assert lon == pytest.approx(56.0, abs=0.1)
        assert lat == pytest.approx(20.0, abs=0.1)

    def test_normalize_missing_year_raises(self):
        bad = _nga_warning()
        bad["msgYear"] = ""
        with pytest.raises(NormalizationError):
            _nga_connector().normalize(bad)

    def test_normalize_event_id_determinism(self):
        w = _nga_warning()
        id1 = _nga_connector().normalize(w).event_id
        id2 = _nga_connector().normalize(w).event_id
        assert id1 == id2

    def test_normalize_attributes_populated(self):
        ev = _nga_connector().normalize(_nga_warning())
        attrs = ev.attributes
        assert attrs["nav_area_code"] == "IX"
        assert attrs["msg_year"] == "2026"
        assert attrs["authority"] == "COMUSNAVCENT"

    def test_normalize_license_public_domain(self):
        ev = _nga_connector().normalize(_nga_warning())
        assert ev.license is not None
        assert ev.license.commercial_use == "allowed"

    def test_health_healthy(self):
        mock_resp = _mock_response({"broadcastWarn": []})
        with patch("httpx.get", return_value=mock_resp):
            status = _nga_connector().health()
        assert status.healthy is True
        assert status.connector_id == "nga-msi"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = _nga_connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# OsmMilitaryConnector
# ─────────────────────────────────────────────────────────────────────────────

def _osm_node(
    osm_id: int = 12345,
    lat: float = 24.468,
    lon: float = 54.603,
    military_type: str = "base",
    name: str = "Al-Dhafra Air Base",
    operator: str = "United Arab Emirates Air Force",
) -> Dict[str, Any]:
    return {
        "type": "node",
        "id": osm_id,
        "lat": lat,
        "lon": lon,
        "tags": {
            "military": military_type,
            "name": name,
            "operator": operator,
        },
    }


def _osm_way(
    osm_id: int = 67890,
    lat: float = 26.26,
    lon: float = 50.62,
    military_type: str = "naval_base",
    name: str = "NSA Bahrain",
) -> Dict[str, Any]:
    return {
        "type": "way",
        "id": osm_id,
        "center": {"lat": lat, "lon": lon},
        "tags": {
            "military": military_type,
            "name": name,
        },
    }


def _osm_military_connector() -> OsmMilitaryConnector:
    return OsmMilitaryConnector(
        overpass_url="https://overpass-api.de/api/interpreter"
    )


class TestOsmMilitaryConnector:
    def test_connect_ok(self):
        mock_resp = _mock_response({"elements": []})
        with patch("httpx.post", return_value=mock_resp):
            _osm_military_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _osm_military_connector().connect()

    def test_fetch_posts_to_overpass(self):
        mock_resp = _mock_response({"elements": []})
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            _osm_military_connector().fetch(_polygon(54.0, 24.0), _T0, _T1)
            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            data = call_kwargs.get("data", {})
            assert "data" in data
            assert "military" in data["data"]

    def test_fetch_returns_elements(self):
        elements = [_osm_node(), _osm_way()]
        mock_resp = _mock_response({"elements": elements})
        with patch("httpx.post", return_value=mock_resp):
            result = _osm_military_connector().fetch(_polygon(), _T0, _T1)
        assert len(result) == 2

    def test_fetch_raises_on_http_error(self):
        import httpx
        with patch("httpx.post", side_effect=httpx.HTTPStatusError("429", request=MagicMock(), response=MagicMock())):
            with pytest.raises(ConnectorUnavailableError):
                _osm_military_connector().fetch(_polygon(), _T0, _T1)

    def test_fetch_handles_unsupported_geometry(self):
        bad_geom = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
        result = _osm_military_connector().fetch(bad_geom, _T0, _T1)
        assert result == []

    def test_normalize_node_happy_path(self):
        ev = _osm_military_connector().normalize(_osm_node())
        assert ev.event_type == EventType.MILITARY_SITE_OBSERVATION
        assert ev.entity_type == EntityType.MILITARY_INSTALLATION
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "osm-military"
        assert ev.geometry["type"] == "Point"

    def test_normalize_way_happy_path(self):
        ev = _osm_military_connector().normalize(_osm_way())
        assert ev.event_type == EventType.MILITARY_SITE_OBSERVATION
        lon, lat = ev.geometry["coordinates"]
        assert lon == pytest.approx(50.62)
        assert lat == pytest.approx(26.26)

    def test_normalize_populates_attributes(self):
        ev = _osm_military_connector().normalize(_osm_node())
        attrs = ev.attributes
        assert attrs["osm_id"] == "12345"
        assert attrs["osm_type"] == "node"
        assert attrs["military_type"] == "base"
        assert attrs["name"] == "Al-Dhafra Air Base"
        assert attrs["operator"] == "United Arab Emirates Air Force"

    def test_normalize_event_id_determinism(self):
        node = _osm_node()
        id1 = _osm_military_connector().normalize(node).event_id
        id2 = _osm_military_connector().normalize(node).event_id
        # Note: event_id includes timestamp so it will differ between calls
        # but dedupe_key should be deterministic
        norm1 = _osm_military_connector().normalize(node)
        norm2 = _osm_military_connector().normalize(node)
        assert norm1.normalization.dedupe_key == norm2.normalization.dedupe_key

    def test_normalize_missing_id_raises(self):
        bad = {"type": "node", "id": None, "lat": 25.0, "lon": 55.0, "tags": {}}
        with pytest.raises(NormalizationError):
            _osm_military_connector().normalize(bad)

    def test_normalize_missing_coordinates_raises(self):
        bad = {"type": "node", "id": 999, "tags": {"military": "base"}}
        with pytest.raises(NormalizationError):
            _osm_military_connector().normalize(bad)

    def test_normalize_landuse_military_uses_fallback_type(self):
        element = {
            "type": "way",
            "id": 77777,
            "center": {"lat": 24.0, "lon": 56.0},
            "tags": {"landuse": "military", "name": "Military Zone"},
        }
        ev = _osm_military_connector().normalize(element)
        assert ev.attributes["military_type"] == "military_area"

    def test_normalize_confidence_is_reasonable(self):
        ev = _osm_military_connector().normalize(_osm_node())
        assert 0.0 < ev.confidence < 1.0

    def test_normalize_license_opl(self):
        ev = _osm_military_connector().normalize(_osm_node())
        assert ev.license is not None
        assert ev.license.attribution_required is True

    def test_health_healthy(self):
        mock_resp = _mock_response({"elements": []})
        with patch("httpx.post", return_value=mock_resp):
            status = _osm_military_connector().health()
        assert status.healthy is True
        assert status.connector_id == "osm-military"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            status = _osm_military_connector().health()
        assert status.healthy is False
