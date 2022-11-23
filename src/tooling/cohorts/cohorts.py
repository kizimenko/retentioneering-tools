from __future__ import annotations

from typing import Literal, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.eventstream.types import EventstreamType

# @TODO В отдельный файл может надо такое вынести? Или может для когорт сократить список? dpanina
DATETIME_UNITS = Literal["Y", "M", "W", "D", "h", "m", "s", "ms", "us", "μs", "ns", "ps", "fs", "as"]


class Cohorts:
    """
    Class which provides methods for cohort analysis based on time.
    Users divided on cohorts depending on the time of their
    first appearance in eventstream.
    Retention rate of active users calculated in coordinates
    of the cohort period and cohort group.

    Parameters
    --------
    cohort_start_unit: :numpy_link:`DATETIME_UNITS<>`
        The way of rounding and format of the moment from which the cohort count begins.
        Minimum timestamp rounding down to the selected datetime unit.

        For example:
        We have eventstream with min timestamp - "2021-12-28 09:08:34.432456"
        The result of roundings with different DATETIME_UNITS is in ithe table below:

        +------------------------+-------------------------+
        | **cohort_start_unit** | **cohort_start_moment** |
        +------------------------+-------------------------+
        | Y                      |  2021-01-01 00:00:00    |
        +------------------------+-------------------------+
        | M                      |  2021-12-01 00:00:00    |
        +------------------------+-------------------------+
        | W                      |  2021-12-27 00:00:00    |
        +------------------------+-------------------------+
        | D                      |  2021-08-28 00:00:00    |
        +------------------------+-------------------------+

    cohort_period: Tuple(int, :numpy_link:`DATETIME_UNITS<>`)
        The cohort_period size and its ``DATETIME_UNIT``. This parameter is used in calculating:
        1) Start moments for each cohort from the moment defined with the ``cohort_start_unit`` parameter
        2) Cohort periods for each cohort from ifs start moment.
    average: bool, default=True
        If ``True`` - calculating average for each cohort period.
        If ``False`` - averaged values don't calculated.
    cut_bottom: int
        Drop from cohort_matrix 'n' rows from the bottom of the cohort matrix.
        Average is recalculated.
    cut_right: int
        Drop from cohort_matrix 'n' columns from the right side.
        Average is recalculated.
    cut_diagonal: int
        Drop from cohort_matrix diagonal with 'n' last period-group cells.
        Average is recalculated.

    Note
    ----
    Parameters ``cohort_start_unit`` and ``cohort_period`` should be consistent.
    Due to "Y" and "M" are non-fixed types it can be used only with each other
    or if ``cohort_period_unit`` is more detailed than ``cohort_start_unit``.
    More information: :numpy_timedelta_link:`About timedelta`<>
    """

    __eventstream: EventstreamType
    cohort_period: int | None
    cohort_period_unit: DATETIME_UNITS | None
    cohort_start_unit: DATETIME_UNITS | None
    DATETIME_UNITS_LIST = ["Y", "M", "W", "D", "h", "m", "s", "ms", "us", "μs", "ns", "ps", "fs", "as"]

    def __init__(self, eventstream: EventstreamType):
        self.__eventstream = eventstream
        self.user_col = self.__eventstream.schema.user_id
        self.event_col = self.__eventstream.schema.event_name
        self.time_col = self.__eventstream.schema.event_timestamp
        self.average = True
        self.cohort_start_unit = None
        self.cohort_period, self.cohort_period_unit = None, None
        self.cut_diagonal = 0
        self.cut_bottom = 0
        self.cut_right = 0

        data = self.__eventstream.to_dataframe()
        self.data = data
        self._cohort_matrix_result = pd.DataFrame

    def fit_cohorts(
        self,
        cohort_start_unit: DATETIME_UNITS,
        cohort_period: Tuple[int, DATETIME_UNITS],
        average: bool = True,
        cut_bottom: int = 0,
        cut_right: int = 0,
        cut_diagonal: int = 0,
    ):
        """
        Calculates cohort matrix with retention rate of active users in coordinates
        of the cohort period and cohort group.

        Returns
        -------
        pd.DataFrame

        Note
        ----
        Only cohorts with at least 1 user are shown.

        """
        self.average = average
        self.cohort_start_unit = cohort_start_unit
        self.cohort_period, self.cohort_period_unit = cohort_period
        self.cut_diagonal = cut_diagonal
        self.cut_bottom = cut_bottom
        self.cut_right = cut_right

        if self.cohort_period <= 0:
            raise ValueError("cohort_period should be positive integer!")

        # @TODO добавить ссылку на numpy с объяснением. dpanina
        if self.cohort_period_unit in ["Y", "M"] and self.cohort_start_unit not in ["Y", "M"]:
            raise ValueError(
                """Parameters ``cohort_start_unit`` and ``cohort_period`` should be consistent.
                                 Due to "Y" and "M" are non-fixed types it can be used only with each other
                                 or if ``cohort_period_unit`` is more detailed than ``cohort_start_unit``.!"""
            )

        df = self._add_min_date(
            data=self.data,
            cohort_start_unit=self.cohort_start_unit,
            cohort_period=self.cohort_period,
            cohort_period_unit=self.cohort_period_unit,
        )

        cohorts = df.groupby(["CohortGroup", "CohortPeriod"])[[self.user_col]].nunique()
        cohorts.reset_index(inplace=True)

        cohorts.rename(columns={self.user_col: "TotalUsers"}, inplace=True)
        cohorts.set_index(["CohortGroup", "CohortPeriod"], inplace=True)
        cohort_group_size = cohorts["TotalUsers"].groupby(level=0).first()
        cohorts.reset_index(inplace=True)
        user_retention = (
            cohorts.pivot(index="CohortPeriod", columns="CohortGroup", values="TotalUsers").divide(
                cohort_group_size, axis=1
            )
        ).T

        user_retention = self._cut_cohort_matrix(
            df=user_retention, cut_diagonal=self.cut_diagonal, cut_bottom=self.cut_bottom, cut_right=self.cut_right
        )
        user_retention.index = user_retention.index.astype(str)
        if self.average:
            user_retention.loc["Average"] = user_retention.mean()

        self._cohort_matrix_result = user_retention

    def _add_min_date(
        self,
        data: pd.DataFrame,
        cohort_start_unit: DATETIME_UNITS,
        cohort_period: int,
        cohort_period_unit: DATETIME_UNITS,
    ) -> pd.DataFrame:

        freq = cohort_start_unit
        data["user_min_date_gr"] = data.groupby(self.user_col)[self.time_col].transform(min)
        min_cohort_date = data["user_min_date_gr"].min().to_period(freq).start_time
        max_cohort_date = data["user_min_date_gr"].max()
        if Cohorts.DATETIME_UNITS_LIST.index(cohort_start_unit) < Cohorts.DATETIME_UNITS_LIST.index(cohort_period_unit):
            freq = cohort_period_unit

        if freq == "W":
            freq = "D"

        data["user_min_date_gr"] = data["user_min_date_gr"].dt.to_period(freq)

        step = np.timedelta64(cohort_period, cohort_period_unit)
        start_point = np.datetime64(min_cohort_date, freq)
        end_point = np.datetime64(max_cohort_date, freq) + np.timedelta64(cohort_period, cohort_period_unit)

        coh_groups_start_dates = np.arange(start_point, end_point, step)
        coh_groups_start_dates = pd.to_datetime(coh_groups_start_dates).to_period(freq)
        if max_cohort_date < coh_groups_start_dates[-1].start_time:  # type: ignore
            coh_groups_start_dates = coh_groups_start_dates[:-1]  # type: ignore

        cohorts_list = pd.DataFrame(
            data=coh_groups_start_dates, index=None, columns=["CohortGroup"]  # type: ignore
        ).reset_index()
        cohorts_list.columns = ["CohortGroupNum", "CohortGroup"]  # type: ignore
        cohorts_list["CohortGroupNum"] += 1

        data["OrderPeriod"] = data[self.time_col].dt.to_period(freq)
        start_int = pd.Series(min_cohort_date.to_period(freq=freq)).view(int)[0]

        converter_freq = np.timedelta64(cohort_period, cohort_period_unit)
        converter_freq_ = converter_freq.astype(f"timedelta64[{freq}]").view(int)
        data["CohortGroupNum"] = (data["user_min_date_gr"].view(int) - start_int + converter_freq_) // converter_freq_

        data = data.merge(cohorts_list, on="CohortGroupNum", how="left")

        data["CohortPeriod"] = (
            (data["OrderPeriod"].view(int) - (data["CohortGroup"].view(int) + converter_freq_)) // converter_freq_
        ) + 1

        return data

    @staticmethod
    def _cut_cohort_matrix(
        df: pd.DataFrame, cut_bottom: int = 0, cut_right: int = 0, cut_diagonal: int = 0
    ) -> pd.DataFrame:

        for row in df.index:
            df.loc[row, max(0, df.loc[row].notna()[::-1].idxmax() + 1 - cut_diagonal) :] = None  # type: ignore

        return df.iloc[: len(df) - cut_bottom, : len(df.columns) - cut_right]

    @property
    def get_values(self):
        return self._cohort_matrix_result

    @property
    def get_params(self):
        return {
            "cohort_start_unit": self.cohort_start_unit,
            "cohort_period": (self.cohort_period, self.cohort_period_unit),
            "average": self.average,
            "cut_bottom": self.cut_bottom,
            "cut_right": self.cut_right,
            "cut_diagonal": self.cut_diagonal,
        }

    def get_heatmap(self, figsize: Tuple[float, float] = (10, 10)) -> sns.heatmap:

        """
        Build the heatmap based on the calculated cohort_matrix.

        Parameters
        --------
        figsize: Tuple[float, float], default = (10, 10)
        Is a tuple of the width and height of the figure in inches.

        Returns
        --------
        sns.heatmap

        """

        df = self._cohort_matrix_result

        plt.figure(figsize=figsize)
        sns.heatmap(df, annot=True, fmt=".1%", linewidths=1, linecolor="gray")

    def get_lineplot(
        self,
        show_plot: Literal["cohorts", "average", "all"] = "cohorts",
        figsize: Tuple[float, float] = (10, 10),
    ) -> sns.lineplot:

        """
        Build lineplots for each cohort and/or for averaged values for each cohort_period

        Parameters
        --------
        show_plot: 'cohorts', 'average' or 'all'
            if 'cohorts' - shows lineplot for each cohort
            if 'average' - shows lineplot only for all cohorts average values
            if 'all' - shows lineplot for each cohort and also for their average values
        figsize: Tuple[float, float], default = (10, 10)
            Is a tuple of the width and height of the figure in inches.

        Returns
        --------
        sns.lineplot

        """
        if show_plot not in ["cohorts", "average", "all"]:
            raise ValueError("show_plot parameter should be 'cohorts', 'average' or 'all'!")

        df_matrix = self._cohort_matrix_result
        df_wo_average = df_matrix[df_matrix.index != "Average"]  # type: ignore
        if show_plot in ["all", "average"] and "Average" not in df_matrix.index:  # type: ignore
            df_matrix.loc["Average"] = df_matrix.mean()  # type: ignore
        df_average = df_matrix[df_matrix.index == "Average"]  # type: ignore
        plt.figure(figsize=figsize)
        if show_plot == "all":
            sns.lineplot(df_wo_average.T, lw=1.5)
            sns.lineplot(df_average.T, lw=2.5, palette=["red"], marker="X", markersize=8, alpha=0.6)

        if show_plot == "average":
            sns.lineplot(df_average.T, lw=2.5, palette=["red"], marker="X", markersize=8, alpha=0.6)

        if show_plot == "cohorts":
            sns.lineplot(df_wo_average.T, lw=1.5)

        plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
        plt.xlabel("Period from the start of observation")
        plt.ylabel("Share of active users")
