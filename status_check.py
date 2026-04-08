import subprocess
import json
from datetime import datetime

print('=' * 90)
print('ARGUS PLATFORM - SERVICES VERIFICATION REPORT')
print('=' * 90)
print(f'Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}')
print('=' * 90)
print()

# Docker Status
print('[1] DOCKER INFRASTRUCTURE')
print('-' * 90)
try:
    result = subprocess.run(['docker', 'version', '--format', 'json'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print('  Docker Engine: RUNNING')
        version_data = json.loads(result.stdout)
        print(f'  Version: {version_data.get('Client', {}).get('Version', 'Unknown')}')
    else:
        print('  Docker Engine: NOT RUNNING')
except Exception as e:
    print(f'  Docker Engine: ERROR - {e}')

print()
print('[2] ACTIVE CONTAINERS')
print('-' * 90)
try:
    result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=5)
    lines = result.stdout.strip().split('\n')
    if len(lines) > 1:
        print(f'  Running: {len(lines) - 1} containers')
        for line in lines[1:]:
            print(f'    {line}')
    else:
        print('  Running: 0 containers')
        print('  Status: BUILD IN progress')
except Exception as e:
    print(f'  ERROR: {e}')

print()
print('[3] EXPECTED DOCKER SERVICES')
print('-' * 90)
services = {
    'redis': 'Redis Cache',
    'db': 'PostgreSQL/PostGIS',
    'minio': 'Object Storage',
    'api': 'FastAPI Application',
    'worker': 'Celery Worker',
    'beat': 'Celery Scheduler'
}
for svc, desc in services.items():
    print(f'  {svc:12s} : {desc}')
