"""
map_screen.py — 地图轨迹显示界面

Android: 用系统浏览器打开地图（最可靠）
PC: 显示提示
"""

import os
import json
import tempfile
from kivy.uix.boxlayout import BoxLayout

FONT = 'SimHei'


class MapScreen(BoxLayout):
    """地图界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self._current_coords = None
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDRaisedButton

        # 顶部标题栏
        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['8dp', '8dp'])
        from kivymd.uix.button import MDIconButton
        header.add_widget(MDIconButton(icon='arrow-left', on_press=self._go_back))
        header.add_widget(MDLabel(text='轨迹地图', font_style='H6', size_hint_x=0.8, font_name=FONT))
        self.add_widget(header)

        # 内容区
        content = MDBoxLayout(orientation='vertical', padding='32dp', spacing='16dp', size_hint_y=1)

        self.info_label = MDLabel(
            text='[b]轨迹地图[/b]\n\n'
                 '点击下方按钮在浏览器中查看地图\n'
                 '（需要先加载轨迹数据）',
            markup=True, font_style='Body1', halign='center', font_name=FONT,
        )
        content.add_widget(self.info_label)

        # 打开地图按钮
        self.open_btn = MDRaisedButton(
            text='在浏览器中打开地图',
            size_hint=(0.8, None),
            height='48dp',
            pos_hint={'center_x': 0.5},
            font_name=FONT,
            disabled=True,
        )
        self.open_btn.bind(on_press=self._open_in_browser)
        content.add_widget(self.open_btn)

        self.add_widget(content)

        # 底部信息栏
        footer = MDBoxLayout(orientation='vertical', size_hint_y=None, height='80dp', padding='16dp')
        self.track_info_label = MDLabel(text='暂无轨迹', font_style='Body1', halign='center', font_name=FONT)
        self.track_stats_label = MDLabel(text='', font_style='Body2', halign='center', theme_text_color='Secondary', font_name=FONT)
        footer.add_widget(self.track_info_label)
        footer.add_widget(self.track_stats_label)
        self.add_widget(footer)

    def show_track(self, track_data):
        """加载轨迹数据"""
        if not track_data or not track_data.get('points'):
            return

        points = track_data['points']
        name = track_data.get('name', '未知轨迹')
        distance = track_data.get('distance', 0)
        point_count = len(points)

        self.track_info_label.text = f'轨迹: {name}'
        self.track_stats_label.text = f'{point_count} 点 · {distance/1000:.1f} km'

        self._current_coords = [[p['longitude'], p['latitude']] for p in points]

        # 启用按钮
        self.open_btn.disabled = False
        self.info_label.text = f'[b]已加载轨迹[/b]\n\n{name}\n{point_count} 个点 · {distance/1000:.1f} km\n\n点击下方按钮查看地图'

    def _open_in_browser(self, instance):
        """在浏览器中打开地图"""
        map_html_path = self._find_map_html()
        if not map_html_path:
            self.info_label.text = '[b]错误[/b]\n\n地图文件未找到'
            return

        try:
            # 读取原始HTML
            with open(map_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 如果有轨迹数据，注入绘制代码
            if self._current_coords:
                coords_json = json.dumps(self._current_coords)
                inject_js = f'\n<script>setTimeout(function(){{drawTrack({coords_json});}}, 1000);</script>\n</body>'
                html_content = html_content.replace('</body>', inject_js)

            # 写入临时文件
            tmp_path = os.path.join(tempfile.gettempdir(), 'gps_track_map.html')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 用系统浏览器打开
            if platform == 'android':
                self._open_android_browser(tmp_path)
            else:
                import webbrowser
                webbrowser.open(f'file:///{tmp_path}')

        except Exception as e:
            self.info_label.text = f'[b]错误[/b]\n\n{e}'

    def _open_android_browser(self, file_path):
        """Android上用系统浏览器打开"""
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            FileProvider = autoclass('android.support.v4.content.FileProvider')

            activity = PythonActivity.mActivity

            @run_on_ui_thread
            def open_browser():
                file = File(file_path)
                uri = FileProvider.getUriForFile(
                    activity,
                    activity.getPackageName() + '.fileprovider',
                    file
                )

                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(uri, 'text/html')
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                activity.startActivity(intent)

            open_browser()

        except Exception as e:
            print(f"Android浏览器打开失败: {e}")
            # 备用方案：尝试直接打开
            try:
                import webbrowser
                webbrowser.open(f'file:///{file_path}')
            except Exception:
                pass

    def _find_map_html(self):
        """查找map.html"""
        paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'map.html'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map.html'),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def show_current_track(self):
        """显示当前记录的轨迹"""
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
        """返回主页"""
        self.app.switch_screen('home')


# 兼容性导入
try:
    from kivy.utils import platform
except ImportError:
    import sys
    platform = 'win' if sys.platform == 'win32' else 'linux'
