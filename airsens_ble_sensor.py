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
"""

from bluetooth import UUID, FLAG_WRITE, FLAG_READ, FLAG_NOTIFY, BLE
from machine import Pin, ADC, reset, SoftI2C, deepsleep
from ubinascii import hexlify, unhexlify
from utime import sleep_ms, ticks_ms
from sys import exit, print_exception
from micropython import const
from uio import StringIO


from lib.adc1_cal import ADC1Cal
from lib.ble_advertising import decode_services, decode_name
from lib.encode_decode import encode_msg

# Hardware choices
CONNECTED_SENSOR_TYPE = None
MICROCONTROLER = None
SENSOR_ID = None
T_DEEPSLEEP_MS = None
        
# def sensor_config_read():
with open('config_sensor.txt', 'r') as f:
    lines = f.readlines()
    for l in lines:
#         l.replace('\n\r', '') #.replace('\r', '')
        c, v = l.replace('\n\r', '').split('=')
        if c == 'CONNECTED_SENSOR_TYPE': CONNECTED_SENSOR_TYPE = v.strip()
        elif c == 'MICROCONTROLER': MICROCONTROLER = v.strip()
        elif c == 'SENSOR_ID': SENSOR_ID = v.strip()
        elif c == 'T_DEEPSLEEP_MS': T_DEEPSLEEP_MS = int(v)

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
    print('ERROR')
    print('No known microcontroler defined. Correct that and restart the program')
    print('Possibilities are TTGO, WEMOS ot NODE')
    exit()

# Time constants
T_BETWEEN_2_DATA = 50 # intervall between two write on the bluetooth
T_WAIT_FOR_IRQ_TERMINATED_MS = 100 # a short break when waititn to reduce power consumtion
T_WAIT_UNTIL_CONNECTD_MS = 500 # wait until the connection with the central is established

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
_IRQ_GATTC_WRITE_DONE = const(17)

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
        self._irq_write_done = False
        
#         self.irq_list = []
        
    def _irq(self, event, data):
#         self.irq_list.append(event)
#         print('event:', event)
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
                pp = get_and_increase_pass_counter()
                get_and_increase_error_counter()
                # error logging
                log_error('reboot at pass: ' + str(pp))
                # reset the machine
                reset()
                
            elif conn_handle == 65535:
                print('\n\nERROR:\nCentral is not running. Start it and restart this programm\n\n')
                self._irq_peripheral_connect = False
                
            self._irq_peripheral_disconnect = True

        elif event == _IRQ_GATTC_WRITE_DONE: #17
            self._irq_write_done = True


    def bytes_to_asc(self, v_bytes):
        return hexlify(bytes(v_bytes)).decode('utf-8')

    def asc_to_bytes(self, v_ascii):
        return unhexlify((v_ascii))
                
    def config_write_conn_info(self, data):
        with open ('config_uart.txt', 'w') as f:
            for d in data:
                if type(d) == int:
                    f.write(str(d) + '\n')
                else:
                    f.write(d + '\n')

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


    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._irq_peripheral_connect

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
    def write(self, v, response=False):
        if not self.is_connected():
            print('not connected')
            return
        self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1 if response else 0)

def restart_ESP32(i, err_msg):
    sleep_ms(1000)
    reset()
        

def time_mesurement(process_info, t_old):
    t = ticks_ms() - t_old
    with open ('process_mes.txt', 'a') as f:
        if process_info == 'total':
            f.write('---------------\n')
        f.write(process_info + ' ---> ' + str(t) + '\n')
        
def log_error(msg):
    # error logging
    try:
        with open ('error.txt', 'a') as f:
            f.write(str(msg) + '\n')
    except:
        with open ('error.txt', 'w') as f:
            f.write(str(msg) + '\n')
            
def get_and_increase_pass_counter():
    # load the pass counter value from file
    try:
        with open ('index.txt', 'r') as f:
            i = int(f.readline()) + 1
    except:
        i = 1
    with open ('index.txt', 'w') as f:
        f.write(str(i))
    return i
            
def get_and_increase_error_counter():
    # load the pass counter value from file
    try:
        with open ('err_count.txt', 'r') as f:
            i = int(f.readline()) + 1
    except:
        i = 1
    with open ('err_count.txt', 'w') as f:
        f.write(str(i))
    return i
            
def get_error_counter():
    # load the pass counter value from file
    try:
        with open ('err_count.txt', 'r') as f:
            i = int(f.readline())
    except:
        i = 1
    return i
        
def main():
    try:
        t_start_total = ticks_ms()
#         with open('process_mes.txt', 'w'): pass # clear the file
        i = get_and_increase_pass_counter()

        # instanciation of bme280, bmex80 - Pin assignment
        i2c = SoftI2C(scl=Pin(BM_SCL_pin), sda=Pin(BM_SDA_PIN), freq=10000)
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
            
        # instatiation of bluetooth.BLE
        ble = BLE()
        sensor = BleJmbSensor(ble)
        # read and initialise variable from config file
        sensor.config_read_conn_info()
        
        if CONNECTED_SENSOR_TYPE == 'BME680':
            gas = bmeX.gas / 1000
        else:
            gas = 0
            
        if CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
            temp = 20.3
            hum = 50.5
            pres = 950
            bat = 4.05
        else:
            temp = float(bmeX.temperature)
            hum = float(bmeX.humidity)
            pres = float(bmeX.pressure)
            bat = float(ubatt.voltage/1000)
            
        msg = encode_msg('jmb', SENSOR_ID, temp, hum, pres, gas, bat)
        #connect to the central
#         print('connecting')
        sensor.connect(sensor._addr_type, sensor._addr)
        while not sensor._irq_peripheral_connect:
#             print('----> waiting for connection')
            sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
        
        sensor.write(msg, 1)
        while not sensor._irq_write_done:
            sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
        print()
        print('jmb_' + str(SENSOR_ID) + ' --> ' + msg)
#         sleep_ms(T_BETWEEN_2_DATA)
        
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
#             print('----> waiting for disconnection')
            sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)

        # finishing tasks
        elapsed = ticks_ms() - t_start_total
#         print('iqr_list:', sensor.irq_list)
        print('pass:', i, '- error count:', get_error_counter(),'-->',  str((ticks_ms() - t_start_total)/1000) + 's', )
        print('going to deepsleep for: ' + str(int((T_DEEPSLEEP_MS - elapsed))) + ' ms')
        print('==============================')
        deepsleep(T_DEEPSLEEP_MS - elapsed)
        
    except Exception as e:
        # manage the pass counter
        get_and_increase_pass_counter()
        get_and_increase_error_counter()
        # make the error message
        s = StringIO()
        print_exception(e, s)  
        s = s.getvalue()
        s = s.split('\n')                                                                   
        line = s[1].split(',')
        line = line[1]
        error = s[2]
        err = error + line
        # write and print the error message
        msg = 'pass:' + str(i) + ' - restart_ESP32 --> ' + str(err)
        print('-------------------------------------------------------')
        print(msg)
        log_error(msg)
        print('-------------------------------------------------------')
        # restart the machine
        sleep_ms(2000)
        restart_ESP32(i, 'msg')

if __name__ == "__main__":
    main()
