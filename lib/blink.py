#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: blink.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

blink internal led
v0.1.0 : 02.02.2022 --> first prototype
v0.1.1 : 24.04.2022 --> limited import to necessary functions
"""

from machine import Pin
from utime import sleep_ms

class Blink:
    def __init__(self, led_pin=2):
#         self._INTERNAL_BLUE_LED_PIN = led_pin
        self._internal_blue_led = Pin(led_pin, Pin.OUT)

    def blink_internal_blue_led(self, t_on_ms=100, t_off_ms=100, t_pause_ms=100, n_repeat=5):
        
        for n in range(n_repeat):
            self._internal_blue_led.on()
            sleep_ms(t_on_ms)
            self._internal_blue_led.off()
            sleep_ms(t_off_ms)
        sleep_ms(t_pause_ms)
    
if __name__ == '__main__':
    led_pin = 2 # the pin of the LED
    blink = Blink(led_pin) # instantiates the class
    # blink on = 500 ms, off = 750 ms, pause = 1000 ms, repeat = 3
    blink.blink_internal_blue_led(500, 750, 1000, 3)
    sleep_ms(1000)
    # blink with the default parameters
    blink.blink_internal_blue_led()
