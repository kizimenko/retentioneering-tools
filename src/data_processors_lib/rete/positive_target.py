from __future__ import annotations

from typing import Any, Callable, List

import pandas as pd
from pandas import DataFrame

from src.data_processor.data_processor import DataProcessor
from src.eventstream.eventstream import Eventstream
from src.eventstream.schema import EventstreamSchema
from src.params_model import ParamsModel
from src.widget.widgets import ReteFunction

EventstreamFilter = Callable[[DataFrame, EventstreamSchema], Any]


def _default_func_positive(eventstream: Eventstream, positive_target_events: list[str]) -> pd.DataFrame:
    user_col = eventstream.schema.user_id
    time_col = eventstream.schema.event_timestamp
    event_col = eventstream.schema.event_name
    df = eventstream.to_dataframe()

    positive_events_index = (
        df[df[event_col].isin(positive_target_events)].groupby(user_col)[time_col].idxmin()  # type: ignore
    )

    return df.iloc[positive_events_index]  # type: ignore


class PositiveTargetParams(ParamsModel):
    positive_target_events: List[str]
    positive_function: Callable = _default_func_positive

    _widgets = {
        'positive_function': ReteFunction,
    }


class PositiveTarget(DataProcessor):
    params: PositiveTargetParams

    def __init__(self, params: PositiveTargetParams):
        super().__init__(params=params)

    def apply(self, eventstream: Eventstream) -> Eventstream:
        type_col = eventstream.schema.event_type
        event_col = eventstream.schema.event_name

        positive_function: Callable[[Eventstream, list[str]], pd.DataFrame] = self.params.positive_function
        positive_target_events = self.params.positive_target_events

        positive_targets = positive_function(eventstream, positive_target_events)
        positive_targets[type_col] = "positive_target"
        positive_targets[event_col] = "positive_target_" + positive_targets[event_col]
        positive_targets["ref"] = None

        eventstream = Eventstream(
            raw_data_schema=eventstream.schema.to_raw_data_schema(),
            raw_data=positive_targets,
            relations=[{"raw_col": "ref", "eventstream": eventstream}],
        )
        return eventstream
