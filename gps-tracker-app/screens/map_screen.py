"""
map_screen.py — 地图轨迹显示界面

Android: 使用 WebView 加载高德地图
PC测试: 用浏览器打开地图
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
        self.webview = None
        self._webview_available = False
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton, MDRaisedButton

        # 顶部标题栏
        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['8dp', '8dp'])
        header.add_widget(MDIconButton(icon='arrow-left', on_press=self._go_back))
        header.add_widget(MDLabel(text='轨迹地图', font_style='H6', size_hint_x=0.8, font_name=FONT))
        self.add_widget(header)

        # 尝试加载 WebView（Android可用，PC上不可用）
        try:
            from kivy_garden.webview import WebView
            map_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'map.html')
            self.webview = WebView(url=map_html, size_hint_y=1)
            self.add_widget(self.webview)
            self._webview_available = True
        except ImportError:
            self._webview_available = False

        # PC上显示提示和浏览器按钮
        if not self._webview_available:
            content = MDBoxLayout(orientation='vertical', padding='32dp', spacing='16dp', size_hint_y=1)

            content.add_widget(MDLabel(
                text='[b]PC测试模式[/b]\n\nWebView组件仅在Android上可用。\n请点击下方按钮在浏览器中查看地图。',
                markup=True, font_style='Body1', halign='center', size_hint_y=0.4, font_name=FONT,
            ))

            open_btn = MDRaisedButton(text='在浏览器中打开地图', size_hint=(0.6, None), height='48dp', pos_hint={'center_x': 0.5}, font_name=FONT)
            open_btn.bind(on_press=self._open_in_browser)
            content.add_widget(open_btn)

            self.browser_info_label = MDLabel(text='暂无轨迹数据', font_style='Body2', halign='center', size_hint_y=0.4, font_name=FONT)
            content.add_widget(self.browser_info_label)
            self.add_widget(content)
        else:
            self.browser_info_label = None

        # 底部信息栏
        footer = MDBoxLayout(orientation='vertical', size_hint_y=None, height='80dp', padding='16dp')
        self.track_info_label = MDLabel(text='暂无轨迹', font_style='Body1', halign='center', font_name=FONT)
        self.track_stats_label = MDLabel(text='', font_style='Body2', halign='center', theme_text_color='Secondary', font_name=FONT)
        footer.add_widget(self.track_info_label)
        footer.add_widget(self.track_stats_label)
        self.add_widget(footer)

    def show_track(self, track_data):
        if not track_data or not track_data.get('points'):
            return

        points = track_data['points']
        name = track_data.get('name', '未知轨迹')
        distance = track_data.get('distance', 0)
        point_count = len(points)

        self.track_info_label.text = f'轨迹: {name}'
        self.track_stats_label.text = f'{point_count} 点 · {distance/1000:.1f} km'

        coords = [[p['longitude'], p['latitude']] for p in points]

        if self._webview_available and self.webview:
            js_code = f'drawTrack({json.dumps(coords)})'
            try:
                self.webview.evaluate_js(js_code)
            except Exception as e:
                print(f"WebView JS执行失败: {e}")
        else:
            if self.browser_info_label:
                self.browser_info_label.text = f'已加载轨迹: {name}\n{point_count} 点 · {distance/1000:.1f} km'
            self._current_coords = coords

    def _open_in_browser(self, instance):
        import webbrowser
        map_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'map.html')

        if hasattr(self, '_current_coords') and self._current_coords:
            coords_json = json.dumps(self._current_coords)
            with open(map_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            inject_js = f'\n<script>drawTrack({coords_json});</script>\n</body>'
            html_content = html_content.replace('</body>', inject_js)
            tmp_path = os.path.join(tempfile.gettempdir(), 'gps_track_map.html')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            webbrowser.open(f'file:///{tmp_path}')
        else:
            webbrowser.open(f'file:///{map_html}')

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
