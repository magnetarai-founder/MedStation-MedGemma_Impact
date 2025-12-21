"""
Pulsar Core - JSON to Excel Engine Stub
Temporary stub to allow server to start
"""

import pandas as pd
from typing import Dict, Any


class JsonToExcelEngine:
    """Stub for JSON to Excel conversion"""

    def load_json(self, file_path: str) -> Dict[str, Any]:
        """Load and analyze JSON file"""
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                return {'success': False, 'error': 'Invalid JSON format'}

            # Get column names
            columns = df.columns.tolist()

            # Preview first 10 rows
            preview = df.head(10)

            return {
                'success': True,
                'columns': columns,
                'preview': preview,
                'data': data
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def convert_to_excel(self, data, output_path: str, selected_columns=None) -> dict:
        """Convert JSON data to Excel"""
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                raise ValueError("Invalid data format")

            if selected_columns:
                df = df[selected_columns]

            df.to_excel(output_path, index=False)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
