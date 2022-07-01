#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: blink.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

blink internal led
v0.1.0 : 12.06.2021 --> first prototype
v0.1.1 : 01.07.2022 --> added "isconnected_wifi"
"""
import network
import utime

class WifiEsp32: 
    
    def __init__(self, ssid, pw):
        
        self.WIFI_SSID = ssid
        self.WIFI_PW = pw
        self.station = None
        
    def connect_wifi(self):
        ssid = self.WIFI_SSID 
        password = self.WIFI_PW
        self.station = network.WLAN(network.STA_IF)
        self.station.active(True)
        self.station.connect(ssid, password)

        # check connection
        tmo = 100
        while not self.isconnected_wifi():
           utime.sleep_ms(100)
           tmo -= 1
           if tmo == 0:
               print('wifi connection breaked')
               break
        print('wifi connected on ' + self.WIFI_SSID + ' -> ' + str(self.station.isconnected()))
        print('network config:', self.station.ifconfig())
        
    def isconnected_wifi(self):
        return self.station.isconnected()
        
    
# demo prg for this class
if __name__ == '__main__':
    
    print('---------------------------------------------------------')
    my_wifi = WifiEsp32('jmb-guest', 'pravidondaz')  # initialize the class
    my_wifi.connect_wifi()  # connect to the wifi network
    print('---------------------------------------------------------')

