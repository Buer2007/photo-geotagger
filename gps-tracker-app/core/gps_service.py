"""
gps_service.py — GPS后台记录服务

核心功能：
1. 使用 plyer 获取GPS位置更新
2. 按时间间隔记录轨迹点
3. 后台持续运行
4. 过滤精度差的点
"""

import time
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict

try:
    from plyer import gps
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False


@dataclass
class TrackPoint:
    """单个GPS轨迹点"""
    timestamp: str          # ISO 8601 UTC时间
    latitude: float         # 纬度
    longitude: float        # 经度
    altitude: float = 0.0   # 海拔（米）
    accuracy: float = 0.0   # 精度（米）
    speed: float = 0.0      # 速度（m/s）
    bearing: float = 0.0    # 方向（度）

    def to_dict(self) -> dict:
        return asdict(self)


class GPSService:
    """GPS记录服务"""

    def __init__(self):
        self.is_recording = False
        self.current_track: List[TrackPoint] = []
        self.start_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._gps_started = False

        # 回调函数
        self.on_location_update: Optional[Callable] = None
        self.on_status_change: Optional[Callable] = None

        # 配置
        self.min_accuracy = 50.0     # 最大允许精度误差（米）
        self.update_interval = 5     # 记录间隔（秒）

        # Android WakeLock（防止CPU休眠）
        self._wakelock = None

    def _acquire_wakelock(self):
        """获取WakeLock，防止CPU休眠"""
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            PowerManager = autoclass('android.os.PowerManager')

            pm = PythonActivity.mActivity.getSystemService(Context.POWER_SERVICE)
            self._wakelock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                'GPSTracker::WakeLock'
            )
            self._wakelock.acquire()
        except Exception as e:
            print(f"无法获取WakeLock: {e}")

    def _release_wakelock(self):
        """释放WakeLock"""
        try:
            if self._wakelock:
                self._wakelock.release()
                self._wakelock = None
        except Exception as e:
            print(f"释放WakeLock失败: {e}")

    def start_recording(self):
        """开始记录GPS轨迹"""
        if self.is_recording:
            return

        with self._lock:
            self.current_track = []
            self.start_time = datetime.now(timezone.utc)
            self.is_recording = True

        # 获取WakeLock
        self._acquire_wakelock()

        # 启动GPS
        if GPS_AVAILABLE:
            try:
                gps.configure(
                    on_location=self._on_location,
                    on_status=self._on_status,
                )
                gps.start(minTime=self.update_interval * 1000, minDistance=0)
                self._gps_started = True
            except Exception as e:
                print(f"GPS启动失败: {e}")
                self._gps_started = False

        if self.on_status_change:
            self.on_status_change("recording")

    def stop_recording(self) -> List[TrackPoint]:
        """
        停止记录，返回轨迹点列表。

        返回:
            TrackPoint 列表（深拷贝）
        """
        if not self.is_recording:
            return []

        with self._lock:
            self.is_recording = False

        # 停止GPS
        if self._gps_started:
            try:
                gps.stop()
            except Exception as e:
                print(f"GPS停止失败: {e}")
            self._gps_started = False

        # 释放WakeLock
        self._release_wakelock()

        if self.on_status_change:
            self.on_status_change("stopped")

        # 返回轨迹副本
        with self._lock:
            return list(self.current_track)

    def _on_location(self, **kwargs):
        """GPS位置更新回调"""
        if not self.is_recording:
            return

        lat = kwargs.get('lat', 0)
        lon = kwargs.get('lon', 0)
        altitude = kwargs.get('altitude', 0) or 0
        accuracy = kwargs.get('accuracy', 999) or 999
        speed = kwargs.get('speed', 0) or 0
        bearing = kwargs.get('bearing', 0) or 0

        # 过滤精度差的点
        if accuracy > self.min_accuracy:
            return

        point = TrackPoint(
            timestamp=datetime.now(timezone.utc).isoformat(),
            latitude=lat,
            longitude=lon,
            altitude=altitude,
            accuracy=accuracy,
            speed=speed,
            bearing=bearing,
        )

        with self._lock:
            self.current_track.append(point)

        # 触发回调
        if self.on_location_update:
            self.on_location_update(point)

    def _on_status(self, **kwargs):
        """GPS状态回调"""
        status = kwargs.get('status', '')
        if self.on_status_change:
            self.on_status_change(status)

    def get_current_stats(self) -> dict:
        """获取当前轨迹统计信息"""
        with self._lock:
            points = list(self.current_track)

        if not points:
            return {
                'point_count': 0,
                'distance': 0.0,
                'duration': 0,
                'current_lat': 0,
                'current_lon': 0,
                'current_alt': 0,
                'current_accuracy': 0,
            }

        # 计算总距离
        distance = 0.0
        for i in range(1, len(points)):
            distance += self._haversine(
                points[i-1].latitude, points[i-1].longitude,
                points[i].latitude, points[i].longitude,
            )

        # 计算持续时间
        duration = 0
        if self.start_time:
            duration = int((datetime.now(timezone.utc) - self.start_time).total_seconds())

        last = points[-1]
        return {
            'point_count': len(points),
            'distance': distance,
            'duration': duration,
            'current_lat': last.latitude,
            'current_lon': last.longitude,
            'current_alt': last.altitude,
            'current_accuracy': last.accuracy,
        }

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点之间的距离（米），使用Haversine公式"""
        import math
        R = 6371000  # 地球半径（米）

        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
