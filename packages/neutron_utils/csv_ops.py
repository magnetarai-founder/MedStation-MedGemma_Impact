"""
CSV normalization utilities to keep row/column counts stable.

Guarantees:
- Column count remains equal to header length.
- No rows are dropped; short rows are padded, long rows are folded into the last column.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Tuple, Optional
import uuid


def detect_delimiter(sample_lines: list[str]) -> str:
    """
    Heuristic delimiter detection among common candidates.
    """
    candidates = [",", "\t", ";", "|"]
    counts = {c: 0 for c in candidates}
    for line in sample_lines:
        for c in candidates:
            counts[c] += line.count(c)
    # Pick the delimiter with highest total count; default comma
    delim = max(counts, key=lambda k: counts[k]) if sample_lines else ","
    # If all zero, default comma
    if all(v == 0 for v in counts.values()):
        return ","
    return delim


def normalize_csv_to_temp(
    file_path: str | Path,
    encoding: str = "utf-8",
) -> Tuple[Path, str]:
    """
    Normalize a CSV to guarantee consistent column width across all rows.

    - Determines delimiter heuristically.
    - Reads header to establish column count N.
    - For each row: if len(row) > N, joins overflow into last column; if len(row) < N, pads empties.

    Returns: (normalized_csv_path, delimiter_used)
    """
    src = Path(file_path)
    temp = src.with_name(f"{src.stem}__ns_norm_{uuid.uuid4().hex[:8]}.csv")

    # Read a small sample for delimiter detection
    sample_lines: list[str] = []
    with open(src, "r", encoding=encoding, newline="") as rf:
        for _ in range(10):
            line = rf.readline()
            if not line:
                break
            sample_lines.append(line)
    delim = detect_delimiter(sample_lines)

    # Now normalize
    with open(src, "r", encoding=encoding, newline="") as rf, open(temp, "w", encoding=encoding, newline="") as wf:
        reader = csv.reader(rf, delimiter=delim, quotechar='"', escapechar='\\')
        writer = csv.writer(wf, delimiter=delim, quotechar='"', escapechar='\\', quoting=csv.QUOTE_MINIMAL)

        # Skip leading empty lines
        header: Optional[list[str]] = None
        for row in reader:
            if row and any(cell != "" for cell in row):
                header = row
                break
        if header is None:
            # Empty file; create a minimal header
            header = ["col_1"]
        N = len(header)
        writer.writerow(header)

        # Process remaining rows
        for row in reader:
            # Treat completely empty rows as all-empty
            if not row:
                writer.writerow([""] * N)
                continue
            if len(row) > N:
                fixed = row[: N - 1] + [delim.join(row[N - 1 :])]
            elif len(row) < N:
                fixed = row + [""] * (N - len(row))
            else:
                fixed = row
            writer.writerow(fixed)

    return temp, delim

