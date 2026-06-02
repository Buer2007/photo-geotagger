"""
main.py — GPS轨迹记录器 Android App 主程序

功能：
1. GPS轨迹记录（后台持续运行）
2. 高德地图实时轨迹显示
3. 历史轨迹管理
4. GPX文件导出
"""

import os
import sys

# 设置项目路径
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem

from core.gps_service import GPSService
from core.track_manager import TrackManager


class GPSTrackerApp(MDApp):
    """GPS轨迹记录器 App"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'GPS轨迹记录器'
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'

        # 核心服务
        self.gps_service = GPSService()
        self.track_manager = TrackManager(
            base_dir=os.path.join(APP_DIR, 'data')
        )

        # 界面引用
        self.home_screen = None
        self.map_screen = None
        self.history_screen = None
        self.bottom_nav = None

    def build(self):
        """构建App界面"""
        # 主布局
        root = MDBoxLayout(orientation='vertical')

        # 底部导航栏
        self.bottom_nav = MDBottomNavigation(
            panel_color=self.theme_cls.bg_darkest,
        )

        # 主页标签
        self.bottom_nav.add_widget(self._create_home_tab())

        # 地图标签
        self.bottom_nav.add_widget(self._create_map_tab())

        # 历史标签
        self.bottom_nav.add_widget(self._create_history_tab())

        root.add_widget(self.bottom_nav)

        return root

    def _create_home_tab(self) -> MDBottomNavigationItem:
        """创建主页标签"""
        from screens.home_screen import HomeScreen

        tab = MDBottomNavigationItem(
            name='home',
            text='主页',
            icon='home',
        )
        self.home_screen = HomeScreen(app=self)
        tab.add_widget(self.home_screen)
        return tab

    def _create_map_tab(self) -> MDBottomNavigationItem:
        """创建地图标签"""
        from screens.map_screen import MapScreen

        tab = MDBottomNavigationItem(
            name='map',
            text='地图',
            icon='map-marker',
        )
        self.map_screen = MapScreen(app=self)
        tab.add_widget(self.map_screen)
        return tab

    def _create_history_tab(self) -> MDBottomNavigationItem:
        """创建历史标签"""
        from screens.history_screen import HistoryScreen

        tab = MDBottomNavigationItem(
            name='history',
            text='历史',
            icon='history',
        )
        self.history_screen = HistoryScreen(app=self)
        tab.add_widget(self.history_screen)
        return tab

    def switch_screen(self, screen_name: str):
        """切换底部标签"""
        self.bottom_nav.switch_tab(screen_name)

    def show_track_on_map(self, track_data: dict):
        """在地图上显示轨迹并切换到地图标签"""
        self.switch_screen('map')
        # 延迟一帧确保WebView已加载
        Clock.schedule_once(lambda dt: self.map_screen.show_track(track_data), 0.5)

    def on_pause(self):
        """App进入后台时调用（Android）"""
        # GPS记录在后台继续运行
        return True

    def on_resume(self):
        """App从后台恢复时调用（Android）"""
        pass

    def on_stop(self):
        """App退出时清理"""
        if self.gps_service.is_recording:
            # 退出时自动保存轨迹
            points = self.gps_service.stop_recording()
            if points:
                point_dicts = [p.to_dict() for p in points]
                self.track_manager.save_track(point_dicts, name='自动保存')


def main():
    """入口函数"""
    GPSTrackerApp().run()


if __name__ == '__main__':
    main()
