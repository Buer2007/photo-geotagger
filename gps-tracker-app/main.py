"""
main.py — GPS轨迹记录器 Android App 主程序
"""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from kivy.core.text import LabelBase

# 注册中文字体
FONT_PATH = os.path.join(APP_DIR, 'assets', 'simhei.ttf')
LabelBase.register(name='SimHei', fn_regular=FONT_PATH)

from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.font_definitions import fonts, theme_font_styles

from core.gps_service import GPSService
from core.track_manager import TrackManager

# ============================================================
# 关键：替换 KivyMD 的字体系统，把所有 Roboto 改为 SimHei
# ============================================================

# 1. 替换 fonts 列表中所有字体为 SimHei
for font_item in fonts:
    font_item['name'] = 'SimHei'
    font_item['fn_regular'] = FONT_PATH
    font_item['fn_bold'] = FONT_PATH
    font_item['fn_italic'] = FONT_PATH
    font_item['fn_bolditalic'] = FONT_PATH
    if 'fn_thin' in font_item:
        font_item['fn_thin'] = FONT_PATH
    if 'fn_light' in font_item:
        font_item['fn_light'] = FONT_PATH

# 2. 重新注册所有 KivyMD 字体名称指向 SimHei 文件
for name in ['Roboto', 'RobotoMono', 'RobotoMonoLight', 'RobotoThin', 'RobotoLight',
             'RobotoMedium', 'RobotoBlack', 'RobotoSlab']:
    LabelBase.register(name=name, fn_regular=FONT_PATH)

LabelBase.register(name='Icons', fn_regular=os.path.join(APP_DIR, 'assets', 'simhei.ttf'))


class GPSTrackerApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'GPS轨迹记录器'
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'

        # 3. 替换 theme_cls 中的 font_styles
        for style_name in list(self.theme_cls.font_styles.keys()):
            self.theme_cls.font_styles[style_name] = [FONT_PATH, 16, 0, False]

        self.gps_service = GPSService()
        self.track_manager = TrackManager(base_dir=os.path.join(APP_DIR, 'data'))

        self.home_screen = None
        self.map_screen = None
        self.history_screen = None
        self.bottom_nav = None

    def build(self):
        root = MDBoxLayout(orientation='vertical')
        self.bottom_nav = MDBottomNavigation(panel_color=self.theme_cls.bg_darkest)

        self.bottom_nav.add_widget(self._create_home_tab())
        self.bottom_nav.add_widget(self._create_map_tab())
        self.bottom_nav.add_widget(self._create_history_tab())

        root.add_widget(self.bottom_nav)
        return root

    def _create_home_tab(self):
        from screens.home_screen import HomeScreen
        tab = MDBottomNavigationItem(name='home', text='主页', icon='home')
        self.home_screen = HomeScreen(app=self)
        tab.add_widget(self.home_screen)
        return tab

    def _create_map_tab(self):
        from screens.map_screen import MapScreen
        tab = MDBottomNavigationItem(name='map', text='地图', icon='map-marker')
        self.map_screen = MapScreen(app=self)
        tab.add_widget(self.map_screen)
        return tab

    def _create_history_tab(self):
        from screens.history_screen import HistoryScreen
        tab = MDBottomNavigationItem(name='history', text='历史', icon='history')
        self.history_screen = HistoryScreen(app=self)
        tab.add_widget(self.history_screen)
        return tab

    def switch_screen(self, screen_name):
        self.bottom_nav.switch_tab(screen_name)

    def show_track_on_map(self, track_data):
        self.switch_screen('map')
        Clock.schedule_once(lambda dt: self.map_screen.show_track(track_data), 0.5)

    def on_pause(self):
        return True

    def on_stop(self):
        if self.gps_service.is_recording:
            points = self.gps_service.stop_recording()
            if points:
                self.track_manager.save_track([p.to_dict() for p in points], name='自动保存')


def main():
    GPSTrackerApp().run()


if __name__ == '__main__':
    main()
