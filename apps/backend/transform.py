import logging
import pandas as pd
from typing import Optional, Callable
import warnings
import datetime

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


def process_data_with_sql(
    df: pd.DataFrame,
    sql_query: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    table_name: str = "excel_file",
    progress_percent_callback: Optional[Callable[[int], None]] = None,
) -> pd.DataFrame:
    """
    Process catalog data using SQL query - just a pass-through to the SQL processor.

    Args:
        df: Input catalog data
        sql_query: SQL query to execute
        progress_callback: Optional callback for progress updates (fraction, message)
        table_name: Name to use for the table in SQL (default: 'excel_file')
        progress_percent_callback: Optional callback for percentage updates (0-100)

    Returns:
        pd.DataFrame: Query results with only the columns selected in SQL
    """
    from redshift_sql_processor import RedshiftSQLProcessor

    try:
        if progress_callback:
            progress_callback(0.0, "Initializing SQL engine...")
        if progress_percent_callback:
            progress_percent_callback(0)

        # Create processor
        processor = RedshiftSQLProcessor()

        try:
            if progress_callback:
                progress_callback(0.2, "Preparing data for SQL...")
            if progress_percent_callback:
                progress_percent_callback(20)

            # Execute SQL with simulated progress
            # Since DuckDB doesn't provide progress callbacks, we'll simulate it
            if progress_callback:
                progress_callback(0.4, "Executing SQL query...")
            if progress_percent_callback:
                progress_percent_callback(40)

            # Pass the table_name to execute_sql
            result = processor.execute_sql(sql_query, df, table_name)

            if progress_callback:
                progress_callback(0.8, "Finalizing results...")
            if progress_percent_callback:
                progress_percent_callback(80)

            logger.info(f"SQL query executed: {len(result)} rows, {len(result.columns)} columns")

            if progress_callback:
                progress_callback(1.0, f"SQL complete: {len(result):,} rows")
            if progress_percent_callback:
                progress_percent_callback(100)

            return result
        finally:
            # Always close the processor to free resources
            processor.close()
    except Exception as e:
        logger.error(f"SQL processing failed: {str(e)}")
        raise


