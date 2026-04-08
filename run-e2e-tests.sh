#!/usr/bin/env bash
set -euo pipefail

# E2E Test Runner
# Helper script for running Playwright tests with various parallelization options.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Run Playwright E2E tests with various parallelization options.

OPTIONS:
    -m, --mode MODE         Test execution mode:
                            - parallel (default): Run with auto-detected workers
                            - fast: Run with 4 workers
                            - serial: Run with 1 worker (slowest)
                            - debug: Run in debug mode with UI
                            - ui: Run with Playwright UI mode
                            - headed: Run in headed mode (visible browser)

    -w, --workers NUM       Number of parallel workers (1-100)
    -s, --shard SHARD       Run specific shard (e.g., "1/4")
    -g, --grep PATTERN      Filter test names by pattern
    -f, --file FILE         Run specific test file (e.g., "smoke.spec.ts")
    -H, --headed            Run tests in headed mode
    -r, --report            Show HTML test report
    -h, --help              Show this help message

EXAMPLES:
    $(basename "$0")                              # Run with default parallel config
    $(basename "$0") -m fast                      # Run with 4 workers
    $(basename "$0") -m debug -f smoke.spec.ts    # Debug smoke tests
    $(basename "$0") -s "1/4"                     # Run first shard of 4
    $(basename "$0") -w 2 -g "accessibility"      # Run accessibility tests with 2 workers

EOF
}

check_backend() {
    echo -e "${CYAN}Checking backend health...${NC}"
    
    local urls=("http://127.0.0.1:8000/api/health" "http://localhost:8000/api/health")
    local healthy=false
    
    for url in "${urls[@]}"; do
        if curl -s -f -m 2 "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}βœ" Backend is running at $url${NC}"
            healthy=true
            break
        fi
    done
    
    if [ "$healthy" = false ]; then
        echo -e "${YELLOW}Warning: Backend doesn't appear to be running. E2E tests require the backend API.${NC}"
        echo -e "${YELLOW}To start the backend, run:${NC}"
        echo -e "${YELLOW}  python -m uvicorn app.main:app --reload${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Parse arguments
MODE="parallel"
WORKERS=""
SHARD=""
GREP=""
FILE=""
HEADED=""
REPORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -s|--shard)
            SHARD="$2"
            shift 2
            ;;
        -g|--grep)
            GREP="$2"
            shift 2
            ;;
        -f|--file)
            FILE="$2"
            shift 2
            ;;
        -H|--headed)
            HEADED="--headed"
            shift
            ;;
        -r|--report)
            REPORT="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Change to frontend directory
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Cannot find frontend directory at: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Show report and exit if requested
if [ "$REPORT" = "true" ]; then
    echo -e "${CYAN}Opening test report...${NC}"
    npx playwright show-report
    exit 0
fi

# Check backend health
check_backend

# Build playwright command
PLAYWRIGHT_ARGS=("test")

# Configure workers based on mode
case $MODE in
    fast)
        if [ -z "$WORKERS" ]; then
            PLAYWRIGHT_ARGS+=("--workers=4")
            echo -e "${CYAN}Running in FAST mode (4 workers)...${NC}"
        fi
        ;;
    serial)
        if [ -z "$WORKERS" ]; then
            PLAYWRIGHT_ARGS+=("--workers=1" "--fully-parallel=false")
            echo -e "${CYAN}Running in SERIAL mode (1 worker)...${NC}"
        fi
        ;;
    debug)
        PLAYWRIGHT_ARGS+=("--debug")
        echo -e "${CYAN}Running in DEBUG mode...${NC}"
        ;;
    ui)
        PLAYWRIGHT_ARGS+=("--ui")
        echo -e "${CYAN}Running in UI mode...${NC}"
        ;;
    headed)
        PLAYWRIGHT_ARGS+=("--headed")
        echo -e "${CYAN}Running in HEADED mode...${NC}"
        ;;
    parallel)
        echo -e "${CYAN}Running in PARALLEL mode (auto workers)...${NC}"
        ;;
    *)
        echo -e "${RED}Invalid mode: $MODE${NC}"
        show_help
        exit 1
        ;;
esac

# Override workers if specified
if [ -n "$WORKERS" ]; then
    PLAYWRIGHT_ARGS+=("--workers=$WORKERS")
    echo -e "${CYAN}Using $WORKERS worker(s)...${NC}"
fi

# Add shard configuration
if [ -n "$SHARD" ]; then
    PLAYWRIGHT_ARGS+=("--shard=$SHARD")
    echo -e "${CYAN}Running shard $SHARD...${NC}"
fi

# Add grep filter
if [ -n "$GREP" ]; then
    PLAYWRIGHT_ARGS+=("--grep=$GREP")
    echo -e "${CYAN}Filtering tests matching: $GREP${NC}"
fi

# Add headed flag
if [ -n "$HEADED" ]; then
    PLAYWRIGHT_ARGS+=("$HEADED")
fi

# Add specific file
if [ -n "$FILE" ]; then
    PLAYWRIGHT_ARGS+=("$FILE")
    echo -e "${CYAN}Running test file: $FILE${NC}"
fi

# Display command
echo -e "${GRAY}"
echo "Executing: npx playwright ${PLAYWRIGHT_ARGS[*]}"
echo -e "${NC}"

# Run playwright
START_TIME=$(date +%s)

set +e
npx playwright "${PLAYWRIGHT_ARGS[@]}"
EXIT_CODE=$?
set -e

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$(echo "scale=1; $DURATION / 60" | bc)

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}βœ" Tests passed in ${DURATION_MIN} minutes${NC}"
    echo -e "${CYAN}To view the HTML report, run:${NC}"
    echo -e "${CYAN}  $0 --report${NC}"
else
    echo -e "${RED}βœ— Tests failed after ${DURATION_MIN} minutes${NC}"
    echo -e "${CYAN}To view the failure report, run:${NC}"
    echo -e "${CYAN}  $0 --report${NC}"
fi

exit $EXIT_CODE
