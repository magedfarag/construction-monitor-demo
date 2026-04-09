#!/usr/bin/env python3
"""
Project Structure Organization Script
Moves misplaced files to proper locations and removes obsolete files.
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).parent.parent
moves = [
    # Move test data to fixtures
    ("ne_10m_land.geojson", "tools/data/ne_10m_land.geojson"),
    ("playback_check.json", "tests/fixtures/playback_check.json"),
    ("playback_response.json", "tests/fixtures/playback_response.json"),
    ("production_readiness_report.json", "docs/reports/production_readiness_report.json"),
    
    # Move screenshots to docs/images
    ("argus-app-loaded.png", "docs/images/argus-app-loaded.png"),
    ("argus-initial-load.png", "docs/images/argus-initial-load.png"),
]

deletions = [
    # Delete obsolete debug scripts
    "debug_test2.py",
    "debug_test3.py",
    "create_maritime.py",
    
    # Delete temporary output files
    "uvicorn.log",
    "frontend/list-output.txt",
    "frontend/debug-output.txt",
    "frontend/vitest_output.txt",
    "frontend/ts_errors.txt",
    "frontend/test-output.txt",
    "frontend/demo-debug.err",
]

def main():
    print("=" * 80)
    print("PROJECT STRUCTURE ORGANIZATION")
    print("=" * 80)
    
    # Execute moves
    print("\n[MOVES]")
    for src, dest in moves:
        src_path = ROOT / src
        dest_path = ROOT / dest
        
        if not src_path.exists():
            print(f"  SKIP   {src} (not found)")
            continue
            
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dest_path.exists():
            print(f"  EXISTS {dest} (skipping)")
            continue
            
        shutil.move(str(src_path), str(dest_path))
        print(f"  MOVED  {src} -> {dest}")
    
    # Execute deletions
    print("\n[DELETIONS]")
    for path in deletions:
        file_path = ROOT / path
        
        if not file_path.exists():
            print(f"  SKIP   {path} (not found)")
            continue
            
        file_path.unlink()
        print(f"  DELETED {path}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
