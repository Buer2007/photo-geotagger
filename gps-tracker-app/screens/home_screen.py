"""
home_screen.py — 主界面（GPS记录控制）

显示当前GPS状态、记录时间、距离、轨迹点数等信息。
提供开始/停止记录的按钮。
"""

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import BooleanProperty, StringProperty


class HomeScreen(BoxLayout):
    """主界面"""

    is_recording = BooleanProperty(False)
    status_text = StringProperty('准备就绪')
    duration_text = StringProperty('00:00:00')
    distance_text = StringProperty('0.0 km')
    point_count_text = StringProperty('0 点')
    lat_text = StringProperty('纬度: --')
    lon_text = StringProperty('经度: --')
    alt_text = StringProperty('海拔: --')
    acc_text = StringProperty('精度: --')

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self._update_event = None
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDRaisedButton, MDIconButton
        from kivymd.uix.card import MDCard

        # 顶部标题
        header = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='56dp',
            padding=['16dp', '8dp'],
        )
        title = MDLabel(
            text='GPS轨迹记录器',
            font_style='H5',
            halign='left',
            size_hint_x=0.8,
        )
        header.add_widget(title)
        self.add_widget(header)

        # 状态卡片
        status_card = MDCard(
            orientation='vertical',
            size_hint_y=None,
            height='160dp',
            padding='16dp',
            elevation=3,
            radius=[12],
        )

        self.status_label = MDLabel(
            text='准备就绪',
            font_style='H6',
            halign='center',
            theme_text_color='Primary',
        )
        status_card.add_widget(self.status_label)

        self.duration_label = MDLabel(
            text='00:00:00',
            font_style='H3',
            halign='center',
            theme_text_color='Custom',
            text_color=[0.2, 0.6, 1, 1],
        )
        status_card.add_widget(self.duration_label)

        stats_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='40dp',
        )
        self.distance_label = MDLabel(
            text='0.0 km',
            font_style='Body1',
            halign='center',
        )
        self.points_label = MDLabel(
            text='0 点',
            font_style='Body1',
            halign='center',
        )
        stats_row.add_widget(self.distance_label)
        stats_row.add_widget(self.points_label)
        status_card.add_widget(stats_row)

        self.add_widget(status_card)

        # GPS信息卡片
        info_card = MDCard(
            orientation='vertical',
            size_hint_y=None,
            height='160dp',
            padding='16dp',
            elevation=2,
            radius=[12],
        )

        self.lat_label = MDLabel(text='纬度: --', font_style='Body1')
        self.lon_label = MDLabel(text='经度: --', font_style='Body1')
        self.alt_label = MDLabel(text='海拔: --', font_style='Body1')
        self.acc_label = MDLabel(text='精度: --', font_style='Body1')

        info_card.add_widget(self.lat_label)
        info_card.add_widget(self.lon_label)
        info_card.add_widget(self.alt_label)
        info_card.add_widget(self.acc_label)

        self.add_widget(info_card)

        # 弹性空间
        from kivy.uix.widget import Widget
        self.add_widget(Widget(size_hint_y=1))

        # 控制按钮
        btn_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='64dp',
            padding='16dp',
            spacing='16dp',
        )

        self.record_btn = MDRaisedButton(
            text='● 开始记录',
            font_size='18sp',
            md_bg_color=[0.2, 0.8, 0.2, 1],
            size_hint=(0.6, 1),
        )
        self.record_btn.bind(on_press=self._toggle_recording)

        self.save_btn = MDRaisedButton(
            text='保存轨迹',
            font_size='16sp',
            md_bg_color=[0.2, 0.6, 1, 1],
            size_hint=(0.4, 1),
            disabled=True,
        )
        self.save_btn.bind(on_press=self._save_track)

        btn_layout.add_widget(self.record_btn)
        btn_layout.add_widget(self.save_btn)
        self.add_widget(btn_layout)

    def _toggle_recording(self, instance):
        """切换记录状态"""
        if self.app.gps_service.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """开始记录"""
        self.app.gps_service.on_location_update = self._on_location
        self.app.gps_service.start_recording()

        self.is_recording = True
        self.status_label.text = '● 记录中...'
        self.status_label.theme_text_color = 'Custom'
        self.status_label.text_color = [0.2, 0.8, 0.2, 1]
        self.record_btn.text = '■ 停止记录'
        self.record_btn.md_bg_color = [0.9, 0.2, 0.2, 1]
        self.save_btn.disabled = True

        # 定时更新界面
        self._update_event = Clock.schedule_interval(self._update_display, 1.0)

    def _stop_recording(self):
        """停止记录"""
        self.app.gps_service.stop_recording()

        self.is_recording = False
        self.status_label.text = '已停止 - 请保存轨迹'
        self.status_label.theme_text_color = 'Primary'
        self.record_btn.text = '● 开始记录'
        self.record_btn.md_bg_color = [0.2, 0.8, 0.2, 1]
        self.save_btn.disabled = False

        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def _save_track(self, instance):
        """保存轨迹"""
        points = self.app.gps_service.current_track
        if not points:
            return

        # 转换为字典列表
        point_dicts = [p.to_dict() for p in points]

        track_id = self.app.track_manager.save_track(point_dicts)
        if track_id:
            # 导出GPX
            from core.gpx_exporter import export_gpx, generate_gpx_filename
            track_data = self.app.track_manager.get_track(track_id)
            if track_data:
                gpx_name = generate_gpx_filename(track_data['name'], track_data['start_time'])
                import os
                gpx_dir = os.path.join(self.app.track_manager.base_dir, 'gpx')
                os.makedirs(gpx_dir, exist_ok=True)
                gpx_path = os.path.join(gpx_dir, gpx_name)
                export_gpx(track_data['points'], gpx_path, track_data['name'])

            self.status_label.text = f'已保存: {track_id}'
            self.save_btn.disabled = True

    def _on_location(self, point):
        """GPS位置更新回调"""
        pass  # 由定时器更新显示

    def _update_display(self, dt):
        """定时更新显示"""
        stats = self.app.gps_service.get_current_stats()

        # 时间
        duration = stats['duration']
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        self.duration_label.text = f'{hours:02d}:{minutes:02d}:{seconds:02d}'

        # 距离
        distance_km = stats['distance'] / 1000
        self.distance_label.text = f'{distance_km:.1f} km'

        # 点数
        self.points_label.text = f'{stats["point_count"]} 点'

        # 坐标
        if stats['current_lat'] != 0:
            self.lat_label.text = f'纬度: {stats["current_lat"]:.6f}°'
            self.lon_label.text = f'经度: {stats["current_lon"]:.6f}°'
            self.alt_label.text = f'海拔: {stats["current_alt"]:.1f} m'
            self.acc_label.text = f'精度: {stats["current_accuracy"]:.1f} m'
