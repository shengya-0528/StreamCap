from enum import Enum
from typing import Optional


class FluctuationMode(Enum):
    """波动检测状态机：5 种状态"""
    DETECTING = "detecting"       # 刚检测到中断，开始波动检测
    RETRYING = "retrying"         # 指数退避重试中
    CONFIRMED_DOWN = "confirmed_down"  # 累计等待达标，确认下播
    LIVEDURING = "liveduring"     # 波动中检测到直播恢复
    EXHAUSTED = "exhausted"       # 达到最大重试次数


class FluctuationDetector:
    """波动检测器：按节奏表执行指数退避重试。"""

    def __init__(self, loop_time_seconds: int = 180, max_retries: int = 20):
        self.loop_time_seconds = loop_time_seconds
        self.max_retries = max_retries
        self.current_retry: Optional[int] = None
        self.cumulative_wait: Optional[int] = None

    def get_retry_wait(self, n: int) -> int:
        """返回第 n 次重试的等待时长（秒），按用户要求 B 方案节奏表。"""
        if n == 1:
            return 0
        if n == 2:
            return 5
        if n == 3:
            return 15
        if n == 4:
            return 30
        if n == 5:
            return 45
        return 60 + (n - 6) * 30

    def get_cumulative_wait(self, n: int) -> int:
        """返回前 n 次累计等待时长（秒）。"""
        return sum(self.get_retry_wait(i) for i in range(1, n + 1))

    def is_in_fluctuation(self) -> bool:
        """判断是否在波动检测中。"""
        return self.current_retry is not None

    def should_confirm_down(self) -> bool:
        """判断是否累计等待达标，可确认下播退出波动模式。"""
        return (
            self.cumulative_wait is not None
            and self.cumulative_wait >= self.loop_time_seconds
        )

    def should_give_up(self) -> bool:
        """判断是否达到最大重试次数，应放弃波动检测。"""
        return (
            self.current_retry is not None
            and self.current_retry >= self.max_retries
        )

    def next_retry(self) -> int:
        """推进一次重试，返回当前重试次数。"""
        if self.current_retry is None:
            self.current_retry = 1
            self.cumulative_wait = 0
        else:
            self.current_retry += 1
            self.cumulative_wait += self.get_retry_wait(self.current_retry)
        return self.current_retry

    def reset(self):
        """重置到初始状态（掉线重新触发时调用）。"""
        self.current_retry = None
        self.cumulative_wait = None
