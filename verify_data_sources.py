"""
ARGUS Data Source Verification Script
=====================================

This script verifies all providers and connectors configured in the system,
tests their connectivity, and generates a comprehensive production readiness report.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import AppMode, get_settings


class DataSourceReport:
    """Generates comprehensive report of all data sources."""
    
    def __init__(self):
        self.settings = get_settings()
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "app_mode": self.settings.app_mode.value,
            "v1_providers": {},
            "v2_connectors": {},
            "infrastructure": {},
            "summary": {
                "total": 0,
                "healthy": 0,
                "configured_but_unavailable": 0,
                "not_configured": 0,
                "critical_failures": []
            }
        }
    
    def _test_provider(self, provider_cls, settings, name: str) -> dict:
        """Test a V1 provider."""
        try:
            provider = provider_cls(settings)
            valid, msg = provider.validate_credentials()
            if valid:
                healthy, health_msg = provider.healthcheck()
                return {
                    "status": "healthy" if healthy else "unhealthy",
                    "configured": True,
                    "validation": msg,
                    "health": health_msg,
                    "resolution_m": provider.resolution_m
                }
            else:
                return {
                    "status": "invalid_credentials",
                    "configured": True,
                    "validation": msg,
                    "health": None
                }
        except Exception as exc:
            return {
                "status": "error",
                "configured": True,
                "error": str(exc)
            }
    
    async def _test_connector(self, connector) -> dict:
        """Test a V2 connector."""
        try:
            health = await connector.health()
            return {
                "status": "healthy" if health.healthy else "unhealthy",
                "configured": True,
                "message": health.message,
                "error_count": health.error_count,
                "last_poll": health.last_successful_poll.isoformat() if health.last_successful_poll else None
            }
        except Exception as exc:
            return {
                "status": "error",
                "configured": True,
                "error": str(exc)
            }
    
    async def verify_all(self):
        """Run comprehensive verification of all data sources."""
        print("=" * 80)
        print("ARGUS Production Readiness - Data Source Verification")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"App Mode: {self.settings.app_mode.value}")
        print()
        
        # Test infrastructure
        await self._test_infrastructure()
        
        # Test V1 Providers
        await self._test_v1_providers()
        
        # Test V2 Connectors
        await self._test_v2_connectors()
        
        # Generate summary
        self._generate_summary()
        
        # Save report
        self._save_report()
        
        return self.results
    
    async def _test_infrastructure(self):
        """Test Redis, PostgreSQL, and object storage."""
        print("Testing Infrastructure...")
        print("-" * 80)
        
        # Redis
        redis_status = "not_configured"
        redis_msg = "No Redis URL configured"
        if self.settings.redis_available():
            try:
                import redis
                client = redis.from_url(self.settings.redis_url, socket_timeout=5)
                client.ping()
                redis_status = "healthy"
                redis_msg = f"Connected to {self.settings.redis_url}"
            except Exception as exc:
                redis_status = "unhealthy"
                redis_msg = str(exc)
        
        self.results["infrastructure"]["redis"] = {
            "status": redis_status,
            "message": redis_msg,
            "configured": self.settings.redis_available()
        }
        print(f"  βœ" Redis: {redis_status} - {redis_msg}")
        
        # PostgreSQL
        db_status = "not_configured"
        db_msg = "No database URL configured"
        if self.settings.database_url:
            try:
                from sqlalchemy import create_engine, text
                engine = create_engine(self.settings.database_url, pool_pre_ping=True)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_status = "healthy"
                db_msg = "Database connection successful"
            except Exception as exc:
                db_status = "unhealthy"
                db_msg = str(exc)
        
        self.results["infrastructure"]["postgresql"] = {
            "status": db_status,
            "message": db_msg,
            "configured": bool(self.settings.database_url)
        }
        print(f"  βœ" PostgreSQL: {db_status} - {db_msg}")
        
        # Object Storage
        storage_status = "not_configured"
        storage_msg = "No object storage configured"
        if self.settings.object_storage_endpoint:
            storage_status = "configured"
            storage_msg = f"Endpoint: {self.settings.object_storage_endpoint}"
        
        self.results["infrastructure"]["object_storage"] = {
            "status": storage_status,
            "message": storage_msg,
            "configured": bool(self.settings.object_storage_endpoint)
        }
        print(f"  βœ" Object Storage: {storage_status} - {storage_msg}")
        print()
    
    async def _test_v1_providers(self):
        """Test all V1 satellite imagery providers."""
        print("Testing V1 Satellite Imagery Providers...")
        print("-" * 80)
        
        # Demo Provider (always available)
        print("  βœ" DemoProvider: always available")
        self.results["v1_providers"]["demo"] = {
            "status": "healthy",
            "configured": True,
            "message": "Demo provider with deterministic test data"
        }
        
        # Sentinel-2
        if self.settings.sentinel2_is_configured():
            print("  Testing Sentinel2Provider...")
            try:
                from app.providers.sentinel2 import Sentinel2Provider
                result = self._test_provider(Sentinel2Provider, self.settings, "Sentinel2")
                self.results["v1_providers"]["sentinel2"] = result
                print(f"    Status: {result['status']} - {result.get('validation', result.get('health', result.get('error')))}")
            except Exception as exc:
                self.results["v1_providers"]["sentinel2"] = {"status": "error", "error": str(exc)}
                print(f"    Status: error - {exc}")
        else:
            print("  βœ— Sentinel2Provider: not configured (need CLIENT_ID + CLIENT_SECRET)")
            self.results["v1_providers"]["sentinel2"] = {"status": "not_configured", "configured": False}
        
        # Landsat
        if self.settings.landsat_is_configured():
            print("  Testing LandsatProvider...")
            try:
                from app.providers.landsat import LandsatProvider
                result = self._test_provider(LandsatProvider, self.settings, "Landsat")
                self.results["v1_providers"]["landsat"] = result
                print(f"    Status: {result['status']} - {result.get('validation', result.get('health', result.get('error')))}")
            except Exception as exc:
                self.results["v1_providers"]["landsat"] = {"status": "error", "error": str(exc)}
                print(f"    Status: error - {exc}")
        else:
            print("  βœ— LandsatProvider: not configured")
            self.results["v1_providers"]["landsat"] = {"status": "not_configured", "configured": False}
        
        # Maxar
        if self.settings.maxar_is_configured():
            print("  Testing MaxarProvider...")
            try:
                from app.providers.maxar import MaxarProvider
                result = self._test_provider(MaxarProvider, self.settings, "Maxar")
                self.results["v1_providers"]["maxar"] = result
                print(f"    Status: {result['status']} - {result.get('validation', result.get('health', result.get('error')))}")
            except Exception as exc:
                self.results["v1_providers"]["maxar"] = {"status": "error", "error": str(exc)}
                print(f"    Status: error - {exc}")
        else:
            print("  βœ— MaxarProvider: not configured (need API_KEY)")
            self.results["v1_providers"]["maxar"] = {"status": "not_configured", "configured": False}
        
        # Planet
        if self.settings.planet_is_configured():
            print("  Testing PlanetProvider...")
            try:
                from app.providers.planet import PlanetProvider
                result = self._test_provider(PlanetProvider, self.settings, "Planet")
                self.results["v1_providers"]["planet"] = result
                print(f"    Status: {result['status']} - {result.get('validation', result.get('health', result.get('error')))}")
            except Exception as exc:
                self.results["v1_providers"]["planet"] = {"status": "error", "error": str(exc)}
                print(f"    Status: error - {exc}")
        else:
            print("  βœ— PlanetProvider: not configured (need API_KEY)")
            self.results["v1_providers"]["planet"] = {"status": "not_configured", "configured": False}
        print()
    
    async def _test_v2_connectors(self):
        """Test all V2 connectors."""
        print("Testing V2 Connectors...")
        print("-" * 80)
        
        test_bbox = [55.0, 24.0, 56.0, 25.0]  # Small area in Persian Gulf
        test_start = datetime.utcnow() - timedelta(days=7)
        test_end = datetime.utcnow()
        
        # Free STAC providers (no auth)
        await self._test_connector_safe("earth_search", "EarthSearchConnector",
                                       lambda: __import__('src.connectors.earth_search', fromlist=['EarthSearchConnector']).EarthSearchConnector(
                                           stac_url=self.settings.earth_search_stac_url))
        
        await self._test_connector_safe("planetary_computer", "PlanetaryComputerConnector",
                                       lambda: __import__('src.connectors.planetary_computer', fromlist=['PlanetaryComputerConnector']).PlanetaryComputerConnector(
                                           stac_url=self.settings.planetary_computer_stac_url,
                                           subscription_key=self.settings.planetary_computer_token))
        
        # Sentinel-2 CDSE
        if self.settings.sentinel2_is_configured():
            await self._test_connector_safe("sentinel2_cdse", "CdseSentinel2Connector",
                                           lambda: self._create_sentinel2_connector())
        else:
            print("  βœ— CdseSentinel2Connector: not configured")
            self.results["v2_connectors"]["sentinel2_cdse"] = {"status": "not_configured", "configured": False}
        
        # Landsat USGS
        await self._test_connector_safe("landsat_usgs", "UsgsLandsatConnector",
                                       lambda: __import__('src.connectors.landsat', fromlist=['UsgsLandsatConnector']).UsgsLandsatConnector(
                                           stac_url=self.settings.landsat_stac_url))
        
        # GDELT (free, no auth)
        await self._test_connector_safe("gdelt", "GdeltConnector",
                                       lambda: __import__('src.connectors.gdelt', fromlist=['GdeltConnector', 'DEFAULT_CONSTRUCTION_THEMES']).GdeltConnector(
                                           default_themes=__import__('src.connectors.gdelt', fromlist=['DEFAULT_CONSTRUCTION_THEMES']).DEFAULT_CONSTRUCTION_THEMES))
        
        # AISStream (requires API key)
        aisstream_key = os.getenv("AISSTREAM_API_KEY", "")
        if aisstream_key:
            await self._test_connector_safe("ais_stream", "AisStreamConnector",
                                           lambda: __import__('src.connectors.ais_stream', fromlist=['AisStreamConnector']).AisStreamConnector(api_key=aisstream_key))
        else:
            print("  βœ— AisStreamConnector: not configured (need AISSTREAM_API_KEY)")
            self.results["v2_connectors"]["ais_stream"] = {"status": "not_configured", "configured": False}
        
        # OpenSky (optional auth)
        await self._test_connector_safe("opensky", "OpenSkyConnector",
                                       lambda: __import__('src.connectors.opensky', fromlist=['OpenSkyConnector']).OpenSkyConnector(
                                           username=os.getenv("OPENSKY_USERNAME", ""),
                                           password=os.getenv("OPENSKY_PASSWORD", "")))
        
        # USGS Earthquake (free, no auth)
        await self._test_connector_safe("usgs_earthquake", "UsgsEarthquakeConnector",
                                       lambda: __import__('src.connectors.usgs_earthquake', fromlist=['UsgsEarthquakeConnector']).UsgsEarthquakeConnector(
                                           api_url=self.settings.usgs_earthquake_api_url,
                                           min_magnitude=self.settings.usgs_earthquake_min_magnitude))
        
        # NASA EONET (free, no auth)
        await self._test_connector_safe("nasa_eonet", "NasaEonetConnector",
                                       lambda: __import__('src.connectors.nasa_eonet', fromlist=['NasaEonetConnector']).NasaEonetConnector(
                                           api_url=self.settings.nasa_eonet_api_url,
                                           days_lookback=self.settings.nasa_eonet_days_lookback))
        
        # Open-Meteo (free, no auth)
        await self._test_connector_safe("open_meteo", "OpenMeteoConnector",
                                       lambda: __import__('src.connectors.open_meteo', fromlist=['OpenMeteoConnector']).OpenMeteoConnector(
                                           api_url=self.settings.open_meteo_api_url,
                                           forecast_hours=self.settings.open_meteo_forecast_hours))
        
        # ACLED (requires email + password for OAuth2)
        if self.settings.acled_is_configured():
            await self._test_connector_safe("acled", "AcledConnector",
                                           lambda: __import__('src.connectors.acled', fromlist=['AcledConnector']).AcledConnector(
                                               email=self.settings.acled_email,
                                               password=self.settings.acled_password,
                                               token_url=self.settings.acled_token_url,
                                               api_url=self.settings.acled_api_url))
        else:
            print("  βœ— AcledConnector: not configured (need ACLED_EMAIL + ACLED_PASSWORD)")
            self.results["v2_connectors"]["acled"] = {"status": "not_configured", "configured": False}
        
        # NGA MSI (free, no auth)
        await self._test_connector_safe("nga_msi", "NgaMsiConnector",
                                       lambda: __import__('src.connectors.nga_msi', fromlist=['NgaMsiConnector']).NgaMsiConnector(
                                           api_url=self.settings.nga_msi_api_url,
                                           default_nav_areas=[a.strip() for a in self.settings.nga_msi_default_nav_areas.split(",") if a.strip()]))
        
        # OSM Military (free, no auth)
        await self._test_connector_safe("osm_military", "OsmMilitaryConnector",
                                       lambda: __import__('src.connectors.osm_military', fromlist=['OsmMilitaryConnector']).OsmMilitaryConnector(
                                           overpass_url=self.settings.osm_overpass_url))
        
        # NASA FIRMS (uses DEMO_KEY by default)
        await self._test_connector_safe("nasa_firms", "NasaFirmsConnector",
                                       lambda: __import__('src.connectors.nasa_firms', fromlist=['NasaFirmsConnector']).NasaFirmsConnector(
                                           map_key=self.settings.nasa_firms_map_key,
                                           api_url=self.settings.nasa_firms_api_url,
                                           source=self.settings.nasa_firms_source,
                                           days_lookback=self.settings.nasa_firms_days_lookback))
        
        # NOAA SWPC (free, no auth)
        await self._test_connector_safe("noaa_swpc", "NoaaSwpcConnector",
                                       lambda: __import__('src.connectors.noaa_swpc', fromlist=['NoaaSwpcConnector']).NoaaSwpcConnector(
                                           api_url=self.settings.noaa_swpc_api_url))
        
        # OpenAQ (free, optional API key)
        await self._test_connector_safe("openaq", "OpenAqConnector",
                                       lambda: __import__('src.connectors.openaq', fromlist=['OpenAqConnector']).OpenAqConnector(
                                           api_url=self.settings.openaq_api_url,
                                           api_key=self.settings.openaq_api_key))
        print()
    
    def _create_sentinel2_connector(self):
        """Helper to create Sentinel-2 connector with proper imports."""
        from src.connectors.sentinel2 import _STAC_URL, _TOKEN_URL, CdseSentinel2Connector
        return CdseSentinel2Connector(
            stac_url=_STAC_URL,
            token_url=_TOKEN_URL,
            client_id=self.settings.sentinel2_client_id,
            client_secret=self.settings.sentinel2_client_secret
        )
    
    async def _test_connector_safe(self, connector_id: str, name: str, factory):
        """Test a connector with exception handling."""
        try:
            print(f"  Testing {name}...")
            connector = factory()
            result = await self._test_connector(connector)
            self.results["v2_connectors"][connector_id] = result
            print(f"    Status: {result['status']} - {result.get('message', result.get('error', 'OK'))}")
        except Exception as exc:
            self.results["v2_connectors"][connector_id] = {
                "status": "error",
                "configured": True,
                "error": str(exc)
            }
            print(f"    Status: error - {exc}")
    
    def _generate_summary(self):
        """Generate overall summary statistics."""
        all_sources = {**self.results["v1_providers"], **self.results["v2_connectors"], **self.results["infrastructure"]}
        
        self.results["summary"]["total"] = len(all_sources)
        self.results["summary"]["healthy"] = sum(1 for v in all_sources.values() if v.get("status") == "healthy")
        self.results["summary"]["not_configured"] = sum(1 for v in all_sources.values() if v.get("status") == "not_configured")
        self.results["summary"]["configured_but_unavailable"] = sum(
            1 for v in all_sources.values() 
            if v.get("status") in ["unhealthy", "error", "invalid_credentials"] and v.get("configured", False)
        )
        
        # Identify critical failures
        critical = []
        if self.results["infrastructure"]["redis"]["status"] == "unhealthy":
            critical.append("Redis is configured but unavailable")
        if self.results["infrastructure"]["postgresql"]["status"] == "unhealthy":
            critical.append("PostgreSQL is configured but unavailable")
        
        # Check if we have at least one working imagery provider
        imagery_working = any(
            v.get("status") == "healthy" 
            for k, v in self.results["v1_providers"].items()
        )
        if not imagery_working:
            critical.append("No working imagery providers available")
        
        self.results["summary"]["critical_failures"] = critical
    
    def _save_report(self):
        """Save report to JSON file."""
        report_path = Path("data_source_verification_report.json")
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"Report saved to: {report_path.absolute()}")
    
    def print_summary(self):
        """Print summary to console."""
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        summary = self.results["summary"]
        print(f"Total Data Sources: {summary['total']}")
        print(f"Healthy: {summary['healthy']}")
        print(f"Not Configured: {summary['not_configured']}")
        print(f"Configured but Unavailable: {summary['configured_but_unavailable']}")
        print()
        
        if summary["critical_failures"]:
            print("CRITICAL FAILURES:")
            for failure in summary["critical_failures"]:
                print(f"  βœ— {failure}")
            print()
            print("⚠️  PRODUCTION READINESS: NOT READY")
        else:
            print("βœ" No critical failures detected")
            if summary["configured_but_unavailable"] > 0:
                print(f"⚠️  WARNING: {summary['configured_but_unavailable']} configured sources are unavailable")
                print("PRODUCTION READINESS: READY WITH WARNINGS")
            else:
                print("βœ" PRODUCTION READINESS: READY")
        print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        not_configured = [
            k for k, v in {**self.results["v1_providers"], **self.results["v2_connectors"]}.items()
            if v.get("status") == "not_configured"
        ]
        if not_configured:
            print("  Configure the following optional sources to enhance coverage:")
            for source in not_configured[:5]:  # Show first 5
                print(f"    - {source}")
            if len(not_configured) > 5:
                print(f"    ... and {len(not_configured) - 5} more")
        print()


async def main():
    """Main entry point."""
    report = DataSourceReport()
    await report.verify_all()
    report.print_summary()
    
    # Return exit code based on critical failures
    if report.results["summary"]["critical_failures"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
