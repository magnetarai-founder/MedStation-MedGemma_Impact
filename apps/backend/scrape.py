# scrape.py
"""
Simple data reader - reads Excel files and makes them available for SQL processing
"""

import os
import logging
import pandas as pd
from typing import Optional, Callable
import time
import warnings

# Suppress the pandas downcasting warning
warnings.filterwarnings("ignore", message="Downcasting behavior in `replace`")

# ---- logging setup ----------------------------------------------------------
# Console logging only, no file output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
    force=True,
)
logger = logging.getLogger(__name__)

# ---- core function -------------------------------------------------------


def read_catalog_data(
    file_path: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    row_limit: Optional[int] = None,
    smart_sample: bool = False,
) -> pd.DataFrame:
    """
    Read catalog data from Excel file only.

    Args:
        file_path: Path to the catalog file (Excel .xlsx/.xls only)
        progress_callback: Optional callback for progress updates
        row_limit: Optional limit on number of rows to read (for preview mode)
        smart_sample: If True and row_limit is set, sample rows throughout the file instead of just first N

    Returns:
        pd.DataFrame: The catalog data as-is, no modifications
    """
    try:
        start_time = time.time()

        # Report starting
        if progress_callback:
            progress_callback(0.0, "Starting to read file...")

        # Validate file type
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in [".xlsx", ".xls"]:
            # Get file size for progress estimation
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)

            if progress_callback:
                progress_callback(0.1, f"Loading Excel file ({size_mb:.1f} MB)...")

            # Define columns that should always be read as strings to preserve leading zeros
            string_columns = ["BARCODE", "SKU", "MERCHANT_SKU", "UPC", "EAN", "GTIN"]

            # First, quickly read just the headers to determine dtypes
            if progress_callback:
                progress_callback(0.2, "Reading file structure...")

            df_preview = pd.read_excel(file_path, nrows=0)

            # Create dtype dictionary for columns that exist
            dtype_dict = {}
            for col in df_preview.columns:
                # Check if column name matches any of our string column identifiers (case-insensitive)
                col_upper = col.upper()
                for str_col in string_columns:
                    # Exact match or column contains the identifier as a whole word
                    if col_upper == str_col or f"_{str_col}" in col_upper or f"{str_col}_" in col_upper:
                        dtype_dict[col] = str
                        break

            # Use pandas read_excel with optimizations
            if progress_callback:
                progress_callback(0.3, "Loading data (optimized)...")

            # Smart sampling logic
            if smart_sample and row_limit and row_limit < 10000:  # Only for preview mode
                # First, get a quick estimate of total rows
                # Read a small chunk to estimate row count
                sample_df = pd.read_excel(file_path, nrows=1000)

                # If file has more rows than our sample
                if len(sample_df) == 1000:
                    # For Excel files, we need to read the whole file to know exact row count
                    # So we'll use a hybrid approach: skip first few rows (often headers/notes)
                    # then read sequentially
                    skip_rows = 5  # Skip potential header rows

                    # Read with skiprows
                    df = pd.read_excel(
                        file_path,
                        dtype=dtype_dict,
                        na_values=["", "NA", "N/A", "NULL", "null", "None", "-"],
                        keep_default_na=True,
                        skiprows=range(1, skip_rows + 1),  # Skip rows 1-5 (keep header at 0)
                        nrows=row_limit,
                    )

                    if progress_callback:
                        progress_callback(0.7, f"Smart sampling: skipped first {skip_rows} rows")
                else:
                    # File is small, just read normally
                    df = pd.read_excel(
                        file_path,
                        dtype=dtype_dict,
                        na_values=["", "NA", "N/A", "NULL", "null", "None", "-"],
                        keep_default_na=True,
                        nrows=row_limit,
                    )
            else:
                # Normal read - first N rows or entire file
                df = pd.read_excel(
                    file_path,
                    dtype=dtype_dict,
                    na_values=["", "NA", "N/A", "NULL", "null", "None", "-"],  # Handle nulls during read
                    keep_default_na=True,
                    nrows=row_limit,  # Apply row limit if specified (for preview mode)
                )

            if progress_callback:
                progress_callback(0.9, "Finalizing data...")

            # Log basic info
            elapsed = time.time() - start_time
            preview_text = f" (preview mode - limited to {row_limit} rows)" if row_limit else ""
            if smart_sample and row_limit:
                preview_text = f" (smart preview - {row_limit} rows after skipping headers)"
            logger.info(
                f"Excel file loaded{preview_text}: {df.shape[0]:,} rows × {df.shape[1]} columns in {elapsed:.1f}s"
            )

            if progress_callback:
                progress_callback(1.0, f"Loaded {df.shape[0]:,} rows{preview_text} in {elapsed:.1f}s")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Only Excel files (.xlsx, .xls) are supported.")

        # Validate DataFrame is not empty
        if df is None or df.empty:
            raise ValueError("Excel file is empty or contains no data")

        if len(df.columns) == 0:
            raise ValueError("Excel file has no columns")

        return df

    except Exception as e:
        logger.error(f"Failed to read catalog file {file_path}: {str(e)}")
        if progress_callback:
            progress_callback(0.0, f"Error: {str(e)}")
        raise


