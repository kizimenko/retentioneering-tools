from __future__ import annotations

import unittest

import pandas as pd

from src.data_processors_lib.simple_processors.delete_events import (
    DeleteEvents,
    DeleteEventsParams,
)
from src.data_processors_lib.simple_processors.simple_group import (
    SimpleGroup,
    SimpleGroupParams,
)
from src.eventstream.eventstream import Eventstream
from src.eventstream.schema import EventstreamSchema, RawDataSchema


class SimpleProcessorsTest(unittest.TestCase):
    def test_simple_group(self):
        source_df = pd.DataFrame(
            [
                {"event_name": "pageview", "event_timestamp": "2021-10-26 12:00", "user_id": "1"},
                {"event_name": "cart_btn_click", "event_timestamp": "2021-10-26 12:02", "user_id": "1"},
                {"event_name": "pageview", "event_timestamp": "2021-10-26 12:03", "user_id": "1"},
                {"event_name": "plus_icon_click", "event_timestamp": "2021-10-26 12:04", "user_id": "1"},
            ]
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event_name", event_timestamp="event_timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )

        source_df = source.to_dataframe()

        def filter_(df: pd.DataFrame, schema: EventstreamSchema) -> pd.Series[bool]:
            return df[schema.event_name].isin(["cart_btn_click", "plus_icon_click"])

        params = SimpleGroupParams(
            event_name="add_to_cart",
            event_type="group_alias",
            filter=filter_,
        )

        group = SimpleGroup(params=params)

        result = group.apply(source)
        result_df = result.to_dataframe()

        events_names: list[str] = result_df[result.schema.event_name].to_list()
        events_type: list[str] = result_df[result.schema.event_type].to_list()
        refs: list[str] = result_df["ref_0"].to_list()

        self.assertEqual(events_names, ["add_to_cart", "add_to_cart"])
        self.assertEqual(events_type, ["group_alias", "group_alias"])
        self.assertEqual(refs, [source_df.iloc[1][source.schema.event_id], source_df.iloc[3][source.schema.event_id]])

    def test_delete_factory(self):
        source_df = pd.DataFrame(
            [
                {"event_name": "pageview", "event_timestamp": "2021-10-26 12:00", "user_id": "1"},
                {"event_name": "cart_btn_click", "event_timestamp": "2021-10-26 12:02", "user_id": "1"},
                {"event_name": "pageview", "event_timestamp": "2021-10-26 12:03", "user_id": "1"},
                {"event_name": "plus_icon_click", "event_timestamp": "2021-10-26 12:04", "user_id": "1"},
            ]
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event_name", event_timestamp="event_timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )

        def filter_(df: pd.DataFrame, schema: EventstreamSchema) -> pd.Series[bool]:
            return df[schema.event_name].isin(["cart_btn_click", "plus_icon_click"])

        delete_factory = DeleteEvents(DeleteEventsParams(filter=filter_))

        result = delete_factory.apply(source)
        result_df = result.to_dataframe(show_deleted=True)
        events_names: list[str] = result_df[result.schema.event_name].to_list()

        self.assertEqual(events_names, ["cart_btn_click", "plus_icon_click"])