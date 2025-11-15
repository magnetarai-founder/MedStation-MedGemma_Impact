"""
Data Profiler Service

Analyzes datasets to discover patterns, generate statistics, and provide insights.
Uses pandas/numpy only (no SciPy in Week 1 for fast offline operation).
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Performance constraints
MAX_ANALYSIS_TIME_SECONDS = 30
DEFAULT_SAMPLE_SIZE = 50000
MAX_OUTLIERS_PER_COLUMN = 50
MAX_CORRELATION_PAIRS = 10


class DataProfiler:
    """Service for profiling datasets and discovering patterns"""

    def __init__(self):
        self.data_engine = None

    def _get_data_engine(self):
        """Lazy init for data engine"""
        if self.data_engine is None:
            from api.data_engine import DataEngine
            self.data_engine = DataEngine()
        return self.data_engine

    def profile_dataset(
        self,
        dataset_id: Optional[str] = None,
        session_id: Optional[str] = None,
        table_name: Optional[str] = None,
        sample_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Profile a dataset and discover patterns

        Args:
            dataset_id: Dataset UUID
            session_id: Session UUID
            table_name: Table name to analyze
            sample_rows: Max rows to analyze (default: 50k)

        Returns:
            {
                "columns": {...},
                "correlations": [...],
                "insights": [...],
                "metadata": {...}
            }
        """
        start_time = time.time()
        warnings = []

        try:
            # Get dataset metadata
            engine = self._get_data_engine()

            if dataset_id:
                metadata = engine.get_dataset_metadata(dataset_id)
                if not metadata:
                    raise ValueError(f"Dataset not found: {dataset_id}")
                table_name = metadata["table_name"]
            elif session_id:
                datasets = engine.list_datasets(session_id=session_id)
                if not datasets:
                    raise ValueError(f"No datasets found for session: {session_id}")
                # Use latest dataset
                metadata = datasets[0]
                if not table_name:
                    table_name = metadata["table_name"]
            else:
                raise ValueError("Either dataset_id or session_id must be provided")

            # Determine sample size
            total_rows = metadata.get("rows", 0) if dataset_id or session_id else 0
            sample_size = sample_rows or DEFAULT_SAMPLE_SIZE

            if total_rows > sample_size:
                sample_query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
                warnings.append(f"Analyzing sample of {sample_size:,} rows (total: {total_rows:,})")
            else:
                sample_query = f"SELECT * FROM {table_name}"

            # Load data into DataFrame
            result = engine.execute_sql(sample_query)
            df = pd.DataFrame(result["rows"])

            if df.empty:
                return {
                    "columns": {},
                    "correlations": [],
                    "insights": ["No data to analyze"],
                    "metadata": {
                        "total_rows": 0,
                        "total_time_ms": 0,
                        "warnings": warnings
                    }
                }

            # Check time budget
            if time.time() - start_time > MAX_ANALYSIS_TIME_SECONDS:
                warnings.append("Analysis time limit reached, returning partial results")

            # Analyze columns
            columns_analysis = self._analyze_columns(df, start_time)

            # Calculate correlations (numeric columns only)
            correlations = self._calculate_correlations(df, start_time)

            # Generate insights
            insights = self._generate_insights(columns_analysis, correlations, df)

            total_time = (time.time() - start_time) * 1000

            return {
                "columns": columns_analysis,
                "correlations": correlations,
                "insights": insights,
                "metadata": {
                    "total_rows": len(df),
                    "sampled": len(df) < total_rows if total_rows > 0 else False,
                    "total_time_ms": round(total_time, 2),
                    "warnings": warnings if warnings else None
                }
            }

        except Exception as e:
            logger.error(f"Dataset profiling error: {e}", exc_info=True)
            raise

    def _analyze_columns(self, df: pd.DataFrame, start_time: float) -> Dict[str, Any]:
        """Analyze each column and return statistics"""
        columns_stats = {}

        for col in df.columns:
            if time.time() - start_time > MAX_ANALYSIS_TIME_SECONDS:
                break

            col_data = df[col]
            col_type = self._detect_column_type(col_data)

            if col_type == "numeric":
                columns_stats[col] = self._analyze_numeric_column(col_data, col)
            elif col_type == "categorical":
                columns_stats[col] = self._analyze_categorical_column(col_data, col)
            elif col_type == "temporal":
                columns_stats[col] = self._analyze_temporal_column(col_data, col)
            elif col_type == "text":
                columns_stats[col] = self._analyze_text_column(col_data, col)

        return columns_stats

    def _detect_column_type(self, series: pd.Series) -> str:
        """Detect column type (numeric, categorical, temporal, text)"""
        dtype = series.dtype

        if pd.api.types.is_numeric_dtype(dtype):
            return "numeric"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "temporal"
        elif pd.api.types.is_categorical_dtype(dtype) or dtype == 'object':
            # Check if it's mostly unique (text) or limited values (categorical)
            cardinality = series.nunique()
            if cardinality > 50 and cardinality > len(series) * 0.5:
                return "text"
            else:
                return "categorical"
        else:
            return "text"

    def _analyze_numeric_column(self, series: pd.Series, col_name: str) -> Dict[str, Any]:
        """Analyze numeric column"""
        # Drop nulls for stats
        clean_series = series.dropna()

        if len(clean_series) == 0:
            return {
                "type": "numeric",
                "null_count": len(series),
                "null_percent": 100.0
            }

        # Basic stats
        stats = {
            "type": "numeric",
            "min": float(clean_series.min()),
            "max": float(clean_series.max()),
            "mean": float(clean_series.mean()),
            "median": float(clean_series.median()),
            "std": float(clean_series.std()) if len(clean_series) > 1 else 0.0,
            "quartiles": [
                float(clean_series.quantile(0.25)),
                float(clean_series.quantile(0.50)),
                float(clean_series.quantile(0.75))
            ],
            "null_count": int(series.isna().sum()),
            "null_percent": round(float(series.isna().sum() / len(series) * 100), 2)
        }

        # Detect outliers using z-score
        if stats["std"] > 0:
            z_scores = np.abs((clean_series - stats["mean"]) / stats["std"])
            outlier_mask = z_scores > 3
            outliers_data = clean_series[outlier_mask]

            if len(outliers_data) > 0:
                outliers_list = []
                for idx, value in outliers_data.items():
                    if len(outliers_list) >= MAX_OUTLIERS_PER_COLUMN:
                        break
                    outliers_list.append({
                        "row_index": int(idx),
                        "value": float(value),
                        "z": round(float(z_scores[idx]), 2)
                    })

                stats["outliers"] = outliers_list
                stats["outlier_count"] = int(len(outliers_data))

        return stats

    def _analyze_categorical_column(self, series: pd.Series, col_name: str) -> Dict[str, Any]:
        """Analyze categorical column"""
        value_counts = series.value_counts()
        cardinality = series.nunique()

        # Top 10 values
        top_values = []
        for value, count in value_counts.head(10).items():
            top_values.append({
                "value": str(value),
                "count": int(count),
                "percent": round(float(count / len(series) * 100), 2)
            })

        # Approximate entropy (simple measure of diversity)
        # H = -sum(p * log(p))
        if cardinality > 1:
            proportions = value_counts / len(series)
            entropy = -np.sum(proportions * np.log2(proportions + 1e-10))
        else:
            entropy = 0.0

        return {
            "type": "categorical",
            "cardinality": int(cardinality),
            "top_values": top_values,
            "entropy": round(float(entropy), 2),
            "null_count": int(series.isna().sum()),
            "null_percent": round(float(series.isna().sum() / len(series) * 100), 2)
        }

    def _analyze_temporal_column(self, series: pd.Series, col_name: str) -> Dict[str, Any]:
        """Analyze temporal/date column"""
        # Try to convert to datetime if not already
        try:
            if not pd.api.types.is_datetime64_any_dtype(series):
                series = pd.to_datetime(series, errors='coerce')

            clean_series = series.dropna()

            if len(clean_series) == 0:
                return {"type": "temporal", "null_count": len(series)}

            stats = {
                "type": "temporal",
                "min_date": str(clean_series.min()),
                "max_date": str(clean_series.max()),
                "range_days": int((clean_series.max() - clean_series.min()).days),
                "null_count": int(series.isna().sum()),
                "null_percent": round(float(series.isna().sum() / len(series) * 100), 2)
            }

            # Simple trend detection using numpy.polyfit
            # Convert to ordinal for linear regression
            ordinal_dates = pd.Series([d.toordinal() for d in clean_series if pd.notna(d)])
            if len(ordinal_dates) > 2:
                # Count per day (bucketed)
                daily_counts = series.value_counts().sort_index()
                if len(daily_counts) > 1:
                    x = np.array([d.toordinal() for d in daily_counts.index])
                    y = daily_counts.values

                    # Simple linear fit
                    slope, _ = np.polyfit(x, y, 1)

                    if slope > 0.1:
                        stats["trend"] = "increasing"
                    elif slope < -0.1:
                        stats["trend"] = "decreasing"
                    else:
                        stats["trend"] = "flat"

            return stats

        except Exception as e:
            logger.warning(f"Temporal analysis failed for {col_name}: {e}")
            return {"type": "temporal", "error": str(e)}

    def _analyze_text_column(self, series: pd.Series, col_name: str) -> Dict[str, Any]:
        """Analyze text column"""
        # String length stats
        lengths = series.astype(str).str.len()

        return {
            "type": "text",
            "min_length": int(lengths.min()) if len(lengths) > 0 else 0,
            "max_length": int(lengths.max()) if len(lengths) > 0 else 0,
            "avg_length": round(float(lengths.mean()), 2) if len(lengths) > 0 else 0.0,
            "null_count": int(series.isna().sum()),
            "null_percent": round(float(series.isna().sum() / len(series) * 100), 2),
            "empty_count": int((series == '').sum())
        }

    def _calculate_correlations(self, df: pd.DataFrame, start_time: float) -> List[Dict[str, Any]]:
        """Calculate correlations between numeric columns"""
        if time.time() - start_time > MAX_ANALYSIS_TIME_SECONDS:
            return []

        # Get numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            return []

        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr(method='pearson')

        # Extract pairs (upper triangle only, no self-correlation)
        pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                col1 = numeric_cols[i]
                col2 = numeric_cols[j]
                r = corr_matrix.loc[col1, col2]

                if pd.notna(r):  # Skip NaN correlations
                    pairs.append({
                        "col1": col1,
                        "col2": col2,
                        "method": "pearson",
                        "r": round(float(r), 3),
                        "abs_r": abs(float(r))
                    })

        # Sort by absolute correlation strength, take top N
        pairs.sort(key=lambda x: x["abs_r"], reverse=True)
        top_pairs = pairs[:MAX_CORRELATION_PAIRS]

        # Remove abs_r helper field
        for p in top_pairs:
            del p["abs_r"]

        return top_pairs

    def _generate_insights(
        self,
        columns_analysis: Dict[str, Any],
        correlations: List[Dict[str, Any]],
        df: pd.DataFrame
    ) -> List[str]:
        """Generate natural language insights"""
        insights = []

        # Outlier insights
        for col_name, stats in columns_analysis.items():
            if stats.get("type") == "numeric" and "outlier_count" in stats:
                count = stats["outlier_count"]
                if count > 0:
                    insights.append(f"{count} outlier{'s' if count != 1 else ''} detected in {col_name}")

        # Correlation insights
        for corr in correlations:
            r = corr["r"]
            if abs(r) > 0.7:
                strength = "strong" if abs(r) > 0.8 else "moderate"
                direction = "positive" if r > 0 else "negative"
                insights.append(
                    f"{strength.capitalize()} {direction} correlation between {corr['col1']} and {corr['col2']} (r={r})"
                )

        # Trend insights
        for col_name, stats in columns_analysis.items():
            if stats.get("type") == "temporal" and "trend" in stats:
                trend = stats["trend"]
                if trend != "flat":
                    insights.append(f"{col_name} shows {trend} trend over time")

        # Data quality insights
        high_null_cols = [
            col for col, stats in columns_analysis.items()
            if stats.get("null_percent", 0) > 20
        ]
        if high_null_cols:
            insights.append(f"High null percentage in: {', '.join(high_null_cols[:3])}")

        # If no insights, provide basic summary
        if not insights:
            insights.append(f"Analyzed {len(columns_analysis)} columns with {len(df)} rows")

        return insights


# Global instance
_data_profiler = None


def get_data_profiler() -> DataProfiler:
    """Get global data profiler instance"""
    global _data_profiler
    if _data_profiler is None:
        _data_profiler = DataProfiler()
    return _data_profiler
