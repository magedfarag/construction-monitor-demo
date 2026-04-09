# E2E Test Parallelization Guide

## Overview

The E2E test suite is configured for parallel execution with GPU-aware constraints. Tests run in parallel by default, but GPU-intensive suites opt into serial execution to prevent resource saturation.

## Configuration

### Parallel Execution (Default)

- **Local**: Uses all available CPU cores (typically 4-8 workers)
- **CI**: Uses 50% of available cores to balance speed with resource usage
- **Mode**: `fullyParallel: true` enables parallel execution across test files

### Serial Test Suites

The following test suites run serially due to GPU constraints:

- `performance.spec.ts` - Requires accurate timing measurements
- `render-mode.spec.ts` - GPU-intensive render mode switching
- `full-exploratory-walkthrough.spec.ts` - Comprehensive demo with heavy GPU usage

These suites use `test.describe.configure({ mode: 'serial' })` to opt out of parallelization.

## Running Tests

### Basic Usage

```bash
# Run all tests in parallel (default)
npm run test:e2e

# Run with specific worker count
npx playwright test --workers=4

# Run specific test file
npx playwright test smoke.spec.ts

# Run tests matching a pattern
npx playwright test --grep "accessibility"
```

### Advanced Parallelization

```bash
# Use test sharding for distributed execution (e.g., across CI jobs)
# Shard 1 of 3
npx playwright test --shard=1/3

# Shard 2 of 3
npx playwright test --shard=2/3

# Shard 3 of 3
npx playwright test --shard=3/3

# Run with maximum parallelism (may saturate GPU on some systems)
npx playwright test --workers=100%

# Run with conservative parallelism (recommended for GPU-constrained systems)
npx playwright test --workers=2

# Run with fully serial execution (slowest, original behavior)
npx playwright test --workers=1 --fully-parallel=false
```

### Performance Optimization Tips

1. **Local Development**: Use default settings (`npm run test:e2e`)
   - Auto-detects available cores
   - Balances speed with system resources

2. **CI/CD Pipeline**: Use sharding for faster execution
   ```yaml
   # GitHub Actions example
   strategy:
     matrix:
       shard: [1, 2, 3, 4]
   steps:
     - run: npx playwright test --shard=${{ matrix.shard }}/4
   ```

3. **GPU-Constrained Systems**: Reduce worker count
   ```bash
   npx playwright test --workers=2
   ```

4. **Debugging**: Run single worker for easier console output
   ```bash
   npx playwright test --workers=1 --headed --debug
   ```

## Adding New Tests

### Default Behavior

New test files run in parallel by default. No configuration needed:

```typescript
import { test, expect } from "./fixtures";

test.describe("My New Feature", () => {
  test("does something", async ({ page }) => {
    // Test code
  });
});
```

### Opting Into Serial Execution

If your tests are GPU-intensive or require serialization:

```typescript
import { test, expect } from "./fixtures";

// Add this line to run serially
test.describe.configure({ mode: 'serial' });

test.describe("GPU-Heavy Feature", () => {
  test("renders 3D scene", async ({ page }) => {
    // GPU-intensive test code
  });
});
```

## Performance Benchmarks

Based on typical test suite execution:

| Configuration | Duration | Use Case |
|--------------|----------|----------|
| Workers=1 (original) | ~45-60 min | Legacy, debugging |
| Workers=2 | ~25-35 min | GPU-constrained systems |
| Workers=4 | ~15-20 min | Typical local development |
| Workers=auto (8 cores) | ~10-15 min | Modern multi-core systems |
| Sharded 4 ways | ~8-12 min | CI parallel jobs |

*Note: Actual durations vary based on hardware, especially GPU capabilities.*

## Troubleshooting

### Tests Fail in Parallel but Pass Serially

1. Check for shared state between tests
2. Ensure proper test isolation in `beforeEach`/`afterEach`
3. Add `test.describe.configure({ mode: 'serial' })` temporarily

### GPU/Video Recording Timeouts

1. Reduce worker count: `--workers=2`
2. Check GPU driver updates
3. Verify WebGL cleanup fixture in `fixtures.ts`

### Inconsistent Performance Results

Performance tests require serial execution for accurate measurements. Verify:
```typescript
test.describe.configure({ mode: 'serial' });
```

## CI Configuration Examples

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm install
      - run: npx playwright install --with-deps chromium
      - run: npx playwright test --shard=${{ matrix.shard }}/4
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report-${{ matrix.shard }}
          path: playwright-report/
```

### Azure Pipelines

```yaml
strategy:
  parallel: 4
steps:
  - script: npx playwright test --shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase)
    displayName: 'Run E2E Tests (Sharded)'
```

## Further Reading

- [Playwright Parallelization](https://playwright.dev/docs/test-parallel)
- [Test Sharding](https://playwright.dev/docs/test-sharding)
- [Performance Best Practices](https://playwright.dev/docs/best-practices)
