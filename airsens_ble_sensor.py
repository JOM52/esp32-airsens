#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_ble_sensor.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

The sensors are made with an ESP32 microcontroller and can be powered by battery or by USB.
They transmit the data to a central also realized with an ESP32 by a bluetooth
low energy communication (BLE)

v0.1.0 : 07.01.2022 --> first prototype
v0.1.1 : 09.01.2022 --> process in work
v0.1.2 : 11.01.2022 --> process time measurment
v0.1.3 : 13.01.2022 --> added logic for uC NODE
v0.1.4 : 16.01.2022 --> transfert functions from sensor to scan (git branch: sensor_test)
v0.1.5 : 17.01.2022 --> optimized the import --> prototype stable for long test
v0.1.6 : 19.01.2022 --> corrected error management
v0.1.7 : 20.01.2022 --> corrected errors on conection
v0.1.8 : 21.01.2022 --> the message is coded in 20 bytes (added module lib encode_decode.py)
v0.1.9 : 22.02.2022 --> error management improved
v0.1.10 : 22.01.2022 --> write on uart improved
v0.1.11 : 22.01.2022 --> read config_sensor.txt improved
v0.1.12 : 22.01.2022 --> improved error counter and dispaly
v0.1.13 : 23.01.2022 --> _IRQ_GATTC_SERVICE_DONE checked
v0.1.14 : 24.01.2022 --> T_WAIT_FOR_IRQ_TERMINATED_MS removed
v0.1.15 : 26.01.2022 --> error management impoved
v0.1.16 : 27.01.2022 --> mgmt of central not running error
v0.1.17 : 27.01.2022 --> added execution time mesurment
v0.1.18 : 31.01.2022 --> added crc management for transmission errors
v0.1.19 : 02.02.2022 --> modified the deepsleep time calculation
v0.1.20 : 02.02.2022 --> some lib files modified into class
v0.1.21 : 04.02.2022 --> adapted for log error with numer of occurences
v0.1.22 : 08.02.2022 --> integed all count in the file counter (no kore file error.txt)
v0.1.23 : 08.02.2022 --> impoved the loading of libraries
v0.1.24 : 14.02.2022 --> added WROOM uC
v0.1.25 : 14.02.2022 --> if battery low endless deepsleep to protect battery
v0.1.26 : 16.02.2022 --> add check if ON_BATTERY
v0.1.27 : 20.02.2022 --> added PROTO uC
v0.1.28 : 23.02.2022 --> small correction on error management
v0.1.29 : 23.02.2022 --> working on write data over uart (BleJmbSensor.write)
v0.1.30 : 24.02.2022 --> better error management on write over uart
v0.1.31 : 07.03.2022 --> procedure connect simplified
v0.1.32 : 09.03.2022 --> integration of config_parser.py
v0.1.33.ppk : 21.04.2022 --> intégration of flags for Nordic PPK II
v0.1.34.ppk : 22.04.2022 --> revision off exec time measurement
v0.1.35.ppk : 26.04.2022 --> try to reduce exec time
v0.1.36 : 03.05.2022 --> limit import to necessary
v0.1.37 : 06.05.2022 --> simplified ADC measure (without calibration)
v0.1.38 : 25.05.2022 --> added LED_I0 and LED_I1 for status info
v0.1.39 : 29.05.2022 --> added TOUCH_0 IO12
v0.1.40 : 29.05.2022 --> added wake_on_touch IO13
v0.1.41 : 01.06.2022 --> ppk logic signals included
                            before ppk0: system loading
                            ppk0: const init and standard import
                            ppk1: lib import and class instatiation (encode_decode, log_and_count, config_parser)
                            ppk2: class instantiation (I2C, Sensor, BLE)
                            ppk3: sensor and bat measurement
                            ppk4: encode and sens message on BLE
                            ppk5: finishing actions
