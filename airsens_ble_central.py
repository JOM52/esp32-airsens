#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_central.py

version: 1.0
date: 7.1.2022
author: jom52

email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

the *central* is always in listening mode (advertising).
It accepts the connections of the sensors, receives the data and then transmits them to MQTT by WIFI.
"""

from machine import Pin, Timer, SoftI2C
from utime import sleep_ms
import ubluetooth

class BLE():
    def __init__(self, name):   
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)

        self.led = Pin(2, Pin.OUT)
        self.timer1 = Timer(0)
        self.timer2 = Timer(1)
        
        self.pass_counter = 0
        
        self.disconnected()
        self.ble.irq(self.ble_irq)
        self.register()
        self.advertiser()

    # the blue led stop blinking wenn disconnected
    def disconnected(self):        
        self.timer1.deinit()
        self.timer2.deinit()

    # the blue led blink wen connected
    def connected(self):        
        self.timer1.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: self.led(1))
        sleep_ms(200)
        self.timer2.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: self.led(0))

    # irq handler
    def ble_irq(self, event, data):
        if event == 1:
            '''Central disconnected'''
            self.disconnected()
            self.led(1)
        
        elif event == 2:
            '''Central disconnected'''
            self.advertiser()
            self.connected()
        
        elif event == 3:
            '''New message received'''            
            buffer = self.ble.gatts_read(self.rx)
            message = buffer.decode('UTF-8').strip()
            if message[:3] == 'jmb':
                data = message.split(' ')
                if len(data) > 1:
                    print(data[1], data[2])
                else:
                    self.pass_counter += 1
                    print('passe:', self.pass_counter)
                    print('----------')
                
            if message == 'blue_led':
                blue_led.value(not blue_led.value())
                print('blue_led', blue_led.value())
                ble.send('blue_led' + str(blue_led.value()))

    # Nordic UART Service (NUS)       
    def register(self):        
        NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
        RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
        TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
            
        BLE_NUS = ubluetooth.UUID(NUS_UUID)
        BLE_RX = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
        BLE_TX = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_NOTIFY)
            
        BLE_UART = (BLE_NUS, (BLE_TX, BLE_RX,))
        SERVICES = (BLE_UART, )
        ((self.tx, self.rx,), ) = self.ble.gatts_register_services(SERVICES)

    
    def advertiser(self):
        name = bytes(self.name, 'UTF-8')
        self.ble.gap_advertise(100, bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name)
  
def main():
    print('program started')
    blue_led = Pin(2, Pin.OUT)
    ble = BLE("jmb_airsens_ttgo")

if __name__ == '__main__':
    main()

