"""
gui.py — 照片GPS轨迹合并工具（图形界面版）

使用 tkinter 实现，提供文件选择、参数配置、实时日志等功能。
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

from geotagger import geotag_photos, load_gpx


class GeotaggerApp:
    """照片GPS轨迹合并工具 GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("照片GPS轨迹合并工具")
        self.root.geometry("720x680")
        self.root.resizable(True, True)

        # 变量
        self.gpx_paths = tk.StringVar()
        self.photo_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.mode_var = tk.StringVar(value="interpolate")
        self.threshold_var = tk.StringVar(value="60")
        self.timezone_var = tk.StringVar(value="8")

        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- 文件选择区 ----
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding=8)
        file_frame.pack(fill=tk.X, pady=(0, 8))

        # GPX文件
        row1 = ttk.Frame(file_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="GPX轨迹文件:", width=12).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.gpx_paths).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row1, text="浏览...", command=self._browse_gpx).pack(side=tk.LEFT)

        # 照片目录
        row2 = ttk.Frame(file_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="照片目录:", width=12).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.photo_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row2, text="浏览...", command=self._browse_photos).pack(side=tk.LEFT)

        # 输出目录
        row3 = ttk.Frame(file_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="输出目录:", width=12).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(row3, text="浏览...", command=self._browse_output).pack(side=tk.LEFT)
        ttk.Label(row3, text="(留空=覆盖原文件)", foreground="gray").pack(side=tk.LEFT, padx=4)

        # ---- 参数配置区 ----
        param_frame = ttk.LabelFrame(main_frame, text="参数配置", padding=8)
        param_frame.pack(fill=tk.X, pady=(0, 8))

        param_row = ttk.Frame(param_frame)
        param_row.pack(fill=tk.X)

        # 匹配模式
        mode_frame = ttk.LabelFrame(param_row, text="匹配模式", padding=4)
        mode_frame.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(mode_frame, text="线性插值（推荐）", variable=self.mode_var, value="interpolate").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="最近点匹配", variable=self.mode_var, value="nearest").pack(anchor=tk.W)

        # 数值参数
        val_frame = ttk.Frame(param_row)
        val_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        r1 = ttk.Frame(val_frame)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="时间阈值:").pack(side=tk.LEFT)
        ttk.Entry(r1, textvariable=self.threshold_var, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Label(r1, text="秒（超出此时间差的照片将被跳过）", foreground="gray").pack(side=tk.LEFT)

        r2 = ttk.Frame(val_frame)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="时区偏移:").pack(side=tk.LEFT)
        ttk.Entry(r2, textvariable=self.timezone_var, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Label(r2, text="小时（照片EXIF时间的时区，东八区为8）", foreground="gray").pack(side=tk.LEFT)

        # ---- 操作按钮 ----
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_dry_run = ttk.Button(btn_frame, text="试运行", command=self._start_dry_run)
        self.btn_dry_run.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_start = ttk.Button(btn_frame, text="开始处理", command=self._start_process)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = ttk.Button(btn_frame, text="停止", command=self._stop_process, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT)

        # ---- 进度条 ----
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # ---- 日志区 ----
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ---- 状态栏 ----
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(4, 0))

    # ---- 文件浏览 ----

    def _browse_gpx(self):
        paths = filedialog.askopenfilenames(
            title="选择GPX轨迹文件",
            filetypes=[("GPX文件", "*.gpx"), ("所有文件", "*.*")],
        )
        if paths:
            self.gpx_paths.set(";".join(paths))

    def _browse_photos(self):
        path = filedialog.askdirectory(title="选择照片目录")
        if path:
            self.photo_dir.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)

    # ---- 日志 ----

    def _log(self, message):
        """线程安全的日志输出"""
        def _append():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _append)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ---- 验证 ----

    def _validate_inputs(self):
        """验证输入参数"""
        # GPX文件
        gpx_str = self.gpx_paths.get().strip()
        if not gpx_str:
            messagebox.showwarning("提示", "请选择GPX轨迹文件")
            return None
        gpx_paths = [p.strip() for p in gpx_str.split(";") if p.strip()]
        for p in gpx_paths:
            if not os.path.isfile(p):
                messagebox.showerror("错误", f"GPX文件不存在: {p}")
                return None

        # 照片目录
        photo_dir = self.photo_dir.get().strip()
        if not photo_dir:
            messagebox.showwarning("提示", "请选择照片目录")
            return None
        if not os.path.isdir(photo_dir):
            messagebox.showerror("错误", f"照片目录不存在: {photo_dir}")
            return None

        # 输出目录（可选）
        output_dir = self.output_dir.get().strip() or None

        # 阈值
        try:
            threshold = float(self.threshold_var.get())
            if threshold <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "时间阈值必须为正数")
            return None

        # 时区
        try:
            timezone_offset = float(self.timezone_var.get())
        except ValueError:
            messagebox.showerror("错误", "时区偏移必须为数字")
            return None

        return {
            "gpx_paths": gpx_paths,
            "photo_dir": photo_dir,
            "output_dir": output_dir,
            "mode": self.mode_var.get(),
            "threshold": threshold,
            "timezone_offset": timezone_offset,
        }

    # ---- 处理 ----

    def _start_dry_run(self):
        self._run_process(dry_run=True)

    def _start_process(self):
        if messagebox.askyesno("确认", "即将修改照片文件的EXIF数据。是否继续？"):
            self._run_process(dry_run=False)

    def _stop_process(self):
        self.is_running = False
        self.status_var.set("正在停止...")
        self._log("\n⚠ 用户请求停止处理")

    def _run_process(self, dry_run=False):
        params = self._validate_inputs()
        if params is None:
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_dry_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self._clear_log()
        self.progress_var.set(0)

        mode_name = "线性插值" if params["mode"] == "interpolate" else "最近点匹配"
        self._log("=" * 50)
        self._log("  照片GPS轨迹合并工具")
        self._log("=" * 50)
        self._log(f"  GPX文件:  {', '.join(params['gpx_paths'])}")
        self._log(f"  照片目录: {params['photo_dir']}")
        self._log(f"  输出目录: {params['output_dir'] or '(覆盖原文件)'}")
        self._log(f"  匹配模式: {mode_name}")
        self._log(f"  时间阈值: {params['threshold']} 秒")
        self._log(f"  时区偏移: {params['timezone_offset']:+.1f} 小时")
        if dry_run:
            self._log(f"  模式:     *** 试运行（不修改文件）***")
        self._log("=" * 50)
        self._log("")

        # 在后台线程运行
        thread = threading.Thread(
            target=self._process_thread,
            args=(params, dry_run),
            daemon=True,
        )
        thread.start()

    def _process_thread(self, params, dry_run):
        """后台处理线程"""
        try:
            # 显示轨迹信息
            points = load_gpx(params["gpx_paths"])
            if not points:
                self._log("错误: GPX文件中未找到轨迹点")
                self._finish()
                return

            self._log(f"轨迹点数量: {len(points)}")
            self._log(f"时间范围:   {points[0].time.strftime('%Y-%m-%d %H:%M:%S')} ~ "
                      f"{points[-1].time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
            self._log("")
            self._log("开始处理...")
            self._log("-" * 50)

            success_count = 0
            skip_count = 0
            fail_count = 0
            total_count = 0

            # 先计算照片总数用于进度条
            photo_extensions = {'.jpg', '.jpeg', '.JPG', '.JPEG'}
            photo_files = []
            for root, dirs, files in os.walk(params["photo_dir"]):
                for f in files:
                    if os.path.splitext(f)[1] in photo_extensions:
                        photo_files.append(os.path.join(root, f))
            total_photos = len(photo_files)

            if total_photos == 0:
                self._log("未找到JPEG照片文件")
                self._finish()
                return

            def on_progress(result):
                nonlocal success_count, skip_count, fail_count, total_count
                if not self.is_running:
                    return

                total_count += 1
                filename = os.path.basename(result.photo_path)

                if result.success:
                    success_count += 1
                    elev_str = f", 海拔 {result.elevation:.1f}m" if result.elevation else ""
                    diff_str = f" (时间差 {result.time_diff:.1f}s)" if result.time_diff else ""
                    self._log(f"  ✓ {filename} → {result.latitude:.6f}, {result.longitude:.6f}{elev_str}{diff_str}")
                elif result.time_diff is not None:
                    skip_count += 1
                    self._log(f"  ⚠ {filename} → {result.message}")
                else:
                    fail_count += 1
                    self._log(f"  ✗ {filename} → {result.message}")

                # 更新进度
                progress = (total_count / total_photos) * 100
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_var.set(
                    f"处理中... {total_count}/{total_photos}"
                ))

            results = geotag_photos(
                gpx_paths=params["gpx_paths"],
                photo_dir=params["photo_dir"],
                output_dir=params["output_dir"],
                mode=params["mode"],
                threshold=params["threshold"],
                timezone_offset=params["timezone_offset"],
                dry_run=dry_run,
                callback=on_progress,
            )

            # 输出统计
            self._log("-" * 50)
            self._log(f"处理完成！")
            self._log(f"  成功: {success_count} 张")
            self._log(f"  跳过: {skip_count} 张（时间差超出阈值）")
            self._log(f"  失败: {fail_count} 张")
            self._log(f"  总计: {len(results)} 张")

            if dry_run:
                self._log("")
                self._log("提示: 以上为试运行结果，未修改任何文件。")
                self._log("      点击「开始处理」即可实际写入GPS数据。")

            self.root.after(0, lambda: self.status_var.set(
                f"完成 — 成功 {success_count}, 跳过 {skip_count}, 失败 {fail_count}"
            ))

        except Exception as e:
            self._log(f"\n错误: {e}")
            self.root.after(0, lambda: self.status_var.set(f"出错: {e}"))

        finally:
            self._finish()

    def _finish(self):
        """处理完成后的UI状态恢复"""
        def _restore():
            self.is_running = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_dry_run.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
        self.root.after(0, _restore)


def main():
    root = tk.Tk()
    GeotaggerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
