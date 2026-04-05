"""Celery tasks for async analysis execution."""
from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

log = logging.getLogger(__name__)

try:
    from app.workers.celery_app import celery_app
    if celery_app is None:
        raise ImportError("celery_app is None")

    @celery_app.task(bind=True, name="run_analysis_task")
    def run_analysis_task(self, request_json: dict[str, Any]) -> dict[str, Any]:
        """Execute a full analysis and return the serialised AnalyzeResponse."""
        from app.cache.client import CacheClient
        from app.config import get_settings
        from app.models.requests import AnalyzeRequest
        from app.providers.demo import DemoProvider
        from app.providers.registry import ProviderRegistry
        from app.services.analysis import AnalysisService

        settings = get_settings()
        cache    = CacheClient.from_settings(settings)

        # Build minimal registry for worker process
        registry = ProviderRegistry()
        registry.register(DemoProvider())

        # Register live providers if configured
        if settings.sentinel2_is_configured():
            try:
                from app.providers.sentinel2 import Sentinel2Provider
                registry.register(Sentinel2Provider(settings))
            except Exception as exc:
                log.warning("Sentinel2Provider unavailable in worker: %s", exc)

        if settings.landsat_is_configured():
            try:
                from app.providers.landsat import LandsatProvider
                registry.register(LandsatProvider(settings))
            except Exception as exc:
                log.warning("LandsatProvider unavailable in worker: %s", exc)

        svc     = AnalysisService(registry=registry, cache=cache, settings=settings)
        request = AnalyzeRequest(**request_json)
        result  = svc.run_sync(request)
        return result.model_dump(mode="json")

    @celery_app.task(name="poll_gdelt_context")
    def poll_gdelt_context() -> dict[str, Any]:
        """P2-1.4: 15-minute GDELT polling task.

        Fetches the latest GDELT contextual events for all active AOIs and
        normalizes them into CanonicalEvents.  Uses the in-memory AOI store
        until PostGIS persistence is wired (P0-4).

        Returns a summary dict: {polled_at, aoi_count, article_count, errors}.
        """
        from datetime import datetime, timedelta

        from src.connectors.gdelt import DEFAULT_CONSTRUCTION_THEMES, GdeltConnector
        from src.services.aoi_store import AoiStore
        from src.services.source_health import get_health_service

        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        aoi_store = AoiStore()
        connector = GdeltConnector(default_themes=DEFAULT_CONSTRUCTION_THEMES)

        aois = aoi_store.list_aois()
        article_count = 0
        errors: list = []

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=30)  # overlap window

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw_articles = connector.fetch(
                    geometry, start_time, end_time, max_results=50
                )
                events = connector.normalize_all(raw_articles)
                # Phase 1 Track B: persist normalised events to EventStore
                from src.services.event_store import get_default_event_store
                get_default_event_store().ingest_batch(events)
                article_count += len(events)
                health_svc.record_success(
                    connector.connector_id,
                    connector.display_name,
                    connector.source_type,
                )
                log.info(
                    "poll_gdelt_context: AOI %s → %d events",
                    aoi.get("id", "unknown"),
                    len(events),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_gdelt_context: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {
            "polled_at": polled_at,
            "aoi_count": len(aois),
            "article_count": article_count,
            "errors": errors,
        }

    @celery_app.task(name="poll_opensky_positions")
    def poll_opensky_positions() -> dict[str, Any]:
        """P3-2.5: 60-second OpenSky aviation polling task.

        Fetches state vectors for all active AOIs and normalises them
        into aircraft_position CanonicalEvents.
        Returns a summary dict: {polled_at, aoi_count, aircraft_count, errors}.
        """
        import os
        from datetime import datetime, timedelta

        from src.connectors.opensky import OpenSkyConnector
        from src.services.aoi_store import AoiStore
        from src.services.source_health import get_health_service

        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = OpenSkyConnector(
            username=os.getenv("OPENSKY_USERNAME", ""),
            password=os.getenv("OPENSKY_PASSWORD", ""),
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=2)
        aircraft_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw_states = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw_states)
                # Phase 1 Track B: persist aircraft positions to EventStore and TelemetryStore
                from src.services.event_store import get_default_event_store
                from src.services.telemetry_store import get_default_telemetry_store
                get_default_event_store().ingest_batch(events)
                get_default_telemetry_store().ingest_batch(events)
                aircraft_count += len(events)
                health_svc.record_success(
                    connector.connector_id,
                    connector.display_name,
                    connector.source_type,
                )
                log.info(
                    "poll_opensky_positions: AOI %s → %d aircraft",
                    aoi.get("id", "unknown"),
                    len(events),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_opensky_positions: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {
            "polled_at": polled_at,
            "aoi_count": len(aois),
            "aircraft_count": aircraft_count,
            "errors": errors,
        }

    @celery_app.task(name="poll_aisstream_positions")
    def poll_aisstream_positions() -> dict[str, Any]:
        """P5-2.1: 30-second AIS maritime polling task.

        Fetches ship positions for all active AOIs via AISStream.io WebSocket.
        The connector is bounded by collect_timeout_s to avoid blocking.
        Returns a summary dict: {polled_at, aoi_count, ship_count, errors}.
        """
        import os
        from datetime import datetime

        from src.connectors.ais_stream import AisStreamConnector
        from src.services.aoi_store import AoiStore
        from src.services.source_health import get_health_service

        api_key = os.getenv("AISSTREAM_API_KEY", "")
        if not api_key:
            return {"polled_at": datetime.now(UTC).isoformat(), "skipped": True}

        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = AisStreamConnector(api_key=api_key, collect_timeout_s=25)
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        ship_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                import asyncio
                raw_msgs = asyncio.run(connector.fetch_async(geometry, max_messages=100))
                events = connector.normalize_all(raw_msgs)
                # Phase 1 Track B: persist ship positions to EventStore and TelemetryStore
                from src.services.event_store import get_default_event_store
                from src.services.telemetry_store import get_default_telemetry_store
                get_default_event_store().ingest_batch(events)
                get_default_telemetry_store().ingest_batch(events)
                ship_count += len(events)
                health_svc.record_success(
                    connector.connector_id,
                    connector.display_name,
                    connector.source_type,
                )
                log.info(
                    "poll_aisstream_positions: AOI %s → %d ship events",
                    aoi.get("id", "unknown"),
                    len(events),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_aisstream_positions: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {
            "polled_at": polled_at,
            "aoi_count": len(aois),
            "ship_count": ship_count,
            "errors": errors,
        }

    @celery_app.task(name="poll_rapidapi_ais")
    def poll_rapidapi_ais() -> dict[str, Any]:
        """Poll vessel positions via a configurable RapidAPI AIS endpoint.

        Uses the bbox defined by RAPID_API_SOUTH/WEST/NORTH/EAST when no AOIs
        are stored, otherwise queries per-AOI.  Writes results into the
        in-memory TelemetryStore.
        Returns: {polled_at, aoi_count, ship_count, errors}.
        """
        from datetime import datetime

        from app.config import get_settings
        from src.connectors.rapidapi_ais import RapidApiAisConnector
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service
        from src.services.telemetry_store import get_default_telemetry_store

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        connector = RapidApiAisConnector(
            api_key=settings.rapid_api_key,
            host=settings.rapid_api_host,
            south=settings.rapid_api_south,
            west=settings.rapid_api_west,
            north=settings.rapid_api_north,
            east=settings.rapid_api_east,
        )
        if not settings.rapid_api_is_configured():
            log.debug("poll_rapidapi_ais: RAPID_API_KEY not configured, skipping")
            return {"polled_at": polled_at, "aoi_count": 0, "ship_count": 0, "errors": 0}

        store = get_default_telemetry_store()
        ship_count = 0
        errors = 0

        try:
            records = connector.fetch()
            events = connector.normalize_all(records)
            # Phase 1 Track B: persist to both EventStore (for replay) and TelemetryStore
            get_default_event_store().ingest_batch(events)
            ship_count += store.ingest_batch(events)
            get_health_service().record_success(
                "rapidapi-ais", "RapidAPI AIS", "rapidapi"
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("poll_rapidapi_ais: fetch failed — %s", exc)
            get_health_service().record_error("rapidapi-ais", str(exc))
            errors += 1

        log.info("poll_rapidapi_ais: %d ship events (%d errors)", ship_count, errors)
        return {"polled_at": polled_at, "aoi_count": 1, "ship_count": ship_count, "errors": errors}

    @celery_app.task(name="poll_vessel_data")
    def poll_vessel_data() -> dict[str, Any]:
        """Poll vessel positions from vessel-data.p.rapidapi.com.

        Uses the centre+radius derived from VESSEL_DATA_SOUTH/WEST/NORTH/EAST.
        Writes results into the in-memory TelemetryStore.
        Returns: {polled_at, aoi_count, ship_count, errors}.
        """
        from datetime import datetime

        from app.config import get_settings
        from src.connectors.vessel_data import VesselDataConnector
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service
        from src.services.telemetry_store import get_default_telemetry_store

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        connector = VesselDataConnector(
            api_key=settings.vessel_data_api_key,
            south=settings.vessel_data_south,
            west=settings.vessel_data_west,
            north=settings.vessel_data_north,
            east=settings.vessel_data_east,
        )

        if not settings.vessel_data_is_configured():
            log.debug("poll_vessel_data: VESSEL_DATA_API_KEY not configured, skipping")
            return {"polled_at": polled_at, "aoi_count": 0, "ship_count": 0, "errors": 0}

        store = get_default_telemetry_store()
        ship_count = 0
        errors = 0

        try:
            records = connector.fetch()
            events = connector.normalize_all(records)
            # Phase 1 Track B: persist to both EventStore (for replay) and TelemetryStore
            get_default_event_store().ingest_batch(events)
            ship_count += store.ingest_batch(events)
            get_health_service().record_success(
                "vessel-data", "VesselData", "rapidapi"
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("poll_vessel_data: fetch failed — %s", exc)
            get_health_service().record_error("vessel-data", str(exc))
            errors += 1

        log.info("poll_vessel_data: %d ship events (%d errors)", ship_count, errors)
        return {"polled_at": polled_at, "aoi_count": 1, "ship_count": ship_count, "errors": errors}

    @celery_app.task(name="enforce_telemetry_retention")
    def enforce_telemetry_retention() -> dict[str, Any]:
        """P5-4.4: Automated data retention enforcement task.

        Prunes ship/aircraft telemetry to the configured retention policy.
        Runs via Celery beat on a configurable interval (default: 1 hour).
        Returns a summary dict: {enforced_at, entities_pruned, events_pruned}.
        """
        from datetime import datetime

        from src.services.source_health import get_health_service
        from src.services.telemetry_store import RetentionPolicy, TelemetryStore

        enforced_at = datetime.now(UTC).isoformat()
        # DEMO-ONLY: operates on the in-memory TelemetryStore singleton; data does not
        # survive worker restarts — see Phase 1 Track B for PostgreSQL/TimescaleDB persistence
        store = TelemetryStore()        # Uses the module-level in-memory store
        policy = RetentionPolicy()      # Uses defaults (max_age_days=30)

        try:
            result = store.enforce_retention(policy)
            store.thin_old_positions(policy)
            log.info(
                "enforce_telemetry_retention: pruned %d events across %d entities",
                result.get("events_pruned", 0),
                result.get("entities_pruned", 0),
            )
            get_health_service().record_success(
                "telemetry-retention", "Telemetry Retention", "internal"
            )
            return {"enforced_at": enforced_at, **result}
        except Exception as exc:  # noqa: BLE001
            log.error("enforce_telemetry_retention failed: %s", exc)
            get_health_service().record_error("telemetry-retention", str(exc))
            return {"enforced_at": enforced_at, "error": str(exc)}

    @celery_app.task(name="probe_stac_connectors")
    def probe_stac_connectors() -> dict[str, Any]:
        """Lightweight STAC catalog health probe.

        Hits the /collections endpoint of each imagery connector to verify
        reachability.  Records health on SourceHealthService so the dashboard
        shows fresh/stale instead of 'unknown'.
        """
        from datetime import datetime

        import httpx

        from src.services.source_health import get_health_service

        health_svc = get_health_service()
        probed_at = datetime.now(UTC).isoformat()
        results: dict[str, str] = {}

        # Lightweight probe targets: connector_id -> STAC root URL
        targets = {
            "earth-search": "https://earth-search.aws.element84.com/v1",
            "planetary-computer": "https://planetarycomputer.microsoft.com/api/stac/v1",
            "usgs-landsat": "https://landsatlook.usgs.gov/stac-server",
        }

        for cid, url in targets.items():
            try:
                resp = httpx.get(f"{url}/", timeout=10.0)
                resp.raise_for_status()
                health_svc.record_success(cid)
                results[cid] = "ok"
            except Exception as exc:  # noqa: BLE001
                health_svc.record_error(cid, str(exc))
                results[cid] = f"error: {exc}"
                log.warning("probe_stac_connectors: %s — %s", cid, exc)

        return {"probed_at": probed_at, "results": results}

    @celery_app.task(name="poll_usgs_earthquakes")
    def poll_usgs_earthquakes() -> dict[str, Any]:
        """Poll USGS earthquake catalog for all active AOIs (15-minute window overlap)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.usgs_earthquake import UsgsEarthquakeConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = UsgsEarthquakeConnector(
            api_url=settings.usgs_earthquake_api_url,
            min_magnitude=settings.usgs_earthquake_min_magnitude,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=30)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_usgs_earthquakes: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_usgs_earthquakes: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_nasa_eonet")
    def poll_nasa_eonet() -> dict[str, Any]:
        """Poll NASA EONET natural hazard events for all active AOIs (30-min cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.nasa_eonet import NasaEonetConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = NasaEonetConnector(
            api_url=settings.nasa_eonet_api_url,
            days_lookback=settings.nasa_eonet_days_lookback,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=settings.nasa_eonet_days_lookback)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_nasa_eonet: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_nasa_eonet: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_open_meteo")
    def poll_open_meteo() -> dict[str, Any]:
        """Poll Open-Meteo weather forecast for all active AOIs (60-min cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.open_meteo import OpenMeteoConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = OpenMeteoConnector(
            api_url=settings.open_meteo_api_url,
            forecast_hours=settings.open_meteo_forecast_hours,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_open_meteo: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_open_meteo: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_acled_events")
    def poll_acled_events() -> dict[str, Any]:
        """Poll ACLED armed conflict events for all active AOIs (60-min cadence, requires API key)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.services.source_health import get_health_service

        settings = get_settings()
        if not settings.acled_is_configured():
            log.debug("poll_acled_events: ACLED_API_KEY/ACLED_EMAIL not configured, skipping")
            return {"polled_at": datetime.now(UTC).isoformat(), "skipped": True}

        from src.connectors.acled import AcledConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store

        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = AcledConnector(
            api_key=settings.acled_api_key,
            email=settings.acled_email,
            api_url=settings.acled_api_url,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=7)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_acled_events: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_acled_events: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_nga_msi")
    def poll_nga_msi() -> dict[str, Any]:
        """Poll NGA MSI maritime safety warnings for all active AOIs (15-min cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.nga_msi import NgaMsiConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = NgaMsiConnector(
            api_url=settings.nga_msi_api_url,
            default_nav_areas=[a.strip() for a in settings.nga_msi_default_nav_areas.split(",") if a.strip()],
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=7)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_nga_msi: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_nga_msi: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_osm_military")
    def poll_osm_military() -> dict[str, Any]:
        """Poll OSM Overpass military installations for all active AOIs (6-hour cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.osm_military import OsmMilitaryConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = OsmMilitaryConnector(overpass_url=settings.osm_overpass_url)
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=6)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_osm_military: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_osm_military: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_nasa_firms")
    def poll_nasa_firms() -> dict[str, Any]:
        """Poll NASA FIRMS thermal anomaly / active fire detections for all active AOIs (30-min cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.nasa_firms import NasaFirmsConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = NasaFirmsConnector(
            map_key=settings.nasa_firms_map_key,
            api_url=settings.nasa_firms_api_url,
            source=settings.nasa_firms_source,
            days_lookback=settings.nasa_firms_days_lookback,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=settings.nasa_firms_days_lookback)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_nasa_firms: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_nasa_firms: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="poll_noaa_swpc")
    def poll_noaa_swpc() -> dict[str, Any]:
        """Poll NOAA SWPC space weather alerts (10-min cadence, global — no AOI required)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.noaa_swpc import NoaaSwpcConnector
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = NoaaSwpcConnector(api_url=settings.noaa_swpc_api_url)
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=1)
        # SWPC is global — no AOI geometry required; geometry param is accepted but ignored
        dummy_geometry: dict[str, Any] = {
            "type": "Polygon",
            "coordinates": [[[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]],
        }
        event_count = 0
        try:
            raw = connector.fetch(dummy_geometry, start_time, end_time)
            events = connector.normalize_all(raw)
            get_default_event_store().ingest_batch(events)
            event_count = len(events)
            health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
            log.info("poll_noaa_swpc: %d space weather events ingested", event_count)
        except Exception as exc:  # noqa: BLE001
            log.warning("poll_noaa_swpc: fetch failed — %s", exc)
            health_svc.record_error(connector.connector_id, str(exc))
            return {"polled_at": polled_at, "event_count": 0, "errors": [str(exc)]}

        return {"polled_at": polled_at, "event_count": event_count, "errors": []}

    @celery_app.task(name="poll_openaq")
    def poll_openaq() -> dict[str, Any]:
        """Poll OpenAQ air quality measurements for all active AOIs (30-min cadence)."""
        from datetime import datetime, timedelta

        from app.config import get_settings
        from src.connectors.openaq import OpenAqConnector
        from src.services.aoi_store import AoiStore
        from src.services.event_store import get_default_event_store
        from src.services.source_health import get_health_service

        settings = get_settings()
        polled_at = datetime.now(UTC).isoformat()
        health_svc = get_health_service()
        connector = OpenAqConnector(
            api_url=settings.openaq_api_url,
            api_key=settings.openaq_api_key,
        )
        aoi_store = AoiStore()
        aois = aoi_store.list_aois()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=2)
        event_count = 0
        errors: list = []

        for aoi in aois:
            try:
                geometry = aoi.get("geometry") or {}
                if not geometry:
                    continue
                raw = connector.fetch(geometry, start_time, end_time)
                events = connector.normalize_all(raw)
                get_default_event_store().ingest_batch(events)
                event_count += len(events)
                health_svc.record_success(connector.connector_id, connector.display_name, connector.source_type)
                log.info("poll_openaq: AOI %s → %d events", aoi.get("id", "unknown"), len(events))
            except Exception as exc:  # noqa: BLE001
                log.warning("poll_openaq: AOI poll failed — %s", exc)
                errors.append(str(exc))
                health_svc.record_error(connector.connector_id, str(exc))

        return {"polled_at": polled_at, "aoi_count": len(aois), "event_count": event_count, "errors": errors}

    @celery_app.task(name="workers.warm_playback_windows", ignore_result=True)
    def warm_playback_windows() -> None:
        """Phase 1 Track C: Pre-warm 24h, 7d, and 30d playback window materialization.

        Calls standard_playback_windows() to resolve window bounds, then enqueues
        a MaterializeRequest for each window via the PlaybackService singleton.
        Runs every 6 hours via Celery beat.
        """
        from src.api.playback import get_playback_service
        from src.models.playback import MaterializeRequest
        from src.services.playback_service import standard_playback_windows

        svc = get_playback_service()
        windows = standard_playback_windows()
        for name, (start, end) in windows.items():
            try:
                req = MaterializeRequest(start_time=start, end_time=end)
                svc.enqueue_materialize(req)
                log.info("warm_playback_windows: materialized window '%s'", name)
            except Exception as exc:  # noqa: BLE001
                log.warning("warm_playback_windows: window '%s' failed — %s", name, exc)

except (ImportError, Exception) as exc:
    log.warning("Celery tasks not registered: %s", exc)

    def run_analysis_task(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_gdelt_context(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_opensky_positions(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_aisstream_positions(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_rapidapi_ais(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_vessel_data(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def probe_stac_connectors(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def enforce_telemetry_retention(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def warm_playback_windows(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_usgs_earthquakes(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_nasa_eonet(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_open_meteo(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_acled_events(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_nga_msi(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_osm_military(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_nasa_firms(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_noaa_swpc(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")

    def poll_openaq(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("Celery is not configured")
