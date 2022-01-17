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

v1.0 : 07.01.2022 --> first prototype
v1.1 : 09.01.2022 --> process in work
v1.2 : 11.01.2022 --> process time measurment
v1.3 : 13.01.2022 --> added logic for uC NODE
v1.4 : 16.01.2022 --> transfert functions from sensor to scan (git branch: sensor_test)
"""

from bluetooth import UUID, FLAG_WRITE, FLAG_READ, FLAG_NOTIFY, BLE
from machine import Pin, ADC, reset, SoftI2C, deepsleep
from ubinascii import hexlify, unhexlify
from utime import sleep_ms, ticks_ms
from sys import exit

from lib.adc1_cal import ADC1Cal
from lib.blink import blink_internal_blue_led
from lib.ble_advertising import decode_services, decode_name
from micropython import const

# Hardware choices
CONNECTED_SENSOR_TYPE = 'BME280' # 'NO_SENSOR' / 'BME280' / 'BME680'
# 'TTGO' for ESP32 TTGO T-Display / WEMOS for ESP32 WEMOS D1 MINI / NODE for node esp-32s
MICROCONTROLER = "TTGO" 

if CONNECTED_SENSOR_TYPE == 'BME280':
    import lib.bme280 as bmex80
elif CONNECTED_SENSOR_TYPE == 'BME680':
    import lib.bme680 as bmex80
elif CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
    pass
else:
    print('ERROR\nNo known sensor defined. Correct that and restart the program')
    print('Possibilities are 0, BME280 or BME680')
    print()
    print('push <ENTER> to exit')
    input()
    exit()
    
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
    BM_VCC_PIN = 23
    BM_VCC_PIN = Pin(BM_VCC_PIN, Pin.OUT)
    BM_VCC_PIN.on()
else:
    print('ERROR\nNo known microcontroler defined. Correct that and restart the program')
    print('Possibilities are TTGO or WEMOS')
    print()
    print('push <ENTER> to exit')
    input()
    exit()

# Time constants
T_DEEPSLEEP_MS = 10000 # interval between two measures
T_BEFORE_DEEPSLEEP_MS = 50 # a short break before to go in deepsleep
T_BETWEEN_2_DATA = 50 # intervall between two write on the bluetooth
T_WAIT_FOR_IRQ_TERMINATED_MS = 5 # a short break when waititn to reduce power consumtion

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

# IRQ constants
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)

NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
    
_UART_SERVICE_UUID = UUID(NUS_UUID)
_UART_RX_CHAR_UUID = (UUID(RX_UUID), FLAG_WRITE)
_UART_TX_CHAR_UUID = (UUID(TX_UUID), FLAG_READ | FLAG_NOTIFY)
    
BLE_UART_SERVICES = ((_UART_SERVICE_UUID, (_UART_TX_CHAR_UUID, _UART_RX_CHAR_UUID,)),)

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
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                # A system error has occurred. 
                try:
                    with open ('index.txt', 'r') as f:
                        pp = f.readline().strip()
                        if len(pp) == 0:
                            pp = 1
                except:
                    pp = '1'
                # error logging
                try:
                    with open ('error.txt', 'a') as f:
                        f.write('reboot at pass: ' + pp + '\n')
                except:
                    with open ('error.txt', 'w') as f:
                        f.write('reboot at pass: 1\n')
                # reset the machine
                reset()
            elif conn_handle == 65535:
                exit('\n\nERROR:\nCentral is not running. Start it and restart this programm\n\n')
            self._irq_peripheral_disconnect = True

    def bytes_to_asc(self, v_bytes):
        return hexlify(bytes(v_bytes)).decode('utf-8')

    def asc_to_bytes(self, v_ascii):
        return unhexlify((v_ascii))
                
    def config_write_conn_info(self, data):
        with open ('config.txt', 'w') as f:
            for d in data:
                if type(d) == int:
                    f.write(str(d) + '\n')
                else:
                    f.write(d + '\n')

    def config_read_conn_info(self):
        with open ('config.txt', 'r') as f:
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

    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._irq_peripheral_connect

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, scan_duration_ms=500): #, callback=None):
        self._addr_type = addr_type
        self._addr = addr
        if self._addr_type is None or self._addr is None:
            self._ble.gap_connect(None)
            print('-------> self._ble.gap_connect(None)')
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Send data over the UART
    def write(self, v, response=False):
        if not self.is_connected():
            print('not connected')
            return
        self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1 if response else 0)

def restart_ESP32(i, err_msg):
    msg = str(i) + ' - restart_ESP32: ' + err_msg
    print(msg)
    with open('error.txt' , 'a') as f:
        f.write(msg+'\n')
    sleep_ms(1000)
    reset()
        

def time_mesurement(process_info, t_old):
    t = ticks_ms() - t_old
    with open ('process_mes.txt', 'a') as f:
        if process_info == 'total':
            f.write('---------------\n')
        f.write(process_info + ' ---> ' + str(t) + '\n')
        
def main():
#     try:
# =========================================================
        t_old = ticks_ms()
        t_start_total = ticks_ms()
        with open('process_mes.txt', 'w'): pass # clear the file
# =========================================================
#         print('----------------------')
#         print('initializing bluetooth')
        # instanciation of bme280, bmex80 - Pin assignment
        i2c = SoftI2C(scl=Pin(BM_SCL_pin), sda=Pin(BM_SDA_PIN), freq=10000)
# =========================================================
        time_mesurement('I2C initialise', t_old)
        t_old = ticks_ms()
# =========================================================
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
            print()
            print('push enter to exit')
            exit()
            
# =========================================================
        time_mesurement('sensor instantiation', t_old)
        t_old = ticks_ms()
# =========================================================
        
        # instatiation of bluetooth.BLE
        ble = BLE()
        sensor = BleJmbSensor(ble)
# =========================================================
        time_mesurement('ble instantiation', t_old)
        t_old = ticks_ms()
# =========================================================
        # read and initialise variable from config file
        sensor.config_read_conn_info()
        addr_type = sensor._addr_type
        addr = sensor._addr
# =========================================================
        time_mesurement('sensor init config', t_old)
        t_old = ticks_ms()
# =========================================================
        # mesure time for a single pass
        # blink the blue led
#         blink_internal_blue_led(t_on_ms=100, t_off_ms=100, t_pause_ms=2, n_repeat=1)
# =========================================================
#         time_mesurement('blink', t_old)
#         t_old = ticks_ms()
# =========================================================
        # load the pass counter value from file
        try:
            with open ('index.txt', 'r') as f:
                i = int(f.readline()) + 1
        except:
            i = 1
        with open ('index.txt', 'w') as f:
            f.write(str(i))
# =========================================================
        time_mesurement('index update', t_old)
        t_old = ticks_ms()
# =========================================================
        #connect to the central
        sensor._addr_type, sensor._addr = addr_type, addr
        print('connecting')
        sensor.connect(sensor._addr_type, sensor._addr)
# =========================================================
        time_mesurement('connect', t_old)
        t_old = ticks_ms()
# =========================================================
#         time_mesurement('connect wait', t_old)
#         t_old = ticks_ms()
# =========================================================
        # prepare the data's
        msg_template = 'jmb'
        if CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
            temp = [msg_template, 'temp', str(20)]
            hum = [msg_template, 'hum', str(50)]
            pres = [msg_template, 'pres', str(950)]
            alt = [msg_template, 'alt', str(750)]
            bat = [msg_template, 'bat', str(4)]
            data_all = [temp, hum, pres, alt, bat]
        else:            
            temp = [msg_template, 'temp', str(bmeX.temperature)]
            hum = [msg_template, 'hum', str(bmeX.humidity)]
            pres = [msg_template, 'pres', str(bmeX.pressure)]
            alt = [msg_template, 'alt', str(bmeX.altitude)]
            bat = [msg_template, 'bat', str(ubatt.voltage / 1000)]
            if CONNECTED_SENSOR_TYPE == 'BME680':
                gas = [msg_template, 'gas', str(bmeX.gas / 1000)]
                data_all = [temp, hum, pres, gas, alt, bat]
            else:
                data_all = [temp, hum, pres, alt, bat]
        print()
# =========================================================
        time_mesurement('read sensor', t_old)
        t_old = ticks_ms()
# =========================================================
        # transmit the data to the central
        for m in data_all:
            msg = " ".join(m)
            sensor.write(msg)
            print(len(msg), msg)
            sleep_ms(T_BETWEEN_2_DATA)
        sensor.write('jmb\n')
# =========================================================
        time_mesurement('write on ble', t_old)
        t_old = ticks_ms()
# =========================================================
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
            sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
# =========================================================
        time_mesurement('disconnect', t_old)
        t_old = ticks_ms()
# =========================================================
        # last tasks
#         blink_internal_blue_led(t_on_ms=200, t_off_ms=100, t_pause_ms=2, n_repeat=2)
# =========================================================
#         time_mesurement('blink', t_old)
#         t_old = ticks_ms()
# =========================================================
        elapsed = ticks_ms() - t_start_total
        print()
        print('pass:', i, '-->',  str((ticks_ms() - t_start_total)/1000) + 's', )
        print('going to deepsleep for: ' + str(int((T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)/1000)) + 's')
        print('======================')
# =========================================================
        time_mesurement('finish', t_old)
        time_mesurement('total', t_start_total)
# =========================================================
        deepsleep(T_DEEPSLEEP_MS - elapsed)
        
#     except:
#         try:
#             with open ('index.txt', 'r') as f:
#                 i = int(f.readline())
#         except:
#             i = 1
#         restart_ESP32(i, 'msg')
#         msg = str(i) + ' - restart_ESP32: ' 
#         print(msg)
#         with open('error.txt' , 'a') as f:
#             f.write(msg+'\n')
#         sleep_ms(2000)
#         reset()
        

if __name__ == "__main__":
    main()