"""
VERSION = '0.1.40'
PROGRAM_NAME = 'airsens_ble_sensor.py'

from machine import Pin, freq, TouchPad
from esp32 import wake_on_touch
freq(160000000)

# Nordic Power Profiler Kkit II logic chanels p01
# PPK_0_PIN = 5
# PPK_1_PIN = 25
# PPK_2_PIN = 32
# PPK_3_PIN = 26
# PPK_4_PIN = 4
# PPK_5_PIN = 33
# p02
PPK_0_PIN = 14 
PPK_0 = Pin(PPK_0_PIN, Pin.OUT)
# ppk logics signals ------------------------
PPK_0.on() # const init and standard import
#--------------------------------------------

PPK_1_PIN = 25
PPK_2_PIN = 26
PPK_3_PIN = 27
PPK_4_PIN = 32
PPK_5_PIN = 33

PPK_1 = Pin(PPK_1_PIN, Pin.OUT)
PPK_2 = Pin(PPK_2_PIN, Pin.OUT)
PPK_3 = Pin(PPK_3_PIN, Pin.OUT)
PPK_4 = Pin(PPK_4_PIN, Pin.OUT)
PPK_5 = Pin(PPK_5_PIN, Pin.OUT)

PPK_1.off()
PPK_2.off()
PPK_3.off()
PPK_4.off()
PPK_5.off()

# LED_I0_PIN = 4
# LED_I1_PIN = 5
# LED_I0 = Pin(LED_I0_PIN, Pin.OUT)
# LED_I1 = Pin(LED_I1_PIN, Pin.OUT)
# LED_I0.off()
# LED_I1.off()
# LED_I0.on()
# LED_I1.on()

# TOUCH
# TOUCH_0_PIN = 12
# TOUCH_0 = TouchPad(Pin(TOUCH_0_PIN))
# TOUCH_0_VAL = TOUCH_0.read()
# print('TOUCH_0_VAL:', TOUCH_0_VAL)

# wake on touch
TOUCH_WAKE_PIN = 13
TOUCH_WAKE = TouchPad(Pin(TOUCH_WAKE_PIN, mode = Pin.IN))
TOUCH_WAKE.config(500)
wake_on_touch(True)

DEBUG_MES_EXEC_TIME = False
if DEBUG_MES_EXEC_TIME:
    from lib.exec_time_mes import exec_time_mes
    mes = exec_time_mes(stat_mes=False)
    mes.time_step('start')

ON_BATTERY = True

from utime import sleep_ms
from bluetooth import BLE
from machine import ADC, reset, SoftI2C, deepsleep
from ubinascii import unhexlify
from sys import exit
from micropython import const

if DEBUG_MES_EXEC_TIME: mes.time_step('standard import')

# ppk logics signals ------------------------
PPK_0.off()
PPK_1.on() # lib import and class instantiation
#--------------------------------------------

# from lib.adc1_cal import ADC1Cal
# if DEBUG_MES_EXEC_TIME: mes.time_step('lib import ADC1Cal')

from lib.encode_decode import EncodeDecode
encode_decode = EncodeDecode()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import EncodeDecode')

from lib.log_and_count import LogAndCount
log = LogAndCount()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import LogAndCount')

# from lib.blink import Blink
# blink = Blink(2)
# if DEBUG_MES_EXEC_TIME: mes.time_step('lib import Blink')


# Hardware choices to import from config_sensor.txt
CONNECTED_SENSOR_TYPE = None
MICROCONTROLER = None
SENSOR_ID = None
T_DEEPSLEEP_MS = None

# read options in airsens.conf
from lib.config_parser import ConfigParser
conf_filename = 'airsens.conf'
cp = ConfigParser()
if DEBUG_MES_EXEC_TIME: mes.time_step('conf import')

cp.read(conf_filename)

if DEBUG_MES_EXEC_TIME: mes.time_step('conf read file')

CONNECTED_SENSOR_TYPE = 'BME280'
MICROCONTROLER = 'WEMOS'
SENSOR_ID = 'pi'
T_DEEPSLEEP_MS = 15000
# if DEBUG_MES_EXEC_TIME: mes.time_step('conf read values')

if CONNECTED_SENSOR_TYPE == 'BME280':
    import lib.bme280 as bmex80
elif CONNECTED_SENSOR_TYPE == 'BME680':
    import lib.bme680 as bmex80
elif CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
    pass
else:
    print('ERROR')
    print('No known sensor defined. Correct that and restart the program')
    print('Possibilities are BME280, BME680 ot NO_SENSOR')
    exit()
if DEBUG_MES_EXEC_TIME: mes.time_step('sensor import')
    
# sensor pins and init
BM_SDA_PIN = 21
BM_SCL_pin = 22
# 
# if MICROCONTROLER == 'TTGO':
#     BM_VCC_PIN = 15
#     BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
#     BM_VCC_PIN.on()
# elif MICROCONTROLER == 'WEMOS':
#     BM_VCC_PIN = 17
#     BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
#     BM_VCC_PIN.on()
#     BM_GND_PIN = 16
#     BM_GND_PIN = Pin(BM_GND_PIN, Pin.OUT)
#     BM_GND_PIN.off()
# elif MICROCONTROLER == 'NODE':
#     BM_VCC_PIN = 19
#     BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
#     BM_VCC_PIN.on()
#     BM_GND_PIN = 18
#     BM_GND_PIN = Pin(BM_GND_PIN, Pin.OUT)
#     BM_GND_PIN.off()
# elif MICROCONTROLER == 'WROOM':
#     BM_VCC_PIN = 23
#     BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
#     BM_VCC_PIN.on()
# elif MICROCONTROLER == 'PROTO':
#     pass
# else:
#     print('ERROR')
#     print('No known microcontroler defined. Correct that and restart the program')
#     print('Possibilities are TTGO, WEMOS, NODE or WROOM')
#     exit()
# if DEBUG_MES_EXEC_TIME: mes.time_step('uC config')

# analog voltage measurement
R1 = 100000 # first divider bridge resistor
R2 = 33000 # second divider bridge resistor
ADC1_PIN = const(35) # Measure of analog voltage (ex: battery voltage following)
DIV = R2 / (R1 + R2) # (R2 / R1 + R2) 
AVERAGING = const(10)                # no. of samples for averaging
# ubatt = ADC1Cal(Pin(ADC1_PIN, Pin.IN), DIV, None, AVERAGING, "ADC1 eFuse Calibrated")
# # set ADC result width
# ubatt.width(ADC.WIDTH_12BIT)
# # set attenuation
# ubatt.atten(ADC.ATTN_6DB)
# battery
UBAT_100 = 3.0
UBAT_0 = 2.5

pot = ADC(Pin(ADC1_PIN))            
pot.atten(ADC.ATTN_6DB ) # Umax = 2V
pot.width(ADC.WIDTH_12BIT) # 0 ... 4095

# IRQ constants
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_WRITE_DONE = const(17)

if DEBUG_MES_EXEC_TIME: mes.time_step('analog config')

class BleJmbSensor:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
#         self._name = None
        self._addr_type = None
        self._addr = None

        # Connected device.
        self._conn_handle = None
        self._rx_handle = None
        
        # connect handling
        self._irq_peripheral_connect = False
        self._irq_peripheral_disconnect = False
        self._irq_write_done = False
        self._irq_service_done = False
        
    def _irq(self, event, data):
        if event == _IRQ_PERIPHERAL_CONNECT: #7
            conn_handle, addr_type, addr = data
            # Connect successful.
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)
                self._irq_peripheral_connect = True

        elif event == _IRQ_PERIPHERAL_DISCONNECT: #8
            # Disconnect (either initiated by us or the remote end).
            self._irq_peripheral_disconnect = True
            conn_handle, _, _ = data
            if conn_handle == 65535:
                log.log_error('Central is not running')
                reset()
        
        elif event == _IRQ_GATTC_SERVICE_DONE: #10
            self._irq_service_done = True

        elif event == _IRQ_GATTC_WRITE_DONE: #17
            self._irq_write_done = True

    def asc_to_bytes(self, v_ascii):
        return unhexlify((v_ascii))

#     def config_read_conn_info(self):
#         with open ('config_uart.txt', 'r') as f:
#             config_data = f.readlines()
#             for l in config_data:
#                 n, v = l.split(':')
#                 if n == 'addr_type':
#                     self._addr_type = int(v)
#                 elif n == 'addr':
#                     self._addr = self.asc_to_bytes(v.replace('\n', ''))
#                 elif n == 'name':
#                     self._name = v.replace('\n', '')
#                 elif n == 'rx_handle':
#                     self._rx_handle = int(v)
                
    def config_read_conn_info(self):
        
#         self._addr_type = 0 #int(cp.get('UART', 'ADDR_TYPE'))
#         self._addr = self.asc_to_bytes('84cca85f4a82') #self.asc_to_bytes(cp.get('UART', 'ADDR').replace('\n', '')) 
#         self._name = 'jmb_central_01' #cp.get('UART', 'NAME').replace('\n', '')
#         self._rx_handle = 24 #int(cp.get('UART', 'RX_HANDLE'))

        self._addr_type = int(cp.get('UART', 'ADDR_TYPE'))
        self._addr = self.asc_to_bytes(cp.get('UART', 'ADDR').replace('\n', '')) 
        self._name = cp.get('UART', 'NAME').replace('\n', '')
        self._rx_handle = int(cp.get('UART', 'RX_HANDLE'))

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, scan_duration_ms=500): 
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Send data over the UART
    def write(self, v, i):
        n_tries = 5
        write_ok = False
        err = None
        while n_tries > 0:
            try:
                self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1)
                n_tries = 0
                write_ok = True
            except Exception as e:
                err = e
                try:
                    log.log_error('Try to reconnect in write essai:' + str(n_tries-1), e)
#                     self.connect(self._addr_type, self._addr)
                    self.connect()
                    while not self._irq_peripheral_connect or not self._irq_service_done:
                        pass
                except:
                    print('connect not possible')
                    log.log_error('Connect not possible', err)
                n_tries -= 1
                print('n_tries:', n_tries)
                sleep_ms(500)
            
        if not write_ok:
            log.counters('error', True) # increment error counter
            log.log_error('Write on BLE UART error --> reset()', err)
            reset()

def main():
#     try:

        # ppk logics signals ------------------------
        PPK_1.off()
        PPK_2.on() # class instantiation (I2C, Sensor, BLE)
        #--------------------------------------------
        print('=================================================')
        print(PROGRAM_NAME + ' - Version:' + VERSION)
        if DEBUG_MES_EXEC_TIME: mes.time_step('entering main')
        i = log.counters('passe', True)
        if DEBUG_MES_EXEC_TIME: mes.time_step('log init')

        # instanciation of bme280, bmex80 - Pin assignment
        i2c = SoftI2C(scl=Pin(BM_SCL_pin), sda=Pin(BM_SDA_PIN), freq=10000)
        if DEBUG_MES_EXEC_TIME: mes.time_step('I2C class initialise')
        try:
            if CONNECTED_SENSOR_TYPE == 'BME280':
                bmeX = bmex80.BME280(i2c=i2c)
            elif CONNECTED_SENSOR_TYPE == 'BME680':
                bmeX = bmex80.BME680_I2C(i2c=i2c)
            elif CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
                bmeX = None
        except:
            print('Pas trouvé de ' + CONNECTED_SENSOR_TYPE + ' branché?')
            print('Corrigez et relancez le programme!')
            exit()
        if DEBUG_MES_EXEC_TIME: mes.time_step('sensor class initialise')
        
        # instatiation of bluetooth.BLE
        ble = BLE()
        sensor = BleJmbSensor(ble)
        if DEBUG_MES_EXEC_TIME: mes.time_step('ble class initialise')
        
        # ppk logics signals ------------------------
        PPK_2.off()
        PPK_3.on() # sensor and bat measurement
        #--------------------------------------------

        # read and initialise variable from config file
        sensor.config_read_conn_info()
        
        if CONNECTED_SENSOR_TYPE == 'BME680':
            gas = bmeX.gas / 1000
        else:
            gas = 0
            
        if CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
            temp = 22.2
            hum = 55.5
            pres = 999
#             bat = 4.44
        else:
            temp = float(bmeX.temperature)
            hum = float(bmeX.humidity)
            pres = float(bmeX.pressure)
#             bat = float(ubatt.voltage/1000)
        if DEBUG_MES_EXEC_TIME: mes.time_step('sensor read')
            
        bat = 0
        for a in range(AVERAGING):
            bat += pot.read()
        # atten = 6dB ==> u max = 2V
        # width = 12 bits ==> 0 ... 4095
        bat = bat / AVERAGING * (2 / 4095) / DIV
#         print('Ubat:', '{:.2f}'.format(bat))
        if DEBUG_MES_EXEC_TIME: mes.time_step('U bat read')
        
        # ppk logics signals ------------------------
        PPK_3.off()
        PPK_4.on() # encode and sens message on BLE
        #--------------------------------------------
            
        msg = encode_decode.encode_msg('jmb', SENSOR_ID, temp, hum, pres, bat)
        crc_val = encode_decode.get_crc(msg)
        msg += crc_val
        if DEBUG_MES_EXEC_TIME: mes.time_step('encode measures')
        
        #connect to the central
#         sensor.connect(sensor._addr_type, sensor._addr)
        sensor.connect()
        while not sensor._irq_peripheral_connect or not sensor._irq_service_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('central connect')
        
        sensor.write(msg, i)
        while  not sensor._irq_write_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('message write')

#         blink.blink_internal_blue_led(100, 100, 100, 3)
#         if DEBUG_MES_EXEC_TIME: mes.time_step('blink')
        
        print('jmb_' + str(SENSOR_ID) + ' --> ' + msg + ' crc:' + crc_val + ' --> ' + sensor._name)
        
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('central disconnect')
        
        # ppk logics signals ------------------------
        PPK_4.off()
        PPK_5.on() # finishing actions
        #--------------------------------------------

        # check the level of the battery
        if bat > (0.98 * UBAT_0) or not ON_BATTERY:
            # finishing tasks
#             if DEBUG_MES_EXEC_TIME: mes.time_step('stop')
            if DEBUG_MES_EXEC_TIME:
                mes.time_step('stop')
                t_deepsleep = max(T_DEEPSLEEP_MS - mes._total_time, 10)
                print('passe', i, '- error count:', log.counters('error'),'-->',  str(mes._total_time) + 'ms')
            else:
                t_deepsleep = T_DEEPSLEEP_MS
                print('passe', i, '- error count:', log.counters('error'))
            print('going to deepsleep for: ' + str(t_deepsleep) + ' ms')
            print('=================================================')
        
            # ppk logics signals ------------------------
            PPK_5.off() # program terminated
            #--------------------------------------------
            
            deepsleep(t_deepsleep)
        else:
            print('Endless deepsleep due to low battery')
            if DEBUG_MES_EXEC_TIME: mes.time_step('endless deepsleep due to low battery')
            deepsleep()
        
#     except Exception as e:
#         log.counters('error', True)
#         log.log_error('Main program error', e)
#         sleep_ms(2000)
#         reset()

if __name__ == "__main__":
    main()
