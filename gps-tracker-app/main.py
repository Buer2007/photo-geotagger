"""
main.py — GPS轨迹记录器 Android App 主程序
"""

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from kivy.core.text import LabelBase
from kivy.resources import resource_add_path

# 添加资源路径（Android兼容）
resource_add_path(APP_DIR)
resource_add_path(os.path.join(APP_DIR, 'assets'))

# 注册中文字体（Android兼容路径）
FONT_PATH = os.path.join(APP_DIR, 'assets', 'simhei.ttf')

# 如果字体文件不存在（Android打包后可能在不同位置），尝试其他路径
if not os.path.exists(FONT_PATH):
    # Android上 assets 可能在 app 目录下
    alt_paths = [
        os.path.join(os.path.dirname(APP_DIR), 'assets', 'simhei.ttf'),
        os.path.join(APP_DIR, 'simhei.ttf'),
        'assets/simhei.ttf',
        'simhei.ttf',
    ]
    for p in alt_paths:
        if os.path.exists(p):
            FONT_PATH = p
            break

LabelBase.register(name='SimHei', fn_regular=FONT_PATH)

from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.font_definitions import fonts

from core.gps_service import GPSService
from core.track_manager import TrackManager

# 替换 KivyMD 字体系统
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

for name in ['Roboto', 'RobotoMono', 'RobotoMonoLight', 'RobotoThin', 'RobotoLight',
             'RobotoMedium', 'RobotoBlack', 'RobotoSlab', 'Icons']:
    LabelBase.register(name=name, fn_regular=FONT_PATH)


class GPSTrackerApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'GPS轨迹记录器'
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.theme_style = 'Light'

        for style_name in list(self.theme_cls.font_styles.keys()):
            self.theme_cls.font_styles[style_name] = [FONT_PATH, 16, 0, False]

        self.gps_service = GPSService()

        # 数据目录：Android上使用应用私有目录，PC上使用项目目录
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            files_dir = context.getFilesDir().getAbsolutePath()
            data_dir = os.path.join(files_dir, 'geotagger_data')
        except Exception:
            data_dir = os.path.join(APP_DIR, 'data')

        self.track_manager = TrackManager(base_dir=data_dir)

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
