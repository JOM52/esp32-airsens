#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import esp
# esp.osdebug("*", esp.LOG_DEBUG) 

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
"""
VERSION = '0.1.35.ppk'
PROGRAM_NAME = 'airsens_ble_sensor_ppk.py'

from machine import Pin

# Nordic Power Prefiler Kkit II logic chanels
PPK_0_PIN = 5
PPK_1_PIN = 25
PPK_2_PIN = 32
PPK_3_PIN = 26
PPK_4_PIN = 4
PPK_5_PIN = 33

PPK_0 = Pin(PPK_0_PIN, Pin.OUT)
PPK_1 = Pin(PPK_1_PIN, Pin.OUT)
PPK_2 = Pin(PPK_2_PIN, Pin.OUT)
PPK_3 = Pin(PPK_3_PIN, Pin.OUT)
PPK_4 = Pin(PPK_4_PIN, Pin.OUT)
PPK_5 = Pin(PPK_5_PIN, Pin.OUT)

PPK_0.on()
PPK_1.off()
PPK_2.off()
PPK_3.off()
PPK_4.off()
PPK_5.off()

from utime import sleep_ms, ticks_ms
start_time = ticks_ms()
DEBUG_MES_EXEC_TIME = True

if DEBUG_MES_EXEC_TIME:
    from lib.exec_time_mes import exec_time_mes
    mes = exec_time_mes()
    mes.time_step('start')

ON_BATTERY = True

from bluetooth import BLE
from ubinascii import unhexlify
from sys import exit
from micropython import const
from machine import ADC, reset, SoftI2C, deepsleep
if DEBUG_MES_EXEC_TIME: mes.time_step('standard import')

from lib.adc1_cal import ADC1Cal
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import ADC1Cal')

from lib.encode_decode import EncodeDecode
encode_decode = EncodeDecode()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import EncodeDecode')

from lib.log_and_count import LogAndCount
log = LogAndCount()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import LogAndCount')

from lib.config_parser import ConfigParser
cp = ConfigParser()
if DEBUG_MES_EXEC_TIME: mes.time_step('lib import ConfigParser')

# from lib.blink import Blink
# blink = Blink(2)
# if DEBUG_MES_EXEC_TIME: mes.time_step('lib import Blink')

# Hardware choices to import from config_sensor.txt
CONNECTED_SENSOR_TYPE = None
MICROCONTROLER = None
SENSOR_ID = None
T_DEEPSLEEP_MS = None

# read options in airsens.conf
conf_filename = 'airsens.conf'
cp.read(conf_filename)
try:
    # SENSOR options
    if cp.has_option('SENSOR', 'TYPE'):
        CONNECTED_SENSOR_TYPE = cp.get('SENSOR', 'TYPE')
    else:
        raise Exception('"SENSOR:TYPE"')
    
    if cp.has_option('SENSOR', 'UC'):
        MICROCONTROLER = cp.get('SENSOR', 'UC')
    else:
        raise Exception('"SENSOR:UC"')
    
    if cp.has_option('SENSOR', 'ID'):
        SENSOR_ID = cp.get('SENSOR', 'ID')
    else:
        raise Exception('"SENSOR:ID"')
    
    if cp.has_option('SENSOR', 'T_DEEPSLEEP_MS'):
        T_DEEPSLEEP_MS = int(cp.get('SENSOR', 'T_DEEPSLEEP_MS'))
    else:
        raise Exception('"SENSOR:T_DEEPSLEEP_MS"')
except Exception as e:
    print('The ' + str(e) + ' key does not exist in the "airsens.conf" configuration file.')
    print('Correct the file then relaunch the program.')
    exit()

if DEBUG_MES_EXEC_TIME: mes.time_step('read file airsens.conf')

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
if DEBUG_MES_EXEC_TIME: mes.time_step('sensor ' + CONNECTED_SENSOR_TYPE + ' import')
    
# sensor pins and init
BM_SDA_PIN = 21
BM_SCL_pin = 22

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

    PPK_1.on()
    PPK_0.off()
    try:
        print('=================================================')
        print(PROGRAM_NAME + ' - Version:' + VERSION)
        i = log.counters('passe', True)
        if DEBUG_MES_EXEC_TIME: mes.time_step('entering main')
#############################################
# flag 26 Import and config
        PPK_2.on()
        PPK_1.off()

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
        if DEBUG_MES_EXEC_TIME: mes.time_step('sensor ' + CONNECTED_SENSOR_TYPE + ' class initialise')
        
        # instatiation of bluetooth.BLE
        ble = BLE()
        sensor = BleJmbSensor(ble)
        
        # read and initialise variable from config file
        sensor.config_read_conn_info()
        if DEBUG_MES_EXEC_TIME: mes.time_step('ble class initialise')
        
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
            
        msg = encode_decode.encode_msg('jmb', SENSOR_ID, temp, hum, pres, bat)
        crc_val = encode_decode.get_crc(msg)
        msg += crc_val
        if DEBUG_MES_EXEC_TIME: mes.time_step('sensor read and encode')

#############################################
# flag 18 initiale end
        PPK_2.off()
        PPK_3.on()

        #connect to the central
#         sensor.connect(sensor._addr_type, sensor._addr)
        sensor.connect()
        while not sensor._irq_peripheral_connect or not sensor._irq_service_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('central connect')

#############################################
# flag 19 connect end
        PPK_3.off()
        PPK_4.on()
        
        sensor.write(msg, i)
        while  not sensor._irq_write_done:
            pass
        if DEBUG_MES_EXEC_TIME: mes.time_step('message write')
#         blink.blink_internal_blue_led(t_on_ms=100, t_off_ms=100, t_pause_ms=100, n_repeat=3)
#         if DEBUG_MES_EXEC_TIME: mes.time_step('blink blue led')
        
        print('jmb_' + str(SENSOR_ID) + ' --> ' + msg + ' crc:' + crc_val + ' --> ' + sensor._name)
# flag 19 write on BLE end
        PPK_4.off()
        PPK_5.on()
        
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
            print('going to deepsleep for: ' + str(t_deepsleep) + ' ms')
            print('=================================================')
            if DEBUG_MES_EXEC_TIME: mes.time_step('finish and display results')
            if DEBUG_MES_EXEC_TIME: mes.time_step('stop')
# flag 23 prg end
            PPK_5.off()
            deepsleep(t_deepsleep)
        else:
            print('Endless deepsleep due to low battery')
            if DEBUG_MES_EXEC_TIME: mes.time_step('endless deepsleep due to low battery')
            deepsleep()

#############################################

    except Exception as e:
        log.counters('error', True)
        log.log_error('Main program error', e)
        sleep_ms(2000)
        reset()

if __name__ == "__main__":
    main() 
