"""
geotagger.py — 照片GPS轨迹合并核心模块

功能：
1. 解析GPX轨迹文件
2. 读取照片EXIF拍摄时间
3. 按时间戳匹配GPS坐标（支持插值/最近点）
4. 将GPS坐标写入照片EXIF
"""

import os
from datetime import datetime, timezone, timedelta
from bisect import bisect_left, bisect_right
from typing import List, Tuple, Optional, NamedTuple

import gpxpy
import piexif


# ============================================================
# 数据结构
# ============================================================

class TrackPoint(NamedTuple):
    """GPX轨迹点"""
    time: datetime       # UTC时间
    latitude: float      # 纬度（十进制度）
    longitude: float     # 经度（十进制度）
    elevation: Optional[float]  # 海拔（米）


class MatchResult(NamedTuple):
    """匹配结果"""
    photo_path: str
    success: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    time_diff: Optional[float] = None   # 时间差（秒）
    message: str = ""


# ============================================================
# GPX轨迹解析
# ============================================================

def load_gpx(gpx_paths: List[str]) -> List[TrackPoint]:
    """
    加载一个或多个GPX文件，返回按时间排序的轨迹点列表。

    参数:
        gpx_paths: GPX文件路径列表

    返回:
        按时间升序排列的 TrackPoint 列表
    """
    all_points: List[TrackPoint] = []

    for path in gpx_paths:
        with open(path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time is None:
                        continue
                    t = point.time
                    if t.tzinfo is None:
                        t = t.replace(tzinfo=timezone.utc)
                    else:
                        t = t.astimezone(timezone.utc)
                    all_points.append(TrackPoint(
                        time=t,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        elevation=point.elevation,
                    ))

        for route in gpx.routes:
            for point in route.points:
                if point.time is None:
                    continue
                t = point.time
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                else:
                    t = t.astimezone(timezone.utc)
                all_points.append(TrackPoint(
                    time=t,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    elevation=point.elevation,
                ))

    all_points.sort(key=lambda p: p.time)
    return all_points


# ============================================================
# 照片EXIF时间读取
# ============================================================

def read_photo_time(photo_path: str, timezone_offset: float = 0.0) -> Optional[datetime]:
    """
    读取照片EXIF中的拍摄时间（DateTimeOriginal），并转换为UTC。

    参数:
        photo_path: 照片文件路径
        timezone_offset: 时区偏移（小时），例如东八区为 +8.0

    返回:
        UTC时间，如果无法读取则返回 None
    """
    try:
        exif_dict = piexif.load(photo_path)
    except Exception:
        return None

    exif_ifd = exif_dict.get("Exif", {})
    raw_time = (
        exif_ifd.get(piexif.ExifIFD.DateTimeOriginal)
        or exif_ifd.get(piexif.ExifIFD.DateTimeDigitized)
    )

    if raw_time is None:
        zeroth_ifd = exif_dict.get("0th", {})
        raw_time = zeroth_ifd.get(piexif.ImageIFD.DateTime)

    if raw_time is None:
        return None

    if isinstance(raw_time, bytes):
        raw_time = raw_time.decode('utf-8', errors='ignore')

    try:
        local_time = datetime.strptime(raw_time, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None

    tz = timezone(timedelta(hours=timezone_offset))
    local_time = local_time.replace(tzinfo=tz)
    utc_time = local_time.astimezone(timezone.utc)

    return utc_time


# ============================================================
# 时间匹配算法
# ============================================================

def _find_nearest_index(points: List[TrackPoint], target_time: datetime) -> int:
    """二分查找时间最接近的轨迹点索引"""
    times = [p.time for p in points]
    idx = bisect_left(times, target_time)

    if idx == 0:
        return 0
    if idx >= len(points):
        return len(points) - 1

    before = times[idx - 1]
    after = times[idx]

    if (target_time - before) <= (after - target_time):
        return idx - 1
    else:
        return idx


def match_nearest(
    points: List[TrackPoint],
    photo_time: datetime,
    threshold: float = 60.0,
) -> Tuple[Optional[TrackPoint], float]:
    """
    最近点直接匹配模式。

    返回:
        (匹配的轨迹点, 时间差秒数)，超阈值则返回 (None, time_diff)
    """
    if not points:
        return None, 0.0

    idx = _find_nearest_index(points, photo_time)
    nearest = points[idx]
    diff = abs((photo_time - nearest.time).total_seconds())

    if diff > threshold:
        return None, diff

    return nearest, diff


def match_interpolate(
    points: List[TrackPoint],
    photo_time: datetime,
    threshold: float = 60.0,
) -> Tuple[Optional[TrackPoint], float]:
    """
    线性插值匹配模式。

    在照片时间前后的两个轨迹点之间进行线性插值，
    计算精确的经纬度和海拔。

    返回:
        (插值后的轨迹点, 时间差秒数)，超阈值则返回 (None, time_diff)
    """
    if not points:
        return None, 0.0

    if len(points) == 1:
        diff = abs((photo_time - points[0].time).total_seconds())
        if diff > threshold:
            return None, diff
        return points[0], diff

    times = [p.time for p in points]
    idx = bisect_right(times, photo_time)

    if idx == 0:
        diff = abs((photo_time - points[0].time).total_seconds())
        if diff > threshold:
            return None, diff
        return points[0], diff

    if idx >= len(points):
        diff = abs((photo_time - points[-1].time).total_seconds())
        if diff > threshold:
            return None, diff
        return points[-1], diff

    p1 = points[idx - 1]
    p2 = points[idx]

    total_sec = (p2.time - p1.time).total_seconds()
    if total_sec == 0:
        return p1, 0.0

    elapsed = (photo_time - p1.time).total_seconds()
    ratio = elapsed / total_sec

    lat = p1.latitude + ratio * (p2.latitude - p1.latitude)
    lon = p1.longitude + ratio * (p2.longitude - p1.longitude)

    elev = None
    if p1.elevation is not None and p2.elevation is not None:
        elev = p1.elevation + ratio * (p2.elevation - p1.elevation)

    interpolated = TrackPoint(
        time=photo_time,
        latitude=lat,
        longitude=lon,
        elevation=elev,
    )

    diff = min(
        abs((photo_time - p1.time).total_seconds()),
        abs((photo_time - p2.time).total_seconds()),
    )

    if diff > threshold:
        return None, diff

    return interpolated, diff


# ============================================================
# EXIF GPS写入
# ============================================================

def _decimal_to_dms_rational(value: float):
    """
    将十进制度数转换为 EXIF GPS 所需的度/分/秒有理数格式。
    """
    value = abs(value)
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds_float = (minutes_float - minutes) * 60
    seconds_num = round(seconds_float * 100)
    seconds_den = 100

    return (
        (degrees, 1),
        (minutes, 1),
        (seconds_num, seconds_den),
    )


def write_gps_to_photo(
    photo_path: str,
    latitude: float,
    longitude: float,
    elevation: Optional[float] = None,
    output_path: Optional[str] = None,
) -> bool:
    """
    将GPS坐标写入照片EXIF。

    参数:
        photo_path: 原始照片路径
        latitude: 纬度（十进制度，正=N，负=S）
        longitude: 经度（十进制度，正=E，负=W）
        elevation: 海拔（米），可选
        output_path: 输出路径，None则覆盖原文件

    返回:
        是否成功
    """
    try:
        exif_dict = piexif.load(photo_path)
    except Exception:
        return False

    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 3, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
        piexif.GPSIFD.GPSLatitude: _decimal_to_dms_rational(latitude),
        piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
        piexif.GPSIFD.GPSLongitude: _decimal_to_dms_rational(longitude),
    }

    if elevation is not None:
        alt_ref = 0 if elevation >= 0 else 1
        gps_ifd[piexif.GPSIFD.GPSAltitudeRef] = alt_ref
        alt_cm = round(abs(elevation) * 100)
        gps_ifd[piexif.GPSIFD.GPSAltitude] = (alt_cm, 100)

    exif_dict["GPS"] = gps_ifd

    try:
        exif_bytes = piexif.dump(exif_dict)
    except Exception:
        return False

    target = output_path if output_path else photo_path

    if output_path is None:
        tmp_path = photo_path + ".tmp"
        try:
            with open(photo_path, 'rb') as f:
                data = f.read()
            new_data = piexif.insert(exif_bytes, data)
            with open(tmp_path, 'wb') as f:
                f.write(new_data)
            os.replace(tmp_path, photo_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False
    else:
        try:
            with open(photo_path, 'rb') as f:
                data = f.read()
            new_data = piexif.insert(exif_bytes, data)
            os.makedirs(os.path.dirname(target) or '.', exist_ok=True)
            with open(target, 'wb') as f:
                f.write(new_data)
        except Exception:
            return False

    return True


# ============================================================
# 批量处理
# ============================================================

def geotag_photos(
    gpx_paths: List[str],
    photo_dir: str,
    output_dir: Optional[str] = None,
    mode: str = "interpolate",
    threshold: float = 60.0,
    timezone_offset: float = 0.0,
    dry_run: bool = False,
    callback=None,
) -> List[MatchResult]:
    """
    批量为照片添加GPS标签。

    参数:
        gpx_paths: GPX文件路径列表
        photo_dir: 照片目录路径
        output_dir: 输出目录（None则覆盖原文件）
        mode: 匹配模式 "interpolate" 或 "nearest"
        threshold: 时间阈值（秒）
        timezone_offset: 时区偏移（小时）
        dry_run: 试运行模式，不写入文件
        callback: 进度回调函数 callback(result: MatchResult)

    返回:
        MatchResult 列表
    """
    points = load_gpx(gpx_paths)
    if not points:
        return []

    photo_extensions = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
    photo_files = []
    for root, dirs, files in os.walk(photo_dir):
        for f in files:
            if os.path.splitext(f)[1] in photo_extensions:
                photo_files.append(os.path.join(root, f))
    photo_files.sort()

    match_fn = match_interpolate if mode == "interpolate" else match_nearest

    results: List[MatchResult] = []

    for photo_path in photo_files:
        photo_time = read_photo_time(photo_path, timezone_offset)
        if photo_time is None:
            result = MatchResult(
                photo_path=photo_path,
                success=False,
                message="无法读取EXIF拍摄时间",
            )
            results.append(result)
            if callback:
                callback(result)
            continue

        matched_point, time_diff = match_fn(points, photo_time, threshold)

        if matched_point is None:
            result = MatchResult(
                photo_path=photo_path,
                success=False,
                time_diff=time_diff,
                message=f"无匹配轨迹点（最近时间差 {time_diff:.1f} 秒，阈值 {threshold:.0f} 秒）",
            )
            results.append(result)
            if callback:
                callback(result)
            continue

        if dry_run:
            result = MatchResult(
                photo_path=photo_path,
                success=True,
                latitude=matched_point.latitude,
                longitude=matched_point.longitude,
                elevation=matched_point.elevation,
                time_diff=time_diff,
                message=f"[试运行] {matched_point.latitude:.6f}, {matched_point.longitude:.6f}",
            )
        else:
            out_path = None
            if output_dir:
                rel = os.path.relpath(photo_path, photo_dir)
                out_path = os.path.join(output_dir, rel)

            ok = write_gps_to_photo(
                photo_path,
                matched_point.latitude,
                matched_point.longitude,
                matched_point.elevation,
                output_path=out_path,
            )

            if ok:
                result = MatchResult(
                    photo_path=photo_path,
                    success=True,
                    latitude=matched_point.latitude,
                    longitude=matched_point.longitude,
                    elevation=matched_point.elevation,
                    time_diff=time_diff,
                    message=f"✓ {matched_point.latitude:.6f}, {matched_point.longitude:.6f}",
                )
            else:
                result = MatchResult(
                    photo_path=photo_path,
                    success=False,
                    message="EXIF写入失败",
                )

        results.append(result)
        if callback:
            callback(result)

    return results
