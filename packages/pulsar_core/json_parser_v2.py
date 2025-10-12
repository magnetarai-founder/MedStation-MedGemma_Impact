"""
Enhanced JSON parsing with proper nested array handling
"""
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JsonParserV2:
    """Enhanced JSON parser that properly handles nested arrays

    Notes on cross-product behavior:
    - For dict roots, arrays under different keys are combined via cross-product.
    - For list roots (top-level arrays), each element is flattened independently; 
      there is no cross-product across different root elements.
    """
    
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
    def flatten_json_recursive(data: Union[Dict, List], 
                             parent_key: str = '',
                             sep: str = '.',
                             max_depth: Optional[int] = None,
                             current_depth: int = 0) -> List[Dict[str, Any]]:
        """
        Recursively flatten JSON with proper array expansion
        
        This method expands nested arrays into separate rows
        """
        if max_depth is not None and current_depth >= max_depth:
            # If we've reached max depth, stringify the remaining structure
            if isinstance(data, (dict, list)):
                return [{parent_key: json.dumps(data)}]
            else:
                return [{parent_key: data}]
        
        if isinstance(data, dict):
            items = []
            for k, v in data.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, list):
                    # Handle arrays specially
                    array_results = []
                    for idx, item in enumerate(v):
                        # Recursively flatten each array item
                        flattened_items = JsonParserV2.flatten_json_recursive(
                            item, f"{new_key}[{idx}]", sep, max_depth, current_depth + 1
                        )
                        array_results.extend(flattened_items)
                    
                    if not array_results:
                        array_results = [{new_key: None}]
                    
                    # If we already have items, we need to cross-product
                    if items:
                        new_items = []
                        for existing_item in items:
                            for array_item in array_results:
                                combined = {**existing_item, **array_item}
                                new_items.append(combined)
                        items = new_items
                    else:
                        items = array_results
                else:
                    # Recursively process non-array values
                    sub_items = JsonParserV2.flatten_json_recursive(
                        v, new_key, sep, max_depth, current_depth + 1
                    )
                    
                    # Merge with existing items using cross-product to preserve all combinations
                    if items:
                        new_items = []
                        for item in items:
                            for sub_item in sub_items:
                                new_items.append({**item, **sub_item})
                        items = new_items
                    else:
                        items = sub_items
            
            return items if items else [{}]
        
        elif isinstance(data, list):
            # If the root is a list, flatten each item
            all_items = []
            for item in data:
                flattened = JsonParserV2.flatten_json_recursive(
                    item, parent_key, sep, max_depth, current_depth
                )
                all_items.extend(flattened)
            return all_items if all_items else [{}]
        
        else:
            # Leaf node
            return [{parent_key: data}] if parent_key else [{"value": data}]
    
    @staticmethod
    def flatten_with_array_expansion(data: Union[Dict, List],
                                   sep: str = '.',
                                   max_depth: Optional[int] = None,
                                   expand_arrays: bool = True,
                                   preserve_indices: bool = False) -> pd.DataFrame:
        """
        Flatten JSON with option to expand arrays into rows
        
        Args:
            data: JSON data
            sep: Key separator
            max_depth: Maximum depth to flatten
            expand_arrays: If True, expand arrays into separate rows
            
        Returns:
            Flattened DataFrame
        """
        if expand_arrays:
            # Use our recursive flattening that expands arrays
            flattened_data = JsonParserV2.flatten_json_recursive(data, '', sep, max_depth)
            # Defensive: ensure each record is a dict
            safe_rows = []
            for rec in flattened_data:
                if isinstance(rec, dict):
                    safe_rows.append(rec)
                else:
                    # Wrap non-dict rows under a generic key
                    safe_rows.append({"value": rec})
            df = pd.DataFrame(safe_rows)
        else:
            # Use pandas json_normalize for standard flattening
            try:
                if isinstance(data, list):
                    df = pd.json_normalize(data, sep=sep, max_level=max_depth)
                else:
                    df = pd.json_normalize([data], sep=sep, max_level=max_depth)
            except Exception:
                # Fallback: coerce scalars/lists into dict rows
                rows = []
                seq = data if isinstance(data, list) else [data]
                for obj in seq:
                    if isinstance(obj, dict):
                        rows.append(obj)
                    else:
                        rows.append({"value": obj})
                df = pd.DataFrame(rows)
        
        # Clean up column names (remove leading separator)
        df.columns = [col.lstrip(sep) for col in df.columns]
        
        # Remove array indices from column names for cleaner output
        if expand_arrays and not preserve_indices:
            # Group columns by base name (without array index)
            import re
            cleaned_columns = {}
            for col in df.columns:
                # Remove array indices like [0], [1], etc.
                base_col = re.sub(r'\[\d+\]', '', col)
                if base_col not in cleaned_columns:
                    cleaned_columns[base_col] = []
                cleaned_columns[base_col].append(col)
            
            # Rename columns to remove indices where there's no ambiguity
            rename_map = {}
            for base_col, original_cols in cleaned_columns.items():
                if len(original_cols) == 1:
                    rename_map[original_cols[0]] = base_col
            
            if rename_map:
                df = df.rename(columns=rename_map)

            # Final cleanup pass: robustly strip any remaining array indices like [0], [1]
            # and handle potential duplicates
            new_columns = []
            seen_columns = {}
            for col in df.columns:
                clean_col = re.sub(r'\[\d+\]', '', col)
                if clean_col in seen_columns:
                    # Add suffix to make unique
                    seen_columns[clean_col] += 1
                    new_columns.append(f"{clean_col}_{seen_columns[clean_col]}")
                else:
                    seen_columns[clean_col] = 0
                    new_columns.append(clean_col)
            df.columns = new_columns
        
        logger.info(f"Flattened JSON to DataFrame: {len(df)} rows × {len(df.columns)} columns")
        return df
    
    @staticmethod
    def detect_data_arrays(data: Union[Dict, List]) -> Dict[str, Any]:
        """
        Detect all arrays in the JSON structure that could be data arrays
        
        Returns:
            Dictionary with array paths and their lengths
        """
        arrays = {}
        
        def find_arrays(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, list) and len(value) > 0:
                        # Check if it's an array of objects
                        if all(isinstance(item, dict) for item in value):
                            arrays[new_path] = {
                                'length': len(value),
                                'sample': value[0] if value else {}
                            }
                    find_arrays(value, new_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj[:5]):  # Check first 5 items
                    find_arrays(item, f"{path}[{idx}]")
        
        if isinstance(data, list):
            arrays['(root)'] = {
                'length': len(data),
                'sample': data[0] if data else {}
            }
        else:
            find_arrays(data)
        
        return arrays
    
    @staticmethod
    def flatten_specific_array(data: Union[Dict, List],
                             array_path: Optional[str] = None,
                             include_parent_data: bool = True,
                             sep: str = '.',
                             preserve_indices: bool = False) -> pd.DataFrame:
        """
        Flatten a specific array from the JSON structure
        
        Args:
            data: JSON data
            array_path: Path to the array to flatten (e.g., "users.orders")
            include_parent_data: Include data from parent levels
            sep: Separator for nested keys
            
        Returns:
            Flattened DataFrame
        """
        if array_path is None or array_path == '(root)':
            # Flatten the root
            return JsonParserV2.flatten_with_array_expansion(data, sep=sep, preserve_indices=preserve_indices)
        
        # Navigate to the specified array
        current = data
        parent_data = {}
        path_parts = array_path.split('.')
        
        for i, part in enumerate(path_parts):
            if isinstance(current, dict) and part in current:
                if i < len(path_parts) - 1:
                    # Store parent data if requested
                    if include_parent_data:
                        for k, v in current.items():
                            if k != part and not isinstance(v, (dict, list)):
                                parent_key = '.'.join(path_parts[:i] + [k])
                                parent_data[parent_key] = v
                current = current[part]
            else:
                raise ValueError(f"Path '{array_path}' not found in JSON structure")
        
        if not isinstance(current, list):
            raise ValueError(f"Path '{array_path}' does not point to an array")
        
        # Flatten the array
        df = JsonParserV2.flatten_with_array_expansion(current, sep=sep, preserve_indices=preserve_indices)
        
        # Add parent data to each row
        if include_parent_data and parent_data:
            for key, value in parent_data.items():
                df[key] = value
        
        return df
