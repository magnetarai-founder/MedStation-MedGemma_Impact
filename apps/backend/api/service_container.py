"""
Lightweight Dependency Injection Container for ElohimOS

Surgical approach: Wraps existing singletons without requiring full refactor.
Provides testability and service lifecycle management.

Usage:
    from service_container import services

    # Get service instance
    data_engine = services.get("data_engine")
    chat_memory = services.get("chat_memory")

    # For testing: override with mock
    services.override("data_engine", mock_engine)
"""

from typing import Dict, Any, Optional, Callable
from pathlib import Path
import threading


class ServiceContainer:
    """
    Lightweight DI container that wraps existing singleton pattern.

    Benefits:
    - Testability: Can override services with mocks
    - Lifecycle management: Proper shutdown
    - Thread-safe service initialization
    - Backwards compatible with existing get_* functions
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._overrides: Dict[str, Any] = {}

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """
        Register a factory function for lazy initialization

        Args:
            name: Service name
            factory: Function that returns service instance
        """
        with self._lock:
            self._factories[name] = factory

    def get(self, name: str) -> Any:
        """
        Get service instance (creates if not exists)

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Check for test override
        if name in self._overrides:
            return self._overrides[name]

        # Return cached instance if exists
        if name in self._services:
            return self._services[name]

        # Initialize service using factory
        with self._lock:
            # Double-check after acquiring lock
            if name in self._services:
                return self._services[name]

            if name not in self._factories:
                raise KeyError(f"Service '{name}' not registered")

            # Create service instance
            factory = self._factories[name]
            instance = factory()
            self._services[name] = instance
            return instance

    def override(self, name: str, instance: Any) -> None:
        """
        Override service with mock (for testing)

        Args:
            name: Service name
            instance: Mock instance
        """
        self._overrides[name] = instance

    def clear_override(self, name: str) -> None:
        """Clear service override"""
        self._overrides.pop(name, None)

    def clear_all_overrides(self) -> None:
        """Clear all overrides (useful for test cleanup)"""
        self._overrides.clear()

    def is_initialized(self, name: str) -> bool:
        """Check if service is initialized"""
        return name in self._services

    def shutdown_all(self) -> None:
        """Shutdown all services (call close/cleanup methods)"""
        with self._lock:
            for name, instance in self._services.items():
                try:
                    # Try common cleanup method names
                    if hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    elif hasattr(instance, 'shutdown'):
                        instance.shutdown()
                except Exception as e:
                    # Log but don't crash on cleanup errors
                    print(f"Warning: Error shutting down {name}: {e}")

            # Clear all cached instances
            self._services.clear()

    def get_all_service_names(self) -> list[str]:
        """Get list of all registered service names"""
        return list(self._factories.keys())


# ===== Global Container Instance =====

services = ServiceContainer()


# ===== Register Existing Services =====

def register_core_services() -> None:
    """
    Register all core services with their factories.

    Call this AFTER all modules are imported to avoid circular imports.
    """

    # Data Engine
    def create_data_engine() -> Any:
        from data_engine import get_data_engine
        return get_data_engine()

    services.register_factory("data_engine", create_data_engine)

    # Chat Memory
    def create_chat_memory() -> Any:
        from chat_memory import get_memory
        return get_memory()

    services.register_factory("chat_memory", create_chat_memory)

    # Metal4 Diagnostics
    def create_metal4_diagnostics() -> Any:
        from metal4_diagnostics import get_diagnostics
        return get_diagnostics()

    services.register_factory("metal4_diagnostics", create_metal4_diagnostics)

    # Metal4 Engine
    def create_metal4_engine() -> Any:
        from metal4_engine import get_metal4_engine
        return get_metal4_engine()

    services.register_factory("metal4_engine", create_metal4_engine)

    # Vault Service
    def create_vault_service() -> Any:
        from vault_service import get_vault_service
        return get_vault_service()

    services.register_factory("vault_service", create_vault_service)

    # User Service (migrated to services layer)
    def create_user_service() -> Any:
        from services.users import get_or_create_user_profile
        return get_or_create_user_profile

    services.register_factory("user_service", create_user_service)

    # Docs Service
    def create_docs_service() -> Any:
        from docs_service import get_docs_service
        return get_docs_service()

    services.register_factory("docs_service", create_docs_service)

    # Model Manager
    def create_model_manager() -> Any:
        from model_manager import get_model_manager
        return get_model_manager()

    services.register_factory("model_manager", create_model_manager)


# NOTE: Don't auto-register on import to avoid circular dependencies
# Call register_core_services() from main.py after imports are complete


# ===== Backwards Compatibility Helpers =====

def get_service(name: str) -> Any:
    """Get service by name (backwards compatible)"""
    return services.get(name)


def shutdown_services() -> None:
    """Shutdown all services (call from app shutdown)"""
    services.shutdown_all()
