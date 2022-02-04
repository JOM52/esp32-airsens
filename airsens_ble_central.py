#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_central.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

the *central* is always in listening mode (advertising).
It accepts the connections of the sensors, receives the data and then transmits them to MQTT by WIFI.

v0.1.0 : 07.01.2022 --> first prototype
v0.1.2 : 17.01.2022 --> cleaned up, prototype stable for long test
v0.1.3 : 22.01.2022 --> message is now coded (added module lib.encode_decode.py)
v0.1.4 : 28.01.2022 --> new message removed gas measurement
v0.1.5 : 30.01.2022 --> wifi, rtc, mqtt impemented
v0.1.6 : 31.01.2022 --> added crc management for transmission errors

"""

from machine import Pin, Timer, SoftI2C
from utime import sleep_ms
import ubluetooth
import ubinascii
import machine

from lib.encode_decode import decode_msg, crc
from lib import wifi_esp32 as wifi
from lib import umqttsimple2_jo as umqttsimple
from lib import rtc_esp32
from lib.log_and_count import LogAndCount
log = LogAndCount()

CENTRAL_NAME = "jmb_airsens_ttgo_01"
ADVERTISE_INTERVAL = 250 # org value = 100

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
    
MQTT_BROKER = '192.168.1.108'
CLIENT_ID = ubinascii.hexlify(machine.unique_id())
TOPIC_PUB = 'airsens_test'

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
        
        self.my_rtc = rtc_esp32.RtcEsp32()  # initialize the class
        self.my_rtc.rtc_init()  # initialize the rtc with local date and time


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
            try:
                '''Central connected'''
                self.disconnected()
                self.led(1)
            except Exception as err:
                err_no = log.counters('error', True)
                log.get_and_log_error_info(err, err_no, ' - _IRQ_CENTRAL_CONNECT')
                print(err)
        
        elif event == _IRQ_CENTRAL_DISCONNECT: #2
            try:
                '''Central disconnected'''
                self.advertiser()
                self.connected()
    #             print(self.irq_list)
                self.irq_list = []
            except Exception as err:
                err_no = log.counters('error', True)
                log.get_and_log_error_info(err, err_no, ' - _IRQ_CENTRAL_DISCONNECT')
                print(err)
        
        elif event == _IRQ_GATTS_WRITE: #3
            try:
                '''New message received'''
                buffer = self.ble.gatts_read(self.rx)
    #             print(buffer)
                message = buffer.decode('UTF-8').strip()
                if message[:3] == 'jmb':
                    passe = log.counters('passe', True)
                    now = self.my_rtc.rtc_now()  # get date and time
                    datetime_formated = self.my_rtc.format_datetime(now)
                    jmb_id, piece, temp, hum, pres, bat, rx_crc = decode_msg(message)
                    calc_crc = crc(message[:17])
                    if rx_crc == calc_crc:
                        try:
                            client = self.connect_and_subscribe(CLIENT_ID, MQTT_BROKER, TOPIC_PUB)
                            client.publish(TOPIC_PUB, message)
                            client.disconnect()
                            print(str(passe) + ' - '
                                  + datetime_formated + ' - '
                                  + jmb_id + '-'
                                  + piece
                                  + ' --> temp: ' + str(temp)
                                  + ' --> hum: ' + str(hum)
                                  + ' --> pres: ' + str(pres)
                                  + ' --> bat: ' + str(bat)
                                  + ' --> crc: ' + str(calc_crc)
                                  + ' --> errors: ' + str(log.counters('error')))
                        except Exception as err:
                            err_no = log.counters('error', True)
                            log.get_and_log_error_info(err, err_no, ' - MQTT publish')
                            print(err)
                    else:
                        err_no = log.counters('error', True)
                        log.get_and_log_error_info('Transmission error: bad CRC', err_no)                    
                            
            except Exception as err:
                err_no = log.counters('error', True)
                log.get_and_log_error_info(err, err_no, ' - _IRQ_GATTS_WRITE')
                print(err)
        
    def connect_and_subscribe(self, client_id, mqtt_broker, topic_pub):
        client = umqttsimple.MQTTClient(client_id, mqtt_broker)
        client.connect(True)
    #     print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt_broker, topic_pub))
        return client

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
    
    print('-----------------------------------------------------------')
#     client = connect_and_subscribe(CLIENT_ID, MQTT_BROKER, TOPIC_PUB)
#     print('MQTT client connected on ' + MQTT_BROKER + ' with the topic ' + TOPIC_PUB)
#     

    my_wifi = wifi.WifiEsp32('jmb-home', 'lu-mba01')
    my_wifi.connect_wifi()
    my_rtc = rtc_esp32.RtcEsp32()  # initialize the class
    my_rtc.rtc_init()  # initialize the rtc with local date and time
    now = my_rtc.rtc_now()  # get date and time
    datetime_formated = my_rtc.format_datetime(now)
    msg = "now date and time :" + datetime_formated + '\n'
    my_rtc = None
    print(msg)
    print('-----------------------------------------------------------')
    print('central listening as <' + CENTRAL_NAME + '>')
    blue_led = Pin(2, Pin.OUT)
    ble = BLE(CENTRAL_NAME)

if __name__ == '__main__':
    main()

