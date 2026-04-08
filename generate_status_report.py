"""
ARGUS Platform - Comprehensive Services Status Report Generator
================================================================
Generates a professional status report for all infrastructure and external services.
"""
import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, timeout=10):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def check_docker_status():
    """Check Docker engine and container status."""
    status = {
        'engine': 'UNKNOWN',
        'version': 'N/A',
        'containers_running': 0,
        'containers_total': 0,
        'container_details': []
    }
    
    # Check Docker version
    code, stdout, stderr = run_command('docker version --format json')
    if code == 0:
        try:
            version_data = json.loads(stdout)
            status['engine'] = 'OPERATIONAL'
            status['version'] = version_data.get('Client', {}).get('Version', 'Unknown')
        except:
            status['engine'] = 'RUNNING (JSON parse failed)'
    else:
        status['engine'] = 'NOT RUNNING'
    
    # Check containers
    code, stdout, stderr = run_command('docker ps --format json')
    if code == 0 and stdout:
        running = [json.loads(line) for line in stdout.split('\n') if line.strip()]
        status['containers_running'] = len(running)
    
    code, stdout, stderr = run_command('docker ps -a --format json')
    if code == 0 and stdout:
        all_containers = [json.loads(line) for line in stdout.split('\n') if line.strip()]
        status['containers_total'] = len(all_containers)
        status['container_details'] = all_containers
    
    return status


def check_docker_compose_status():
    """Check docker-compose services."""
    status = {
        'services': [],
        'status': 'UNKNOWN'
    }
    
    code, stdout, stderr = run_command('docker-compose ps --format json', timeout=10)
    if code == 0 and stdout:
        try:
            services = [json.loads(line) for line in stdout.split('\n') if line.strip()]
            status['services'] = services
            status['status'] = 'CONFIGURED' if services else 'NO SERVICES'
        except:
            status['status'] = 'PARSE ERROR'
    else:
        status['status'] = 'NOT RUNNING'
    
    return status


def check_env_configuration():
    """Check .env file configuration."""
    config = {
        'file_exists': False,
        'total_vars': 0,
        'configured_vars': 0,
        'key_apis': {}
    }
    
    env_file = Path('.env')
    if env_file.exists():
        config['file_exists'] = True
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if '=' in line and not line.startswith('#')]
        
        config['total_vars'] = len(lines)
        config['configured_vars'] = len([l for l in lines if l.split('=', 1)[1]])
        
        # Check key API credentials
        key_vars = {
            'ACLED_EMAIL': 'ACLED Conflict Data',
            'ACLED_PASSWORD': 'ACLED OAuth2',
            'OPENSKY_USERNAME': 'OpenSky Aviation',
            'OPENSKY_PASSWORD': 'OpenSky Auth',
            'AISSTREAM_API_KEY': 'AIS Stream Maritime',
            'RAPIDAPI_KEY': 'RapidAPI Services',
            'COPERNICUS_CLIENT_ID': 'Sentinel-2 Imagery',
            'NASA_FIRMS_MAP_KEY': 'NASA Fire Detection'
        }
        
        for var, desc in key_vars.items():
            val = next((l.split('=', 1)[1] for l in lines if l.startswith(var + '=')), '')
            config['key_apis'][desc] = 'CONFIGURED' if val else 'NOT SET'
    
    return config


