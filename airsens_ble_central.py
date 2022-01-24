#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_central.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

the *central* is always in listening mode (advertising).
It accepts the connections of the sensors, receives the data and then transmits them to MQTT by WIFI.

v1.0 : 07.01.2022 --> first prototype
v1.2 : 17.01.2022 --> cleaned up, prototype stable for long test
v1.3 : 22.01.2022 --> message is now coded (added module lib.encode_decode.py)
"""

from machine import Pin, Timer, SoftI2C
from utime import sleep_ms
import ubluetooth
from lib.encode_decode import decode_msg

CENTRAL_NAME = "jmb_airsens_ttgo_02"
ADVERTISE_INTERVAL = 250 # org value = 100

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)


class BLE():
    def __init__(self, name):   
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)

        self.led = Pin(2, Pin.OUT)
        self.timer1 = Timer(0)
        self.timer2 = Timer(1)
        self.disconnected()
        
        self.ble.irq(self.ble_irq)
        self.register()
        self.advertiser()
        
        self.irq_list = []
        self.pass_counter = 0

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
        
        self.irq_list.append(event)
        
        if event == _IRQ_CENTRAL_CONNECT: #1
            '''Central connected'''
            self.disconnected()
            self.led(1)
        
        elif event == _IRQ_CENTRAL_DISCONNECT: #2
            '''Central disconnected'''
            self.advertiser()
            self.connected()
            print(self.irq_list)
            self.irq_list = []
        
        elif event == _IRQ_GATTS_WRITE: #3
            '''New message received'''
            buffer = self.ble.gatts_read(self.rx)
            message = buffer.decode('UTF-8').strip()
            if message[:3] == 'jmb':
                jmb_id, piece, temp, hum, pres, gas, bat = decode_msg(message)
                print(jmb_id + '-' + piece)
                print('--> temp: ' + str(temp))
                print('--> hum: ' + str(hum))
                print('--> pres: ' + str(pres))
                print('--> gas: ' + str(gas))
                print('--> bat: ' + str(bat))
                print('--------------')

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
        self.ble.gap_advertise(ADVERTISE_INTERVAL, bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name)
  
def main():
    print('central listening as <' + CENTRAL_NAME + '>')
    blue_led = Pin(2, Pin.OUT)
    ble = BLE(CENTRAL_NAME)

if __name__ == '__main__':
    main()

