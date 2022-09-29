from __future__ import annotations

import pandas as pd
import pytest

from pydantic import ValidationError
from src.data_processors_lib.rete import LostUsersEvents, LostUsersParams
from src.eventstream.eventstream import Eventstream
from src.eventstream.schema import EventstreamSchema, RawDataSchema
from src.graph.p_graph import PGraph, EventsNode


class TestLostUsers:
    def test_lost_users_apply__lost_users_list(self):
        source_df = pd.DataFrame([
            [1, 'event1', '2022-01-01 00:01:00'],
            [1, 'event1', '2022-01-01 00:02:00'],
            [1, 'event2', '2022-01-01 00:01:02'],
            [1, 'event1', '2022-01-01 00:03:00'],
            [1, 'event1', '2022-01-01 00:04:00'],
            [1, 'event1', '2022-01-01 00:05:00'],
            [2, 'event1', '2022-01-02 00:00:00'],
            [2, 'event1', '2022-01-02 00:00:05'],
            [2, 'event2', '2022-01-02 00:00:05'],
        ], columns=['user_id', 'event', 'timestamp']
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event", event_timestamp="timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )

        events = LostUsersEvents(params=LostUsersParams(lost_users_list=[2], lost_cutoff=None))

        correct_result_columns = ['user_id', 'event_name', 'event_type', 'event_timestamp']

        correct_result = pd.DataFrame([
            [1, 'absent_user', 'absent_user', '2022-01-01 00:05:00'],
            [2, 'lost_user', 'lost_user', '2022-01-02 00:00:05']
        ], columns=correct_result_columns
        )
        result = events.apply(source)
        result_df = result.to_dataframe()[correct_result_columns].reset_index(drop=True)

        assert result_df.compare(correct_result).shape == (0, 0)

    def test_lost_users_apply__lost_cutoff(self):
        source_df = pd.DataFrame([
            [1, 'event1', '2022-01-01 00:01:00'],
            [1, 'event1', '2022-01-01 00:02:00'],
            [1, 'event2', '2022-01-01 00:01:02'],
            [1, 'event1', '2022-01-01 00:03:00'],
            [1, 'event1', '2022-01-01 00:04:00'],
            [1, 'event1', '2022-01-01 00:05:00'],
            [2, 'event1', '2022-01-02 00:00:00'],
            [2, 'event1', '2022-01-02 00:00:05'],
            [2, 'event2', '2022-01-02 00:00:05'],
        ], columns=['user_id', 'event', 'timestamp']
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event", event_timestamp="timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )

        events = LostUsersEvents(params=LostUsersParams(lost_users_list=None, lost_cutoff=(4, 'h')))

        correct_result_columns = ['user_id', 'event_name', 'event_type', 'event_timestamp']

        correct_result = pd.DataFrame([
            [1, 'lost_user', 'lost_user', '2022-01-01 00:05:00'],
            [2, 'absent_user', 'absent_user', '2022-01-02 00:00:05']
        ], columns=correct_result_columns
        )
        result = events.apply(source)
        result_df = result.to_dataframe()[correct_result_columns].reset_index(drop=True)

        assert result_df.compare(correct_result).shape == (0, 0)

    def test_params_model__incorrect_datetime_unit(self):
        with pytest.raises(ValidationError):
            p = LostUsersParams(lost_cutoff=(1, 'xxx'))


