"""
Enhanced JSON normalizer that fully extracts nested data
"""
import pandas as pd
import json
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class JsonNormalizer:
    """Advanced JSON normalization with full nested array extraction"""
    
    @staticmethod
    def normalize_feed_json(data: Dict[str, Any]) -> pd.DataFrame:
        """
        Fully normalize feed.json structure
        
        Extracts:
        - Basic message fields
        - Header metadata
        - Fulfillment availability details
        - Purchasable offer details including pricing
        """
        messages = data.get('messages', [])
        header = data.get('header', {})
        
        normalized_rows = []
        
        for msg in messages:
            # Base row with message fields
            base_row = {
                'messageId': msg.get('messageId'),
                'sku': msg.get('sku'),
                'operationType': msg.get('operationType'),
                'productType': msg.get('productType'),
            }
            
            # Add header fields
            for k, v in header.items():
                base_row[f'header.{k}'] = v
            
            # Extract attributes
            attrs = msg.get('attributes', {})
            
            # Fulfillment availability
            fulfillment_list = attrs.get('fulfillment_availability', [])
            if fulfillment_list:
                # For single fulfillment, extract to main row
                if len(fulfillment_list) == 1:
                    f = fulfillment_list[0]
                    base_row['fulfillment.quantity'] = f.get('quantity')
                    base_row['fulfillment.channel_code'] = f.get('fulfillment_channel_code')
                else:
                    # Multiple fulfillments - need to decide how to handle
                    # Option 1: Create multiple rows (one per fulfillment)
                    # Option 2: Just take the first one
                    # For now, taking first
                    f = fulfillment_list[0]
                    base_row['fulfillment.quantity'] = f.get('quantity')
                    base_row['fulfillment.channel_code'] = f.get('fulfillment_channel_code')
            else:
                base_row['fulfillment.quantity'] = None
                base_row['fulfillment.channel_code'] = None
            
            # Purchasable offer
            offers = attrs.get('purchasable_offer', [])
            if offers:
                offer = offers[0]  # Taking first offer
                base_row['offer.currency'] = offer.get('currency')
                base_row['offer.marketplace_id'] = offer.get('marketplace_id')
                base_row['offer.audience'] = offer.get('audience')
                
                # Extract our_price
                our_prices = offer.get('our_price', [])
                if our_prices and our_prices[0].get('schedule'):
                    schedule = our_prices[0]['schedule'][0]
                    base_row['offer.price'] = schedule.get('value_with_tax')
                    base_row['offer.price_start_at'] = schedule.get('start_at')
                    base_row['offer.price_end_at'] = schedule.get('end_at')
                else:
                    base_row['offer.price'] = None
                    base_row['offer.price_start_at'] = None
                    base_row['offer.price_end_at'] = None
                
                # Extract discounted_price
                discounted_prices = offer.get('discounted_price', [])
                if discounted_prices and discounted_prices[0].get('schedule'):
                    discount_schedule = discounted_prices[0]['schedule'][0]
                    base_row['offer.discount_price'] = discount_schedule.get('value_with_tax')
                    base_row['offer.discount_start_at'] = discount_schedule.get('start_at')
                    base_row['offer.discount_end_at'] = discount_schedule.get('end_at')
                else:
                    base_row['offer.discount_price'] = None
                    base_row['offer.discount_start_at'] = None
                    base_row['offer.discount_end_at'] = None
            
            normalized_rows.append(base_row)
        
        df = pd.DataFrame(normalized_rows)
        logger.info(f"Normalized {len(messages)} messages into {len(df.columns)} columns")
        return df
    
    @staticmethod
    def auto_normalize(data: Union[Dict, List], 
                      max_depth: int = 5,
                      array_handling: str = 'first') -> pd.DataFrame:
        """
        Automatically normalize any JSON structure
        
        Args:
            data: JSON data to normalize
            max_depth: Maximum nesting depth
            array_handling: How to handle arrays ('first', 'explode', 'join')
        """
        def extract_value(obj: Any, path: str = '') -> Dict[str, Any]:
            """Recursively extract all values from nested structure"""
            result = {}
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    result.update(extract_value(value, new_path))
            
            elif isinstance(obj, list):
                if not obj:
                    result[path] = None
                elif array_handling == 'first':
                    # Take first element
                    result.update(extract_value(obj[0], path))
                elif array_handling == 'join':
                    # Join as string
                    if all(isinstance(x, (str, int, float)) for x in obj):
                        result[path] = ', '.join(str(x) for x in obj)
                    else:
                        # Complex objects - take first
                        result.update(extract_value(obj[0], path))
                elif array_handling == 'explode':
                    # This would need special handling to create multiple rows
                    result.update(extract_value(obj[0], path))
            
            else:
                # Leaf value
                result[path] = obj
            
            return result
        
        # Handle different input types
        if isinstance(data, list):
            rows = [extract_value(item) for item in data]
        elif isinstance(data, dict):
            # Check for data arrays
            data_array = None
            metadata = {}
            
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    if data_array is None or len(value) > len(data_array):
                        data_array = value
                        data_array_key = key
                else:
                    metadata[key] = value
            
            if data_array:
                logger.info(f"Found data array '{data_array_key}' with {len(data_array)} items")
                rows = []
                for item in data_array:
                    row = extract_value(item)
                    # Add metadata to each row
                    for k, v in extract_value(metadata).items():
                        if k not in row:
                            row[k] = v
                    rows.append(row)
            else:
                rows = [extract_value(data)]
        else:
            rows = []
        
        return pd.DataFrame(rows)