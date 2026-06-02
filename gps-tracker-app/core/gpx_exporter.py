"""
gpx_exporter.py — GPX文件导出模块

生成标准GPX 1.1格式文件，兼容所有GPS轨迹合并工具。
"""

import os
from datetime import datetime, timezone
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString


def export_gpx(
    points: List[dict],
    output_path: str,
    track_name: str = None,
    track_description: str = None,
) -> bool:
    """
    将轨迹点导出为GPX文件。

    参数:
        points: 轨迹点列表，每个点包含 timestamp, latitude, longitude, altitude
        output_path: 输出GPX文件路径
        track_name: 轨迹名称（可选）
        track_description: 轨迹描述（可选）

    返回:
        是否成功
    """
    if not points:
        return False

    # GPX 1.1 命名空间
    gpx_ns = "http://www.topografix.com/GPX/1/1"
    xsi_ns = "http://www.w3.org/2001/XMLSchema-instance"
    schema_loc = "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"

    # 根元素
    gpx = Element('gpx')
    gpx.set('version', '1.1')
    gpx.set('creator', 'GPS Tracker App')
    gpx.set('xmlns', gpx_ns)
    gpx.set('xmlns:xsi', xsi_ns)
    gpx.set('xsi:schemaLocation', schema_loc)

    # 元数据
    metadata = SubElement(gpx, 'metadata')
    meta_name = SubElement(metadata, 'name')
    meta_name.text = track_name or f"轨迹_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if track_description:
        meta_desc = SubElement(metadata, 'desc')
        meta_desc.text = track_description

    meta_time = SubElement(metadata, 'time')
    meta_time.text = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # 轨迹
    trk = SubElement(gpx, 'trk')
    trk_name = SubElement(trk, 'name')
    trk_name.text = track_name or f"轨迹_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    trkseg = SubElement(trk, 'trkseg')

    # 轨迹点
    for point in points:
        trkpt = SubElement(trkseg, 'trkpt')
        trkpt.set('lat', str(point['latitude']))
        trkpt.set('lon', str(point['longitude']))

        if point.get('altitude') is not None and point['altitude'] != 0:
            ele = SubElement(trkpt, 'ele')
            ele.text = f"{point['altitude']:.1f}"

        time_elem = SubElement(trkpt, 'time')
        # 确保时间格式为ISO 8601 UTC
        ts = point['timestamp']
        if 'T' in ts and not ts.endswith('Z'):
            # 如果有时区信息但不是Z结尾，转换为Z
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                ts = dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                pass
        elif 'T' not in ts:
            # 没有T分隔符，尝试解析
            try:
                dt = datetime.fromisoformat(ts)
                ts = dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                pass
        time_elem.text = ts

        # 精度信息（非标准但有用的扩展）
        if point.get('accuracy') is not None and point['accuracy'] > 0:
            extensions = SubElement(trkpt, 'extensions')
            acc = SubElement(extensions, 'accuracy')
            acc.text = f"{point['accuracy']:.1f}"

    # 格式化输出
    xml_str = tostring(gpx, encoding='unicode')
    dom = parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding=None)

    # 移除多余的XML声明行（toprettyxml会添加）
    lines = pretty_xml.split('\n')
    if lines[0].startswith('<?xml'):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    pretty_xml = '\n'.join(lines)

    # 写入文件
    try:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        return True
    except Exception as e:
        print(f"GPX导出失败: {e}")
        return False


def generate_gpx_filename(track_name: str = None, start_time: str = None) -> str:
    """
    生成GPX文件名。

    参数:
        track_name: 轨迹名称
        start_time: 开始时间（ISO格式）

    返回:
        文件名（不含路径）
    """
    if track_name:
        # 清理文件名中的非法字符
        safe_name = ''.join(c for c in track_name if c.isalnum() or c in '-_ ')
        return f"{safe_name}.gpx"

    if start_time:
        try:
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            return f"轨迹_{dt.strftime('%Y%m%d_%H%M%S')}.gpx"
        except ValueError:
            pass

    return f"轨迹_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gpx"
