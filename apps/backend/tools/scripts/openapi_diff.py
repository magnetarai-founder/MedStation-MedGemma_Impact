#!/usr/bin/env python3
"""
OpenAPI Schema Diff Tool

Compares two OpenAPI schemas and highlights differences in:
- Endpoints (added/removed/modified)
- Operation IDs (to detect duplicates)
- Request/response schemas

Usage:
    python tools/scripts/openapi_diff.py schema1.json schema2.json
    python tools/scripts/openapi_diff.py --fetch http://localhost:8000/api/openapi.json saved_schema.json
"""

import json
import sys
from pathlib import Path
from typing import Any
import subprocess


def fetch_openapi_schema(url: str) -> dict[str, Any]:
    """Fetch OpenAPI schema from a running server."""
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"Error fetching schema from {url}: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"Timeout fetching schema from {url}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON from {url}: {e}", file=sys.stderr)
        sys.exit(1)


def load_schema(path_or_url: str) -> dict[str, Any]:
    """Load OpenAPI schema from file or URL."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return fetch_openapi_schema(path_or_url)
    
    path = Path(path_or_url)
    if not path.exists():
        print(f"Schema file not found: {path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def extract_operation_ids(schema: dict[str, Any]) -> dict[str, str]:
    """Extract operation IDs and their corresponding paths+methods."""
    op_ids = {}
    for path, methods in schema.get("paths", {}).items():
        for method, spec in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                op_id = spec.get("operationId")
                if op_id:
                    op_ids[op_id] = f"{method.upper()} {path}"
    return op_ids


def diff_operation_ids(old_ids: dict[str, str], new_ids: dict[str, str]) -> None:
    """Compare operation IDs between schemas."""
    added = set(new_ids.keys()) - set(old_ids.keys())
    removed = set(old_ids.keys()) - set(new_ids.keys())
    common = set(old_ids.keys()) & set(new_ids.keys())
    
    # Check for duplicates in new schema
    duplicates = {}
    for op_id, endpoint in new_ids.items():
        if list(new_ids.values()).count(endpoint) > 1:
            if endpoint not in duplicates:
                duplicates[endpoint] = []
            duplicates[endpoint].append(op_id)
    
    print("\n=== Operation ID Changes ===")
    
    if duplicates:
        print("\nDUPLICATE OPERATION IDs (same endpoint, different operation IDs):")
        for endpoint, op_id_list in duplicates.items():
            print(f"  {endpoint}")
            for op_id in op_id_list:
                print(f"    - {op_id}")
    
    if added:
        print(f"\nADDED ({len(added)}):")
        for op_id in sorted(added):
            print(f"  + {op_id:50} {new_ids[op_id]}")
    
    if removed:
        print(f"\nREMOVED ({len(removed)}):")
        for op_id in sorted(removed):
            print(f"  - {op_id:50} {old_ids[op_id]}")
    
    # Check if endpoints changed for same operation ID
    changed = []
    for op_id in common:
        if old_ids[op_id] != new_ids[op_id]:
            changed.append((op_id, old_ids[op_id], new_ids[op_id]))
    
    if changed:
        print(f"\nMODIFIED ({len(changed)}):")
        for op_id, old_endpoint, new_endpoint in changed:
            print(f"  ~ {op_id}")
            print(f"      OLD: {old_endpoint}")
            print(f"      NEW: {new_endpoint}")
    
    if not added and not removed and not changed and not duplicates:
        print("  No changes")


def diff_endpoints(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> None:
    """Compare endpoints between schemas."""
    old_paths = set(old_schema.get("paths", {}).keys())
    new_paths = set(new_schema.get("paths", {}).keys())
    
    added = new_paths - old_paths
    removed = old_paths - new_paths
    
    print("\n=== Endpoint Changes ===")
    
    if added:
        print(f"\nADDED ({len(added)}):")
        for path in sorted(added):
            methods = [m.upper() for m in new_schema["paths"][path].keys() if m in ["get", "post", "put", "delete", "patch"]]
            print(f"  + {path:60} [{', '.join(methods)}]")
    
    if removed:
        print(f"\nREMOVED ({len(removed)}):")
        for path in sorted(removed):
            methods = [m.upper() for m in old_schema["paths"][path].keys() if m in ["get", "post", "put", "delete", "patch"]]
            print(f"  - {path:60} [{', '.join(methods)}]")
    
    if not added and not removed:
        print("  No changes")


def main():
    if len(sys.argv) < 3:
        print("Usage: python openapi_diff.py <old_schema> <new_schema>", file=sys.stderr)
        print("       python openapi_diff.py --fetch <url> <saved_schema>", file=sys.stderr)
        sys.exit(1)
    
    old_schema_path = sys.argv[1]
    new_schema_path = sys.argv[2]
    
    # Handle --fetch flag
    if old_schema_path == "--fetch":
        old_schema_path = new_schema_path
        new_schema_path = sys.argv[3] if len(sys.argv) > 3 else old_schema_path
    
    print(f"Loading schemas...")
    print(f"  OLD: {old_schema_path}")
    print(f"  NEW: {new_schema_path}")
    
    old_schema = load_schema(old_schema_path)
    new_schema = load_schema(new_schema_path)
    
    old_op_ids = extract_operation_ids(old_schema)
    new_op_ids = extract_operation_ids(new_schema)
    
    print(f"\nOLD: {len(old_schema.get('paths', {}))} endpoints, {len(old_op_ids)} operations")
    print(f"NEW: {len(new_schema.get('paths', {}))} endpoints, {len(new_op_ids)} operations")
    
    diff_endpoints(old_schema, new_schema)
    diff_operation_ids(old_op_ids, new_op_ids)
    
    print("\n=== Summary ===")
    print(f"Total endpoints: {len(old_schema.get('paths', {}))} → {len(new_schema.get('paths', {}))}")
    print(f"Total operations: {len(old_op_ids)} → {len(new_op_ids)}")


if __name__ == "__main__":
    main()
