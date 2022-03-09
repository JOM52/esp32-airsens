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
v0.1.7 : 22.02.2022 --> improved error management
v0.1.8 : 23.02.2022 --> corrected import and use for encode_decode
v0.1.9 : 23.02.2022 --> corrected import for log_and_count
v0.1.10 : 23.02.2022 --> level of debug increased
v0.1.11 : 23.02.2022 --> added line number and file in log_error
v0.1.12 : 07.03.2022 --> wifi account as constant
v0.1.13 : 09.03.2022 --> integration of config_parser.py
"""
VERSION = '0.1.13'
PROGRAM_NAME = 'airsens_ble_central.py'

from machine import Pin, Timer, SoftI2C
from utime import sleep_ms
import ubluetooth
import ubinascii
import machine
import sys

from lib.encode_decode import EncodeDecode
encode_decode = EncodeDecode()
from lib import wifi_esp32 as wifi
from lib import umqttsimple2_jo as umqttsimple
from lib import rtc_esp32
from lib.log_and_count import LogAndCount
log = LogAndCount()

# read options in airsens.conf
from lib.config_parser import ConfigParser
conf_filename = 'airsens.conf'
cp = ConfigParser()
cp.read(conf_filename)
try:
    # CENTRAL options
    if cp.has_option('CENTRAL', 'ADVERTISING_INTERVAL_MS'):
        ADVERTISE_INTERVAL = int(cp.get('CENTRAL', 'ADVERTISING_INTERVAL_MS'))
    else:
        raise Exception('"CENTRAL:ADVERTISING_INTERVAL_MS"')
    if cp.has_option('CENTRAL', 'NAME'):
        CENTRAL_NAME = cp.get('CENTRAL', 'NAME')
    else:
        raise Exception('"CENTRAL:NAME"')
    
    # MQTT options
    if cp.has_option('MQTT', 'BROKER_IP'):
        BROKER_IP = cp.get('MQTT', 'BROKER_IP')
    else:
        raise Exception('"MQTT:BROKER_IP"')
    if cp.has_option('MQTT', 'TOPIC'):
        TOPIC = cp.get('MQTT', 'TOPIC')
    else:
        raise Exception('"MQTT:TOPIC"')
    BROKER_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
    
    # BLE options
    if cp.has_option('BLE', 'NUS_UUID'):
        NUS_UUID = cp.get('BLE', 'NUS_UUID')
    else:
        raise Exception('"BLE:NUS_UUID"')
    if cp.has_option('BLE', 'RX_UUID'):
        RX_UUID = cp.get('BLE', 'RX_UUID')
    else:
        raise Exception('"BLE:RX_UUID"')
    if cp.has_option('BLE', 'TX_UUID'):
        TX_UUID = cp.get('BLE', 'TX_UUID')
    else:
        raise Exception('"BLE:TX_UUID"')
    
    # WIFI options
    if cp.has_option('WIFI', 'WAN'):
        WIFI_WAN = cp.get('WIFI', 'WAN')
    else:
        raise Exception('"WIFI:WAN"')
    if cp.has_option('WIFI', 'PW'):
        WIFI_PW = cp.get('WIFI', 'PW')
    else:
        raise Exception('"WIFI:PW"')
except Exception as e:
    print('The ' + str(e) + ' key does not exist in the "airsens.conf" configuration file.')
    print('Correct the file then relaunch the program.')
    sys.exit()

# CENTRAL_NAME = "jmb_airsens_wroom_01"
# ADVERTISE_INTERVAL = 250 # org value = 100
# BROKER_IP = '192.168.1.123'
# BROKER_CLIENT_ID = ubinascii.hexlify(machine.unique_id())
# TOPIC = 'airsens_test'
# WIFI_WAN = 'jmb-home'
# WIFI_PW = 'lu-mba01'
# NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
# RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
# TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'

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
        print('--> 00')        
        self.irq_list.append(event)
        if event == _IRQ_CENTRAL_CONNECT: #1
            try:
                '''Central connected'''
                self.disconnected()
                print('--> 01')        
                self.led(1)
            except Exception as err:
                print('--> 02')        
                log.counters('error', True)
                log.log_error('_IRQ_CENTRAL_CONNECT', err)
                print(err)
        
        elif event == _IRQ_CENTRAL_DISCONNECT: #2
            try:
                print('--> 03')        
                '''Central disconnected'''
                self.advertiser()
                self.connected()
                print('--> 04')        
    #             print(self.irq_list)
                self.irq_list = []
            except Exception as err:
                print('--> 05')        
                log.counters('error', True)
                log.log_error('_IRQ_CENTRAL_DISCONNECT', err)
                print(err)
        
        elif event == _IRQ_GATTS_WRITE: #3
            print('--> 06')        
            try:
                '''New message received'''
                print('-----> 0')
                buffer = self.ble.gatts_read(self.rx)
                print('-----> 1')
                message = buffer.decode('UTF-8').strip()
                print('-----> 2')
                if message[:3] == 'jmb':
                    print('-----> 3')
                    passe = log.counters('passe', True)
                    now = self.my_rtc.rtc_now()  # get date and time
                    datetime_formated = self.my_rtc.format_datetime(now)
                    jmb_id, piece, temp, hum, pres, bat, rx_crc = encode_decode.decode_msg(message)
                    calc_crc = encode_decode.get_crc(message[:17])
                    print('-----> 4')
                    if rx_crc == calc_crc:
                        try:
                            client = self.connect_and_subscribe(BROKER_CLIENT_ID, BROKER_IP, TOPIC)
                            print('-----> 5')
                            client.publish(TOPIC, message)
                            print('-----> 6')
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
                            print('--> 07')        
                            log.counters('error', True)
                            log.log_error('MQTT publish', err)
                            print(err)
                    else:
                        print('--> 08')        
                        log.counters('error', True)
                        log.log_error('Transmission error: bad CRC')                    
                            
            except Exception as err:
                print('--> 09')        
                log.counters('error', True)
                log.log_error('_IRQ_GATTS_WRITE', err)
                print('err:', err)
       
    def connect_and_subscribe(self, broker_client_id, broker_ip, topic):
        print('--> 10')        
        client = umqttsimple.MQTTClient(broker_client_id, broker_ip)
        client.connect(True)
    #     print('Connected to %s MQTT broker, subscribed to %s topic' % (broker_ip, topic))
        print('--> 11')        
        return client

    # Nordic UART Service (NUS)       
    def register(self):        
        print('--> 12')        
            
        BLE_NUS = ubluetooth.UUID(NUS_UUID)
        BLE_RX = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
        BLE_TX = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_NOTIFY)
            
        BLE_UART = (BLE_NUS, (BLE_TX, BLE_RX,))
        SERVICES = (BLE_UART, )
        ((self.tx, self.rx,), ) = self.ble.gatts_register_services(SERVICES)
        print('--> 13')        

    
    def advertiser(self):
        print('--> 14')        
        name = bytes(self.name, 'UTF-8')
        self.ble.gap_advertise(ADVERTISE_INTERVAL, bytearray('\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name)
        print('--> 15')        
  
def main():
    
#     client = connect_and_subscribe(BROKER_CLIENT_ID, BROKER_IP, TOPIC)
#     print('MQTT client connected on ' + BROKER_IP + ' with the topic ' + TOPIC)
#     
    try:
        print('-----------------------------------------------------------')
        print(PROGRAM_NAME + ' - Version:' + VERSION)
#         my_wifi = wifi.WifiEsp32('jmb-home', 'lu-mba01')
        my_wifi = wifi.WifiEsp32(WIFI_WAN, WIFI_PW)
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
    except Exception as err:
        log.counters('error', True)
        log.log_error('_IRQ_GATTS_WRITE', err)
        print('err:', err)

if __name__ == '__main__':
    main()

