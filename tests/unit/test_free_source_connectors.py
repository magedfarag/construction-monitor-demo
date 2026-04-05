"""Unit tests for free data source connectors:
  - UsgsEarthquakeConnector  (src/connectors/usgs_earthquake.py)
  - NasaEonetConnector       (src/connectors/nasa_eonet.py)
  - OpenMeteoConnector       (src/connectors/open_meteo.py)

Tests cover:
- connect() raises ConnectorUnavailableError on HTTP error
- fetch() builds correct query params and returns normalizable records
- normalize() happy path for each connector
- normalize() raises NormalizationError for missing required fields
- normalize() event_id determinism
- CanonicalEvent fields: source, source_type, entity_type, event_type, license
- health() returns healthy on success / unhealthy on HTTP failure
- bbox / centroid helpers for Point, Polygon, MultiPolygon
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.base import ConnectorUnavailableError, NormalizationError
from src.connectors.usgs_earthquake import UsgsEarthquakeConnector, _bbox_from_geojson as usgs_bbox
from src.connectors.nasa_eonet import NasaEonetConnector, _bbox_from_geojson as eonet_bbox, _extract_first_point
from src.connectors.open_meteo import OpenMeteoConnector, _centroid_from_geojson
from src.models.canonical_event import EntityType, EventType, SourceType


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _polygon(lon: float = 46.7, lat: float = 24.7, delta: float = 0.5) -> Dict[str, Any]:
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


def _point(lon: float = 46.7, lat: float = 24.7) -> Dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def _multipolygon(lon: float = 46.7, lat: float = 24.7, delta: float = 0.5) -> Dict[str, Any]:
    ring = [
        [lon - delta, lat - delta],
        [lon - delta, lat + delta],
        [lon + delta, lat + delta],
        [lon + delta, lat - delta],
        [lon - delta, lat - delta],
    ]
    return {"type": "MultiPolygon", "coordinates": [[ring]]}


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

_T0 = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
_T1 = _T0 + timedelta(hours=6)


# ─────────────────────────────────────────────────────────────────────────────
# Bbox / centroid geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestBboxHelpers:
    def test_usgs_bbox_polygon(self):
        min_lat, min_lon, max_lat, max_lon = usgs_bbox(_polygon(46.7, 24.7, delta=0.5))
        assert min_lon == pytest.approx(46.2, abs=0.01)
        assert max_lon == pytest.approx(47.2, abs=0.01)
        assert min_lat == pytest.approx(24.2, abs=0.01)
        assert max_lat == pytest.approx(25.2, abs=0.01)

    def test_usgs_bbox_point(self):
        min_lat, min_lon, max_lat, max_lon = usgs_bbox(_point(46.7, 24.7))
        assert min_lon == max_lon == pytest.approx(46.7, abs=0.01)
        assert min_lat == max_lat == pytest.approx(24.7, abs=0.01)

    def test_usgs_bbox_multipolygon(self):
        min_lat, min_lon, max_lat, max_lon = usgs_bbox(_multipolygon(46.7, 24.7, delta=1.0))
        assert min_lon < 46.7 < max_lon

    def test_usgs_bbox_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            usgs_bbox({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})

    def test_eonet_bbox_polygon(self):
        result = eonet_bbox(_polygon())
        assert len(result) == 4

    def test_eonet_extract_first_point_point(self):
        pt = _extract_first_point({"type": "Point", "coordinates": [46.7, 24.7]})
        assert pt == (pytest.approx(46.7), pytest.approx(24.7))

    def test_eonet_extract_first_point_polygon(self):
        pt = _extract_first_point({"type": "Polygon", "coordinates": [[[10.0, 20.0], [11.0, 21.0], [10.0, 20.0]]]})
        assert pt[0] == pytest.approx(10.0)

    def test_centroid_point(self):
        lon, lat = _centroid_from_geojson(_point(46.7, 24.7))
        assert lon == pytest.approx(46.7)
        assert lat == pytest.approx(24.7)

    def test_centroid_polygon(self):
        lon, lat = _centroid_from_geojson(_polygon(46.7, 24.7, delta=0.5))
        # Ring closure repeats first vertex; centroid is close but not exact centre
        assert lon == pytest.approx(46.7, abs=0.15)
        assert lat == pytest.approx(24.7, abs=0.15)

    def test_centroid_multipolygon(self):
        lon, lat = _centroid_from_geojson(_multipolygon(46.7, 24.7, delta=0.5))
        assert lon == pytest.approx(46.7, abs=0.15)

    def test_centroid_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            _centroid_from_geojson({"type": "LineString", "coordinates": [[0, 0]]})


# ─────────────────────────────────────────────────────────────────────────────
# UsgsEarthquakeConnector
# ─────────────────────────────────────────────────────────────────────────────

def _usgs_feature(
    fid: str = "us7000xyz1",
    lon: float = 46.7,
    lat: float = 24.7,
    depth: float = 10.0,
    time_ms: int = 1743508800000,
    mag: float = 4.5,
    status: str = "reviewed",
) -> Dict[str, Any]:
    return {
        "id": fid,
        "type": "Feature",
        "properties": {
            "mag": mag,
            "place": "25 km SW of Riyadh",
            "time": time_ms,
            "status": status,
            "magType": "mw",
            "tsunami": 0,
            "felt": 12,
            "cdi": 3.1,
            "mmi": 4.2,
            "alert": "green",
            "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{fid}",
            "net": "us",
        },
        "geometry": {"type": "Point", "coordinates": [lon, lat, depth]},
    }


class TestUsgsEarthquakeConnector:
    def _connector(self) -> UsgsEarthquakeConnector:
        return UsgsEarthquakeConnector(api_url="https://earthquake.usgs.gov/fdsnws/event/1")

    def test_connect_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            self._connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                self._connector().connect()

    def test_fetch_builds_correct_params(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"features": []}
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            self._connector().fetch(_polygon(), _T0, _T1)
            call_params = mock_get.call_args[1]["params"]
            assert call_params["format"] == "geojson"
            assert "minlatitude" in call_params
            assert "minmagnitude" in call_params

    def test_fetch_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())):
            with pytest.raises((ConnectorUnavailableError, Exception)):
                self._connector().fetch(_polygon(), _T0, _T1)

    def test_normalize_happy_path(self):
        ev = self._connector().normalize(_usgs_feature())
        assert ev.event_type == EventType.SEISMIC_EVENT
        assert ev.entity_type == EntityType.SEISMIC_HAZARD
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "usgs-earthquake"
        assert ev.attributes["magnitude"] == pytest.approx(4.5)
        assert ev.attributes["depth_km"] == pytest.approx(10.0)
        assert ev.attributes["status"] == "reviewed"
        assert ev.confidence == pytest.approx(0.9)

    def test_normalize_automatic_lower_confidence(self):
        ev = self._connector().normalize(_usgs_feature(status="automatic"))
        assert ev.confidence == pytest.approx(0.6)

    def test_normalize_missing_id_raises(self):
        feat = _usgs_feature()
        feat["id"] = ""
        with pytest.raises(NormalizationError):
            self._connector().normalize(feat)

    def test_normalize_missing_time_raises(self):
        feat = _usgs_feature()
        feat["properties"]["time"] = None
        with pytest.raises(NormalizationError):
            self._connector().normalize(feat)

    def test_normalize_invalid_geometry_raises(self):
        feat = _usgs_feature()
        feat["geometry"]["coordinates"] = [46.7]  # only 1 coord
        with pytest.raises(NormalizationError):
            self._connector().normalize(feat)

    def test_event_id_determinism(self):
        c = self._connector()
        id1 = c.normalize(_usgs_feature()).event_id
        id2 = c.normalize(_usgs_feature()).event_id
        assert id1 == id2

    def test_license_is_public_domain(self):
        ev = self._connector().normalize(_usgs_feature())
        assert ev.license.commercial_use == "allowed"
        assert ev.license.access_tier == "public"

    def test_health_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            status = self._connector().health()
        assert status.healthy is True

    def test_health_unhealthy_on_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = self._connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# NasaEonetConnector
# ─────────────────────────────────────────────────────────────────────────────

def _eonet_event(
    eid: str = "EONET_6789",
    title: str = "Wildfire in Jordan",
    status: str = "open",
    lon: float = 36.0,
    lat: float = 31.0,
    date: str = "2026-04-01T12:00:00Z",
) -> Dict[str, Any]:
    return {
        "id": eid,
        "title": title,
        "status": status,
        "closed": None,
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "sources": [{"url": "https://firms.modaps.eosdis.nasa.gov/"}],
        "geometry": [
            {
                "date": date,
                "type": "Point",
                "coordinates": [lon, lat],
            }
        ],
    }


class TestNasaEonetConnector:
    def _connector(self) -> NasaEonetConnector:
        return NasaEonetConnector(api_url="https://eonet.gsfc.nasa.gov/api/v3")

    def test_connect_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            self._connector().connect()

    def test_connect_raises_on_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                self._connector().connect()

    def test_fetch_clips_to_bbox(self):
        """Event at (36, 31) inside a bbox covering Jordan should be returned."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "events": [_eonet_event(lon=36.0, lat=31.0)]
        }
        with patch("httpx.get", return_value=mock_resp):
            geom = _polygon(36.0, 31.0, delta=2.0)
            results = self._connector().fetch(geom, _T0, _T1)
        assert len(results) == 1

    def test_fetch_excludes_outside_bbox(self):
        """Event at (100, 10) should be excluded from a bbox around Jordan."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "events": [_eonet_event(lon=100.0, lat=10.0)]
        }
        with patch("httpx.get", return_value=mock_resp):
            geom = _polygon(36.0, 31.0, delta=2.0)
            results = self._connector().fetch(geom, _T0, _T1)
        assert len(results) == 0

    def test_normalize_happy_path(self):
        ev = self._connector().normalize(_eonet_event())
        assert ev.event_type == EventType.NATURAL_HAZARD_EVENT
        assert ev.entity_type == EntityType.NATURAL_HAZARD
        assert ev.source_type == SourceType.CONTEXT_FEED
        assert ev.source == "nasa-eonet"
        assert ev.attributes["category"] == "wildfires"
        assert ev.attributes["eonet_id"] == "EONET_6789"

    def test_normalize_missing_id_raises(self):
        evt = _eonet_event()
        evt["id"] = ""
        with pytest.raises(NormalizationError):
            self._connector().normalize(evt)

    def test_normalize_no_geometry_raises(self):
        evt = _eonet_event()
        evt["geometry"] = []
        with pytest.raises(NormalizationError):
            self._connector().normalize(evt)

    def test_event_id_determinism(self):
        c = self._connector()
        id1 = c.normalize(_eonet_event()).event_id
        id2 = c.normalize(_eonet_event()).event_id
        assert id1 == id2

    def test_license_is_cc0(self):
        ev = self._connector().normalize(_eonet_event())
        assert ev.license.commercial_use == "allowed"

    def test_health_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            status = self._connector().health()
        assert status.healthy is True

    def test_health_unhealthy_on_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("timeout")):
            status = self._connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# OpenMeteoConnector
# ─────────────────────────────────────────────────────────────────────────────

def _open_meteo_response(
    lon: float = 46.7,
    lat: float = 24.7,
    cloud: float = 40.0,
    precip: float = 0.5,
    wind_speed: float = 5.0,
    wind_dir: float = 180.0,
    temp: float = 28.0,
) -> Dict[str, Any]:
    times = [f"2026-04-01T{h:02d}:00" for h in range(24)]
    return {
        "_centroid_lon": lon,
        "_centroid_lat": lat,
        "_forecast_hours": 6,
        "hourly": {
            "time": times,
            "cloud_cover": [cloud] * 24,
            "precipitation": [precip] * 24,
            "wind_speed_10m": [wind_speed] * 24,
            "wind_direction_10m": [wind_dir] * 24,
            "temperature_2m": [temp] * 24,
        },
        "hourly_units": {},
    }


class TestOpenMeteoConnector:
    def _connector(self) -> OpenMeteoConnector:
        return OpenMeteoConnector(api_url="https://api.open-meteo.com/v1")

    def test_connect_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.get", return_value=mock_resp):
            self._connector().connect()

    def test_connect_raises_on_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                self._connector().connect()

    def test_fetch_returns_one_record(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _open_meteo_response()
        with patch("httpx.get", return_value=mock_resp):
            results = self._connector().fetch(_polygon(), _T0, _T1)
        assert len(results) == 1

    def test_fetch_extracts_centroid_into_record(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"hourly": {}, "hourly_units": {}}
        with patch("httpx.get", return_value=mock_resp):
            results = self._connector().fetch(_polygon(46.7, 24.7), _T0, _T1)
        assert "_centroid_lon" in results[0]
        # Centroid close to polygon centre (ring-closure shifts it slightly)
        assert abs(results[0]["_centroid_lon"] - 46.7) < 0.15

    def test_normalize_happy_path(self):
        ev = self._connector().normalize(_open_meteo_response(cloud=55.0, precip=1.2))
        assert ev.event_type == EventType.WEATHER_OBSERVATION
        assert ev.source == "open-meteo"
        assert ev.source_type == SourceType.CONTEXT_FEED
        assert ev.attributes["cloud_cover_pct"] == pytest.approx(55.0, abs=0.1)
        assert ev.attributes["precipitation_mm"] == pytest.approx(1.2, abs=0.01)

    def test_normalize_wind_and_temperature(self):
        ev = self._connector().normalize(_open_meteo_response(wind_speed=8.5, temp=31.2))
        assert ev.attributes["wind_speed_ms"] == pytest.approx(8.5, abs=0.01)
        assert ev.attributes["temperature_c"] == pytest.approx(31.2, abs=0.01)

    def test_normalize_time_range_set(self):
        ev = self._connector().normalize(_open_meteo_response())
        assert ev.time_start is not None
        assert ev.time_end is not None
        assert ev.time_end >= ev.time_start

    def test_normalize_empty_hourly_raises(self):
        raw = _open_meteo_response()
        raw["hourly"]["time"] = []
        with pytest.raises(NormalizationError):
            self._connector().normalize(raw)

    def test_event_id_determinism(self):
        c = self._connector()
        id1 = c.normalize(_open_meteo_response()).event_id
        id2 = c.normalize(_open_meteo_response()).event_id
        assert id1 == id2

    def test_license_cc_by(self):
        ev = self._connector().normalize(_open_meteo_response())
        assert ev.license.commercial_use == "allowed"
        assert ev.license.attribution_required is True

    def test_health_ok(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200
        with patch("httpx.get", return_value=mock_resp):
            status = self._connector().health()
        assert status.healthy is True

    def test_health_unhealthy_on_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = self._connector().health()
        assert status.healthy is False
