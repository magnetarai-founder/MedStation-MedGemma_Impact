"""
Centralized Excel operations utilities
"""

import pandas as pd
from typing import Optional, List, Dict, Any, Iterator
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExcelReader:
    """Efficient Excel file reader with chunking support"""

    @staticmethod
    def read_excel_chunked(
        file_path: str,
        sheet_name: Optional[str] = None,
        chunk_size: int = 10000,
        usecols: Optional[List[str]] = None,
        dtype: Optional[Dict[str, Any]] = None,
    ) -> Iterator[pd.DataFrame]:
        """
        Read Excel file in chunks for memory efficiency

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read (default: first sheet)
            chunk_size: Number of rows per chunk
            usecols: List of columns to read
            dtype: Dictionary of column dtypes

        Yields:
            DataFrame chunks
        """
        try:
            # For large files, use openpyxl's read_only mode
            excel_file = pd.ExcelFile(file_path, engine="openpyxl")

            if sheet_name is None:
                sheet_name = excel_file.sheet_names[0]

            # Read in chunks
            skiprows = 0
            while True:
                df_chunk = pd.read_excel(
                    excel_file,
                    sheet_name=sheet_name,
                    skiprows=skiprows if skiprows > 0 else None,
                    nrows=chunk_size,
                    usecols=usecols,
                    dtype=dtype,
                    header=0 if skiprows == 0 else None,
                )

                if df_chunk.empty:
                    break

                yield df_chunk
                skiprows += chunk_size

        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}")
            raise

    @staticmethod
    def read_excel_optimized(
        file_path: str,
        sheet_name: Optional[str] = None,
        usecols: Optional[List[str]] = None,
        dtype: Optional[Dict[str, Any]] = None,
        parse_dates: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Read entire Excel file with optimizations

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to read
            usecols: List of columns to read
            dtype: Dictionary of column dtypes
            parse_dates: List of columns to parse as dates

        Returns:
            DataFrame
        """
        try:
            return pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                usecols=usecols,
                dtype=dtype,
                parse_dates=parse_dates,
                engine="openpyxl",
                na_values=["", "NA", "N/A", "null", "NULL", "None", "NONE"],
            )
        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}")
            raise

    @staticmethod
    def get_sheet_names(file_path: str) -> List[str]:
        """Get list of sheet names from Excel file"""
        try:
            with pd.ExcelFile(file_path, engine="openpyxl") as excel_file:
                return excel_file.sheet_names
        except Exception as e:
            logger.error(f"Error getting sheet names from {file_path}: {e}")
            raise


class ExcelWriter:
    """Efficient Excel file writer"""

    @staticmethod
    def write_excel_optimized(
        df: pd.DataFrame,
        file_path: str,
        sheet_name: str = "Sheet1",
        index: bool = False,
        freeze_panes: Optional[tuple] = (1, 0),
    ) -> None:
        """
        Write DataFrame to Excel with optimizations

        Args:
            df: DataFrame to write
            file_path: Output file path
            sheet_name: Name of sheet
            index: Whether to write index
            freeze_panes: Tuple of (row, col) to freeze
        """
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=index, freeze_panes=freeze_panes)
        except Exception as e:
            logger.error(f"Error writing Excel file {file_path}: {e}")
            raise

    @staticmethod
    def append_to_excel(df: pd.DataFrame, file_path: str, sheet_name: str = "Sheet1", index: bool = False) -> None:
        """
        Append DataFrame to existing Excel file

        Args:
            df: DataFrame to append
            file_path: Excel file path
            sheet_name: Name of sheet
            index: Whether to write index
        """
        try:
            path = Path(file_path)
            if not path.exists():
                ExcelWriter.write_excel_optimized(df, file_path, sheet_name, index)
                return

            with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
                # Get existing data
                existing_df = pd.read_excel(file_path, sheet_name=sheet_name)
                startrow = len(existing_df) + 1

                df.to_excel(writer, sheet_name=sheet_name, index=index, startrow=startrow, header=False)
        except Exception as e:
            logger.error(f"Error appending to Excel file {file_path}: {e}")
            raise
