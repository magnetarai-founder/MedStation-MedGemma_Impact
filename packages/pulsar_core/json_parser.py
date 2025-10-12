"""
JSON parsing and flattening utilities
"""
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JsonParser:
    """Handles JSON file parsing and flattening operations"""
    
    @staticmethod
    def load_json(file_path: Union[str, Path]) -> Union[Dict, List]:
        """Load JSON file and return raw data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded JSON from {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            raise
    
    @staticmethod
    def analyze_structure(data: Union[Dict, List], max_depth: int = 10) -> Dict[str, Any]:
        """Analyze JSON structure to help with column selection"""
        def _analyze(obj, path="", depth=0):
            if depth > max_depth:
                return {"truncated": True}
            
            if isinstance(obj, dict):
                result = {"type": "object", "keys": {}}
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    result["keys"][key] = _analyze(value, new_path, depth + 1)
                return result
            
            elif isinstance(obj, list):
                if not obj:
                    return {"type": "array", "items": {"type": "empty"}}
                
                # Analyze first few items to get structure
                sample_size = min(5, len(obj))
                items_analysis = []
                for i in range(sample_size):
                    items_analysis.append(_analyze(obj[i], f"{path}[{i}]", depth + 1))
                
                return {
                    "type": "array",
                    "length": len(obj),
                    "items": items_analysis[0] if items_analysis else {"type": "empty"}
                }
            
            else:
                return {
                    "type": type(obj).__name__,
                    "sample": str(obj)[:50] if obj is not None else None
                }
        
        return _analyze(data)
    
    @staticmethod
    def flatten_json(data: Union[Dict, List], 
                    max_depth: Optional[int] = None,
                    columns_to_include: Optional[List[str]] = None,
                    sep: str = ".") -> pd.DataFrame:
        """
        Flatten nested JSON structure into DataFrame
        
        Args:
            data: JSON data (dict or list)
            max_depth: Maximum depth to flatten (None for unlimited)
            columns_to_include: List of column paths to include (None for all)
            sep: Separator for nested keys
            
        Returns:
            Flattened DataFrame
        """
        # Check if this is a structure with a data array inside
        if isinstance(data, dict):
            # Look for common data array patterns
            potential_arrays = []
            metadata = {}
            
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    # This looks like a data array
                    potential_arrays.append((key, value))
                elif not isinstance(value, list):
                    # This is metadata
                    metadata[key] = value
            
            # If we found data arrays, use the largest one
            if potential_arrays:
                # Sort by size and take the largest
                potential_arrays.sort(key=lambda x: len(x[1]), reverse=True)
                array_key, array_data = potential_arrays[0]
                logger.info(f"Found data array '{array_key}' with {len(array_data)} records")
                
                # Flatten the array data
                df = pd.json_normalize(array_data, sep=sep, max_level=max_depth)
                
                # Add metadata to each row if it exists
                if metadata:
                    metadata_df = pd.json_normalize([metadata], sep=sep)
                    for col in metadata_df.columns:
                        if col not in df.columns:
                            df[col] = metadata_df[col].iloc[0]
                
                data = array_data  # For column filtering below
            else:
                # No arrays found, treat as single record
                data = [data]
                df = pd.json_normalize(data, sep=sep, max_level=max_depth)
        elif isinstance(data, list):
            # Already a list
            if not data:
                return pd.DataFrame()
            df = pd.json_normalize(data, sep=sep, max_level=max_depth)
        else:
            raise ValueError("Data must be a dictionary or list")
        
        # Filter columns if specified
        if columns_to_include:
            # Handle wildcard patterns
            selected_cols = []
            for pattern in columns_to_include:
                if '*' in pattern:
                    # Simple wildcard matching
                    prefix = pattern.rstrip('*')
                    selected_cols.extend([col for col in df.columns if col.startswith(prefix)])
                elif pattern in df.columns:
                    selected_cols.append(pattern)
            
            df = df[selected_cols] if selected_cols else df
        
        logger.info(f"Flattened JSON to DataFrame: {len(df)} rows × {len(df.columns)} columns")
        return df
    
    @staticmethod
    def get_column_paths(data: Union[Dict, List], prefix: str = "") -> List[str]:
        """Get all possible column paths from JSON structure"""
        paths = []
        
        def _extract_paths(obj, current_prefix):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{current_prefix}.{key}" if current_prefix else key
                    if isinstance(value, (dict, list)):
                        _extract_paths(value, new_prefix)
                    else:
                        paths.append(new_prefix)
            elif isinstance(obj, list) and obj:
                # Sample first item
                _extract_paths(obj[0], current_prefix)
        
        if isinstance(data, list) and data:
            _extract_paths(data[0], prefix)
        elif isinstance(data, dict):
            _extract_paths(data, prefix)
        
        return sorted(list(set(paths)))
    
    @staticmethod
    def preview_data(df: pd.DataFrame, rows: int = 10) -> pd.DataFrame:
        """Get preview of DataFrame"""
        return df.head(rows)