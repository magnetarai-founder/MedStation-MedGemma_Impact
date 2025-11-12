"""
SQL and DataFrame utilities for session-based data processing.

Contains helpers for column analysis and JSON conversion.
"""

import pandas as pd
from api.schemas.api_models import ColumnInfo


def get_column_info(df: pd.DataFrame) -> list[ColumnInfo]:
    """Get column information with clean names"""
    from neutron_utils.sql_utils import ColumnNameCleaner
    cleaner = ColumnNameCleaner()

    columns: list[ColumnInfo] = []
    for col in df.columns:
        # Use the supported cleaner API (instance method `clean`)
        clean_name = cleaner.clean(str(col))
        columns.append(ColumnInfo(
            original_name=str(col),
            clean_name=clean_name,
            dtype=str(df[col].dtype),
            non_null_count=int(df[col].notna().sum()),
            null_count=int(df[col].isna().sum())
        ))
    return columns


def df_to_jsonsafe_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to JSON-safe records using neutron_utils"""
    from neutron_utils.json_utils import df_to_jsonsafe_records as _df_to_jsonsafe_records
    return _df_to_jsonsafe_records(df)
