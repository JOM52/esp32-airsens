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
v1.2 : 17.01.2022 -->cleaned up, prototype stable for long test
"""

import ubluetooth
import ubinascii
import machine
import utime
import lib.umqttsimple2_jo as umqttsimple

from lib.wifi_esp32 import WifiEsp32 
from lib.rtc_esp32 import RtcEsp32
from machine import Pin, Timer, SoftI2C
from utime import sleep_ms

CENTRAL_NAME = "jmb_airsens_wemos_01"

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
        
        self.client = None
        self.TOPIC_PUB = None
        
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
                    msg = str(data[1]) + '-' + str(data[2])
                    print(msg)
            #         msg += 'MQTT client connected on ' + MQTT_BROKER + ' with the topic ' + TOPIC_PUB
                    self.client.publish(self.TOPIC_PUB, msg)
#                     utime.sleep_ms(50)
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
        
def connect_and_subscribe(client_id, mqtt_broker, topic_pub):
    client = umqttsimple.MQTTClient(client_id, mqtt_broker)
    client.connect()
#     print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_broker, topic_pub))
    return client
  
def main():
    
    MQTT_BROKER = '192.168.1.108'
    CLIENT_ID = ubinascii.hexlify(machine.unique_id())
    TOPIC_PUB = 'airsens_test'
    
    print('central listening as <' + CENTRAL_NAME + '>')
    print('-----------------------------------------------------------')
    
    my_wifi = WifiEsp32('jmb-home', 'lu-mba01')  # initialize the class
    my_wifi.connect_wifi()  # connect to the wifi network
    
    my_rtc = RtcEsp32()  # initialize the class
    my_rtc.rtc_init()  # initialize the rtc with local date and time
    # extract the date and time values in str format and print it
    now = my_rtc.rtc_now()  # get date and time
    datetime_formated = my_rtc.format_datetime(now)
    print("now date and time :", datetime_formated)
    print('-----------------------------------------------------------')
    
    blue_led = Pin(2, Pin.OUT)
    ble = BLE(CENTRAL_NAME)
    ble.TOPIC_PUB = TOPIC_PUB
    ble.client = connect_and_subscribe(CLIENT_ID, MQTT_BROKER, TOPIC_PUB)

if __name__ == '__main__':
    main()

