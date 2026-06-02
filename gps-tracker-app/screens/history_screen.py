"""
history_screen.py — 历史轨迹管理界面

显示所有已记录的轨迹列表，
支持查看、重命名、导出GPX、删除操作。
"""

import os
from kivy.uix.boxlayout import BoxLayout


class HistoryScreen(BoxLayout):
    """历史轨迹界面"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.list import MDList
        from kivy.uix.scrollview import ScrollView

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
            text='历史轨迹',
            font_style='H6',
            size_hint_x=0.8,
        )
        refresh_btn = MDIconButton(
            icon='refresh',
            on_press=lambda x: self.refresh_list(),
        )
        header.add_widget(back_btn)
        header.add_widget(title)
        header.add_widget(refresh_btn)
        self.add_widget(header)

        # 轨迹列表
        scroll = ScrollView()
        self.track_list = MDList()
        scroll.add_widget(self.track_list)
        self.add_widget(scroll)

        # 空状态提示
        self.empty_label = MDLabel(
            text='暂无轨迹记录\n\n请先在主页开始记录GPS轨迹',
            halign='center',
            font_style='Body1',
            theme_text_color='Secondary',
        )

    def refresh_list(self):
        """刷新轨迹列表"""
        self.track_list.clear_widgets()

        tracks = self.app.track_manager.get_all_tracks()

        if not tracks:
            self.track_list.add_widget(self.empty_label)
            return

        from kivymd.uix.list import ThreeLineListItem, ThreeLineAvatarIconListItem
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        for track in tracks:
            # 格式化距离和时间
            distance = track.get('distance', 0)
            point_count = track.get('point_count', 0)
            start_time = track.get('start_time', '')

            # 计算时长
            duration_str = ''
            if track.get('start_time') and track.get('end_time'):
                try:
                    from datetime import datetime
                    fmt = '%Y-%m-%dT%H:%M:%S%z'
                    start = datetime.fromisoformat(track['start_time'].replace('Z', '+00:00'))
                    end = datetime.fromisoformat(track['end_time'].replace('Z', '+00:00'))
                    duration = (end - start).total_seconds()
                    minutes = int(duration) // 60
                    duration_str = f' · {minutes}分钟'
                except ValueError:
                    pass

            # 格式化开始时间
            time_str = ''
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except (ValueError, AttributeError):
                time_str = start_time[:16] if start_time else '未知时间'

            item = ThreeLineAvatarIconListItem(
                text=track['name'],
                secondary_text=f'{point_count} 点 · {distance/1000:.1f} km{duration_str}',
                tertiary_text=time_str,
            )

            # 添加操作按钮
            view_btn = MDIconButton(
                icon='map-marker',
                on_press=lambda x, tid=track['id']: self._view_track(tid),
            )
            export_btn = MDIconButton(
                icon='export',
                on_press=lambda x, tid=track['id']: self._export_track(tid),
            )
            delete_btn = MDIconButton(
                icon='delete',
                on_press=lambda x, tid=track['id']: self._confirm_delete(tid),
            )

            item.add_widget(view_btn)
            item.add_widget(export_btn)
            item.add_widget(delete_btn)

            self.track_list.add_widget(item)

    def _view_track(self, track_id: str):
        """查看轨迹（跳转到地图）"""
        track_data = self.app.track_manager.get_track(track_id)
        if track_data:
            self.app.show_track_on_map(track_data)

    def _export_track(self, track_id: str):
        """导出GPX文件"""
        from core.gpx_exporter import export_gpx, generate_gpx_filename

        track_data = self.app.track_manager.get_track(track_id)
        if not track_data:
            return

        gpx_name = generate_gpx_filename(track_data['name'], track_data['start_time'])

        # 导出到共享存储或应用目录
        import os
        gpx_dir = os.path.join(self.app.track_manager.base_dir, 'gpx')
        os.makedirs(gpx_dir, exist_ok=True)
        gpx_path = os.path.join(gpx_dir, gpx_name)

        if export_gpx(track_data['points'], gpx_path, track_data['name']):
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text=f'GPX已导出: {gpx_name}').open()
        else:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text='GPX导出失败').open()

    def _confirm_delete(self, track_id: str):
        """确认删除对话框"""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        dialog = MDDialog(
            title='确认删除',
            text='确定要删除这条轨迹吗？此操作不可撤销。',
            buttons=[
                MDFlatButton(
                    text='取消',
                    on_press=lambda x: dialog.dismiss(),
                ),
                MDFlatButton(
                    text='删除',
                    theme_text_color='Custom',
                    text_color=[1, 0, 0, 1],
                    on_press=lambda x: self._delete_track(track_id, dialog),
                ),
            ],
        )
        dialog.open()

    def _delete_track(self, track_id: str, dialog):
        """删除轨迹"""
        self.app.track_manager.delete_track(track_id)
        dialog.dismiss()
        self.refresh_list()

        from kivymd.uix.snackbar import Snackbar
        Snackbar(text='轨迹已删除').open()

    def _go_back(self, instance):
        """返回主界面"""
        self.app.switch_screen('home')
