"""
track_manager.py — 轨迹数据管理模块

管理轨迹的存储、查询、删除等操作。
轨迹存储在应用私有目录的 tracks/ 文件夹下。
"""

import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional


class TrackManager:
    """轨迹管理器"""

    def __init__(self, base_dir: str = None):
        """
        初始化轨迹管理器。

        参数:
            base_dir: 数据存储根目录（默认使用应用目录下的 data/）
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

        self.base_dir = base_dir
        self.tracks_dir = os.path.join(base_dir, 'tracks')
        os.makedirs(self.tracks_dir, exist_ok=True)

    def save_track(
        self,
        points: List[dict],
        name: str = None,
        description: str = None,
    ) -> Optional[str]:
        """
        保存一条轨迹。

        参数:
            points: 轨迹点列表
            name: 轨迹名称（可选，默认使用开始时间）
            description: 轨迹描述

        返回:
            轨迹ID（用于后续操作），失败返回None
        """
        if not points:
            return None

        # 生成轨迹ID
        track_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # 计算统计信息
        start_time = points[0].get('timestamp', '')
        end_time = points[-1].get('timestamp', '')
        distance = self._calculate_distance(points)

        # 自动命名
        if not name:
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                name = dt.strftime('%Y-%m-%d %H:%M')
            except (ValueError, AttributeError):
                name = f"轨迹_{track_id}"

        # 轨迹数据
        track_data = {
            'id': track_id,
            'name': name,
            'description': description or '',
            'start_time': start_time,
            'end_time': end_time,
            'point_count': len(points),
            'distance': distance,
            'points': points,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        # 保存为JSON
        json_path = os.path.join(self.tracks_dir, f'{track_id}.json')
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(track_data, f, ensure_ascii=False, indent=2)
            return track_id
        except Exception as e:
            print(f"保存轨迹失败: {e}")
            return None

    def get_all_tracks(self) -> List[dict]:
        """
        获取所有轨迹列表（不含轨迹点详情，减少内存占用）。

        返回:
            轨迹摘要列表，按时间倒序排列
        """
        tracks = []
        for filename in os.listdir(self.tracks_dir):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(self.tracks_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 摘要信息（不含轨迹点）
                tracks.append({
                    'id': data['id'],
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'start_time': data['start_time'],
                    'end_time': data['end_time'],
                    'point_count': data['point_count'],
                    'distance': data.get('distance', 0),
                    'created_at': data.get('created_at', ''),
                })
            except Exception as e:
                print(f"读取轨迹文件失败 {filename}: {e}")

        # 按创建时间倒序
        tracks.sort(key=lambda t: t.get('created_at', ''), reverse=True)
        return tracks

    def get_track(self, track_id: str) -> Optional[dict]:
        """
        获取指定轨迹的完整数据（包含轨迹点）。

        参数:
            track_id: 轨迹ID

        返回:
            轨迹完整数据，不存在返回None
        """
        filepath = os.path.join(self.tracks_dir, f'{track_id}.json')
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取轨迹失败: {e}")
            return None

    def delete_track(self, track_id: str) -> bool:
        """
        删除指定轨迹。

        参数:
            track_id: 轨迹ID

        返回:
            是否成功
        """
        filepath = os.path.join(self.tracks_dir, f'{track_id}.json')
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"删除轨迹失败: {e}")
            return False

    def rename_track(self, track_id: str, new_name: str) -> bool:
        """
        重命名轨迹。

        参数:
            track_id: 轨迹ID
            new_name: 新名称

        返回:
            是否成功
        """
        track = self.get_track(track_id)
        if not track:
            return False

        track['name'] = new_name
        filepath = os.path.join(self.tracks_dir, f'{track_id}.json')
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(track, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"重命名轨迹失败: {e}")
            return False

    @staticmethod
    def _calculate_distance(points: List[dict]) -> float:
        """计算轨迹总距离（米）"""
        import math

        if len(points) < 2:
            return 0.0

        distance = 0.0
        R = 6371000  # 地球半径（米）

        for i in range(1, len(points)):
            lat1 = math.radians(points[i-1]['latitude'])
            lat2 = math.radians(points[i]['latitude'])
            dlat = math.radians(points[i]['latitude'] - points[i-1]['latitude'])
            dlon = math.radians(points[i]['longitude'] - points[i-1]['longitude'])

            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance += R * c

        return distance
