import asyncio
import io
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pytz
from disnake import User, Embed, File
from matplotlib.font_manager import FontProperties
from scipy.interpolate import pchip_interpolate

from app.config import logger, config
from app.core.models import User as UserModel, BalanceHistory
from app.core.schemas import BalanceAnalyticsData
from app.core.variables import variables
from app.embeds.economy_embeds import format_report_embed
from app.localization import t
from app.utils.time_utils import time_utils


class BalanceAnalyticsService:
    def __init__(self):
        self.period_map = {
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=28),
        }
        self.period_locales = {
            "day": t("commands.balance_stats.params.period.choices.day"),
            "week": t("commands.balance_stats.params.period.choices.week"),
            "month": t("commands.balance_stats.params.period.choices.month"),
        }

    async def _fetch_data_with_initial_balance(
            self, user_id: int, period: str
    ) -> Tuple[Optional[int], List[BalanceHistory]]:
        user, _ = await UserModel.get_or_create(user_id=user_id)
        current_time = await time_utils.get_current()
        start_date = current_time - self.period_map[period]
        last_record_before_period = (
            await BalanceHistory.filter(user=user, timestamp__lt=start_date)
            .order_by("-timestamp")
            .first()
        )
        initial_balance = (
            last_record_before_period.new_balance if last_record_before_period else 0
        )
        history_in_period = await BalanceHistory.filter(
            user=user, timestamp__gte=start_date
        ).order_by("timestamp")
        return initial_balance, history_in_period

    @staticmethod
    def _calculate_stats(history: List[BalanceHistory]) -> BalanceAnalyticsData:
        gains = [h for h in history if h.change_amount > 0]
        losses = [h for h in history if h.change_amount < 0]
        total_earned = sum(h.change_amount for h in gains)
        total_lost = sum(h.change_amount for h in losses)
        if gains:
            biggest_gain = max(
                gains, key=lambda x: x.change_amount
            )
        else:
            biggest_gain = None

        if losses:
            biggest_loss = min(losses, key=lambda x: x.change_amount)
        else:
            biggest_loss = None

        return BalanceAnalyticsData(
            total_earned=total_earned,
            total_lost=abs(total_lost),
            biggest_gain_reason=(
                biggest_gain.reason
                if biggest_gain
                else t("ui.analytics.no_data")
            ),
            biggest_gain_amount=(
                biggest_gain.change_amount
                if biggest_gain else 0
            ),
            biggest_loss_reason=(
                biggest_loss.reason
                if biggest_loss
                else t("ui.analytics.no_data")
            ),
            biggest_loss_amount=(
                abs(biggest_loss.change_amount)
                if biggest_loss else 0
            ),
        )

    @staticmethod
    def _downsample_data(
            dates: List[datetime],
            balances: List[int],
            num_segments: int,
            period_start: datetime,
            period_end: datetime,
    ) -> Tuple[List[datetime], List[int]]:
        points = list(zip(dates, balances))
        if not points:
            return [], []

        start_time, end_time = period_start, period_end
        total_duration = end_time - start_time

        initial_period_balance = points[0][1]

        if total_duration.total_seconds() == 0:
            return [start_time, end_time], [initial_period_balance, balances[-1]]

        segment_duration = total_duration / num_segments

        balance_buckets: List[List[int]] = [[] for _ in range(num_segments)]
        for time, balance in points[1:]:
            time_offset = time - start_time
            bucket_index = int(time_offset.total_seconds() / segment_duration.total_seconds())
            bucket_index = min(bucket_index, num_segments - 1)
            balance_buckets[bucket_index].append(balance)

        selected_balances: List[Optional[int]] = [None] * num_segments
        last_balance = balances[-1]

        selected_balances[-1] = last_balance
        target_value = last_balance

        for i in range(num_segments - 2, -1, -1):
            current_bucket = balance_buckets[i]
            if not current_bucket:
                continue

            if target_value == 0 and any(val != 0 for val in current_bucket):
                closest_value = current_bucket[-1]
            else:
                closest_value = min(current_bucket, key=lambda x: abs(x - target_value))

            selected_balances[i] = closest_value
            target_value = closest_value

        stabilized_balances = selected_balances.copy()

        if stabilized_balances[0] is None:
            stabilized_balances[0] = initial_period_balance

        for i in range(1, num_segments):
            if stabilized_balances[i] is None:
                stabilized_balances[i] = stabilized_balances[i - 1]

        segment_end_times = [
            period_start + segment_duration * (i + 1)
            for i in range(num_segments)
        ]

        final_dates = [period_start] + segment_end_times
        final_balances = [initial_period_balance] + stabilized_balances

        return final_dates, final_balances

    @staticmethod
    def _downsample_by_taking_last(
            dates: List[datetime],
            balances: List[int],
            num_segments: int,
            period_start: datetime,
            period_end: datetime,
    ) -> Tuple[List[datetime], List[int]]:
        points = list(zip(dates, balances))
        if len(points) <= 1:
            return dates, balances

        total_duration = period_end - period_start
        if total_duration.total_seconds() <= 0:
            return dates, balances

        segment_duration = total_duration / num_segments

        last_point_in_bucket: Dict[int, Tuple[datetime, int]] = {}
        for time, balance in points:
            time_offset = time - period_start
            bucket_index = int(time_offset.total_seconds() / segment_duration.total_seconds())
            bucket_index = min(bucket_index, num_segments - 1)
            last_point_in_bucket[bucket_index] = (time, balance)

        final_points = [points[0]]

        for bucket_index in sorted(last_point_in_bucket.keys()):
            final_points.append(last_point_in_bucket[bucket_index])

        if final_points[-1] != points[-1]:
            final_points.append(points[-1])

        final_dates, final_balances = zip(*final_points)

        return list(final_dates), list(final_balances)

    async def _prepare_data_for_graph(
            self, initial_balance: int, history: List[BalanceHistory], period: str
    ) -> Tuple[List[datetime], List[int]]:
        current_time = await time_utils.get_current()

        start_date = current_time - self.period_map[period]
        utc_tz = pytz.UTC
        target_tz = pytz.timezone(config.timezone)

        dates, balances = [start_date], [initial_balance]
        for record in history:
            aware_utc_timestamp = record.timestamp.replace(tzinfo=utc_tz)
            localized_timestamp = aware_utc_timestamp.astimezone(target_tz)

            dates.append(localized_timestamp)
            balances.append(record.new_balance)
        if not history or dates[-1] < current_time:
            dates.append(current_time)
            balances.append(balances[-1])
        return dates, balances

    def _generate_graph_image_sync(
            self,
            dates: List[datetime],
            balances: List[int],
            user_name: str,
            period: str
    ) -> io.BytesIO:
        try:
            main_font = FontProperties(fname=variables.secondary_font_path)
        except Exception as e:
            logger.error(f"Could not load custom font for graph: {e}")
            main_font = FontProperties()

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        fig.patch.set_alpha(0)

        target_tz = pytz.timezone(config.timezone)

        green_line_segments = 12 if period == "day" else 14
        gray_line_segments = green_line_segments * 3

        raw_plot_dates, raw_plot_balances = self._downsample_by_taking_last(
            dates, balances,
            num_segments=gray_line_segments,
            period_start=dates[0],
            period_end=dates[-1]
        )

        if len(raw_plot_dates) >= 2:
            ax.plot(
                raw_plot_dates,
                raw_plot_balances,
                marker='o',
                linestyle='--',
                color='gray',
                linewidth=1.5,
                markersize=4,
                alpha=0.7,
                drawstyle='steps-post',
                label=t("ui.analytics.graph_legend_actual")
            )

        simplified_dates, simplified_balances = self._downsample_data(
            dates,
            balances,
            num_segments=green_line_segments,
            period_start=dates[0],
            period_end=dates[-1]
        )

        if all(item == 0 for item in simplified_balances):
            buf = io.BytesIO()
            plt.close(fig)
            return buf

        x_numeric = mdates.date2num(simplified_dates)
        y = np.array(simplified_balances)

        if len(x_numeric) >= 4:
            x_smooth_numeric = np.linspace(x_numeric.min(), x_numeric.max(), 300)
            y_smooth = pchip_interpolate(x_numeric, y, x_smooth_numeric)
            x_smooth_dates = mdates.num2date(x_smooth_numeric)
            ax.plot(
                x_smooth_dates,
                y_smooth,
                color="#4CAF50",
                linewidth=2.5,
                label=t("ui.analytics.graph_legend_trend")
            )
            ax.fill_between(
                x_smooth_dates,
                y_smooth,
                color="#4CAF50",
                alpha=0.2
            )
        elif len(x_numeric) >= 2:
            ax.plot(
                simplified_dates,
                simplified_balances,
                color="#4CAF50",
                linewidth=2.5,
                drawstyle='steps-post',
                label=t("ui.analytics.graph_legend_trend")
            )
            ax.fill_between(
                simplified_dates,
                simplified_balances,
                color="#4CAF50",
                alpha=0.2,
                step='post'
            )

        legend = ax.legend(prop=main_font, frameon=False)
        plt.setp(legend.get_texts(), color='w')

        period_str = self.period_locales.get(period, "").lower()
        ax.set_title(
            t(
                "ui.analytics.graph_title_period",
                user_name=user_name,
                period=period_str,
            ),
            fontsize=18,
            color="white",
            fontproperties=main_font,
        )
        ax.set_ylabel(
            t("ui.analytics.balance_axis"),
            fontsize=12,
            color="white",
            fontproperties=main_font,
        )
        date_format = "%H:%M" if period == "day" else "%d.%m"
        formatter = mdates.DateFormatter(date_format, tz=target_tz)
        ax.xaxis.set_major_formatter(formatter)

        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        ax.grid(
            True,
            which="both",
            linestyle="--",
            linewidth=0.5,
            color="#444444"
        )
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")

        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(main_font)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", transparent=True)
        buf.seek(0)
        plt.close(fig)
        return buf

    async def generate_user_report(
            self, user: User, period: str
    ) -> Optional[Tuple[Embed, File]]:
        initial_balance, history_in_period = (
            await self._fetch_data_with_initial_balance(user.id, period)
        )
        if len(history_in_period) == 0:
            return None

        stats = self._calculate_stats(history_in_period)

        graph_dates, graph_balances = await self._prepare_data_for_graph(
            initial_balance, history_in_period, period
        )

        image_buffer = await asyncio.to_thread(
            self._generate_graph_image_sync,
            graph_dates,
            graph_balances,
            user.display_name,
            period,
        )

        if image_buffer.getbuffer().nbytes == 0:
            logger.warning(f"Graph generation for user {user.id} resulted in an empty image")
            return None

        image_file = File(fp=image_buffer, filename="balance_graph.png")
        embed = await format_report_embed(user, stats, image_file, self.period_locales.get(period, "").lower())
        return embed, image_file


balance_analytics_service = BalanceAnalyticsService()
