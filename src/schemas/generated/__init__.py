# Generated; do not edit.
# fmt: off
from importlib import import_module
from types import ModuleType

from pydantic import BaseModel

# Modules can reference each other without requiring eager import cycles.
_modules: dict[str, ModuleType] = {name: import_module(f'{__name__}.{name}') for name in ["errors", "health", "playback", "shared", "thumbnails", "uploads", "videos", "operations"]}
for _module in _modules.values():
    for _name, _target in _modules.items():
        vars(_module)[f'_schema_{_name}'] = _target
for _module in _modules.values():
    for _definition in tuple(vars(_module).values()):
        if isinstance(_definition, type) and issubclass(_definition, BaseModel) and _definition.__module__ == _module.__name__:
            _definition.model_rebuild()
