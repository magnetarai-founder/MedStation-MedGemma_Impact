"""
Excel writing functionality adapted from Data Tool
"""
import os
import uuid
import pandas as pd
from typing import Optional, Union, Callable, Dict, Any
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class ExcelWriter:
    """Handles Excel file writing with optimizations"""
    
    # Excel row limit
    EXCEL_MAX_ROWS = 1048576
    
    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        """Sanitize Excel sheet name according to Excel constraints."""
        import re
        invalid = set(':\\/?*[]')
        cleaned = ''.join('_' if ch in invalid else ch for ch in str(name))
        cleaned = re.sub(r"[\x00-\x1F]", '', cleaned).strip()
        if not cleaned:
            cleaned = 'Sheet1'
        return cleaned[:31]
    
    @staticmethod
    def write_excel(df: pd.DataFrame,
                   output_path: Union[str, Path],
                   sheet_name: str = 'Sheet1',
                   chunk_size: int = 50000,
                   progress_callback: Optional[Callable] = None,
                   summary: Optional[Dict[str, Any]] = None) -> None:
        """
        Write DataFrame to Excel with handling for large files
        
        Args:
            df: DataFrame to write
            output_path: Output file path
            sheet_name: Name of the Excel sheet
            chunk_size: Number of rows to write at a time
            progress_callback: Optional callback(progress_percent, message)
        """
        try:
            total_rows = len(df)
            # Validate and normalize output path (prevents traversal)
            output_path = ExcelWriter.validate_output_path(output_path)
            
            # Ensure .xlsx extension
            if output_path.suffix.lower() not in ['.xlsx', '.xls']:
                output_path = output_path.with_suffix('.xlsx')
            
            logger.info(f"Writing {total_rows:,} rows to {output_path}")
            
            # Sanitize sheet name and dataframe for Excel compatibility
            sheet_name = ExcelWriter._sanitize_sheet_name(sheet_name)
            df = ExcelWriter._sanitize_dataframe(df)
            
            if progress_callback:
                progress_callback(0, "Starting Excel export...")
            
            # Check if we need to split into multiple sheets
            # Acquire a simple lock to avoid concurrent clobbering
            lock_path = output_path.with_suffix(output_path.suffix + '.lock')
            lock_fd = None
            for _ in range(20):  # retry for ~2 seconds
                try:
                    lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    break
                except FileExistsError:
                    time.sleep(0.1)
                except (OSError, PermissionError) as e:
                    # Read-only directory or permission issues - fail immediately
                    raise
            # Write to a temp path in the same directory for atomic replace
            tmp_path = output_path.with_suffix(output_path.suffix + f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
            try:
                if total_rows == 0:
                    # Handle empty dataframe
                    ExcelWriter._write_simple(df, tmp_path, sheet_name, progress_callback, summary=summary)
                elif total_rows >= ExcelWriter.EXCEL_MAX_ROWS:
                    ExcelWriter._write_multi_sheet(df, tmp_path, chunk_size, progress_callback, summary=summary)
                elif total_rows > 100000:
                    # Large file - use streaming
                    ExcelWriter._write_streaming(df, tmp_path, sheet_name, chunk_size, progress_callback, summary=summary)
                else:
                    # Small file - simple write
                    ExcelWriter._write_simple(df, tmp_path, sheet_name, progress_callback, summary=summary)
                # Atomic replace to final destination
                Path(tmp_path).replace(output_path)
            finally:
                # Best-effort cleanup if temp remains
                try:
                    if Path(tmp_path).exists():
                        Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass
                # Release lock
                if lock_fd is not None:
                    try:
                        os.close(lock_fd)
                    except Exception:
                        pass
                    try:
                        Path(lock_path).unlink(missing_ok=True)
                    except Exception:
                        pass
            
            if progress_callback:
                progress_callback(100, "Excel export complete")
                
            logger.info(f"Successfully wrote Excel file: {output_path}")
            
        except Exception as e:
            logger.error(f"Error writing Excel file: {e}")
            raise
    
    @staticmethod
    def _write_simple(df: pd.DataFrame,
                     output_path: Path,
                     sheet_name: str,
                     progress_callback: Optional[Callable],
                     summary: Optional[Dict[str, Any]] = None) -> None:
        """Simple Excel write for small files"""
        if progress_callback:
            progress_callback(50, "Writing to Excel...")

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Optional summary sheet
                if summary:
                    sdf = pd.DataFrame([summary])
                    sdf.to_excel(writer, sheet_name=ExcelWriter._sanitize_sheet_name('Summary'), index=False)
                # Don't use freeze_panes for empty dataframes
                if len(df) > 0:
                    df.to_excel(writer, sheet_name=ExcelWriter._sanitize_sheet_name(sheet_name), index=False, freeze_panes=(1, 0))
                else:
                    df.to_excel(writer, sheet_name=ExcelWriter._sanitize_sheet_name(sheet_name), index=False)
        except Exception as e:
            # Defensive fallback: ensure at least one visible sheet exists
            logger.warning(f"Retrying Excel write with empty sheet due to error: {e}")
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                pd.DataFrame().to_excel(writer, sheet_name=ExcelWriter._sanitize_sheet_name(sheet_name or 'Sheet1'), index=False)
    
    @staticmethod
    def _write_streaming(df: pd.DataFrame,
                        output_path: Path,
                        sheet_name: str,
                        chunk_size: int,
                        progress_callback: Optional[Callable],
                        summary: Optional[Dict[str, Any]] = None) -> None:
        """Streaming write for large files"""
        total_rows = len(df)
        
        try:
            # Try xlsxwriter first for better memory efficiency
            with pd.ExcelWriter(output_path, engine='xlsxwriter',
                              engine_kwargs={
                                  'options': {
                                      'constant_memory': True,
                                      'strings_to_urls': False,
                                      'strings_to_formulas': False
                                  }
                              }) as writer:
                
                workbook = writer.book
                # Optional summary sheet (key/value pairs)
                if summary:
                    sum_ws = workbook.add_worksheet(ExcelWriter._sanitize_sheet_name('Summary'))
                    row = 0
                    for k, v in summary.items():
                        sum_ws.write(row, 0, str(k))
                        sum_ws.write(row, 1, '' if pd.isna(v) else v)
                        row += 1
                worksheet = workbook.add_worksheet(ExcelWriter._sanitize_sheet_name(sheet_name))
                
                # Write headers
                for col_num, col_name in enumerate(df.columns):
                    worksheet.write(0, col_num, col_name)
                
                # Write data in chunks
                for start_idx in range(0, total_rows, chunk_size):
                    end_idx = min(start_idx + chunk_size, total_rows)
                    chunk = df.iloc[start_idx:end_idx]
                    
                    if progress_callback:
                        progress = int((end_idx / total_rows) * 100)
                        progress_callback(progress, f"Writing rows {start_idx:,} to {end_idx:,}")
                    
                    # Write chunk
                    for row_idx, (_, row) in enumerate(chunk.iterrows()):
                        excel_row = start_idx + row_idx + 1  # +1 for header
                        for col_idx, value in enumerate(row):
                            if pd.isna(value):
                                continue
                            worksheet.write(excel_row, col_idx, value)
                
        except ImportError:
            # Fallback to openpyxl if xlsxwriter not available
            logger.warning("xlsxwriter not available, using openpyxl")
            ExcelWriter._write_simple(df, output_path, sheet_name, progress_callback)
    
    @staticmethod
    def _write_multi_sheet(df: pd.DataFrame,
                          output_path: Path,
                          chunk_size: int,
                          progress_callback: Optional[Callable],
                          summary: Optional[Dict[str, Any]] = None) -> None:
        """Write to multiple sheets when exceeding Excel limits"""
        total_rows = len(df)
        rows_per_sheet = ExcelWriter.EXCEL_MAX_ROWS - 1  # -1 for header
        num_sheets = (total_rows // rows_per_sheet) + (1 if total_rows % rows_per_sheet else 0)
        
        logger.info(f"Splitting {total_rows:,} rows into {num_sheets} sheets")
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Optional summary sheet
                if summary:
                    sdf = pd.DataFrame([summary])
                    sdf.to_excel(writer, sheet_name=ExcelWriter._sanitize_sheet_name('Summary'), index=False)
                if num_sheets == 0:
                    # Ensure at least one sheet exists even when total_rows is 0
                    pd.DataFrame().to_excel(writer, sheet_name='Sheet1', index=False)
                    return
                for sheet_num in range(num_sheets):
                    start_row = sheet_num * rows_per_sheet
                    end_row = min(start_row + rows_per_sheet, total_rows)
                    sheet_df = df.iloc[start_row:end_row]
                    sheet_name = f'Sheet{sheet_num + 1}'

                    if progress_callback:
                        progress = int(((sheet_num + 1) / num_sheets) * 100)
                        progress_callback(progress, f"Writing {sheet_name}: rows {start_row:,} to {end_row:,}")

                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False, freeze_panes=(1, 0))

                    logger.info(f"Written {sheet_name}: rows {start_row:,} to {end_row:,}")
        except Exception as e:
            logger.warning(f"Retrying multi-sheet export with empty sheet due to error: {e}")
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                pd.DataFrame().to_excel(writer, sheet_name='Sheet1', index=False)
    
    @staticmethod
    def validate_output_path(output_path: Union[str, Path]) -> Path:
        """Validate and prepare output path.

        Rules:
        - Resolve to an absolute path.
        - Create parent directory if needed.
        """
        p = Path(output_path)

        # Normalize path: resolve to absolute
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (Path.cwd() / p).resolve()

        parent = resolved.parent

        # Create parent directory if it doesn't exist
        parent.mkdir(parents=True, exist_ok=True)

        # Proactive permission check: directory must be writable
        try:
            test_path = parent / f".pulsar_write_test_{os.getpid()}_{uuid.uuid4().hex}"
            with open(test_path, 'wb') as _f:
                _f.write(b'')
            # Clean up
            try:
                test_path.unlink(missing_ok=True)
            except Exception:
                pass
        except Exception as e:
            raise PermissionError(f"Output directory is not writable: '{parent}' ({e})")

        # Warn on overwrite
        if resolved.exists():
            logger.warning(f"Output file already exists: {resolved}")

        return resolved
    
    @staticmethod
    def _sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Sanitize DataFrame to ensure Excel compatibility"""
        # Create a copy to avoid modifying original
        df_copy = df.copy()

        # Try to convert date strings to datetime
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO datetime
        ]

        for col in df_copy.columns:
            if df_copy[col].dtype == 'object':  # String columns
                # Try date conversion for string columns
                for pattern in date_patterns:
                    mask = df_copy[col].astype(str).str.match(pattern, na=False)
                    if mask.any():
                        try:
                            df_copy.loc[mask, col] = pd.to_datetime(df_copy.loc[mask, col])
                        except:
                            pass  # Keep as string if conversion fails
                        break
                
                # Replace null characters
                if df_copy[col].dtype == 'object':  # Still string after date attempt
                    s = df_copy[col].astype(str)
                    # Remove illegal control characters for Excel (0x00-0x08, 0x0B-0x0C, 0x0E-0x1F)
                    import re
                    illegal = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")
                    s = s.str.replace(illegal, '', regex=True)
                    # Excel has issues with strings starting with =, +, -, @ (injection)
                    s = s.apply(lambda x: "'" + x if x.startswith(('=', '+', '-', '@')) else x)
                    df_copy[col] = s

        return df_copy
