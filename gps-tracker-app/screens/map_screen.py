"""
map_screen.py — 地图轨迹显示界面

Android: 使用 Android WebView 加载高德地图
PC: 显示提示信息
"""

import os
import json
from kivy.uix.boxlayout import BoxLayout

FONT = 'SimHei'


class MapScreen(BoxLayout):
    """地图界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.webview = None
        self._webview_available = False
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton

        # 顶部标题栏
        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['8dp', '8dp'])
        header.add_widget(MDIconButton(icon='arrow-left', on_press=self._go_back))
        header.add_widget(MDLabel(text='轨迹地图', font_style='H6', size_hint_x=0.8, font_name=FONT))
        self.add_widget(header)

        # 尝试加载 WebView
        try:
            from kivy_garden.webview import WebView

            # 找到 map.html 文件
            map_html = self._find_map_html()
            if map_html:
                self.webview = WebView(url=map_html, size_hint_y=1)
                self.add_widget(self.webview)
                self._webview_available = True
            else:
                self._show_fallback('地图文件未找到')
        except ImportError:
            self._show_fallback('WebView组件未安装\n\nAndroid上请确保已安装kivy-garden-webview')
        except Exception as e:
            self._show_fallback(f'WebView加载失败: {e}')

    def _find_map_html(self):
        """查找 map.html 文件"""
        # 可能的路径
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'map.html'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map.html'),
            'assets/map.html',
            'map.html',
        ]

        # Android 打包后的路径
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            app_dir = context.getFilesDir().getAbsolutePath()
            possible_paths.insert(0, os.path.join(app_dir, 'assets', 'map.html'))
        except Exception:
            pass

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def _show_fallback(self, message):
        """显示备用提示"""
        from kivymd.uix.label import MDLabel

        self._webview_available = False
        self.add_widget(MDLabel(
            text=message,
            font_style='Body1',
            halign='center',
            font_name=FONT,
            size_hint_y=1,
        ))

    def show_track(self, track_data):
        if not track_data or not track_data.get('points'):
            return

        points = track_data['points']
        coords = [[p['longitude'], p['latitude']] for p in points]

        if self._webview_available and self.webview:
            js_code = f'drawTrack({json.dumps(coords)})'
            try:
                self.webview.evaluate_js(js_code)
            except Exception as e:
                print(f"WebView JS执行失败: {e}")

    def show_current_track(self):
        points = self.app.gps_service.current_track
        if not points:
            return
        point_dicts = [p.to_dict() for p in points]
        self.show_track({
            'name': '当前记录',
            'points': point_dicts,
            'distance': self.app.gps_service.get_current_stats()['distance'],
        })

    def _go_back(self, instance):
        self.app.switch_screen('home')
