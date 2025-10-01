"""
JSON utility functions for safe DataFrame conversion
"""

import pandas as pd
import math
import datetime as dt
from typing import Any, List, Dict


def df_to_jsonsafe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records.
    
    - Replaces NaN/NaT/Inf with None
    - Serializes datetime-like values to ISO strings
    """
    # Work on object dtype so None is preserved (not coerced back to NaN)
    safe = df.copy().astype(object)
    # Replace NaN/NaT with None first, then infinities
    safe = safe.where(pd.notna(safe), None)
    safe = safe.replace([float('inf'), float('-inf')], None)

    def _conv(x):
        # Pandas Timestamp
        if isinstance(x, pd.Timestamp):
            try:
                return x.to_pydatetime().isoformat()
            except Exception:
                return str(x)
        # Pandas Timedelta
        if isinstance(x, pd.Timedelta):
            # represent as total seconds string
            try:
                return str(x)
            except Exception:
                return None
        # Python datetime/date/time -> ISO
        if isinstance(x, (dt.datetime, dt.date, dt.time)):
            try:
                return x.isoformat()
            except Exception:
                return str(x)
        # Numpy scalar -> Python scalar
        try:
            import numpy as np
            if isinstance(x, (np.generic,)):
                x = x.item()
        except Exception:
            pass
        # Decimal -> float (or string if not finite)
        try:
            from decimal import Decimal
            if isinstance(x, Decimal):
                x = float(x)
        except Exception:
            pass
        # Normalize floats (remove inf/nan)
        if isinstance(x, float):
            if not math.isfinite(x):
                return None
            return x
        # Basic JSON primitives allowed
        if isinstance(x, (str, int, bool)) or x is None:
            return x
        # Fallback to string for any other type
        try:
            return str(x)
        except Exception:
            return None

    # Apply conversion element-wise via Series.map (avoids applymap deprecation)
    safe = safe.apply(lambda s: s.map(_conv))
    # Coercion during map can reintroduce NaN in float-typed Series; force object and null-out again
    safe = safe.astype(object)
    safe = safe.where(pd.notna(safe), None)
    return safe.to_dict('records')