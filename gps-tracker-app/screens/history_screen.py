"""
history_screen.py — 历史轨迹管理界面
"""

from kivy.uix.boxlayout import BoxLayout

FONT = 'SimHei'


class HistoryScreen(BoxLayout):
    """历史轨迹界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self._loaded = False
        self._build_ui()

    def _build_ui(self):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.list import MDList
        from kivy.uix.scrollview import ScrollView

        # 顶部
        header = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='56dp', padding=['8dp', '8dp'])
        header.add_widget(MDIconButton(icon='arrow-left', on_press=self._go_back))
        header.add_widget(MDLabel(text='历史轨迹', font_style='H6', size_hint_x=0.8, font_name=FONT))
        refresh_btn = MDIconButton(icon='refresh', on_press=lambda x: self.refresh_list())
        header.add_widget(refresh_btn)
        self.add_widget(header)

        # 列表
        scroll = ScrollView()
        self.track_list = MDList()
        scroll.add_widget(self.track_list)
        self.add_widget(scroll)

        # 空状态
        self.empty_label = MDLabel(
            text='暂无轨迹记录\n\n请先在主页开始记录GPS轨迹',
            halign='center', font_style='Body1',
            theme_text_color='Secondary', font_name=FONT,
        )

    def on_kv_post(self, base_widget):
        """KV加载后触发"""
        super().on_kv_post(base_widget)
        # 延迟刷新，确保界面已完全加载
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.refresh_list(), 0.1)

    def on_touch_down(self, touch):
        """每次点击此页面时刷新"""
        if self.collide_point(*touch.pos):
            self.refresh_list()
        return super().on_touch_down(touch)

    def refresh_list(self):
        """刷新轨迹列表"""
        from kivymd.uix.list import ThreeLineListItem
        from kivymd.uix.button import MDIconButton

        self.track_list.clear_widgets()
        tracks = self.app.track_manager.get_all_tracks()

        if not tracks:
            self.track_list.add_widget(self.empty_label)
            self._loaded = True
            return

        for track in tracks:
            distance = track.get('distance', 0)
            point_count = track.get('point_count', 0)
            time_str = track.get('start_time', '')[:16] or '未知时间'

            item = ThreeLineListItem(
                text=track['name'],
                secondary_text=f'{point_count} 点 · {distance/1000:.1f} km',
                tertiary_text=time_str,
                font_name=FONT,
            )

            view_btn = MDIconButton(icon='map-marker', on_press=lambda x, tid=track['id']: self._view_track(tid))
            delete_btn = MDIconButton(icon='delete', on_press=lambda x, tid=track['id']: self._confirm_delete(tid))
            item.add_widget(view_btn)
            item.add_widget(delete_btn)
            self.track_list.add_widget(item)

        self._loaded = True

    def _view_track(self, track_id):
        track_data = self.app.track_manager.get_track(track_id)
        if track_data:
            self.app.show_track_on_map(track_data)

    def _confirm_delete(self, track_id):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        dialog = MDDialog(
            title='确认删除',
            text='确定要删除这条轨迹吗？',
            buttons=[
                MDFlatButton(text='取消', on_press=lambda x: dialog.dismiss(), font_name=FONT),
                MDFlatButton(text='删除', text_color=[1, 0, 0, 1], on_press=lambda x: self._do_delete(track_id, dialog), font_name=FONT),
            ],
        )
        dialog.open()

    def _do_delete(self, track_id, dialog):
        self.app.track_manager.delete_track(track_id)
        dialog.dismiss()
        self.refresh_list()

    def _go_back(self, instance):
        self.app.switch_screen('home')
