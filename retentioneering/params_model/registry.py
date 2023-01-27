from __future__ import annotations

import typing

from retentioneering.utils.registry import RegistryValidationError, ReteRegistry

if typing.TYPE_CHECKING:
    from .params_model import ParamsModel


class ParamsModelRegistry:
    REGISTRY: dict[str, "ParamsModel"] = {}  # type: ignore

    objects = "ParamsModel"

    def __setitem__(self, key: str, value: "ParamsModel") -> None:
        if key not in self.REGISTRY:
            self.REGISTRY[key] = value
        else:
            raise RegistryValidationError("%s <%s> already exists" % (self.objects, key))

    @classmethod
    def get_registry(cls: typing.Type[ParamsModelRegistry]) -> dict:
        return cls.REGISTRY


params_model_registry = ParamsModelRegistry()


def register_params_model(cls: ParamsModel) -> None:
    params_model_registry[cls.__class__.__name__] = cls