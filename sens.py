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
v0.1.42.test : 02.06.2022 --> try to filter measures
v0.1.43 : 03.06.2022 --> add error management in disconnect
v0.1.44 : 03.06.2022 --> replaced all 'reset()' with 'deepsleep(t_deepsleep)'
                     --> one measure get lost --> we dont try to repeat it indefintively --> battery saving
v0.1.45 : 03.06.2022 --> error management in write (write data on uart) impoved
v0.1.46 : 04.06.2022 --> added led's management and parameters on the top of the program
v0.1.46.min : 05.06.2022 --> reduce code to minimum to spare energy
v0.1.47.min : 06.06.2022 --> modif to permit to airsens_ble_scan to modify UART params
"""

# PARAMETERS ========================================
VERSION = '0.1.47.min'
SENSOR_ID_x = 'p0'
T_DEEPSLEEP_MS_x = 15000
DEBUG_MES_EXEC_TIME = True
DEBUG_MES_EXEC_TIME_STAT = False
ON_BATTERY = True
#----------------------------------------------------
PARAM_UART_ADDR_x = '84cca85f4a82'
PARAM_UART_ADDR_TYPE_x = '0'
PARAM_UART_RX_HANDLE_x = '24'
PARAM_UART_NAME_x = 'jmb_central_01'
#====================================================

from machine import Pin, freq, TouchPad
from esp32 import wake_on_touch

# wake on touch
TOUCH_WAKE_PIN = 13
TOUCH_WAKE = TouchPad(Pin(TOUCH_WAKE_PIN, mode = Pin.IN))
TOUCH_WAKE.config(500)
wake_on_touch(True)

from utime import sleep_ms
from bluetooth import BLE
from machine import ADC, reset, SoftI2C, deepsleep
from ubinascii import unhexlify
from sys import exit
from micropython import const

from lib.encode_decode import EncodeDecode
encode_decode = EncodeDecode()

from lib.log_and_count import LogAndCount
log = LogAndCount()


CONNECTED_SENSOR_TYPE = 'BME280'
MICROCONTROLER = 'WEMOS'
SENSOR_ID = SENSOR_ID_x #'ts'
T_DEEPSLEEP_MS = T_DEEPSLEEP_MS_x #15000
# if DEBUG_MES_EXEC_TIME: mes.time_step('conf read values')

import lib.bme280 as bmex80
    
# sensor pins and init
BM_SDA_PIN = 21
BM_SCL_pin = 22

# analog voltage measurement
R1 = 100000 # first divider bridge resistor
R2 = 33000 # second divider bridge resistor
ADC1_PIN = const(35) # Measure of analog voltage (ex: battery voltage following)
DIV = R2 / (R1 + R2) # (R2 / R1 + R2) 
AVERAGING = const(10)                # no. of samples for averaging
# battery
UBAT_100 = 3.0
UBAT_0 = 2.6

pot = ADC(Pin(ADC1_PIN))            
pot.atten(ADC.ATTN_6DB ) # Umax = 2V
pot.width(ADC.WIDTH_12BIT) # 0 ... 4095

# IRQ constants
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_WRITE_DONE = const(17)

class BleJmbSensor:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

        self._addr_type = int(PARAM_UART_ADDR_TYPE_x)
        self._addr = self.asc_to_bytes(PARAM_UART_ADDR_x) #'84cca85f4a82')
        self._name = PARAM_UART_NAME_x # 'jmb_central_01'
        self._rx_handle = int(PARAM_UART_RX_HANDLE_x)

    def _reset(self):
        # Cached name and address from a successful scan.
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
                deepsleep(T_DEEPSLEEP_MS)
        
        elif event == _IRQ_GATTC_SERVICE_DONE: #10
            self._irq_service_done = True

        elif event == _IRQ_GATTC_WRITE_DONE: #17
            self._irq_write_done = True

    def asc_to_bytes(self, v_ascii):
        return unhexlify((v_ascii))

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, scan_duration_ms=500): 
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        try:
            self._ble.gap_disconnect(self._conn_handle)
            self._reset()
        except Exception as err:
            log.counters('error', True) # increment error counter
            log.log_error('Disconnect from current device error')
            deepsleep(T_DEEPSLEEP_MS)

    # Send data over the UART
    def write(self, v, i):
        n_tries_max = 5
        n_tries = 0
        write_ok = False
        err = None
        while n_tries < 5:
            try:
                self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1)
                n_tries = n_tries_max
                write_ok = True
            except Exception as err:
                try:
                    msg = 'Try to reconnect in write essai: ' + str(n_tries) + ' - ' + str(type(err)) + ' - "' + str(err) + '"'
                    print(msg)
                    ret = log.log_error(msg)
                    print(ret)
                    self.connect()
                    while not self._irq_peripheral_connect or not self._irq_service_done:
                        pass
                except:
                    msg = 'Connection not possible' 
                    print(msg)
                    ret = log.log_error(msg)
                    print(ret)
                n_tries += 1
                sleep_ms(500)
            
        if not write_ok:
            log.counters('error', True) # increment error counter
            log.log_error('Write on BLE UART error --> reset()', err)
            print('going to deepsleep for ' + str(T_DEEPSLEEP_MS) + ' ms')
            deepsleep(T_DEEPSLEEP_MS)

def main():
    
        t_deepsleep = T_DEEPSLEEP_MS
#     try:
        print('=================================================')
        i = log.counters('passe', True)

        # instanciation of bme280, bmex80 - Pin assignment
        i2c = SoftI2C(scl=Pin(BM_SCL_pin), sda=Pin(BM_SDA_PIN), freq=10000)
        bmeX = bmex80.BME280(i2c=i2c)
        
        # instatiation of bluetooth.BLE
        ble = BLE()
        sensor = BleJmbSensor(ble)

        temp = bmeX.temperature
        hum = bmeX.humidity
        pres = bmeX.pressure
            
        bat = 0
        for a in range(AVERAGING):
            bat += pot.read()
        bat = bat / AVERAGING * (2 / 4095) / DIV
            
        msg = encode_decode.encode_msg('jmb', SENSOR_ID, temp, hum, pres, bat)
        crc_val = encode_decode.get_crc(msg)
        msg += crc_val
        
        #connect to the central
        sensor.connect()
        while not sensor._irq_peripheral_connect or not sensor._irq_service_done:
            pass
        sensor.write(msg, i)
        while  not sensor._irq_write_done:
            pass
        
        print('jmb_' + str(SENSOR_ID) + ' --> ' + msg + ' crc:' + crc_val + ' --> ' + sensor._name)
        
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
            pass

        # check the level of the battery
        if bat > (0.98 * UBAT_0) or not ON_BATTERY:
            # finishing tasks
            print('passe', i, '- error count:', log.counters('error'))
            print('going to deepsleep for: ' + str(t_deepsleep) + ' ms')
            print('=================================================')
            deepsleep(t_deepsleep)
        else:
            print('Endless deepsleep due to low battery')
#             deepsleep()
            exit()
        
#     except Exception as e:
#         log.counters('error', True)
#         log.log_error('Main program error', e)
#         deepsleep(t_deepsleep)

if __name__ == "__main__":
    main()
