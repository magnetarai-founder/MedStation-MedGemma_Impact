# ElohimOS API Tools & Scripts

Utility scripts for API development and testing.

## OpenAPI Diff Tool

Compare OpenAPI schemas to detect breaking changes, duplicate operation IDs, and endpoint modifications.

### Usage

```bash
# Compare two saved schemas
python tools/scripts/openapi_diff.py old_schema.json new_schema.json

# Compare current server against saved schema
python tools/scripts/openapi_diff.py --fetch http://localhost:8000/api/openapi.json saved_schema.json

# Save current schema for future comparison
curl -s http://localhost:8000/api/openapi.json > openapi_$(date +%Y%m%d).json
```

### What It Detects

- Added/removed endpoints
- Added/removed operation IDs
- Modified operation IDs (same ID, different endpoint)
- Duplicate operation IDs (same endpoint, multiple IDs)
- Endpoint method changes

### Example Output

```
=== Operation ID Changes ===

ADDED (2):
  + sessions_validate                                POST /api/sessions/{session_id}/validate
  + sessions_tables                                 GET /api/sessions/{session_id}/tables

DUPLICATE OPERATION IDs (same endpoint, different operation IDs):
  POST /api/sessions/{session_id}/upload
    - upload_file
    - sessions_upload

=== Summary ===
Total endpoints: 45 → 47
Total operations: 45 → 47
```

### Integration with CI/CD

Add to pre-commit hooks or CI pipeline:

```bash
# Save baseline schema
curl -s http://localhost:8000/api/openapi.json > .openapi_baseline.json

# Before merge, check for breaking changes
python tools/scripts/openapi_diff.py .openapi_baseline.json http://localhost:8000/api/openapi.json
```
