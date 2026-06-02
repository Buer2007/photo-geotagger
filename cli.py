"""
cli.py — 照片GPS轨迹合并工具（命令行版）

用法:
    python cli.py --gpx track.gpx --photos ./photos/
    python cli.py --gpx track1.gpx track2.gpx --photos ./photos/ --output ./output/
    python cli.py --gpx track.gpx --photos ./photos/ --mode nearest --threshold 120
    python cli.py --gpx track.gpx --photos ./photos/ --timezone +8 --dry-run
"""

import argparse
import sys
import os
from geotagger import geotag_photos, load_gpx, read_photo_time


def main():
    parser = argparse.ArgumentParser(
        description="照片GPS轨迹合并工具 — 根据GPS轨迹为照片添加地理位置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  基本用法（插值模式，覆盖原文件）:
    python cli.py --gpx track.gpx --photos ./photos/

  输出到新目录:
    python cli.py --gpx track.gpx --photos ./photos/ --output ./geotagged/

  多个GPX文件:
    python cli.py --gpx track1.gpx track2.gpx --photos ./photos/

  指定时区（东八区）:
    python cli.py --gpx track.gpx --photos ./photos/ --timezone +8

  试运行（不修改文件）:
    python cli.py --gpx track.gpx --photos ./photos/ --dry-run
        """,
    )

    parser.add_argument(
        "--gpx",
        nargs="+",
        required=True,
        help="GPX轨迹文件路径（可指定多个）",
    )
    parser.add_argument(
        "--photos",
        required=True,
        help="照片目录路径",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出目录（默认覆盖原文件）",
    )
    parser.add_argument(
        "--mode",
        choices=["interpolate", "nearest"],
        default="interpolate",
        help="匹配模式: interpolate=线性插值(默认), nearest=最近点",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="最大允许时间差，单位秒（默认60）",
    )
    parser.add_argument(
        "--timezone",
        type=float,
        default=0.0,
        help="照片EXIF时间的时区偏移，单位小时（如东八区为+8，默认0即UTC）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，只显示匹配结果不写入文件",
    )

    args = parser.parse_args()

    # 验证GPX文件存在
    for gpx_path in args.gpx:
        if not os.path.isfile(gpx_path):
            print(f"错误: GPX文件不存在: {gpx_path}", file=sys.stderr)
            sys.exit(1)

    # 验证照片目录存在
    if not os.path.isdir(args.photos):
        print(f"错误: 照片目录不存在: {args.photos}", file=sys.stderr)
        sys.exit(1)

    # 显示配置信息
    print("=" * 50)
    print("  照片GPS轨迹合并工具")
    print("=" * 50)
    print(f"  GPX文件:  {', '.join(args.gpx)}")
    print(f"  照片目录: {args.photos}")
    print(f"  输出目录: {args.output or '(覆盖原文件)'}")
    print(f"  匹配模式: {args.mode}")
    print(f"  时间阈值: {args.threshold} 秒")
    print(f"  时区偏移: {args.timezone:+.1f} 小时")
    if args.dry_run:
        print(f"  模式:     *** 试运行（不修改文件）***")
    print("=" * 50)
    print()

    # 显示轨迹信息
    try:
        points = load_gpx(args.gpx)
        if not points:
            print("警告: GPX文件中未找到轨迹点", file=sys.stderr)
            sys.exit(1)
        print(f"轨迹点数量: {len(points)}")
        print(f"时间范围:   {points[0].time.strftime('%Y-%m-%d %H:%M:%S')} ~ "
              f"{points[-1].time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
        print()
    except Exception as e:
        print(f"错误: 无法解析GPX文件: {e}", file=sys.stderr)
        sys.exit(1)

    # 处理照片
    print("开始处理...")
    print("-" * 50)

    success_count = 0
    skip_count = 0
    fail_count = 0

    def on_progress(result):
        nonlocal success_count, skip_count, fail_count
        filename = os.path.basename(result.photo_path)

        if result.success:
            success_count += 1
            elev_str = f", 海拔 {result.elevation:.1f}m" if result.elevation else ""
            diff_str = f" (时间差 {result.time_diff:.1f}s)" if result.time_diff else ""
            print(f"  ✓ {filename} → {result.latitude:.6f}, {result.longitude:.6f}{elev_str}{diff_str}")
        elif result.time_diff is not None:
            skip_count += 1
            print(f"  ⚠ {filename} → {result.message}")
        else:
            fail_count += 1
            print(f"  ✗ {filename} → {result.message}")

    try:
        results = geotag_photos(
            gpx_paths=args.gpx,
            photo_dir=args.photos,
            output_dir=args.output,
            mode=args.mode,
            threshold=args.threshold,
            timezone_offset=args.timezone,
            dry_run=args.dry_run,
            callback=on_progress,
        )
    except Exception as e:
        print(f"\n错误: 处理过程中出错: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出统计
    print("-" * 50)
    print(f"处理完成！")
    print(f"  成功: {success_count} 张")
    print(f"  跳过: {skip_count} 张（时间差超出阈值）")
    print(f"  失败: {fail_count} 张")
    print(f"  总计: {len(results)} 张")

    if args.dry_run:
        print()
        print("提示: 以上为试运行结果，未修改任何文件。")
        print("      去掉 --dry-run 参数即可实际写入GPS数据。")


if __name__ == "__main__":
    main()