def generate_report():
    """Generate comprehensive status report."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("=" * 100)
    print(" " * 20 + "ARGUS PLATFORM - COMPREHENSIVE SERVICES STATUS REPORT")
    print("=" * 100)
    print(f"Generated: {timestamp}")
    print(f"Report Type: Infrastructure & External Services Verification")
    print("=" * 100)
    print()
    
    # Section 1: Docker Infrastructure
    print("[SECTION 1] DOCKER INFRASTRUCTURE STATUS")
    print("-" * 100)
    
    docker_status = check_docker_status()
    engine_symbol = "[OK]" if docker_status['engine'] == 'OPERATIONAL' else "[X]"
    print(f"Docker Engine:           {engine_symbol} {docker_status['engine']}")
    print(f"  Version:               {docker_status['version']}")
    print(f"  Running Containers:    {docker_status['containers_running']}")
    print(f"  Total Containers:      {docker_status['containers_total']}")
    
    if docker_status['container_details']:
        print()
        print("Container Details:")
        for container in docker_status['container_details']:
            name = container.get('Names', 'unknown')
            image = container.get('Image', 'unknown')
            status = container.get('Status', 'unknown')
            state = container.get('State', 'unknown')
            
            state_symbol = "[RUNNING]" if state == 'running' else "[STOPPED]"
            print(f"  {state_symbol} {name:20s} | {image:30s} | {status}")
    else:
        print()
        print("  >> No containers currently defined")
        print("  >> Action Required: Run 'docker-compose up -d' to start services")
    
    print()
    
    # Section 2: Docker Compose Services
    print("[SECTION 2] DOCKER COMPOSE SERVICES")
    print("-" * 100)
    
    compose_status = check_docker_compose_status()
    print(f"Compose Status:          {compose_status['status']}")
    
    expected_services = {
        'redis': 'Redis Cache (Port 6379)',
        'db': 'PostgreSQL/PostGIS Database (Port 5432)',
        'minio': 'MinIO Object Storage (Ports 9000, 9001)',
        'api': 'FastAPI Application Server (Port 8000)',
        'worker': 'Celery Background Worker',
        'beat': 'Celery Beat Task Scheduler'
    }
    
    print()
    print("Expected Services:")
    if compose_status['services']:
        running_names = [s.get('Name', s.get('Service', '')).lower() for s in compose_status['services']]
        for svc, desc in expected_services.items():
            if any(svc in name for name in running_names):
                svc_data = next((s for s in compose_status['services'] if svc in s.get('Name', '').lower()), {})
                state = svc_data.get('State', 'unknown')
                symbol = "[OK]" if state == 'running' else "[!]"
                print(f"  {symbol} {svc:12s} : {desc:50s} [{state.upper()}]")
            else:
                print(f"  [X] {svc:12s} : {desc:50s} [NOT RUNNING]")
    else:
        for svc, desc in expected_services.items():
            print(f"  [...] {svc:12s} : {desc:50s} [PENDING]")
    
    print()
    
    # Section 3: Environment Configuration
    print("[SECTION 3] ENVIRONMENT CONFIGURATION")
    print("-" * 100)
    
    env_config = check_env_configuration()
    
    if env_config['file_exists']:
        print(f"Configuration File:      [OK] .env exists")
        print(f"  Total Variables:       {env_config['total_vars']}")
        print(f"  Configured:            {env_config['configured_vars']}")
        print(f"  Coverage:              {(env_config['configured_vars']/env_config['total_vars']*100):.1f}%")
        
        print()
        print("External API Credentials:")
        for api, status in env_config['key_apis'].items():
            symbol = "[OK]" if status == 'CONFIGURED' else "[!]"
            print(f"  {symbol} {api:30s} : {status}")
    else:
        print("Configuration File:      [X] .env NOT FOUND")
    
    print()
    
    # Section 4: Service Readiness Assessment
    print("[SECTION 4] SERVICE READINESS ASSESSMENT")
    print("-" * 100)
    
    # Calculate readiness scores
    docker_ready = docker_status['engine'] == 'OPERATIONAL'
    containers_ready = docker_status['containers_running'] >= 6
    env_ready = env_config['file_exists'] and env_config['configured_vars'] > 70
    
    print("Component Status:")
    print(f"  {'[OK]' if docker_ready else '[X]'} Docker Engine:          {'OPERATIONAL' if docker_ready else 'NOT READY'}")
    print(f"  {'[OK]' if containers_ready else '[X]'} Service Containers:     {'RUNNING ({})'.format(docker_status['containers_running']) if containers_ready else 'NOT RUNNING'}")
    print(f"  {'[OK]' if env_ready else '[X]'} Environment Config:     {'CONFIGURED' if env_ready else 'INCOMPLETE'}")
    
    total_checks = 3
    passed_checks = sum([docker_ready, containers_ready, env_ready])
    readiness_pct = (passed_checks / total_checks) * 100
    
    print()
    print(f"Overall Readiness:       {readiness_pct:.0f}% ({passed_checks}/{total_checks} checks passed)")
    
    if readiness_pct < 100:
        print()
        print("Required Actions:")
        if not docker_ready:
            print("  [X] Start Docker Engine")
        if not containers_ready:
            print("  [X] Run: docker-compose up -d --build")
        if not env_ready:
            print("  [X] Complete .env configuration")
    
    print()
    
    # Section 5: Next Steps
    print("[SECTION 5] RECOMMENDED ACTIONS")
    print("-" * 100)
    
    if not containers_ready:
        print("CRITICAL: Services Not Running")
        print()
        print("To start all services:")
        print("  1. docker-compose build              # Build application images")
        print("  2. docker-compose up -d              # Start all services in background")
        print("  3. docker-compose ps                 # Verify all services are healthy")
        print("  4. docker-compose logs -f api        # Monitor API startup")
        print()
        print("Once services are running:")
        print("  5. python verify_data_sources.py     # Test external API connectivity")
        print("  6. curl http://localhost:8000/health # Check API health")
        print("  7. curl http://localhost:8000/docs   # Access API documentation")
    else:
        print("[OK] All services operational")
        print()
        print("Verification Commands:")
        print("  - docker-compose logs <service>      # View service logs")
        print("  - python verify_data_sources.py      # Test external APIs")
        print("  - curl http://localhost:8000/health  # API health check")
    
    print()
    print("=" * 100)
    print(" " * 35 + "END OF REPORT")
    print("=" * 100)


if __name__ == '__main__':
    generate_report()
