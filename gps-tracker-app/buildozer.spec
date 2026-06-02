[app]

# App元数据
title = GPS轨迹记录器
package.name = gpstracker
package.domain = com.geotagger
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,json
version = 1.0.0

# Python依赖
requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer,android,pyjnius,pycryptodome

# 图标（如有）
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# 全屏模式
fullscreen = 0

# 屏幕方向：portrait=竖屏，landscape=横屏，sensorLandscape=传感器横屏
orientation = portrait

# Android权限
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,FOREGROUND_SERVICE,INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Android API版本
android.api = 33
android.minapi = 26
android.ndk = 25b

# 目标架构
android.archs = arm64-v8a

# 后台服务
android.services = GPSService:services/gps_service.py:foreground

# Gradle依赖（用于前台服务通知）
# android.gradle_dependencies = 'com.google.android.gms:play-services-location:21.0.1'

# 入口文件
# entry.main = main.py:main

# 包含的额外文件
source.include_patterns = assets/*,screens/*,core/*

# 日志级别
log_level = 2

# P4A (python-for-android) recipe
p4a.branch = develop

# 自动接受SDK许可
android.accept_sdk_license = True

[buildozer]

# Buildozer日志级别 (0=quiet, 1=error, 2=info, 3=debug, 4=verbose)
log_level = 2

# 警告处理
warn_on_root = 0
