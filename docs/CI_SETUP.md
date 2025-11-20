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

## E2E Smoke Tests

ElohimOS includes end-to-end smoke tests that validate the complete Agent + Workflow integration path. These tests run as part of the standard backend test suite.

### Test Suite: `apps/backend/tests/test_e2e_agent_workflow_smoke.py`

**Coverage**: 7 comprehensive E2E scenarios (169 total backend tests)

1. **Template instantiation** - Global templates → team workflows with correct visibility
2. **Agent Assist flow** - Work items reach AGENT_ASSIST stages and receive recommendations
3. **Agent Assist with auto-apply** - Patches automatically applied when enabled
4. **Workflow triggers (single)** - Agent events create work items in listening workflows
5. **Workflow triggers (multiple)** - Single event triggers multiple workflows
6. **Team workflow isolation** - Team boundaries respected (currently skipped, requires orchestrator team_id support)
7. **Personal workflow privacy** - Personal workflows remain private to owner

### Running E2E Tests

**Run only E2E tests:**
```bash
# From repo root
cd apps/backend
ELOHIM_ENV=development PYTHONPATH="../packages:.:$PYTHONPATH" \
  ../venv/bin/python3 -m pytest tests/test_e2e_agent_workflow_smoke.py -v
```

**Run all backend tests (includes E2E):**
```bash
# From repo root
./tools/run_dev_checks.sh
```

### What E2E Tests Validate

These tests exercise the full stack:
- **Workflow orchestration** - Stage transitions, work item lifecycle
- **Agent integration** - Planning, auto-apply, error handling
- **Event triggers** - agent.apply.success → workflow creation
- **Multi-tenancy** - Personal/team/global visibility isolation
- **Storage layer** - SQLite persistence and retrieval
- **Graceful degradation** - Agent failures don't break workflows

### CI Integration

E2E tests run automatically in CI as part of `backend-dev-checks`:
- Included in `pytest tests/` invocation
- No additional configuration needed
- ~1.3 seconds runtime (lightweight, uses mocks)

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
- Frontend E2E tests with Playwright (backend E2E tests already implemented - see above)
- Docker image building for deployments
