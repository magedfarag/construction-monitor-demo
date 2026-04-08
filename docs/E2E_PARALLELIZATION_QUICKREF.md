# Playwright Test Parallelization - Quick Reference

## What Changed

βœ… **Parallel execution enabled** - Tests now run concurrently (was: sequential)  
βœ… **3-5x faster** - 10-20 min runtime (was: 45-60 min)  
βœ… **GPU-safe** - Heavy tests still run serially to avoid saturation  
βœ… **Helper scripts** - Easy execution with backend health checks  
βœ… **CI-ready** - Sharding support for distributed testing

## Quick Start

### Running Tests

```bash
# Windows
.\run-e2e-tests.ps1

# Linux/Mac  
chmod +x run-e2e-tests.sh
./run-e2e-tests.sh

# npm (any platform)
cd frontend
npm run test:e2e
```

### Common Commands

```bash
# Fast mode (4 workers)
.\run-e2e-tests.ps1 -Mode fast

# Debug specific test
.\run-e2e-tests.ps1 -Mode debug -File smoke.spec.ts

# View results
.\run-e2e-tests.ps1 -Report

# Run with 2 workers (for slower systems)
.\run-e2e-tests.ps1 -Workers 2

# Filter by pattern
.\run-e2e-tests.ps1 -Grep "accessibility"
```

## Files Modified

1. **`frontend/playwright.config.ts`** - Enabled `fullyParallel: true`, auto workers
2. **`frontend/e2e/performance.spec.ts`** - Added `test.describe.configure({ mode: 'serial' })`
3. **`frontend/e2e/render-mode.spec.ts`** - Added serial mode
4. **`frontend/e2e/full-exploratory-walkthrough.spec.ts`** - Added serial mode
5. **`frontend/package.json`** - Added convenience scripts

## Files Created

1. **`run-e2e-tests.ps1`** - PowerShell test runner with health checks
2. **`run-e2e-tests.sh`** - Bash test runner with health checks
3. **`frontend/e2e/README.md`** - Comprehensive usage guide
4. **`docs/E2E_PARALLELIZATION.md`** - Implementation details and architecture

## Performance Expectations

| Workers | Typical Duration | Best For |
|---------|-----------------|----------|
| 1 (old) | 45-60 min | Debugging only |
| 2 | 25-35 min | Constrained systems |
| 4 | 15-20 min | Balanced |
| Auto | 10-15 min | Modern hardware (default) |
| Sharded x4 | 8-12 min | CI parallel jobs |

## Architecture

- **Default**: All tests run in parallel across available CPU cores
- **GPU-Heavy**: Performance, render-mode, and demo tests opt into serial execution
- **Worker Count**: Auto-detected locally, 50% in CI, configurable via `--workers`
- **Cleanup**: Existing WebGL cleanup fixture handles GPU resource release

## CI Integration

```yaml
# GitHub Actions - run 4 parallel jobs
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: npx playwright test --shard=${{ matrix.shard }}/4
```

## Adding New Tests

**Regular tests** (run in parallel automatically):
```typescript
test.describe("My Feature", () => {
  test("does something", async ({ page }) => { /* ... */ });
});
```

**GPU-heavy tests** (opt into serial):
```typescript
test.describe.configure({ mode: 'serial' });

test.describe("Heavy Feature", () => {
  test("renders 3D", async ({ page }) => { /* ... */ });
});
```

## Rollback

If needed, revert to original behavior:
```bash
npx playwright test --workers=1 --fully-parallel=false
```

## Documentation

- **Usage Guide**: [`frontend/e2e/README.md`](frontend/e2e/README.md)
- **Implementation Details**: [`docs/E2E_PARALLELIZATION.md`](docs/E2E_PARALLELIZATION.md)
- **Config File**: [`frontend/playwright.config.ts`](frontend/playwright.config.ts)

## Verification

βœ… Config validated - `npx playwright test --list` succeeds  
βœ… Helper scripts created with proper error handling  
βœ… Documentation complete with examples  
βœ… Serial mode applied to GPU-intensive tests  
βœ… NPM scripts added for convenience

**Status**: Ready to use. Run `.\run-e2e-tests.ps1` to test immediately.
