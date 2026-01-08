"""
Metal 4 Capability Detection

Detects Metal GPU capabilities and version on macOS.
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MetalVersion(Enum):
    """Metal framework versions"""
    UNAVAILABLE = 0
    METAL_2 = 2
    METAL_3 = 3
    METAL_4 = 4  # macOS Sequoia 15.0+


@dataclass
class MetalCapabilities:
    """Metal GPU capabilities"""
    available: bool
    version: MetalVersion
    device_name: str
    is_apple_silicon: bool
    supports_unified_memory: bool
    supports_mps: bool
    supports_ane: bool
    supports_sparse_resources: bool
    supports_ml_command_encoder: bool
    max_buffer_size_mb: int
    recommended_heap_size_mb: int


def detect_metal_capabilities() -> MetalCapabilities:
    """
    Detect Metal 4 capabilities on the system

    Returns:
        MetalCapabilities with full feature detection
    """
    try:
        import platform
        import subprocess

        # Check if we're on macOS
        if platform.system() != "Darwin":
            logger.info("Not on macOS - Metal unavailable")
            return MetalCapabilities(
                available=False,
                version=MetalVersion.UNAVAILABLE,
                device_name="N/A",
                is_apple_silicon=False,
                supports_unified_memory=False,
                supports_mps=False,
                supports_ane=False,
                supports_sparse_resources=False,
                supports_ml_command_encoder=False,
                max_buffer_size_mb=0,
                recommended_heap_size_mb=0
            )

        # Check macOS version
        mac_ver = platform.mac_ver()[0]
        major_version = int(mac_ver.split('.')[0]) if mac_ver else 0

        # Determine Metal version based on macOS version
        # macOS 15 (Sequoia) = Metal 4
        # macOS 14 (Sonoma) = Metal 3
        # macOS 13 (Ventura) = Metal 3
        if major_version >= 26:  # macOS 15+ (Darwin 26 = macOS Sequoia)
            metal_version = MetalVersion.METAL_4
        elif major_version >= 23:  # macOS 14/13
            metal_version = MetalVersion.METAL_3
        else:
            metal_version = MetalVersion.METAL_2

        # Check if Apple Silicon
        machine = platform.machine()
        is_apple_silicon = machine == "arm64"

        # Get GPU info
        device_name = "Unknown"
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Chipset Model:' in line:
                        device_name = line.split(':')[1].strip()
                        break
        except Exception as e:
            logger.debug(f"Could not get GPU info: {e}")

        # Feature detection based on version and hardware
        supports_unified_memory = is_apple_silicon
        supports_mps = metal_version.value >= MetalVersion.METAL_3.value and is_apple_silicon
        supports_ane = is_apple_silicon  # ANE available on all Apple Silicon
        supports_sparse_resources = metal_version.value >= MetalVersion.METAL_4.value
        supports_ml_command_encoder = metal_version.value >= MetalVersion.METAL_4.value

        # Calculate recommended sizes
        # Apple Silicon typically has 8-64GB unified memory
        # Use 25% for Metal heaps (conservative)
        try:
            import psutil
            total_memory_gb = psutil.virtual_memory().total / (1024**3)
            max_buffer_size_mb = int(total_memory_gb * 1024 * 0.5)  # 50% of RAM
            recommended_heap_size_mb = int(total_memory_gb * 1024 * 0.25)  # 25% of RAM
        except ImportError:
            # Fallback defaults
            max_buffer_size_mb = 4096  # 4GB
            recommended_heap_size_mb = 2048  # 2GB

        caps = MetalCapabilities(
            available=True,
            version=metal_version,
            device_name=device_name,
            is_apple_silicon=is_apple_silicon,
            supports_unified_memory=supports_unified_memory,
            supports_mps=supports_mps,
            supports_ane=supports_ane,
            supports_sparse_resources=supports_sparse_resources,
            supports_ml_command_encoder=supports_ml_command_encoder,
            max_buffer_size_mb=max_buffer_size_mb,
            recommended_heap_size_mb=recommended_heap_size_mb
        )

        logger.info(f"Metal {metal_version.value} detected on {device_name}")
        logger.info(f"   Apple Silicon: {is_apple_silicon}")
        logger.info(f"   Unified Memory: {supports_unified_memory}")
        logger.info(f"   MPS Available: {supports_mps}")
        logger.info(f"   ANE Available: {supports_ane}")
        logger.info(f"   Sparse Resources: {supports_sparse_resources}")
        logger.info(f"   ML Command Encoder: {supports_ml_command_encoder}")

        return caps

    except Exception as e:
        logger.error(f"Failed to detect Metal capabilities: {e}")
        return MetalCapabilities(
            available=False,
            version=MetalVersion.UNAVAILABLE,
            device_name="Error",
            is_apple_silicon=False,
            supports_unified_memory=False,
            supports_mps=False,
            supports_ane=False,
            supports_sparse_resources=False,
            supports_ml_command_encoder=False,
            max_buffer_size_mb=0,
            recommended_heap_size_mb=0
        )
