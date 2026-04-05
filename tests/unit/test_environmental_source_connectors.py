"""Unit tests for environmental / signals-intelligence data source connectors:
  - NasaFirmsConnector  (src/connectors/nasa_firms.py)
  - NoaaSwpcConnector   (src/connectors/noaa_swpc.py)
  - OpenAqConnector     (src/connectors/openaq.py)

Tests cover:
- connect() raises ConnectorUnavailableError on HTTP error
- fetch() builds correct query URLs / params
- normalize() happy path for each connector
- normalize() raises NormalizationError for missing required fields
- normalize() event_id / dedupe_key determinism
- CanonicalEvent fields: source, source_type, entity_type, event_type
- Confidence scoring logic
- Geometry helpers (bbox extraction)
- SWPC alert parsing: phenomenon, NOAA scale, Kp-index, severity, serial
- FIRMS confidence scoring (VIIRS vs MODIS)
- OpenAQ two-step enrichment and location-only fallback
- health() returns healthy/unhealthy based on HTTP response
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.base import ConnectorUnavailableError, NormalizationError
from src.connectors.nasa_firms import (
    NasaFirmsConnector,
    _bbox_from_geojson as firms_bbox,
    _confidence_score,
)
from src.connectors.noaa_swpc import (
    NoaaSwpcConnector,
    _parse_phenomenon,
    _parse_scale_severity,
    _parse_kp,
    _parse_serial,
    _parse_issue_time,
)
from src.connectors.openaq import (
    OpenAqConnector,
    _bbox_from_geojson as aq_bbox,
)
from src.models.canonical_event import EntityType, EventType, SourceType


# ─────────────────────────────────────────────────────────────────────────────
# Shared geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

_T0 = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
_T1 = _T0 + timedelta(days=1)


def _polygon(lon: float = 50.0, lat: float = 25.0, delta: float = 1.0) -> Dict[str, Any]:
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


def _mock_response(data: Any, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=data)
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Geometry bbox helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestBboxHelpers:
    def test_firms_bbox_polygon(self):
        min_lat, min_lon, max_lat, max_lon = firms_bbox(_polygon(50.0, 25.0, 1.0))
        assert min_lat == pytest.approx(24.0, abs=0.01)
        assert max_lat == pytest.approx(26.0, abs=0.01)
        assert min_lon == pytest.approx(49.0, abs=0.01)
        assert max_lon == pytest.approx(51.0, abs=0.01)

    def test_firms_bbox_point(self):
        min_lat, min_lon, max_lat, max_lon = firms_bbox(_point(50.0, 25.0))
        assert min_lat == max_lat == pytest.approx(25.0, abs=0.01)
        assert min_lon == max_lon == pytest.approx(50.0, abs=0.01)

    def test_firms_bbox_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            firms_bbox({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})

    def test_openaq_bbox_polygon(self):
        min_lat, min_lon, max_lat, max_lon = aq_bbox(_polygon(55.0, 24.0, 0.5))
        assert min_lat == pytest.approx(23.5, abs=0.01)
        assert max_lat == pytest.approx(24.5, abs=0.01)

    def test_openaq_bbox_unsupported_raises(self):
        with pytest.raises(NormalizationError):
            aq_bbox({"type": "GeometryCollection", "geometries": []})


# ─────────────────────────────────────────────────────────────────────────────
# FIRMS confidence scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestFirmsConfidenceScoring:
    def test_viirs_high(self):
        assert _confidence_score("h", is_viirs=True) == pytest.approx(0.95)

    def test_viirs_nominal(self):
        assert _confidence_score("n", is_viirs=True) == pytest.approx(0.75)

    def test_viirs_low(self):
        assert _confidence_score("l", is_viirs=True) == pytest.approx(0.45)

    def test_viirs_case_insensitive(self):
        assert _confidence_score("HIGH", is_viirs=True) == pytest.approx(0.95)

    def test_viirs_unknown_default(self):
        score = _confidence_score("unknown", is_viirs=True)
        assert 0.0 < score <= 1.0

    def test_modis_integer_100(self):
        assert _confidence_score("100", is_viirs=False) == pytest.approx(1.0)

    def test_modis_integer_75(self):
        assert _confidence_score("75", is_viirs=False) == pytest.approx(0.75)

    def test_modis_integer_0(self):
        assert _confidence_score("0", is_viirs=False) == pytest.approx(0.0)

    def test_modis_invalid_default(self):
        score = _confidence_score("abc", is_viirs=False)
        assert 0.0 < score <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# NOAA SWPC message parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

_G3_MSG = (
    "Space Weather Message Code: GEOMAG\n"
    "Serial Number: 1042\n"
    "Issue Time: 2026 Apr 05 1200 UTC\n\n"
    "WARNING: Geomagnetic K-index of 7 expected\n"
    "Valid From: 2026 Apr 05 1200 UTC\n"
    "Valid To: 2026 Apr 05 2100 UTC\n"
    "Warning Condition: Onset\n"
    "NOAA Scale: G3 or Greater\n"
    "Kp index level reached 7\n"
)

_SOLAR_FLARE_MSG = (
    "Space Weather Message Code: ALTXM\n"
    "Serial Number: 2503\n"
    "Issue Time: 2026 Apr 05 0833 UTC\n\n"
    "ALERT: X1.5 solar flare\nNOAA Scale: R3\nKp index: 5"
)


class TestSwpcParsing:
    def test_parse_phenomenon_geomag(self):
        assert _parse_phenomenon("GEOMAG") == "Geomagnetic Storm"

    def test_parse_phenomenon_altef(self):
        assert "Electron" in _parse_phenomenon("ALTEF3")

    def test_parse_phenomenon_altxm(self):
        assert "Solar Flare" in _parse_phenomenon("ALTXM")

    def test_parse_phenomenon_unknown(self):
        result = _parse_phenomenon("XYZUNKNOWN")
        assert isinstance(result, str) and len(result) > 0

    def test_parse_scale_g3(self):
        scale, severity = _parse_scale_severity(_G3_MSG)
        assert scale == "G3"
        assert severity == "Strong"

    def test_parse_scale_r3(self):
        scale, severity = _parse_scale_severity(_SOLAR_FLARE_MSG)
        assert scale == "R3"
        assert severity == "Strong"

    def test_parse_scale_no_scale(self):
        scale, severity = _parse_scale_severity("No scale info here")
        assert scale is None
        assert severity is None

    def test_parse_kp_from_message(self):
        kp = _parse_kp(_G3_MSG)
        assert kp == pytest.approx(7.0)

    def test_parse_kp_from_solar_flare_msg(self):
        kp = _parse_kp(_SOLAR_FLARE_MSG)
        assert kp == pytest.approx(5.0)

    def test_parse_kp_none_when_absent(self):
        assert _parse_kp("No Kp data in this message") is None

    def test_parse_serial(self):
        assert _parse_serial(_G3_MSG) == "1042"

    def test_parse_serial_none_when_absent(self):
        assert _parse_serial("No serial number here") is None

    def test_parse_issue_time_dot_format(self):
        t = _parse_issue_time("2026-04-05 12:00:00.000")
        assert t.year == 2026
        assert t.tzinfo is not None

    def test_parse_issue_time_iso(self):
        t = _parse_issue_time("2026-04-05T12:00:00")
        assert t.month == 4


# ─────────────────────────────────────────────────────────────────────────────
# NasaFirmsConnector
# ─────────────────────────────────────────────────────────────────────────────

def _viirs_detection(
    lat: float = 24.68,
    lon: float = 56.23,
    acq_date: str = "2026-04-05",
    acq_time: str = "0820",
    confidence: str = "h",
    frp: str = "15.20",
    satellite: str = "N",
) -> Dict[str, Any]:
    return {
        "latitude": str(lat),
        "longitude": str(lon),
        "bright_ti4": "321.91",
        "scan": "0.40",
        "track": "0.36",
        "acq_date": acq_date,
        "acq_time": acq_time,
        "satellite": satellite,
        "confidence": confidence,
        "version": "2.0NRT",
        "bright_ti5": "290.14",
        "frp": frp,
        "daynight": "D",
    }


def _modis_detection(
    lat: float = 29.37,
    lon: float = 47.92,
    acq_date: str = "2026-04-05",
    confidence: str = "75",
) -> Dict[str, Any]:
    return {
        "latitude": str(lat),
        "longitude": str(lon),
        "brightness": "320.0",
        "scan": "1.1",
        "track": "1.2",
        "acq_date": acq_date,
        "acq_time": "0745",
        "satellite": "A",
        "confidence": confidence,
        "version": "6.1NRT",
        "bright_t31": "288.0",
        "frp": "22.5",
        "daynight": "D",
    }


def _firms_connector(source: str = "VIIRS_SNPP_NRT") -> NasaFirmsConnector:
    return NasaFirmsConnector(
        map_key="TESTKEY",
        api_url="https://firms.modaps.eosdis.nasa.gov/api",
        source=source,
        days_lookback=2,
    )


class TestNasaFirmsConnector:
    def test_connect_ok(self):
        with patch("httpx.get", return_value=_mock_response([])):
            _firms_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _firms_connector().connect()

    def test_fetch_uses_correct_url_structure(self):
        with patch("httpx.get", return_value=_mock_response([])) as mock_get:
            _firms_connector().fetch(_polygon(50.0, 25.0), _T0, _T1)
            url = mock_get.call_args[0][0]
            assert "TESTKEY" in url
            assert "VIIRS_SNPP_NRT" in url
            assert "json" in url

    def test_fetch_embeds_bbox_in_url(self):
        with patch("httpx.get", return_value=_mock_response([])) as mock_get:
            _firms_connector().fetch(_polygon(50.0, 25.0, 1.0), _T0, _T1)
            url = mock_get.call_args[0][0]
            # bbox coordinates should appear in URL
            assert "49.0" in url or "49." in url
            assert "24.0" in url or "24." in url

    def test_fetch_returns_list(self):
        detections = [_viirs_detection(), _viirs_detection(lat=24.9)]
        with patch("httpx.get", return_value=_mock_response(detections)):
            result = _firms_connector().fetch(_polygon(), _T0, _T1)
        assert len(result) == 2

    def test_fetch_handles_bad_geometry_gracefully(self):
        bad_geom = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
        result = _firms_connector().fetch(bad_geom, _T0, _T1)
        assert result == []

    def test_fetch_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())):
            with pytest.raises(ConnectorUnavailableError):
                _firms_connector().fetch(_polygon(), _T0, _T1)

    def test_normalize_viirs_happy_path(self):
        ev = _firms_connector().normalize(_viirs_detection())
        assert ev.event_type == EventType.THERMAL_ANOMALY_EVENT
        assert ev.entity_type == EntityType.THERMAL_ANOMALY
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "nasa-firms"
        assert ev.geometry["type"] == "Point"

    def test_normalize_viirs_high_confidence(self):
        ev = _firms_connector().normalize(_viirs_detection(confidence="h"))
        assert ev.confidence == pytest.approx(0.95)

    def test_normalize_viirs_low_confidence(self):
        ev = _firms_connector().normalize(_viirs_detection(confidence="l"))
        assert ev.confidence == pytest.approx(0.45)

    def test_normalize_modis_confidence_integer(self):
        conn = _firms_connector("MODIS_NRT")
        ev = conn.normalize(_modis_detection(confidence="75"))
        assert ev.confidence == pytest.approx(0.75)

    def test_normalize_attributes_populated(self):
        ev = _firms_connector().normalize(_viirs_detection())
        attrs = ev.attributes
        assert attrs["instrument"] == "VIIRS"
        assert attrs["acq_date"] == "2026-04-05"
        assert attrs["source_dataset"] == "VIIRS_SNPP_NRT"
        assert attrs["day_night"] == "D"

    def test_normalize_frp_parsed(self):
        ev = _firms_connector().normalize(_viirs_detection(frp="15.20"))
        assert ev.attributes["frp"] == pytest.approx(15.20)

    def test_normalize_event_id_determinism(self):
        rec = _viirs_detection()
        id1 = _firms_connector().normalize(rec).normalization.dedupe_key
        id2 = _firms_connector().normalize(rec).normalization.dedupe_key
        assert id1 == id2

    def test_normalize_missing_date_raises(self):
        bad = _viirs_detection()
        bad["acq_date"] = ""
        with pytest.raises(NormalizationError):
            _firms_connector().normalize(bad)

    def test_normalize_missing_coordinates_raises(self):
        bad = _viirs_detection()
        del bad["latitude"]
        with pytest.raises(NormalizationError):
            _firms_connector().normalize(bad)

    def test_normalize_license_public_domain(self):
        ev = _firms_connector().normalize(_viirs_detection())
        assert ev.license is not None
        assert ev.license.commercial_use == "allowed"
        assert ev.license.attribution_required is True

    def test_health_healthy(self):
        with patch("httpx.get", return_value=_mock_response([])):
            status = _firms_connector().health()
        assert status.healthy is True
        assert status.connector_id == "nasa-firms"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = _firms_connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# NoaaSwpcConnector
# ─────────────────────────────────────────────────────────────────────────────

def _swpc_alert(
    product_id: str = "GEOMAG",
    issue_datetime: str = "2026-04-05 12:00:00.000",
    message: str = _G3_MSG,
) -> Dict[str, Any]:
    return {
        "product_id": product_id,
        "issue_datetime": issue_datetime,
        "message": message,
    }


def _swpc_connector() -> NoaaSwpcConnector:
    return NoaaSwpcConnector(api_url="https://services.swpc.noaa.gov")


class TestNoaaSwpcConnector:
    def test_connect_ok(self):
        with patch("httpx.get", return_value=_mock_response([_swpc_alert()])):
            _swpc_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _swpc_connector().connect()

    def test_fetch_returns_alerts(self):
        alerts = [_swpc_alert(), _swpc_alert(product_id="ALTEF3", message=_SOLAR_FLARE_MSG)]
        with patch("httpx.get", return_value=_mock_response(alerts)):
            result = _swpc_connector().fetch(_polygon(), _T0, _T1)
        assert len(result) == 2

    def test_fetch_ignores_geometry_and_time(self):
        # SWPC returns same feed regardless of geometry — should work with any geometry
        with patch("httpx.get", return_value=_mock_response([])):
            result = _swpc_connector().fetch(_point(), _T0, _T1)
        assert result == []

    def test_fetch_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock())):
            with pytest.raises(ConnectorUnavailableError):
                _swpc_connector().fetch(_polygon(), _T0, _T1)

    def test_normalize_happy_path(self):
        ev = _swpc_connector().normalize(_swpc_alert())
        assert ev.event_type == EventType.SPACE_WEATHER_EVENT
        assert ev.entity_type == EntityType.SPACE_WEATHER_PHENOMENON
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "noaa-swpc"

    def test_normalize_global_geometry(self):
        ev = _swpc_connector().normalize(_swpc_alert())
        assert ev.geometry["coordinates"] == [0.0, 0.0]
        assert "global-phenomenon" in ev.quality_flags

    def test_normalize_geomagnetic_storm_attributes(self):
        ev = _swpc_connector().normalize(_swpc_alert(message=_G3_MSG))
        attrs = ev.attributes
        assert attrs["noaa_scale"] == "G3"
        assert attrs["severity"] == "Strong"
        assert attrs["kp_index"] == pytest.approx(7.0)
        assert attrs["serial_number"] == "1042"
        assert attrs["phenomenon"] == "Geomagnetic Storm"

    def test_normalize_solar_flare_attributes(self):
        ev = _swpc_connector().normalize(
            _swpc_alert(product_id="ALTXM", message=_SOLAR_FLARE_MSG)
        )
        attrs = ev.attributes
        assert attrs["noaa_scale"] == "R3"
        assert attrs["kp_index"] == pytest.approx(5.0)
        assert "Solar Flare" in attrs["phenomenon"]

    def test_normalize_confidence_alert_vs_watch(self):
        alert_ev = _swpc_connector().normalize(_swpc_alert(product_id="ALTEF3"))
        watch_ev = _swpc_connector().normalize(_swpc_alert(product_id="WATA"))
        assert alert_ev.confidence > watch_ev.confidence

    def test_normalize_event_id_determinism(self):
        rec = _swpc_alert()
        k1 = _swpc_connector().normalize(rec).normalization.dedupe_key
        k2 = _swpc_connector().normalize(rec).normalization.dedupe_key
        assert k1 == k2

    def test_normalize_missing_product_id_raises(self):
        bad = {"product_id": "", "issue_datetime": "2026-04-05 12:00:00.000", "message": "X"}
        with pytest.raises(NormalizationError):
            _swpc_connector().normalize(bad)

    def test_normalize_missing_issue_datetime_raises(self):
        bad = {"product_id": "GEOMAG", "issue_datetime": "", "message": "X"}
        with pytest.raises(NormalizationError):
            _swpc_connector().normalize(bad)

    def test_normalize_message_truncated_to_2000_chars(self):
        long_msg = "X" * 5000
        ev = _swpc_connector().normalize(_swpc_alert(message=long_msg))
        assert len(ev.attributes["message"]) <= 2000

    def test_normalize_license(self):
        ev = _swpc_connector().normalize(_swpc_alert())
        assert ev.license.commercial_use == "allowed"

    def test_health_healthy(self):
        with patch("httpx.get", return_value=_mock_response([_swpc_alert()])):
            status = _swpc_connector().health()
        assert status.healthy is True
        assert status.connector_id == "noaa-swpc"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = _swpc_connector().health()
        assert status.healthy is False


# ─────────────────────────────────────────────────────────────────────────────
# OpenAqConnector
# ─────────────────────────────────────────────────────────────────────────────

def _openaq_location(
    loc_id: int = 2178,
    name: str = "Dubai - Al Qusais",
    lat: float = 25.28,
    lon: float = 55.38,
    country_code: str = "AE",
    locality: str = "Dubai",
) -> Dict[str, Any]:
    return {
        "id": loc_id,
        "name": name,
        "locality": locality,
        "country": {"id": country_code, "code": country_code, "name": "UAE"},
        "provider": {"id": 1, "name": "NCMS"},
        "isMobile": False,
        "isMonitor": True,
        "coordinates": {"latitude": lat, "longitude": lon},
        "datetimeLast": {"utc": "2026-04-05T09:00:00Z"},
    }


def _openaq_measurement(
    location_id: int = 2178,
    parameter: str = "pm25",
    value: float = 35.2,
    unit: str = "µg/m³",
    ts: str = "2026-04-05T09:00:00Z",
) -> Dict[str, Any]:
    return {
        "location_id": location_id,
        "location": {"id": location_id, "name": "Dubai - Al Qusais",
                     "coordinates": {"latitude": 25.28, "longitude": 55.38}},
        "parameter": {"id": 2, "name": parameter, "units": unit, "displayName": "PM₂.₅"},
        "value": value,
        "period": {"datetimeFrom": {"utc": ts}, "datetimeTo": {"utc": ts}},
        "sensor_id": 890,
    }


def _openaq_connector() -> OpenAqConnector:
    return OpenAqConnector(api_url="https://api.openaq.org/v3")


class TestOpenAqConnector:
    def test_connect_ok(self):
        resp = _mock_response({"meta": {}, "results": [_openaq_location()]})
        with patch("httpx.get", return_value=resp):
            _openaq_connector().connect()

    def test_connect_raises_on_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _openaq_connector().connect()

    def test_fetch_two_step_returns_enriched_list(self):
        locations_resp = _mock_response({"results": [_openaq_location()]})
        measurements_resp = _mock_response({"results": [_openaq_measurement()]})
        with patch("httpx.get", side_effect=[locations_resp, measurements_resp]):
            result = _openaq_connector().fetch(_polygon(55.0, 25.0), _T0, _T1)
        assert len(result) == 1
        assert "_measurement" in result[0]
        assert "_location" in result[0]

    def test_fetch_degrades_on_measurement_error(self):
        import httpx
        locations_resp = _mock_response({"results": [_openaq_location()]})
        with patch("httpx.get", side_effect=[
            locations_resp,
            httpx.HTTPStatusError("429", request=MagicMock(), response=MagicMock()),
        ]):
            result = _openaq_connector().fetch(_polygon(55.0, 25.0), _T0, _T1)
        # Graceful degradation: location-only records are returned
        assert len(result) == 1
        assert result[0]["_measurement"] is None

    def test_fetch_returns_empty_when_no_locations(self):
        with patch("httpx.get", return_value=_mock_response({"results": []})):
            result = _openaq_connector().fetch(_polygon(), _T0, _T1)
        assert result == []

    def test_fetch_raises_on_locations_http_error(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ConnectorUnavailableError):
                _openaq_connector().fetch(_polygon(), _T0, _T1)

    def test_normalize_happy_path_with_measurement(self):
        raw = {"_location": _openaq_location(), "_measurement": _openaq_measurement()}
        ev = _openaq_connector().normalize(raw)
        assert ev.event_type == EventType.AIR_QUALITY_OBSERVATION
        assert ev.entity_type == EntityType.AIR_QUALITY_SENSOR
        assert ev.source_type == SourceType.PUBLIC_RECORD
        assert ev.source == "openaq"

    def test_normalize_coordinates_from_location(self):
        raw = {"_location": _openaq_location(lat=25.28, lon=55.38), "_measurement": _openaq_measurement()}
        ev = _openaq_connector().normalize(raw)
        lon, lat = ev.geometry["coordinates"]
        assert lon == pytest.approx(55.38, abs=0.01)
        assert lat == pytest.approx(25.28, abs=0.01)

    def test_normalize_attributes_populated(self):
        raw = {"_location": _openaq_location(), "_measurement": _openaq_measurement()}
        ev = _openaq_connector().normalize(raw)
        attrs = ev.attributes
        assert attrs["location_id"] == 2178
        assert attrs["parameter"] == "pm25"
        assert attrs["value"] == pytest.approx(35.2)
        assert attrs["country_code"] == "AE"
        assert attrs["locality"] == "Dubai"

    def test_normalize_confidence_higher_with_value(self):
        with_value = {"_location": _openaq_location(), "_measurement": _openaq_measurement()}
        without_value = {"_location": _openaq_location(), "_measurement": None}
        ev_w = _openaq_connector().normalize(with_value)
        ev_wo = _openaq_connector().normalize(without_value)
        assert ev_w.confidence > ev_wo.confidence

    def test_normalize_dedupe_key_determinism(self):
        raw = {"_location": _openaq_location(), "_measurement": _openaq_measurement()}
        k1 = _openaq_connector().normalize(raw).normalization.dedupe_key
        k2 = _openaq_connector().normalize(raw).normalization.dedupe_key
        assert k1 == k2

    def test_normalize_missing_coordinates_raises(self):
        bad_loc = {"id": 1, "name": "x", "isMobile": False, "isMonitor": False}
        bad_meas = {"location_id": 1}
        with pytest.raises(NormalizationError):
            _openaq_connector().normalize({"_location": bad_loc, "_measurement": bad_meas})

    def test_normalize_location_only_fallback(self):
        raw = {"_location": _openaq_location(), "_measurement": None}
        ev = _openaq_connector().normalize(raw)
        assert ev.event_type == EventType.AIR_QUALITY_OBSERVATION
        assert ev.attributes["value"] is None

    def test_normalize_license_cc_by(self):
        raw = {"_location": _openaq_location(), "_measurement": _openaq_measurement()}
        ev = _openaq_connector().normalize(raw)
        assert ev.license.commercial_use == "allowed"
        assert ev.license.attribution_required is True

    def test_normalize_api_key_sent_in_header(self):
        conn = OpenAqConnector(api_url="https://api.openaq.org/v3", api_key="mykey")
        headers = conn._headers()
        assert headers.get("X-API-Key") == "mykey"

    def test_normalize_no_api_key_no_header(self):
        conn = OpenAqConnector(api_url="https://api.openaq.org/v3", api_key="")
        headers = conn._headers()
        assert "X-API-Key" not in headers

    def test_health_healthy(self):
        resp = _mock_response({"results": [_openaq_location()]})
        with patch("httpx.get", return_value=resp):
            status = _openaq_connector().health()
        assert status.healthy is True
        assert status.connector_id == "openaq"

    def test_health_unhealthy_on_exception(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            status = _openaq_connector().health()
        assert status.healthy is False
