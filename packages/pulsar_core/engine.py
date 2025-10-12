"""
Main JSON to Excel conversion engine
"""
import os
import math
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
import pandas as pd

from .json_parser import JsonParser
from .json_parser_v2 import JsonParserV2
from .excel_writer import ExcelWriter
from .json_normalizer import JsonNormalizer
try:
    from .json_streamer import JsonStreamer
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False

logger = logging.getLogger(__name__)


class JsonToExcelEngine:
    """
    Core engine for JSON to Excel conversion
    
    This class provides a clean API that can be used standalone or integrated
    into other systems like the Data Tool.
    """
    
    def __init__(self):
        self.json_parser = JsonParser()
        self.json_parser_v2 = JsonParserV2()
        self.excel_writer = ExcelWriter()
        self.json_normalizer = JsonNormalizer()
        self._current_data = None
        self._current_df = None
        self._metadata = {}
        self._normalization_mode = 'flatten'  # 'flatten' or 'normalize'
        self._expand_arrays = True  # New option for array expansion
        self._detected_arrays = {}  # Store detected arrays info
        # Soft performance guard: if estimated rows exceed this threshold when
        # expanding arrays via cross-product, auto-safe fallback engages.
        # Can be overridden via environment variable PULSAR_AUTO_SAFE_THRESHOLD.
        try:
            env_threshold = int(os.getenv("PULSAR_AUTO_SAFE_THRESHOLD", "100000"))
        except ValueError:
            env_threshold = 100_000
        self._AUTO_SAFE_ROW_THRESHOLD = max(1, env_threshold)
        # Allow disabling auto-safe via env (PULSAR_AUTO_SAFE=false)
        self._AUTO_SAFE_ENABLED_DEFAULT = os.getenv("PULSAR_AUTO_SAFE", "true").lower() != "false"
        # Optional memory soft limit (MB) to decide fail-fast or fallback
        try:
            env_mem = int(os.getenv("PULSAR_MEMORY_SOFT_LIMIT_MB", "0"))
        except ValueError:
            env_mem = 0
        self._MEMORY_SOFT_LIMIT_MB = env_mem if env_mem > 0 else None

    @staticmethod
    def _quick_size_estimate(data: Any, limit: int) -> int:
        """Conservative upper-bound estimate by multiplying lengths of lists encountered.

        Short-circuits when product reaches limit.
        """
        product = 1

        def walk(obj: Any):
            nonlocal product
            if product >= limit:
                return
            if isinstance(obj, list):
                try:
                    n = len(obj) or 1
                except Exception:
                    n = 1
                product *= n
                for it in obj[:2]:  # sample a few items
                    walk(it)
            elif isinstance(obj, dict):
                for v in obj.values():
                    walk(v)

        walk(data)
        return product

    @staticmethod
    def _estimate_rows(data: Any, threshold: int = 100_000, max_inspect: int = 2) -> int:
        """Roughly estimate expanded row count, with early cutoff.

        Heuristic rules:
        - For dict: multiply factors of values.
        - For list: multiply by length, then inspect up to max_inspect items to account for nested arrays.
        - For scalars: factor 1.
        Overestimates are fine (we only use this to decide fallbacks).
        """
        estimate = 1

        def rec(obj: Any):
            nonlocal estimate
            if estimate >= threshold:
                return
            if isinstance(obj, dict):
                for v in obj.values():
                    rec(v)
                    if estimate >= threshold:
                        return
            elif isinstance(obj, list):
                try:
                    length = len(obj)
                except Exception:
                    length = 1
                estimate *= max(1, length)
                # Inspect a few items to catch nested arrays
                for item in obj[:max_inspect]:
                    rec(item)
                    if estimate >= threshold:
                        return
            else:
                return

        rec(data)
        return estimate
    
    @staticmethod
    def _strip_indices(name: str) -> str:
        """Remove array index tokens like [0] from a column path."""
        import re
        return re.sub(r"\[\d+\]", "", name)

    @staticmethod
    def _select_columns(df: pd.DataFrame,
                        patterns: Optional[List[str]],
                        preserve_indices: bool = False) -> List[str]:
        """Select columns from df using patterns with index-aware matching.

        Rules:
        - Supports exact names and simple prefix wildcard with trailing '*'.
        - If preserve_indices=True, patterns without indices (e.g., users.name)
          match columns that have indices (e.g., users[0].name). Matching is
          performed against an index-stripped view of column names and then
          mapped back to actual columns in original order.
        - Also accepts patterns containing explicit indices or [*]/[] which are
          treated as index-agnostic and match any numeric index.
        """
        if not patterns:
            return list(df.columns)

        cols = list(df.columns)
        deindexed = [JsonToExcelEngine._strip_indices(c) for c in cols]

        selected: List[str] = []
        for pattern in patterns:
            # Normalize wildcard prefix patterns X*
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                if preserve_indices:
                    for c, d in zip(cols, deindexed):
                        if d.startswith(prefix):
                            selected.append(c)
                else:
                    selected.extend([c for c in cols if c.startswith(prefix)])
                continue

            # Handle explicit [*] or [] in pattern as index-agnostic
            pat = pattern.replace('[*]', '').replace('[]', '')

            if preserve_indices:
                if pattern in cols:
                    selected.append(pattern)
                    continue
                for c, d in zip(cols, deindexed):
                    if d == pat:
                        selected.append(c)
            else:
                if pattern in cols:
                    selected.append(pattern)

        # Deduplicate while preserving order
        seen = set()
        return [c for c in selected if not (c in seen or seen.add(c))]

    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        """Sanitize sheet name using ExcelWriter's implementation for consistency."""
        return ExcelWriter._sanitize_sheet_name(name)

    @staticmethod
    def _adapt_patterns_for_array(patterns: List[str], array_path: Optional[str]) -> List[str]:
        """Expand patterns to also include variants relative to the array path.

        If a pattern starts with the array_path prefix, also include a version
        with that prefix removed so it can match columns flattened relative to
        the array root.
        """
        if not array_path or array_path == '(root)':
            return patterns
        out: List[str] = []
        prefix = f"{array_path}."
        for p in patterns:
            out.append(p)
            if p.startswith(prefix):
                out.append(p[len(prefix):])
        # Deduplicate while preserving order
        seen = set()
        return [p for p in out if not (p in seen or seen.add(p))]
    
    def load_json(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load JSON file and analyze structure
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Dictionary with:
                - success: bool
                - data: loaded JSON data
                - structure: analyzed structure
                - columns: available column paths
                - preview: first few rows as DataFrame
                - error: error message if failed
        """
        try:
            # Load JSON
            data = self.json_parser.load_json(file_path)
            # Validate root type early
            if not isinstance(data, (dict, list)):
                raise ValueError("Unsupported JSON root type (expected object or array)")
            self._current_data = data
            
            # Analyze structure
            structure = self.json_parser.analyze_structure(data)
            
            # Detect all data arrays
            self._detected_arrays = self.json_parser_v2.detect_data_arrays(data)
            
            # Create a full flattened version to get actual columns
            # Check if this looks like feed.json structure
            if isinstance(data, dict) and 'messages' in data and 'header' in data:
                # Use specialized normalizer for feed structure
                full_df = self.json_normalizer.normalize_feed_json(data)
                self._normalization_mode = 'normalize'
            else:
                # Use JsonParserV2 for more robust flattening (handles arrays of scalars better)
                full_df = self.json_parser_v2.flatten_with_array_expansion(data, expand_arrays=True, preserve_indices=False)
                self._normalization_mode = 'flatten'
            
            actual_columns = full_df.columns.tolist()
            
            # Store the flattened data for later use
            self._current_df = full_df
            
            # Create preview (first 10 rows)
            preview_df = full_df.head(10)
            
            # Determine actual record count
            if isinstance(data, dict):
                # Check if we found a data array
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        total_records = len(value)
                        break
                else:
                    total_records = 1
            else:
                total_records = len(data) if isinstance(data, list) else 1
            
            # Store metadata
            self._metadata = {
                'file_path': str(file_path),
                'total_records': len(full_df),  # Use actual flattened row count
                'columns_available': len(actual_columns),
                'structure_type': 'array' if isinstance(data, list) else 'object'
            }
            
            return {
                'success': True,
                'data': data,
                'structure': structure,
                'columns': actual_columns,  # Use actual flattened columns
                'preview': preview_df,
                'metadata': self._metadata,
                'detected_arrays': self._detected_arrays  # Include detected arrays
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format in '{file_path}': {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except FileNotFoundError:
            error_msg = f"File not found: '{file_path}'"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Failed to load JSON from '{file_path}': {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def flatten(self, 
               columns: Optional[List[str]] = None,
               max_depth: Optional[int] = None,
               expand_arrays: Optional[bool] = None,
               preserve_indices: Optional[bool] = None,
               progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
        """
        Flatten JSON data with selected columns
        
        Args:
            columns: List of column paths to include (None for all)
            max_depth: Maximum nesting depth to flatten
            progress_callback: Optional callback(percent, message)
            
        Returns:
            Dictionary with:
                - success: bool
                - dataframe: flattened DataFrame
                - rows: number of rows
                - columns: number of columns
                - error: error message if failed
        """
        try:
            if self._current_data is None:
                raise ValueError("No JSON data loaded. Call load_json() first.")
            
            if progress_callback:
                progress_callback(0, "Starting flattening process...")
            
            # Ensure array detection is populated even if load_json() wasn't called
            if not self._detected_arrays and self._current_data is not None:
                try:
                    self._detected_arrays = self.json_parser_v2.detect_data_arrays(self._current_data)
                except Exception:
                    self._detected_arrays = {}

            # If we already have normalized data, just filter columns
            if self._current_df is not None and self._normalization_mode == 'normalize':
                df = self._current_df
                # Apply column filtering if specified (make behavior consistent with flatten mode)
                if columns:
                    selected_cols = self._select_columns(df, columns, preserve_indices=bool(preserve_indices))
                    if selected_cols:
                        df = df[selected_cols]
                method = 'normalize'
            else:
                # Flatten the data
                use_expand_arrays = expand_arrays if expand_arrays is not None else self._expand_arrays
                
                if use_expand_arrays:
                    # Warn if multiple arrays may cause explosive row growth
                    try:
                        est = self._estimate_rows(self._current_data, self._AUTO_SAFE_ROW_THRESHOLD)
                        if est >= self._AUTO_SAFE_ROW_THRESHOLD:
                            logger.warning(
                                "Detected many array combinations; falling back to non-expanding flatten in flatten(). "
                                "Use convert() for arrays-per-sheet auto-safe export."
                            )
                            # Fallback to non-expanding flatten to avoid timeouts when using flatten() directly
                            df = self.json_parser.flatten_json(
                                self._current_data,
                                max_depth=max_depth,
                                columns_to_include=columns
                            )
                            # Apply selection again to be safe
                            if columns:
                                sel = [c for c in df.columns if any(c.startswith(p.rstrip('*')) if p.endswith('*') else c == p for p in columns)]
                                if sel:
                                    df = df[sel]
                            self._current_df = df
                            if progress_callback:
                                progress_callback(100, "Flattening complete (safe fallback)")
                            return {
                                'success': True,
                                'dataframe': df,
                                'rows': len(df),
                                'columns': len(df.columns),
                                'column_names': df.columns.tolist(),
                                'method': 'non-expanding-fallback'
                            }
                        # Additional guard for very large root arrays
                        if isinstance(self._current_data, list) and len(self._current_data) >= self._AUTO_SAFE_ROW_THRESHOLD:
                            logger.warning("Large root array detected; falling back to non-expanding flatten in flatten().")
                            df = self.json_parser.flatten_json(
                                self._current_data,
                                max_depth=max_depth,
                                columns_to_include=columns
                            )
                            if columns:
                                sel = [c for c in df.columns if any(c.startswith(p.rstrip('*')) if p.endswith('*') else c == p for p in columns)]
                                if sel:
                                    df = df[sel]
                            self._current_df = df
                            if progress_callback:
                                progress_callback(100, "Flattening complete (safe fallback)")
                            return {
                                'success': True,
                                'dataframe': df,
                                'rows': len(df),
                                'columns': len(df.columns),
                                'column_names': df.columns.tolist(),
                                'method': 'non-expanding-fallback'
                            }
                    except Exception:
                        pass
                    # Use new parser with array expansion
                    try:
                        df = self.json_parser_v2.flatten_with_array_expansion(
                            self._current_data,
                            max_depth=max_depth,
                            expand_arrays=True,
                            preserve_indices=bool(preserve_indices)
                        )
                        method = 'expand-v2'
                    except Exception as e:
                        logger.warning(f"Array expansion failed ({e}); using non-expanding flatten as fallback")
                        df = self.json_parser.flatten_json(
                            self._current_data,
                            max_depth=max_depth,
                            columns_to_include=columns
                        )
                        method = 'flatten-v1-fallback'
                    # Apply column filtering if specified (index-aware)
                    if columns:
                        selected_cols = self._select_columns(df, columns, preserve_indices=bool(preserve_indices))
                        if selected_cols:
                            df = df[selected_cols]
                        else:
                            missing_cols = [p for p in columns if '*' not in p]
                            if missing_cols:
                                logger.warning(f"Requested columns not found: {missing_cols}")
                            logger.warning("None of the requested columns were found. Returning all columns.")
                            logger.info(
                                "Available columns: "
                                + ', '.join(df.columns.tolist()[:10])
                                + (" ..." if len(df.columns) > 10 else "")
                            )
                else:
                    # Use original parser
                    df = self.json_parser.flatten_json(
                        self._current_data,
                        max_depth=max_depth,
                        columns_to_include=columns
                    )
                    method = 'flatten-v1'
            
            self._current_df = df
            
            if progress_callback:
                progress_callback(100, "Flattening complete")
            
            return {
                'success': True,
                'dataframe': df,
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist(),
                'method': method if 'method' in locals() else 'flatten'
            }
            
        except Exception as e:
            logger.error(f"Failed to flatten JSON: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_to_excel(self,
                       output_path: Union[str, Path],
                       sheet_name: str = 'Sheet1',
                       chunk_size: int = 50000,
                       progress_callback: Optional[Callable[[int, str], None]] = None,
                       include_summary: bool = True) -> Dict[str, Any]:
        """
        Export flattened data to Excel
        
        Args:
            output_path: Output Excel file path
            sheet_name: Name of the Excel sheet
            chunk_size: Rows per chunk for large files
            progress_callback: Optional callback(percent, message)
            
        Returns:
            Dictionary with:
                - success: bool
                - output_path: final output path
                - rows_written: number of rows
                - sheets: number of sheets (if split)
                - error: error message if failed
        """
        try:
            if self._current_df is None:
                raise ValueError("No data to export. Call flatten() first.")
            
            # Validate output path
            output_path = self.excel_writer.validate_output_path(output_path)
            
            # Build summary for Summary sheet (optional)
            summary = None
            if include_summary:
                from datetime import datetime
                summary = {
                    'Input File': self._metadata.get('file_path'),
                    'Rows': len(self._current_df),
                    'Columns': len(self._current_df.columns),
                    'Sheet Name': sheet_name,
                    'Generated At': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
                }

            # Write to Excel
            self.excel_writer.write_excel(
                self._current_df,
                output_path,
                sheet_name=sheet_name,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
                summary=summary
            )
            
            # Calculate sheets if split
            rows = len(self._current_df)
            sheets = (rows // (self.excel_writer.EXCEL_MAX_ROWS - 1)) + 1 if rows >= self.excel_writer.EXCEL_MAX_ROWS else 1
            
            return {
                'success': True,
                'output_path': str(output_path),
                'rows_written': rows,
                'sheets': sheets
            }
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def convert(self,
               input_path: Union[str, Path],
               output_path: Union[str, Path],
               columns: Optional[List[str]] = None,
               max_depth: Optional[int] = None,
               sheet_name: str = 'Sheet1',
               expand_arrays: bool = True,
               preserve_indices: bool = False,
               use_streaming: Optional[bool] = None,
               stream_chunk_size: int = 10000,
               progress_callback: Optional[Callable[[int, str], None]] = None,
               auto_safe: bool = True,
               auto_safe_threshold: Optional[int] = None,
               memory_soft_limit_mb: Optional[int] = None,
               schema_path: Optional[Union[str, Path]] = None,
               include_summary: bool = True) -> Dict[str, Any]:
        """
        One-shot conversion from JSON to Excel
        
        Args:
            input_path: Input JSON file path
            output_path: Output Excel file path
            columns: Optional list of columns to include
            max_depth: Maximum nesting depth
            sheet_name: Excel sheet name
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with conversion results
        """
        try:
            # Check file size to decide on streaming
            file_size = Path(input_path).stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            # Auto-detect streaming need if not specified
            if use_streaming is None:
                use_streaming = size_mb > 100 and STREAMING_AVAILABLE  # Use streaming for files > 100MB
            
            # Use streaming for large files if available
            if use_streaming and STREAMING_AVAILABLE:
                if progress_callback:
                    progress_callback(5, f"Using streaming mode for large file ({size_mb:.1f} MB)...")
                
                result = JsonStreamer.convert_streaming(
                    input_path,
                    output_path,
                    chunk_size=stream_chunk_size,
                    max_depth=max_depth,
                    progress_callback=progress_callback,
                    include_summary=include_summary
                )
                
                if result['success']:
                    return {
                        'success': True,
                        'input_file': str(input_path),
                        'output_file': result['output_path'],
                        'rows': result['rows_written'],
                        'columns': result['columns'],
                        'sheets': 1,
                        'method': 'streaming'
                    }
                else:
                    return result
            
            # Standard loading for smaller files
            if progress_callback:
                progress_callback(10, "Loading JSON file...")
            
            load_result = self.load_json(input_path)
            if not load_result['success']:
                return load_result

            # Optional JSON Schema validation (file path or builtin:name)
            if schema_path:
                try:
                    from jsonschema import validate as _validate
                    schema = None
                    sp = str(schema_path)
                    if sp.startswith('builtin:'):
                        from .schemas import BUILTIN_SCHEMAS
                        key = sp.split(':', 1)[1].strip()
                        schema = BUILTIN_SCHEMAS.get(key)
                        if not schema:
                            return {'success': False, 'error': f"Unknown builtin schema '{key}'."}
                    else:
                        import json as _json
                        with open(sp, 'r', encoding='utf-8') as sf:
                            schema = _json.load(sf)
                    _validate(instance=self._current_data, schema=schema)
                except ImportError:
                    return {'success': False, 'error': 'jsonschema not installed. Install with: pip install jsonschema or use extras: pip install .[schema]'}
                except Exception as ve:
                    logger.error(f"Schema validation failed: {ve}")
                    return {'success': False, 'error': f'Schema validation failed: {ve}'}

            # Optional memory soft limit check before heavy processing
            eff_mem_limit = memory_soft_limit_mb or self._MEMORY_SOFT_LIMIT_MB
            if eff_mem_limit:
                used = self._get_memory_usage_mb()
                if used is not None and used >= 0.9 * eff_mem_limit:
                    if auto_safe:
                        if progress_callback:
                            progress_callback(30, 'Memory near limit; exporting arrays to separate sheets')
                        pa_result = self.process_all_arrays(output_path, preserve_indices=preserve_indices, columns=columns, progress_callback=progress_callback)
                        if pa_result.get('success'):
                            sheets = pa_result.get('sheets_written', [])
                            total_rows = sum(s.get('rows', 0) for s in sheets)
                            max_cols = max((s.get('columns', 0) for s in sheets), default=0)
                            return {
                                'success': True,
                                'input_file': str(input_path),
                                'output_file': pa_result['output_path'],
                                'rows': total_rows,
                                'columns': max_cols,
                                'sheets': len(sheets),
                                'method': 'arrays-per-sheet'
                            }
                        else:
                            return pa_result
                    else:
                        return {'success': False, 'error': f'Memory usage {used}MB exceeds soft limit {eff_mem_limit}MB and auto-safe is disabled.'}
            
            # Auto-safe fallback: avoid cartesian explosion by exporting arrays to separate sheets
            # Respect provided threshold; fallback to configured default
            threshold = int(auto_safe_threshold) if auto_safe_threshold is not None else self._AUTO_SAFE_ROW_THRESHOLD
            if auto_safe is None:
                auto_safe = self._AUTO_SAFE_ENABLED_DEFAULT
            if expand_arrays:
                try:
                    # Use robust estimator instead of relying on detected arrays only
                    product_size = self._estimate_rows(self._current_data, threshold)
                    # Combine with a conservative product to avoid underestimation edge cases
                    product_size = max(product_size, self._quick_size_estimate(self._current_data, threshold))

                    # Hard guard as well: never attempt to exceed Excel limits
                    exceeds_excel = product_size >= self.excel_writer.EXCEL_MAX_ROWS
                    exceeds_soft = product_size >= threshold

                    if (auto_safe and (exceeds_soft or exceeds_excel)):
                        if progress_callback:
                            progress_callback(35, "Large array combinations detected; exporting arrays to separate sheets")
                        pa_result = self.process_all_arrays(
                            output_path,
                            preserve_indices=preserve_indices,
                            columns=columns,
                            progress_callback=progress_callback
                        )
                        if pa_result.get('success'):
                            sheets = pa_result.get('sheets_written', [])
                            total_rows = sum(s.get('rows', 0) for s in sheets)
                            max_cols = max((s.get('columns', 0) for s in sheets), default=0)
                            return {
                                'success': True,
                                'input_file': str(input_path),
                                'output_file': pa_result['output_path'],
                                'rows': total_rows,
                                'columns': max_cols,
                                'sheets': len(sheets),
                                'method': 'arrays-per-sheet'
                            }
                        else:
                            return pa_result
                    elif (not auto_safe) and (exceeds_soft or exceeds_excel):
                        # Fail fast to avoid timeouts when auto-safe disabled
                        return {
                            'success': False,
                            'error': (
                                f"Estimated expanded rows ({product_size:,}) exceed safe threshold ({threshold:,}). "
                                "Enable auto-safe mode or use --all-arrays/filters/max-depth."
                            )
                        }
                except Exception:
                    # If any issue in estimation, proceed with normal flow
                    pass

            # Flatten
            if progress_callback:
                progress_callback(40, "Flattening JSON structure...")
            
            flatten_result = self.flatten(columns=columns, max_depth=max_depth, expand_arrays=expand_arrays, preserve_indices=preserve_indices)
            if not flatten_result['success']:
                return flatten_result
            
            # Export
            if progress_callback:
                progress_callback(70, "Writing to Excel...")
            
            export_result = self.export_to_excel(
                output_path,
                sheet_name=sheet_name,
                progress_callback=lambda p, m: progress_callback(70 + int(p * 0.3), m) if progress_callback else None,
                include_summary=include_summary
            )
            
            if not export_result['success']:
                return export_result
            
            if progress_callback:
                progress_callback(100, "Conversion complete!")
            
            return {
                'success': True,
                'input_file': str(input_path),
                'output_file': export_result['output_path'],
                'rows': export_result['rows_written'],
                'columns': flatten_result['columns'],
                'sheets': export_result['sheets'],
                'method': flatten_result.get('method', 'convert')
            }
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_current_dataframe(self) -> Optional[pd.DataFrame]:
        """Get the current flattened DataFrame"""
        return self._current_df
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the current data"""
        return self._metadata.copy()
    
    def get_detected_arrays(self) -> Dict[str, Any]:
        """Get information about detected arrays in the JSON"""
        return self._detected_arrays.copy()

    @staticmethod
    def _get_memory_usage_mb() -> Optional[int]:
        """Best-effort current process memory usage in MB (psutil if available)."""
        try:
            import psutil
            process = psutil.Process()
            return int(process.memory_info().rss / (1024 * 1024))
        except Exception:
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                # On Linux, ru_maxrss is in KB; on macOS it's bytes
                if usage < 10_000_000:  # likely KB
                    return int(usage / 1024)
                return int(usage / (1024 * 1024))
            except Exception:
                return None
    
    def process_all_arrays(self,
                         output_path: Union[str, Path],
                         sheet_prefix: str = 'Array',
                         preserve_indices: bool = False,
                         columns: Optional[List[str]] = None,
                         progress_callback: Optional[Callable[[int, str], None]] = None,
                         include_index: bool = True) -> Dict[str, Any]:
        """
        Process all detected arrays into separate Excel sheets
        
        Args:
            output_path: Output Excel file path
            sheet_prefix: Prefix for sheet names
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with results
        """
        try:
            if not self._detected_arrays:
                return {
                    'success': False,
                    'error': 'No arrays detected in the JSON data'
                }
            
            # Validate output path and write via atomic temp file
            output_path = Path(self.excel_writer.validate_output_path(output_path))
            import os, uuid
            temp_path = output_path.with_suffix(output_path.suffix + f".tmp-{os.getpid()}-{uuid.uuid4().hex}")

            sheets_written = []

            # Acquire a simple lock to avoid concurrent clobbering
            lock_path = output_path.with_suffix(output_path.suffix + '.lock')
            lock_fd = None
            try:
                for _ in range(20):
                    try:
                        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        break
                    except FileExistsError:
                        import time
                        time.sleep(0.1)

                with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
                    # Optional index sheet mapping sheet names to array paths
                    if include_index:
                        try:
                            index_df = pd.DataFrame([
                                {'sheet_name': self._sanitize_sheet_name(f"{sheet_prefix}_{i+1}"),
                                 'array_path': ap,
                                 'rows': info.get('length', None)}
                                for i, (ap, info) in enumerate(self._detected_arrays.items())
                            ])
                            if not index_df.empty:
                                index_df.to_excel(writer, sheet_name=self._sanitize_sheet_name('Index'), index=False)
                        except Exception:
                            # Non-fatal; continue without index sheet
                            pass
                    used_names = set()
                    for idx, (array_path, array_info) in enumerate(self._detected_arrays.items()):
                        if progress_callback:
                            progress = int((idx / len(self._detected_arrays)) * 100)
                            progress_callback(progress, f"Processing array: {array_path}")
                    
                    # Flatten the specific array
                    df = self.json_parser_v2.flatten_specific_array(
                        self._current_data,
                        array_path=array_path if array_path != '(root)' else None,
                        include_parent_data=True,
                        preserve_indices=preserve_indices
                    )
                    
                    # Always use safe, deterministic sheet names to avoid invalid characters from JSON keys
                    # Keep a mapping via sheets_written for user reference.
                    base_safe = self._sanitize_sheet_name(sheet_prefix)
                    candidate = f"{base_safe}_{idx+1}"
                    candidate = self._sanitize_sheet_name(candidate)
                    # Ensure uniqueness just in case
                    if candidate in used_names:
                        counter = 2
                        while True:
                            c2 = self._sanitize_sheet_name(f"{base_safe}_{idx+1}_{counter}")
                            if c2 not in used_names:
                                candidate = c2
                                break
                            counter += 1
                    used_names.add(candidate)
                    sheet_name = candidate
                    
                    # Optional column filtering per sheet
                    if columns:
                        adj_patterns = self._adapt_patterns_for_array(columns, None if array_path == '(root)' else array_path)
                        selected_cols = self._select_columns(df, adj_patterns, preserve_indices=preserve_indices)
                        if selected_cols:
                            df = df[selected_cols]

                    # Write to Excel with sanitized final name
                    safe_name = self._sanitize_sheet_name(sheet_name)
                    try:
                        df.to_excel(writer, sheet_name=safe_name, index=False)
                    except Exception:
                        # As a last resort, use a deterministic fallback name
                        fallback = self._sanitize_sheet_name(f"{base_safe}_{idx+1}")
                        df.to_excel(writer, sheet_name=fallback, index=False)
                    sheets_written.append({
                        'sheet_name': sheet_name,
                        'array_path': array_path,
                        'rows': len(df),
                        'columns': len(df.columns)
                    })
                # Ensure at least one visible sheet exists
                if not sheets_written:
                    pd.DataFrame().to_excel(writer, sheet_name='Sheet1', index=False)
            
                if progress_callback:
                    progress_callback(100, "All arrays processed")

                # Atomic replace
                Path(temp_path).replace(output_path)

            finally:
                # Release lock
                try:
                    if lock_fd is not None:
                        os.close(lock_fd)
                except Exception:
                    pass
                try:
                    Path(lock_path).unlink(missing_ok=True)
                except Exception:
                    pass

            return {
                'success': True,
                'output_path': str(output_path),
                'sheets_written': sheets_written
            }
            
        except Exception as e:
            logger.error(f"Failed to process all arrays: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear(self) -> None:
        """Clear all loaded data"""
        self._current_data = None
        self._current_df = None
        self._metadata = {}
        self._detected_arrays = {}

    def coalesce_duplicate_columns(self, df: Optional[pd.DataFrame] = None, strip_indices: bool = True) -> pd.DataFrame:
        """Coalesce duplicate logical columns by taking first non-null value.

        - If df is None, uses current dataframe.
        - If strip_indices=True, treats index tokens (e.g., [0]) and
          numeric suffixes (e.g., _1) as variants of the same base column.
        Returns a new DataFrame with unique logical column names.
        """
        if df is None:
            if self._current_df is None:
                raise ValueError("No dataframe available. Call flatten() first or pass df.")
            df = self._current_df

        import re

        def base(name: str) -> str:
            if not strip_indices:
                return name
            n = re.sub(r"\[\d+\]", "", name)
            n = re.sub(r"_\d+$", "", n)
            return n

        ordered = list(df.columns)
        logical = list(dict.fromkeys(base(c) for c in ordered))
        out = {}
        for b in logical:
            members = [c for c in ordered if base(c) == b]
            if len(members) == 1:
                out[b] = df[members[0]]
            else:
                out[b] = df[members].bfill(axis=1).iloc[:, 0]
        return pd.DataFrame(out)
