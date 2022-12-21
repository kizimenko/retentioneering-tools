from __future__ import annotations

import uuid
from typing import Any, Optional, Type, Union

from pydantic import ValidationError

from src.data_processor.data_processor import DataProcessor
from src.data_processor.registry import dataprocessor_registry
from src.eventstream.types import EventstreamType
from src.params_model.registry import params_model_registry


class BaseNode:
    processor: Optional[DataProcessor]
    events: Optional[EventstreamType]
    pk: str

    def __init__(self, **kwargs) -> None:
        self.pk = str(uuid.uuid4())

    def __str__(self) -> str:
        data = {"name": self.__class__.__name__, "pk": self.pk}
        return str(data)

    __repr__ = __str__

    def export(self) -> dict:
        data: dict[str, Any] = {"name": self.__class__.__name__, "pk": self.pk}
        if processor := getattr(self, "processor", None):
            data["processor"] = processor.to_dict()
        return data


class SourceNode(BaseNode):
    events: EventstreamType

    def __init__(self, source: EventstreamType) -> None:
        super().__init__()
        self.events = source


class EventsNode(BaseNode):
    processor: DataProcessor
    events: Optional[EventstreamType]

    def __init__(self, processor: DataProcessor) -> None:
        super().__init__()
        self.processor = processor
        self.events = None

    def calc_events(self, parent: EventstreamType):
        self.events = self.processor.apply(parent)


class MergeNode(BaseNode):
    events: Optional[EventstreamType]

    def __init__(self) -> None:
        super().__init__()
        self.events = None


Node = Union[SourceNode, EventsNode, MergeNode]
nodes = {
    "MergeNode": MergeNode,
    "EventsNode": EventsNode,
    "SourceNode": SourceNode,
}


class NotFoundDataprocessor(Exception):
    pass


def build_node(
    source_stream: EventstreamType,
    pk: str,
    node_name: str,
    processor_name: str | None = None,
    processor_params: dict[str, Any] | None = None,
) -> Node:
    _node = nodes[node_name]
    node_kwargs = {}

    if node_name == "SourceNode":
        node_kwargs["source"] = source_stream

    if not processor_params:
        processor_params = {}

    if processor_name and node_name == "EventsNode":
        _params_model_registry = params_model_registry.get_registry()
        _dataprocessor_registry = dataprocessor_registry.get_registry()

        _processor: Type[DataProcessor] = _dataprocessor_registry[processor_name]  # type: ignore
        params_name = _processor.__annotations__["params"]
        _params_model = _params_model_registry[params_name] if type(params_name) is str else params_name

        params_model = _params_model(**processor_params)

        processor: DataProcessor = _processor(params=params_model)
        node_kwargs["processor"] = processor

    node = _node(**node_kwargs)
    node.pk = pk
    return node
