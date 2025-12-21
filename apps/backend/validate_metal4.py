#!/usr/bin/env python3
"""
Quick Metal 4 validation on startup
Shows key Metal 4 stats when OmniStudio launches
"""

import sys
sys.path.insert(0, 'api')

try:
    from api.metal4_engine import get_metal4_engine

    engine = get_metal4_engine()

    if engine.is_available():
        # Get actual system memory
        import subprocess
        try:
            result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
            if result.returncode == 0:
                memsize = int(result.stdout.split(':')[1].strip())
                total_memory_gb = memsize / (1024**3)
            else:
                # Fallback to Metal's recommended max
                total_memory_gb = engine.device.recommendedMaxWorkingSetSize() / (1024**3)
        except (subprocess.SubprocessError, ValueError, IndexError, AttributeError):
            # Fallback to Metal's recommended max
            total_memory_gb = engine.device.recommendedMaxWorkingSetSize() / (1024**3)

        heap_allocated_gb = engine.H_main.size() / (1024**3)

        print("\n" + "="*60)
        print("⚡ METAL 4 GPU ACCELERATION ACTIVE")
        print("="*60)
        print(f"Device: {engine.device.name()}")
        print(f"Unified Memory: {total_memory_gb:.0f} GB ({heap_allocated_gb:.0f} GB heap allocated)")
        print(f"Command Queues: Q_render, Q_ml, Q_blit")
        print(f"Services: Chat, Insights, Data Engine")
        print("="*60 + "\n")
    else:
        print("\n⚠️  Metal 4 not available - using CPU fallback\n")

except Exception as e:
    print(f"\n⚠️  Metal 4 validation failed: {e}\n")
    sys.exit(0)  # Don't fail startup
