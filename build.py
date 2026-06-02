"""
build.py — 打包脚本

将照片GPS轨迹合并工具打包为 Windows exe 可执行文件。

用法:
    python build.py
"""

import subprocess
import sys
import os
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")


def clean():
    """清理之前的构建产物"""
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"已清理: {d}")
    # 清理 .spec 文件
    for f in os.listdir(PROJECT_DIR):
        if f.endswith(".spec"):
            os.remove(os.path.join(PROJECT_DIR, f))
            print(f"已清理: {f}")


def build_gui():
    """打包 GUI 版本"""
    print("\n" + "=" * 50)
    print("  打包 GUI 版本（照片GPS轨迹合并.exe）")
    print("=" * 50 + "\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "照片GPS轨迹合并",
        "--paths", PROJECT_DIR,
        "--hidden-import", "geotagger",
        "--noconfirm",
        os.path.join(PROJECT_DIR, "gui.py"),
    ]

    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("GUI 版本打包失败！")
        return False

    print("\nGUI 版本打包成功！")
    return True


def build_cli():
    """打包 CLI 版本"""
    print("\n" + "=" * 50)
    print("  打包 CLI 版本（geotagger.exe）")
    print("=" * 50 + "\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "geotagger",
        "--paths", PROJECT_DIR,
        "--hidden-import", "geotagger",
        "--noconfirm",
        os.path.join(PROJECT_DIR, "cli.py"),
    ]

    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("CLI 版本打包失败！")
        return False

    print("\nCLI 版本打包成功！")
    return True


def show_results():
    """显示打包结果"""
    print("\n" + "=" * 50)
    print("  打包完成！产物目录: dist/")
    print("=" * 50)

    if os.path.exists(DIST_DIR):
        for f in os.listdir(DIST_DIR):
            path = os.path.join(DIST_DIR, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  {f}  ({size_mb:.1f} MB)")

    print()
    print("使用方法:")
    print("  GUI版: 双击 dist/照片GPS轨迹合并.exe")
    print("  CLI版: dist/geotagger.exe --gpx track.gpx --photos ./photos/ --timezone +8")
    print()


def main():
    print("照片GPS轨迹合并工具 — 打包脚本")
    print()

    # 检查 PyInstaller 是否已安装
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("错误: PyInstaller 未安装。请先运行:")
        print("  pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple")
        sys.exit(1)

    # 检查依赖
    try:
        import gpxpy
        import piexif
        print(f"gpxpy 版本: {gpxpy.__version__}")
        print(f"piexif 版本: {piexif.VERSION if hasattr(piexif, 'VERSION') else '已安装'}")
    except ImportError as e:
        print(f"错误: 缺少依赖 {e.name}。请先运行:")
        print("  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
        sys.exit(1)

    print()

    # 清理旧构建
    clean()

    # 打包
    gui_ok = build_gui()
    cli_ok = build_cli()

    # 显示结果
    if gui_ok or cli_ok:
        show_results()
    else:
        print("\n打包失败，请检查错误信息。")
        sys.exit(1)


if __name__ == "__main__":
    main()
