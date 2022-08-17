from typing import Callable, Any, Optional

from pandas import DataFrame

from src.data_processor.data_processor import ReteDataProcessor
from src.eventstream.eventstream import Eventstream
from src.eventstream.schema import EventstreamSchema
from src.params_model import ReteParamsModel

EventstreamFilter = Callable[[DataFrame, EventstreamSchema], Any]


class SimpleGroupParams(ReteParamsModel):
    event_name: str
    filter: EventstreamFilter
    event_type: Optional[str] = 'group_alias'


class SimpleGroup(ReteDataProcessor):
    params: SimpleGroupParams

    def __init__(self, params: SimpleGroupParams) -> None:
        super().__init__(params=params)

    def apply(self, eventstream: Eventstream) -> Eventstream:
        event_name = self.params.event_name
        filter_: Callable = self.params.filter
        event_type = self.params.event_type

        events = eventstream.to_dataframe()
        mathed_events_q = filter_(events, eventstream.schema)
        matched_events = events[mathed_events_q].copy()

        if event_type is not None:
            matched_events[eventstream.schema.event_type] = event_type

        matched_events[eventstream.schema.event_name] = event_name
        matched_events["ref"] = matched_events[eventstream.schema.event_id]

        return Eventstream(
            raw_data=matched_events,
            raw_data_schema=eventstream.schema.to_raw_data_schema(),
            relations=[{"raw_col": "ref", "evenstream": eventstream}],
        )
