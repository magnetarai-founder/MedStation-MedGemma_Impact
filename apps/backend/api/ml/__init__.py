"""
Machine Learning module for NeutronStar.

Submodules:
- ane: Apple Neural Engine integration
- metal: Legacy Metal Performance Shaders
- metal4: Metal 4 GPU acceleration (sparse, vector, SQL)
- mlx: MLX framework for Apple Silicon
"""

from api.ml import ane, metal, metal4, mlx

__all__ = ["ane", "metal", "metal4", "mlx"]
