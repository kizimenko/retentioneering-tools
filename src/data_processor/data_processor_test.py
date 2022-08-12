import unittest
from typing import Literal, TypedDict, Union, cast
from eventstream.eventstream import Eventstream
from .data_processor import DataProcessor
from .params_model import ParamsModel, Enum


class StubProcessorParams(TypedDict):
    a: Union[Literal["a"], Literal["b"]]


class StubProcessor(DataProcessor[StubProcessorParams]):
    def __init__(self, params: StubProcessorParams):
        self.params = ParamsModel(
            fields=params,
            fields_schema={
                "a": Enum(["a", "b"]),
            }
        )

    def apply(self, eventstream: Eventstream) -> Eventstream:
        return eventstream.copy()


class TestDataProcessor(unittest.TestCase):
    def test_set_valid_params(self):
        valid_params: StubProcessorParams = {
            "a": "a"
        }
        stub = StubProcessor(params=valid_params)
        self.assertEqual(stub.params.fields, valid_params)

    def test_set_params(self):
        invalid_params: StubProcessorParams = cast(StubProcessorParams, {
            "a": "d"
        })
        with self.assertRaises(ValueError):
            StubProcessor(params=invalid_params)