class TestLostUsersGraph:
    def test_lost_users_graph__lost_users_list(self):
        source_df = pd.DataFrame([
            [1, 'event1', '2022-01-01 00:01:00'],
            [1, 'event2', '2022-01-01 00:01:02'],
            [1, 'event1', '2022-01-01 00:02:00'],
            [1, 'event1', '2022-01-01 00:03:00'],
            [1, 'event1', '2022-01-01 00:04:00'],
            [1, 'event1', '2022-01-01 00:05:00'],
            [2, 'event1', '2022-01-02 00:00:00'],
            [2, 'event1', '2022-01-02 00:00:05'],
            [2, 'event2', '2022-01-02 00:00:05'],
        ], columns=['user_id', 'event', 'timestamp']
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event", event_timestamp="timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )
        graph = PGraph(source_stream=source)
        events = EventsNode(LostUsersEvents(params=LostUsersParams(lost_users_list=[2], lost_cutoff=None)))
        graph.add_node(node=events, parents=[graph.root])
        correct_result_columns = ['user_id', 'event_name', 'event_type', 'event_timestamp']

        correct_result = pd.DataFrame([
            [1, 'event1', 'raw', '2022-01-01 00:01:00'],
            [1, 'event2', 'raw', '2022-01-01 00:01:02'],
            [1, 'event1', 'raw', '2022-01-01 00:02:00'],
            [1, 'event1', 'raw', '2022-01-01 00:03:00'],
            [1, 'event1', 'raw', '2022-01-01 00:04:00'],
            [1, 'event1', 'raw', '2022-01-01 00:05:00'],
            [1, 'absent_user', 'absent_user', '2022-01-01 00:05:00'],
            [2, 'event1', 'raw', '2022-01-02 00:00:00'],
            [2, 'event1', 'raw', '2022-01-02 00:00:05'],
            [2, 'event2', 'raw', '2022-01-02 00:00:05'],
            [2, 'lost_user', 'lost_user', '2022-01-02 00:00:05']
        ], columns=correct_result_columns
        )

        result = graph.combine(node=events)
        result_df = result.to_dataframe()[correct_result_columns].reset_index(drop=True)

        assert result_df.compare(correct_result).shape == (0, 0)

    def test_lost_users_graph__lost_cutoff(self):
        source_df = pd.DataFrame([
            [1, 'event1', '2022-01-01 00:01:00'],
            [1, 'event1', '2022-01-01 00:02:00'],
            [1, 'event2', '2022-01-01 00:01:02'],
            [1, 'event1', '2022-01-01 00:03:00'],
            [1, 'event1', '2022-01-01 00:04:00'],
            [1, 'event1', '2022-01-01 00:05:00'],
            [2, 'event1', '2022-01-02 00:00:00'],
            [2, 'event1', '2022-01-02 00:00:05'],
            [2, 'event2', '2022-01-02 00:00:05'],
        ], columns=['user_id', 'event', 'timestamp']
        )

        source = Eventstream(
            raw_data_schema=RawDataSchema(
                event_name="event", event_timestamp="timestamp", user_id="user_id"
            ),
            raw_data=source_df,
            schema=EventstreamSchema(),
        )
        graph = PGraph(source_stream=source)
        events = EventsNode(LostUsersEvents(params=LostUsersParams(lost_users_list=None, lost_cutoff=(4, 'h'))))
        graph.add_node(node=events, parents=[graph.root])
        correct_result_columns = ['user_id', 'event_name', 'event_type', 'event_timestamp']

        correct_result = pd.DataFrame([
            [1, 'event1', 'raw', '2022-01-01 00:01:00'],
            [1, 'event2', 'raw', '2022-01-01 00:01:02'],
            [1, 'event1', 'raw', '2022-01-01 00:02:00'],
            [1, 'event1', 'raw', '2022-01-01 00:03:00'],
            [1, 'event1', 'raw', '2022-01-01 00:04:00'],
            [1, 'event1', 'raw', '2022-01-01 00:05:00'],
            [1, 'lost_user', 'lost_user', '2022-01-01 00:05:00'],
            [2, 'event1', 'raw', '2022-01-02 00:00:00'],
            [2, 'event1', 'raw', '2022-01-02 00:00:05'],
            [2, 'event2', 'raw', '2022-01-02 00:00:05'],
            [2, 'absent_user', 'absent_user', '2022-01-02 00:00:05']
        ], columns=correct_result_columns
        )
        result = graph.combine(node=events)
        result_df = result.to_dataframe()[correct_result_columns].reset_index(drop=True)

        assert result_df.compare(correct_result).shape == (0, 0)