def save_dataframe(df: pd.DataFrame, output_path: str, format: str = "excel", chunk_size: int = 50000) -> None:
    """Save dataframe to file in specified format with streaming for large files"""
    try:
        total_rows = len(df)

        if format.lower() == "excel":
            # Excel has a hard limit of 1,048,576 rows
            EXCEL_MAX_ROWS = 1048576

            if total_rows >= EXCEL_MAX_ROWS:
                logger.warning(
                    f"Dataset has {total_rows:,} rows, which exceeds Excel's maximum of {EXCEL_MAX_ROWS:,} rows"
                )
                logger.info("Automatically splitting into multiple sheets or saving as CSV")

                # Option 1: Split into multiple sheets (if less than 10 million rows)
                if total_rows < EXCEL_MAX_ROWS * 10:
                    try:
                        num_sheets = (total_rows // (EXCEL_MAX_ROWS - 1)) + 1
                        logger.info(f"Splitting data into {num_sheets} sheets")

                        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                            for sheet_num in range(num_sheets):
                                start_row = sheet_num * (EXCEL_MAX_ROWS - 1)
                                end_row = min(start_row + EXCEL_MAX_ROWS - 1, total_rows)
                                sheet_df = df.iloc[start_row:end_row]
                                sheet_name = f"Sheet{sheet_num + 1}"
                                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                                logger.info(f"Written {sheet_name}: rows {start_row:,} to {end_row:,}")

                        logger.info(
                            f"Successfully saved {total_rows:,} rows to {output_path} across {num_sheets} sheets"
                        )
                        return
                    except Exception as e:
                        logger.error(f"Multi-sheet Excel write failed: {e}")

                # Fall back to CSV for extremely large files
                logger.info("Dataset too large for Excel, saving as CSV instead")
                csv_path = output_path.replace(".xlsx", ".csv")
                save_dataframe(df, csv_path, format="csv", chunk_size=chunk_size)
                raise Exception(
                    f"Dataset exceeds Excel limits ({total_rows:,} rows > {EXCEL_MAX_ROWS:,}), saved as CSV: {csv_path}"
                )

            # For large but within Excel limits, use streaming approach
            elif total_rows > 100000:
                logger.info(f"Large dataset ({total_rows:,} rows), using streaming Excel write")
                try:
                    with pd.ExcelWriter(
                        output_path,
                        engine="xlsxwriter",
                        engine_kwargs={
                            "options": {"constant_memory": True, "strings_to_urls": False, "strings_to_formulas": False}
                        },
                    ) as writer:
                        workbook = writer.book
                        worksheet = workbook.add_worksheet("Sheet1")

                        # Write headers
                        for col_num, col_name in enumerate(df.columns):
                            worksheet.write(0, col_num, col_name)

                        # Write data in chunks using vectorized operations
                        for start_idx in range(0, total_rows, chunk_size):
                            end_idx = min(start_idx + chunk_size, total_rows)
                            chunk = df.iloc[start_idx:end_idx]

                            # Convert chunk to numpy array for faster access
                            chunk_values = chunk.to_numpy()

                            # Write chunk data using numpy array
                            for row_idx in range(len(chunk_values)):
                                excel_row = start_idx + row_idx + 1  # +1 for header row
                                row_data = chunk_values[row_idx]

                                for col_idx, value in enumerate(row_data):
                                    # Handle different data types and potential issues
                                    if pd.isna(value):
                                        worksheet.write_blank(excel_row, col_idx, None)
                                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                                        worksheet.write_number(excel_row, col_idx, value)
                                    elif isinstance(value, bool):
                                        worksheet.write_boolean(excel_row, col_idx, value)
                                    elif isinstance(value, (pd.Timestamp, datetime.datetime)):
                                        worksheet.write_datetime(excel_row, col_idx, value)
                                    else:
                                        # Convert to string and handle any special cases
                                        str_value = str(value)
                                        # Truncate very long strings to avoid Excel issues
                                        if len(str_value) > 32767:  # Excel cell character limit
                                            str_value = str_value[:32764] + "..."
                                        worksheet.write_string(excel_row, col_idx, str_value)

                            if start_idx % (chunk_size * 5) == 0:  # Log every 5 chunks
                                logger.info(f"Written {end_idx:,}/{total_rows:,} rows ({end_idx/total_rows*100:.1f}%)")

                        logger.info(f"Successfully saved {total_rows:,} rows to {output_path}")
                except Exception as e:
                    logger.error(f"Streaming Excel write failed: {e}")
                    # Fall back to CSV for very large files
                    logger.info("Falling back to CSV for large file due to Excel write error")
                    csv_path = output_path.replace(".xlsx", ".csv")
                    save_dataframe(df, csv_path, format="csv", chunk_size=chunk_size)
                    raise Exception(f"Excel export failed ({str(e)}), saved as CSV instead: {csv_path}")
            else:
                # Regular Excel save for smaller files
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning)
                        # Newer xlsxwriter versions use engine_kwargs
                        with pd.ExcelWriter(
                            output_path,
                            engine="xlsxwriter",
                            engine_kwargs={"options": {"strings_to_urls": False, "strings_to_formulas": False}},
                        ) as writer:
                            df.to_excel(writer, index=False, sheet_name="Sheet1")
                    logger.info(f"Saved {len(df)} rows to {output_path} using xlsxwriter")
                except Exception as xlsxwriter_error:
                    logger.warning(f"xlsxwriter failed: {str(xlsxwriter_error)}, trying openpyxl")
                    try:
                        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                            df.to_excel(writer, index=False, sheet_name="Sheet1")
                        logger.info(f"Saved {len(df)} rows to {output_path} using openpyxl")
                    except Exception:
                        logger.error("Both Excel engines failed")
                        csv_path = output_path.replace(".xlsx", ".csv")
                        df.to_csv(csv_path, index=False)
                        raise Exception(f"Excel save failed, saved as CSV instead: {csv_path}")

        elif format.lower() == "csv":
            # Stream CSV writing for large files
            if total_rows > 100000:
                logger.info(f"Large dataset ({total_rows:,} rows), using streaming CSV write")
                df.to_csv(output_path, index=False, chunksize=chunk_size)
            else:
                df.to_csv(output_path, index=False)
            logger.info(f"Saved {total_rows:,} rows to {output_path}")

        elif format.lower() == "tsv":
            if total_rows > 100000:
                df.to_csv(output_path, sep="\t", index=False, chunksize=chunk_size)
            else:
                df.to_csv(output_path, sep="\t", index=False)
            logger.info(f"Saved {total_rows:,} rows to {output_path}")
        else:
            raise ValueError(f"Unsupported format: {format}")
    except Exception as e:
        logger.error(f"Failed to save data: {str(e)}")
        raise
