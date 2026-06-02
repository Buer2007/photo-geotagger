"""
map_screen.py — 地图轨迹显示界面

使用 WebView 加载高德地图 JavaScript API，
显示当前记录的轨迹或历史轨迹。
"""

import os
from kivy.uix.boxlayout import BoxLayout


class MapScreen(BoxLayout):
    """地图界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.webview = None
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton

        # 顶部标题栏
        header = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='56dp',
            padding=['8dp', '8dp'],
        )
        back_btn = MDIconButton(
            icon='arrow-left',
            on_press=self._go_back,
        )
        title = MDLabel(
            text='轨迹地图',
            font_style='H6',
            size_hint_x=0.8,
        )
        header.add_widget(back_btn)
        header.add_widget(title)
        self.add_widget(header)

        # WebView 地图
        try:
            from kivy_garden.webview import WebView
            map_html = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'assets', 'map.html'
            )
            self.webview = WebView(
                url=map_html,
                size_hint_y=1,
            )
            self.add_widget(self.webview)
        except ImportError:
            from kivymd.uix.label import MDLabel as Label
            self.add_widget(Label(
                text='地图组件未安装\n请运行: pip install kivy-garden-webview',
                halign='center',
                font_style='Body1',
            ))

        # 底部信息栏
        footer = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height='80dp',
            padding='16dp',
        )
        self.track_info_label = MDLabel(
            text='暂无轨迹',
            font_style='Body1',
            halign='center',
        )
        self.track_stats_label = MDLabel(
            text='',
            font_style='Body2',
            halign='center',
            theme_text_color='Secondary',
        )
        footer.add_widget(self.track_info_label)
        footer.add_widget(self.track_stats_label)
        self.add_widget(footer)

    def show_track(self, track_data: dict):
        """在地图上显示轨迹"""
        if not track_data or not track_data.get('points'):
            return

        points = track_data['points']
        name = track_data.get('name', '未知轨迹')
        distance = track_data.get('distance', 0)
        point_count = len(points)

        self.track_info_label.text = f'轨迹: {name}'
        self.track_stats_label.text = f'{point_count} 点 · {distance/1000:.1f} km'

        if self.webview:
            import json
            coords = [[p['longitude'], p['latitude']] for p in points]
            js_code = f'drawTrack({json.dumps(coords)})'
            try:
                self.webview.evaluate_js(js_code)
            except Exception as e:
                print(f"WebView JS执行失败: {e}")

    def show_current_track(self):
        """显示当前正在记录的轨迹"""
        points = self.app.gps_service.current_track
        if not points:
            return
        point_dicts = [p.to_dict() for p in points]
        track_data = {
            'name': '当前记录',
            'points': point_dicts,
            'distance': self.app.gps_service.get_current_stats()['distance'],
        }
        self.show_track(track_data)

    def _go_back(self, instance):
        """返回主界面"""
        self.app.switch_screen('home')
