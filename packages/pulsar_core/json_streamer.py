"""
Streaming JSON parser for handling large files
"""
import os
import uuid
import json
import ijson
import pandas as pd
from typing import Iterator, Dict, Any, Optional, Union, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JsonStreamer:
    """Streaming JSON parser that processes files incrementally"""
    
    @staticmethod
    def detect_structure(file_path: Union[str, Path], sample_size: int = 1000) -> Dict[str, Any]:
        """
        Detect JSON structure by sampling the beginning of the file
        
        Args:
            file_path: Path to JSON file
            sample_size: Number of items to sample for array detection
            
        Returns:
            Dictionary with structure information
        """
        structure = {
            'type': None,
            'arrays': {},
            'root_is_array': False
        }
        
        try:
            with open(file_path, 'rb') as f:
                # Try to parse as a complete object first
                parser = ijson.parse(f)
                
                for prefix, event, value in parser:
                    if not prefix and event == 'start_array':
                        structure['root_is_array'] = True
                        structure['type'] = 'array'
                        break
                    elif not prefix and event == 'start_map':
                        structure['type'] = 'object'
                        break
                
                # Reset file position
                f.seek(0)
                
                # If it's an object, look for arrays inside
                if structure['type'] == 'object':
                    parser = ijson.parse(f)
                    array_counts = {}
                    
                    for prefix, event, value in parser:
                        if event == 'start_array':
                            array_path = prefix
                            if array_path not in array_counts:
                                array_counts[array_path] = 0
                        elif event == 'end_array':
                            if prefix in array_counts:
                                structure['arrays'][prefix] = {
                                    'count': array_counts[prefix]
                                }
                        elif prefix in array_counts:
                            # Count items in the array
                            array_counts[prefix] += 1
                            if array_counts[prefix] >= sample_size:
                                # Stop counting this array
                                del array_counts[prefix]
                
            return structure
            
        except Exception as e:
            logger.error(f"Error detecting structure: {e}")
            raise
    
    @staticmethod
    def stream_array(file_path: Union[str, Path], 
                    array_path: Optional[str] = None,
                    chunk_size: int = 1000) -> Iterator[List[Dict]]:
        """
        Stream JSON array data in chunks
        
        Args:
            file_path: Path to JSON file
            array_path: Path to array within JSON (None for root array)
            chunk_size: Number of items per chunk
            
        Yields:
            Chunks of parsed items
        """
        try:
            with open(file_path, 'rb') as f:
                if array_path:
                    # Stream specific array
                    parser = ijson.items(f, f'{array_path}.item')
                else:
                    # Stream root array
                    parser = ijson.items(f, 'item')
                
                chunk = []
                for item in parser:
                    chunk.append(item)
                    
                    if len(chunk) >= chunk_size:
                        yield chunk
                        chunk = []
                
                # Yield remaining items
                if chunk:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error streaming JSON: {e}")
            raise
    
    @staticmethod
    def convert_streaming(file_path: Union[str, Path],
                         output_path: Union[str, Path],
                         array_path: Optional[str] = None,
                         chunk_size: int = 10000,
                         max_depth: Optional[int] = None,
                         progress_callback: Optional[callable] = None,
                         include_summary: bool = True) -> Dict[str, Any]:
        """
        Convert large JSON to Excel using streaming
        
        Args:
            file_path: Input JSON file
            output_path: Output Excel file
            array_path: Path to array to process
            chunk_size: Items per chunk
            max_depth: Maximum flattening depth
            progress_callback: Progress callback function
            
        Returns:
            Result dictionary
        """
        from .json_parser_v2 import JsonParserV2
        from .excel_writer import ExcelWriter
        
        try:
            # Detect structure first
            structure = JsonStreamer.detect_structure(file_path)
            
            if not structure['root_is_array'] and not array_path:
                # Need to specify which array to process
                if structure['arrays']:
                    # Use the first array found
                    array_path = list(structure['arrays'].keys())[0]
                    logger.info(f"Auto-selected array path: {array_path}")
                else:
                    raise ValueError("No arrays found in JSON. Use standard parser instead.")
            
            total_rows = 0
            all_columns = set()
            first_chunk = True
            
            # Use ExcelWriter in append mode
            wrote_any = False
            # Validate output path and write to temp then atomically replace
            output_path = Path(ExcelWriter.validate_output_path(output_path))
            temp_path = output_path.with_suffix(output_path.suffix + f".tmp-{os.getpid()}-{uuid.uuid4().hex}")

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
                    for chunk_num, chunk in enumerate(JsonStreamer.stream_array(file_path, array_path, chunk_size)):
                        if progress_callback:
                            progress_callback(0, f"Processing chunk {chunk_num + 1}...")
                        
                        # Flatten the chunk
                        df_chunk = JsonParserV2.flatten_with_array_expansion(
                            chunk,
                            max_depth=max_depth,
                            expand_arrays=True
                        )
                        
                        # Track all columns
                        all_columns.update(df_chunk.columns)
                        
                        # For first chunk, write with header
                        if first_chunk:
                            df_chunk.to_excel(writer, sheet_name='Sheet1', index=False, startrow=0)
                            first_chunk = False
                            total_rows = len(df_chunk)
                            wrote_any = True
                        else:
                            # Append without header
                            # Ensure column alignment
                            df_chunk = df_chunk.reindex(columns=sorted(all_columns), fill_value='')
                            df_chunk.to_excel(writer, sheet_name='Sheet1', index=False, startrow=total_rows, header=False)
                            total_rows += len(df_chunk)
                            wrote_any = True
                        
                        if progress_callback:
                            progress_callback(50, f"Processed {total_rows:,} rows...")
                    # Ensure at least one visible sheet exists even for empty arrays
                    if not wrote_any:
                        pd.DataFrame().to_excel(writer, sheet_name='Sheet1', index=False)

                    # Write a Summary sheet at the end
                    if include_summary:
                        try:
                            from datetime import datetime
                            summary = {
                                'Input File': str(file_path),
                                'Mode': 'streaming',
                                'Rows': total_rows,
                                'Columns': len(all_columns),
                                'Generated At': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
                            }
                            pd.DataFrame([summary]).to_excel(writer, sheet_name='Summary', index=False)
                        except Exception:
                            pass

                    # Atomic replace
                    Path(temp_path).replace(output_path)
            finally:
                try:
                    if lock_fd is not None:
                        os.close(lock_fd)
                except Exception:
                    pass
                try:
                    Path(lock_path).unlink(missing_ok=True)
                except Exception:
                    pass
            
            if progress_callback:
                progress_callback(100, "Streaming conversion complete!")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'rows_written': total_rows,
                'columns': len(all_columns),
                'method': 'streaming'
            }
            
        except ImportError:
            logger.error("ijson not installed. Install with: pip install ijson")
            return {
                'success': False,
                'error': "Streaming parser requires ijson. Install with: pip install ijson"
            }
        except Exception as e:
            logger.error(f"Streaming conversion failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
