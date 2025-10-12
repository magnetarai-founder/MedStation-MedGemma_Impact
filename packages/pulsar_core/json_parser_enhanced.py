"""
Enhanced JSON parser that handles nested arrays as primary data source
"""
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)


class JsonParserEnhanced:
    """Enhanced JSON parser that can extract data from nested arrays"""
    
    @staticmethod
    def detect_data_array(data: Union[Dict, List]) -> Tuple[Optional[List], Dict[str, Any]]:
        """
        Detect the main data array in JSON structure
        
        Returns:
            Tuple of (data_array, metadata)
        """
        if isinstance(data, list):
            # Already an array
            return data, {}
        
        if isinstance(data, dict):
            # Look for common patterns
            metadata = {}
            
            # Check for arrays that likely contain the main data
            array_candidates = []
            for key, value in data.items():
                if isinstance(value, list) and value:
                    # Check if this looks like a data array
                    first_item = value[0]
                    if isinstance(first_item, dict) and len(first_item) > 1:
                        array_candidates.append((key, value, len(value)))
                elif isinstance(value, (dict, str, int, float)):
                    # This is metadata
                    metadata[key] = value
            
            # Select the largest array as the data source
            if array_candidates:
                array_candidates.sort(key=lambda x: x[2], reverse=True)
                selected_key, selected_array, _ = array_candidates[0]
                logger.info(f"Detected '{selected_key}' as primary data array with {len(selected_array)} records")
                return selected_array, metadata
            
            # No arrays found, treat whole object as single record
            return [data], {}
        
        return None, {}
    
    @staticmethod
    def flatten_with_metadata(data_array: List[Dict], 
                            metadata: Dict[str, Any],
                            max_depth: Optional[int] = None,
                            columns_to_include: Optional[List[str]] = None,
                            sep: str = ".") -> pd.DataFrame:
        """
        Flatten array data and include metadata in each row
        """
        if not data_array:
            return pd.DataFrame()
        
        # First flatten the array data
        df = pd.json_normalize(data_array, sep=sep, max_level=max_depth)
        
        # Flatten metadata
        if metadata:
            metadata_flat = pd.json_normalize([metadata], sep=sep).iloc[0]
            
            # Add metadata columns to each row
            for col, value in metadata_flat.items():
                if col not in df.columns:  # Don't override existing columns
                    df[col] = value
        
        # Filter columns if specified
        if columns_to_include:
            available_cols = [col for col in columns_to_include if col in df.columns]
            df = df[available_cols] if available_cols else df
        
        logger.info(f"Flattened to DataFrame: {len(df)} rows × {len(df.columns)} columns")
        return df
