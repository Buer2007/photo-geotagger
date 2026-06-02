"""
home_screen.py — 主界面（GPS记录控制）
"""

import os
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout

FONT = 'SimHei'


class HomeScreen(BoxLayout):
    """主界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self._update_event = None
        self._recording_seconds = 0
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDRaisedButton
        from kivymd.uix.card import MDCard
        from kivy.uix.widget import Widget

        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['16dp', '8dp'])
        header.add_widget(MDLabel(text='GPS轨迹记录器', font_style='H5', halign='left', size_hint_x=0.8, font_name=FONT))
        self.add_widget(header)

        # 状态卡片
        status_card = MDCard(orientation='vertical', size_hint_y=None, height='160dp', padding='16dp', elevation=3, radius=[12])

        self.status_label = MDLabel(text='准备就绪', font_style='H6', halign='center', theme_text_color='Primary', font_name=FONT)
        status_card.add_widget(self.status_label)

        self.duration_label = MDLabel(text='00:00:00', font_style='H3', halign='center', theme_text_color='Custom', text_color=[0.2, 0.6, 1, 1], font_name=FONT)
        status_card.add_widget(self.duration_label)

        stats_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='40dp')
        self.distance_label = MDLabel(text='0.0 km', font_style='Body1', halign='center', font_name=FONT)
        self.points_label = MDLabel(text='0 点', font_style='Body1', halign='center', font_name=FONT)
        stats_row.add_widget(self.distance_label)
        stats_row.add_widget(self.points_label)
        status_card.add_widget(stats_row)
        self.add_widget(status_card)

        # GPS信息卡片
        info_card = MDCard(orientation='vertical', size_hint_y=None, height='160dp', padding='16dp', elevation=2, radius=[12])
        self.lat_label = MDLabel(text='纬度: --', font_style='Body1', font_name=FONT)
        self.lon_label = MDLabel(text='经度: --', font_style='Body1', font_name=FONT)
        self.alt_label = MDLabel(text='海拔: --', font_style='Body1', font_name=FONT)
        self.acc_label = MDLabel(text='精度: --', font_style='Body1', font_name=FONT)
        for w in [self.lat_label, self.lon_label, self.alt_label, self.acc_label]:
            info_card.add_widget(w)
        self.add_widget(info_card)

        self.add_widget(Widget(size_hint_y=1))

        # 控制按钮
        btn_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='64dp', padding='16dp', spacing='16dp')

        self.record_btn = MDRaisedButton(text='● 开始记录', font_size='18sp', md_bg_color=[0.2, 0.8, 0.2, 1], size_hint=(0.6, 1), font_name=FONT)
        self.record_btn.bind(on_press=self._toggle_recording)

        self.save_btn = MDRaisedButton(text='保存轨迹', font_size='16sp', md_bg_color=[0.2, 0.6, 1, 1], size_hint=(0.4, 1), disabled=True, font_name=FONT)
        self.save_btn.bind(on_press=self._save_track)

        btn_layout.add_widget(self.record_btn)
        btn_layout.add_widget(self.save_btn)
        self.add_widget(btn_layout)

    def _toggle_recording(self, instance):
        if self.app.gps_service.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """开始记录（计时器和GPS独立运行）"""
        # 重置本地计时
        self._recording_seconds = 0

        # 启动GPS（可能在Windows上失败，不影响计时器）
        try:
            self.app.gps_service.on_location_update = self._on_location
            self.app.gps_service.start_recording()
        except Exception as e:
            print(f"GPS启动失败（不影响计时）: {e}")

        # 更新UI状态
        self.status_label.text = '● 记录中...'
        self.status_label.text_color = [0.2, 0.8, 0.2, 1]
        self.record_btn.text = '■ 停止记录'
        self.record_btn.md_bg_color = [0.9, 0.2, 0.2, 1]
        self.save_btn.disabled = True

        # 启动计时器（每秒更新）
        self._update_event = Clock.schedule_interval(self._update_display, 1.0)

    def _stop_recording(self):
        """停止记录"""
        # 停止GPS
        try:
            self.app.gps_service.stop_recording()
        except Exception:
            pass

        # 停止计时器
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

        # 更新UI
        self.status_label.text = '已停止 - 请保存轨迹'
        self.status_label.text_color = [0, 0, 0, 1]
        self.record_btn.text = '● 开始记录'
        self.record_btn.md_bg_color = [0.2, 0.8, 0.2, 1]
        self.save_btn.disabled = False

    def _save_track(self, instance):
        points = self.app.gps_service.current_track
        if not points:
            # 没有GPS点时也允许保存（PC测试用）
            self.status_label.text = '无轨迹数据可保存'
            return

        point_dicts = [p.to_dict() for p in points]
        track_id = self.app.track_manager.save_track(point_dicts)
        if track_id:
            from core.gpx_exporter import export_gpx, generate_gpx_filename
            track_data = self.app.track_manager.get_track(track_id)
            if track_data:
                gpx_name = generate_gpx_filename(track_data['name'], track_data['start_time'])
                gpx_dir = os.path.join(self.app.track_manager.base_dir, 'gpx')
                os.makedirs(gpx_dir, exist_ok=True)
                export_gpx(track_data['points'], os.path.join(gpx_dir, gpx_name), track_data['name'])

            self.status_label.text = f'已保存: {track_id}'
            self.save_btn.disabled = True

    def _on_location(self, point):
        """GPS位置更新回调"""
        pass

    def _update_display(self, dt):
        """每秒更新显示（计时器独立于GPS）"""
        # 本地计时（不依赖GPS服务）
        self._recording_seconds += 1
        h = self._recording_seconds // 3600
        m = (self._recording_seconds % 3600) // 60
        s = self._recording_seconds % 60
        self.duration_label.text = f'{h:02d}:{m:02d}:{s:02d}'

        # GPS数据（如果有）
        stats = self.app.gps_service.get_current_stats()

        if stats['distance'] > 0:
            self.distance_label.text = f'{stats["distance"]/1000:.1f} km'

        if stats['point_count'] > 0:
            self.points_label.text = f'{stats["point_count"]} 点'

        if stats['current_lat'] != 0:
            self.lat_label.text = f'纬度: {stats["current_lat"]:.6f}°'
            self.lon_label.text = f'经度: {stats["current_lon"]:.6f}°'
            self.alt_label.text = f'海拔: {stats["current_alt"]:.1f} m'
            self.acc_label.text = f'精度: {stats["current_accuracy"]:.1f} m'