def read_catalog_data_chunked(file_path: str, chunk_size: int = 50000):
    """
    Read catalog data from Excel file in chunks for memory efficiency.

    Args:
        file_path: Path to the catalog file (Excel .xlsx/.xls only)
        chunk_size: Number of rows per chunk

    Yields:
        pd.DataFrame: Chunks of the catalog data
    """
    try:
        # Validate file type
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext not in [".xlsx", ".xls"]:
            raise ValueError(f"Unsupported file type: {file_ext}. Only Excel files (.xlsx, .xls) are supported.")

        # Get file info
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        logger.info(f"Starting chunked read of {file_path} ({size_mb:.1f} MB) with chunk size {chunk_size:,}")

        # Define columns that should always be read as strings to preserve leading zeros
        string_columns = ["BARCODE", "SKU", "MERCHANT_SKU", "UPC", "EAN", "GTIN"]

        # First, quickly read just the headers to determine dtypes
        df_preview = pd.read_excel(file_path, nrows=0)

        # Create dtype dictionary for columns that exist
        dtype_dict = {}
        for col in df_preview.columns:
            # Check if column name matches any of our string column identifiers (case-insensitive)
            col_upper = col.upper()
            for str_col in string_columns:
                # Exact match or column contains the identifier as a whole word
                if col_upper == str_col or f"_{str_col}" in col_upper or f"{str_col}_" in col_upper:
                    dtype_dict[col] = str
                    break

        # Get total rows for progress tracking (approximate)
        # Note: For Excel files, we can't know the exact row count without reading the whole file
        # So we'll use chunks and track as we go

        chunk_num = 0
        rows_read = 0

        # Read Excel file in chunks
        # pandas read_excel doesn't support chunksize, so we'll read with skiprows and nrows
        while True:
            chunk_num += 1
            skip_rows = 1 + (chunk_num - 1) * chunk_size  # Skip header + previous chunks

            try:
                # Read chunk
                chunk_df = pd.read_excel(
                    file_path,
                    dtype=dtype_dict,
                    na_values=["", "NA", "N/A", "NULL", "null", "None", "-"],
                    keep_default_na=True,
                    skiprows=range(1, skip_rows) if chunk_num > 1 else None,
                    nrows=chunk_size,
                )

                if chunk_df.empty:
                    break

                rows_read += len(chunk_df)
                logger.info(f"Read chunk {chunk_num}: {len(chunk_df):,} rows (total: {rows_read:,})")

                yield chunk_df

                # If we got fewer rows than chunk_size, we've reached the end
                if len(chunk_df) < chunk_size:
                    break

            except Exception as e:
                if "No columns to parse from file" in str(e):
                    # We've reached the end of the file
                    break
                else:
                    logger.error(f"Error reading chunk {chunk_num}: {e}")
                    raise

        logger.info(f"Chunked read complete. Total rows read: {rows_read:,}")

    except Exception as e:
        logger.error(f"Failed to read catalog file in chunks: {str(e)}")
        raise
