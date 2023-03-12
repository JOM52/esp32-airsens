#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file: airsens_central_conf.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-class

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 05.03.2023 --> small changes Venezia
"""
from ubinascii import hexlify
from machine import unique_id
# MQTT
BROKER_IP = '192.168.1.108'
TOPIC = 'airsens_now_test'
BROKER_CLIENT_ID = hexlify(unique_id())

# TTGO
BUTTON_MODE_PIN = 35
BUTTON_PAGE_PIN = 0
MODES = ['AUTO', 'OVERVIEW', 'BATTERY'] #, 'DEADS', 'AGE']  # modes
DEFAULT_MODE = 1 # Mode overview
DEFAULT_ROW_ON_SCREEN = 5 # given by the display hardware
CHOICE_TIMER_MS = 1000 # milli seconds
REFRESH_SCREEN_TIMER_MS = 10000 # milli seconds
BUTTON_DEBOUNCE_TIMER_MS = 10 # milli seconds

# WIFI
WIFI_WAN = 'jmb-home'
WIFI_PW = 'lu-mba01'

# BATTERY
BAT_OK = 3.4
BAT_LOW = 3.3
BAT_AGES_FILE = 'bat_ages.py'


