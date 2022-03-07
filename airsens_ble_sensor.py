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
"""
VERSION = '0.1.30'

import esp
esp.osdebug("*", esp.LOG_DEBUG) 

ON_BATTERY = False

from utime import sleep_ms, ticks_ms
start_time = ticks_ms()

DEBUG_MES_EXEC_TIME = False
if DEBUG_MES_EXEC_TIME:
    from lib.exec_time_mes import exec_time_mes
    mes = exec_time_mes()
    mes.time_step('start')

from bluetooth import UUID, FLAG_WRITE, FLAG_READ, FLAG_NOTIFY, BLE
from machine import Pin, ADC, reset, SoftI2C, deepsleep
from ubinascii import hexlify, unhexlify
from sys import exit, print_exception
from uio import StringIO
from micropython import const
from random import uniform
if DEBUG_MES_EXEC_TIME: mes.time_step('standard import')

from lib.adc1_cal import ADC1Cal
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import ADC1Cal')

from lib.encode_decode import EncodeDecode
encode_decode = EncodeDecode()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import EncodeDecode')

from lib.log_and_count import LogAndCount
log = LogAndCount()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import LogAndCount')

from lib.blink import Blink
blink = Blink(2)
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import Blink')


# Hardware choices to import from config_sensor.txt
CONNECTED_SENSOR_TYPE = None
MICROCONTROLER = None
SENSOR_ID = None
T_DEEPSLEEP_MS = None
        
# def sensor_config_read():
with open('config_sensor.txt', 'r') as f:
    lines = f.readlines()
    for l in lines:
        c, v = l.replace('\n\r', '').split('=')
        if c == 'CONNECTED_SENSOR_TYPE': CONNECTED_SENSOR_TYPE = v.strip()
        elif c == 'MICROCONTROLER': MICROCONTROLER = v.strip()
        elif c == 'SENSOR_ID': SENSOR_ID = v.strip()
        elif c == 'T_DEEPSLEEP_MS': T_DEEPSLEEP_MS = int(v)
        
# todo --- a tester ----------------------------
# T_DEEPSLEEP_MS += uniform(-500, 500)

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

if MICROCONTROLER == 'TTGO':
    BM_VCC_PIN = 15
    BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
    BM_VCC_PIN.on()
elif MICROCONTROLER == 'WEMOS':
    BM_VCC_PIN = 17
    BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
    BM_VCC_PIN.on()
    BM_GND_PIN = 16
    BM_GND_PIN = Pin(BM_GND_PIN, Pin.OUT)
    BM_GND_PIN.off()
elif MICROCONTROLER == 'NODE':
    BM_VCC_PIN = 19
    BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
    BM_VCC_PIN.on()
    BM_GND_PIN = 18
    BM_GND_PIN = Pin(BM_GND_PIN, Pin.OUT)
    BM_GND_PIN.off()
elif MICROCONTROLER == 'WROOM':
    BM_VCC_PIN = 23
    BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
    BM_VCC_PIN.on()
elif MICROCONTROLER == 'PROTO':
    pass
else:
    print('ERROR')
    print('No known microcontroler defined. Correct that and restart the program')
    print('Possibilities are TTGO, WEMOS, NODE or WROOM')
    exit()
if DEBUG_MES_EXEC_TIME: mes.time_step('uC config')

# analog voltage measurement
R1 = 100e3 # first divider bridge resistor
R2 = 33e3 # second divider bridge resistor
ADC1_PIN = const(35) # Measure of analog voltage (ex: battery voltage following)
DIV = R2 / (R1 + R2) # (R2 / R1 + R2) -> V_meas = V(R1 + R2); V_adc = V(R2)  
AVERAGING = const(10)                # no. of samples for averaging
ubatt = ADC1Cal(Pin(ADC1_PIN, Pin.IN), DIV, None, AVERAGING, "ADC1 eFuse Calibrated")
# set ADC result width
ubatt.width(ADC.WIDTH_12BIT)
# set attenuation
ubatt.atten(ADC.ATTN_6DB)
# battery
UBAT_100 = 4.2
UBAT_0 = 3.5
if DEBUG_MES_EXEC_TIME: mes.time_step('analog config')

# IRQ constants
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_WRITE_DONE = const(17)

class BleJmbSensor:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
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

    def config_read_conn_info(self):
        with open ('config_uart.txt', 'r') as f:
            config_data = f.readlines()
            for l in config_data:
                n, v = l.split(':')
                if n == 'addr_type':
                    self._addr_type = int(v)
                elif n == 'addr':
                    self._addr = self.asc_to_bytes(v.replace('\n', ''))
                elif n == 'name':
                    self._name = v.replace('\n', '')
                elif n == 'rx_handle':
                    self._rx_handle = int(v)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, scan_duration_ms=500): #, callback=None):
        self._addr_type = addr_type
        self._addr = addr
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
            print(n_tries, write_ok)
            try:
                self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1)
                n_tries = 0
                write_ok = True
            except Exception as e:
                err = e
                try:
                    log.log_error('Try to reconnect in write essai:' + str(n_tries-1), e)
                    self.connect(self._addr_type, self._addr)
                    while not self._irq_peripheral_connect or not self._irq_service_done:
                        pass
                except:
                    print('connect not possible')
                    log.log_error('Connect not possible', err)
                n_tries -= 1
                sleep_ms(500)
            
        if not write_ok:
            log.counters('error', True) # increment error counter
            log.log_error('Write on BLE UART error --> reset()', err)
            reset()

#     def error_handling(self, e):
#         s=StringIO()
#         print_exception(e, s)  
#         s=s.getvalue()
#         
#         s=s.split('\n')
#         
#         line=s[1].split(',')
#         line=line[1]
#         error=s[2]
#         err=error+line
#         return err
        
# except Exception as e:
#   exc_type, exc_obj, exc_tb = sys.exc_info()
#   fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
#   print(exc_type, fname, exc_tb.tb_lineno)...

def main():
    try:
        i = log.counters('passe', True)
        if DEBUG_MES_EXEC_TIME: mes.time_step('entering main')

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
            bat = 4.44
        else:
            temp = float(bmeX.temperature)
            hum = float(bmeX.humidity)
            pres = float(bmeX.pressure)
            bat = float(ubatt.voltage/1000)
        if DEBUG_MES_EXEC_TIME: mes.time_step('sensor config')
            
        msg = encode_decode.encode_msg('jmb', SENSOR_ID, temp, hum, pres, bat)
        crc_val = encode_decode.get_crc(msg)
        msg += crc_val
        
        #connect to the central
        sensor.connect(sensor._addr_type, sensor._addr)
        while not sensor._irq_peripheral_connect or not sensor._irq_service_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('central connect')
        
        sensor.write(msg, i)
        blink.blink_internal_blue_led(100, 100, 100, 3)
        while  not sensor._irq_write_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('message write')
        
        print()
        print('jmb_' + str(SENSOR_ID) + ' --> ' + msg + ' crc:' + crc_val)
        
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('central disconnect')

        # check the level of the battery
        if bat > (0.98 * UBAT_0) or not ON_BATTERY:
            # finishing tasks
            elapsed = ticks_ms() - start_time
            t_deepsleep = max(T_DEEPSLEEP_MS - elapsed, 10)
            print('passe', i, '- error count:', log.counters('error'),'-->',  str(elapsed) + 'ms', )
            print('going to deepsleep for: ' + str(t_deepsleep) + ' ms - soft V' + VERSION)
            print('=================================================')
            if DEBUG_MES_EXEC_TIME: mes.time_step('stop')
            deepsleep(t_deepsleep)
        else:
            print('Endless deepsleep due to low battery')
            if DEBUG_MES_EXEC_TIME: mes.time_step('endless deepsleep due to low battery')
            deepsleep()
        
    except Exception as e:
        log.counters('error', True)
        log.log_error('Main program error', e)
        sleep_ms(2000)
        reset()

if __name__ == "__main__":
    main()
