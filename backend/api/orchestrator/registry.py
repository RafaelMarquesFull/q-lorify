"""
Function Registry for Orchestrator.
Loads and manages deterministic functions.
"""
import importlib
import os
from typing import Dict, Any, Callable, Optional


# In-memory registry of loaded functions
_function_registry: Dict[str, Callable] = {}


def load_functions():
    """
    Load all functions from the functions directory.
    Functions must have an `execute` function.
    """
    global _function_registry
    _function_registry.clear()
    
    functions_dir = os.path.join(os.path.dirname(__file__), 'functions')
    
    if not os.path.exists(functions_dir):
        return
    
    for filename in os.listdir(functions_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = filename[:-3]  # Remove .py
            try:
                module = importlib.import_module(f'.functions.{module_name}', package='api.orchestrator')
                if hasattr(module, 'execute'):
                    _function_registry[module_name] = module.execute
                    print(f"[Registry] Loaded function: {module_name}")
            except Exception as e:
                print(f"[Registry] Failed to load {module_name}: {e}")


def get_function(name: str) -> Optional[Callable]:
    """Get a function by name from the registry."""
    if not _function_registry:
        load_functions()
    return _function_registry.get(name)


def list_functions() -> list:
    """List all registered function names."""
    if not _function_registry:
        load_functions()
    return list(_function_registry.keys())


def is_function_registered(name: str) -> bool:
    """Check if a function is registered."""
    if not _function_registry:
        load_functions()
    return name in _function_registry


def reload_functions():
    """Force reload of all functions."""
    load_functions()
