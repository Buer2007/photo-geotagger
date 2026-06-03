[app]

# App元数据
title = GPS轨迹记录器
package.name = gpstracker
package.domain = com.geotagger
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,json,ttf
version = 1.0.0

# Python依赖
requirements = python3,kivy,kivymd,plyer,android,pyjnius

# 全屏模式
fullscreen = 0

# 屏幕方向
orientation = portrait

# Android权限（适配Android 14+）
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,FOREGROUND_SERVICE,FOREGROUND_SERVICE_LOCATION,INTERNET,ACCESS_NETWORK_STATE,POST_NOTIFICATIONS

# Android API版本（适配Android 16）
android.api = 35
android.minapi = 26
android.ndk = 25b

# 目标架构
android.archs = arm64-v8a

# 包含的额外文件
source.include_patterns = assets/*,screens/*,core/*,*.html,*.ttf

# 使用稳定的p4a分支
p4a.branch = master

# 自动接受SDK许可
android.accept_sdk_license = True

# 日志级别
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 0
