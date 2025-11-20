# CI/CD Setup

## Overview

ElohimOS uses GitHub Actions for continuous integration, ensuring code quality on every push and pull request.

## Workflows

### Code Quality Checks (`.github/workflows/file-size-check.yml`)

This workflow runs on:
- All pull requests
- Pushes to `main` branch

#### Jobs

**1. check-file-sizes**
- Scans for files larger than 1200 lines
- Warns if large files are detected (non-blocking)
- Helps maintain code quality and modularity

**2. backend-dev-checks**
- **Python Version**: 3.12
- **Caching**: pip dependencies cached for speed
- **Steps**:
  1. Install backend dependencies from `apps/backend/requirements.txt`
  2. Run import validation (`scripts/check_imports.py`)
  3. Run all backend tests (`pytest tests/`)
- **Environment**:
  - `ELOHIM_ENV=development`
  - `PYTHONPATH` includes both `packages/` and `apps/backend/`
  - Test secrets for JWT

**3. frontend-build**
- **Node Version**: 20.x
- **Caching**: npm dependencies cached for speed
- **Steps**:
  1. Install frontend dependencies (`npm ci`)
  2. Build frontend (`npm run build`)
  3. Run linter if available (non-blocking)
- **Working Directory**: `apps/frontend/`

## Jobs Run in Parallel

All three jobs run in parallel to maximize CI speed:
- File size check: ~10 seconds
- Backend dev checks: ~2-3 minutes
- Frontend build: ~1-2 minutes

Total CI time: ~3 minutes

## Caching Strategy

To keep CI fast, the workflow uses GitHub Actions caching:

- **Python dependencies**: Cached based on `apps/backend/requirements.txt` hash
- **Node modules**: Cached based on `apps/frontend/package-lock.json` hash

This reduces dependency installation time from minutes to seconds on subsequent runs.

## Local Development

To run the same checks locally before pushing:

### Backend
```bash
# From repo root
./tools/run_dev_checks.sh
```

This runs:
1. Import validation
2. All backend tests

### Frontend
```bash
cd apps/frontend
npm run build
npm run lint
```

## Extending CI

### Adding New Tests

**Backend**: Add test files to `apps/backend/tests/` - they'll automatically be picked up by pytest.

**Frontend**: Add test scripts to `package.json` and update the workflow to run them.

### Adding Nightly/Scheduled Jobs

For slower integration tests or full regression suites, create a new workflow:

```yaml
# .github/workflows/nightly.yml
name: Nightly Tests
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
```

### Environment Variables

If tests require additional environment variables, add them to the job's `env:` section in the workflow file.

## Troubleshooting

### Import Errors in CI

If tests pass locally but fail in CI with import errors:
1. Ensure all dependencies are in `requirements.txt`
2. Check that `PYTHONPATH` includes necessary directories
3. Verify package structure matches local environment

### Frontend Build Failures

If frontend builds locally but fails in CI:
1. Check Node version matches (`engines` field in package.json)
2. Ensure `package-lock.json` is committed
3. Verify environment variables if needed

### Cache Issues

If dependencies seem stale or incorrect:
1. Clear cache by updating `cache-dependency-path` temporarily
2. Or manually delete cache from GitHub Actions UI

## Future Enhancements

Potential additions:
- Code coverage reporting
- Performance benchmarking
- Security scanning (Dependabot, CodeQL)
- E2E tests with Playwright
- Docker image building for deployments
