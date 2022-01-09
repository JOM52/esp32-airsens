#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_ble_sensor.py 

version: 1.1
date: 7.1.2022
author: jom52

email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

The sensors are made with an ESP32 microcontroller and can be powered by battery or by USB.
They transmit the data to a central also realized with an ESP32 by a bluetooth
low energy communication (BLE)

v1.0 : 7.1.2022 --> first prototype
v1.1 : 9.1.2022 --> 
"""

import ubluetooth
import machine
import ubinascii
import utime
import sys

from lib.adc1_cal import ADC1Cal
from lib.blink import blink_internal_blue_led
from lib.ble_advertising import decode_services, decode_name
from micropython import const

# Hardware choices
CONNECTED_SENSOR_TYPE = 'BME280' # 'NO_SENSOR' / 'BME280' / 'BME680'
MICROCONTROLER = "TTGO" # 'TTGO' for ESP32 TTGO T-Display / WEMOS for ESP32 WEMOS D1 MINI

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
    sys.exit()

# sensor pins and init
if MICROCONTROLER == 'TTGO':
    BM_VCC_PIN = 15
    BM_SDA_PIN = 21
    BM_SCL_pin = 22
    BM_VCC_PIN = machine.Pin(BM_VCC_PIN, machine.Pin.OUT)
    BM_VCC_PIN.on()
elif MICROCONTROLER == 'WEMOS':
    BM_VCC_PIN = 15
    BM_GND_PIN = 16
    BM_SDA_PIN = 21
    BM_SCL_pin = 22
    BM_VCC_PIN = machine.Pin(BM_VCC_PIN, machine.Pin.OUT)
    BM_GND_PIN = machine.Pin(BM_GND_PIN, machine.Pin.OUT)
    BM_VCC_PIN.on()
    BM_GND_PIN.off()
else:
    print('ERROR\nNo known microcontroler defined. Correct that and restart the program')
    print('Possibilities are TTGO or WEMOS')
    print()
    print('push <ENTER> to exit')
    input()
    sys.exit()

# Time constants
T_DEEPSLEEP_MS = 30000 # interval between two measures
T_BEFORE_DEEPSLEEP_MS = 50 # a short break before to go in deepsleep
T_BETWEEN_2_DATA = 50 # intervall between two write on the bluetooth
T_WAIT_FOR_IRQ_TERMINATED_MS = 10 # a short break when waititn to reduce power consumtion

# analog voltage measurement
R1 = 100e3 # first divider bridge resistor
R2 = 33e3 # second divider bridge resistor
ADC1_PIN = const(35) # Measure of analog voltage (ex: battery voltage following)
DIV = R2 / (R1 + R2) # (R2 / R1 + R2) -> V_meas = V(R1 + R2); V_adc = V(R2)  
AVERAGING = const(10)                # no. of samples for averaging
ubatt = ADC1Cal(machine.Pin(ADC1_PIN, machine.Pin.IN), DIV, None, AVERAGING, "ADC1 eFuse Calibrated")
# set ADC result width
ubatt.width(machine.ADC.WIDTH_12BIT)
# set attenuation
ubatt.atten(machine.ADC.ATTN_6DB)

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
    
_UART_SERVICE_UUID = ubluetooth.UUID(NUS_UUID)
_UART_RX_CHAR_UUID = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
_UART_TX_CHAR_UUID = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY)
    
BLE_UART_SERVICES = ((_UART_SERVICE_UUID, (_UART_TX_CHAR_UUID, _UART_RX_CHAR_UUID,)),)

class BleJmbSensor:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        
        self._scan_done = False
        self._gattc_service_done = None
        self._gattc_characteristic_done = None
        self._irq_list = list()

        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._tx_handle = None
        self._rx_handle = None
        
        self._connect_status = False
        self._uart_central_found = False
        self._gattc_service_result = False
        self._gattc_service_done = False
        self._gattc_service_timeout = False
        self._gattc_characteristic_result = False
        self._gattc_characteristic_done = False
        self._irq_peripheral_connect = False
        self._irq_peripheral_disconnect = False
        
    def _irq(self, event, data):
        
        self._irq_list.append(event)
        print('->', event, end=' ')

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
            print('conn_handle:', conn_handle, ' - self._conn_handle:', self._conn_handle)
            if conn_handle == self._conn_handle:
                # A system error has occurred. We reboot the microcontroller
                machine.reset()
            elif conn_handle == 65535:
#                 print('Central is not running. Start it and restart this programm')
                sys.exit('ERROR:\nCentral is not running. Start it and restart this programm')
            self._irq_peripheral_disconnect = True

        elif event == _IRQ_GATTC_SERVICE_RESULT: #9
            # Connected device returned a service.
            while not self._irq_peripheral_connect:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _irq_peripheral_connect')
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _UART_SERVICE_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle
                self._gattc_service_result = True

        elif event == _IRQ_GATTC_SERVICE_DONE: #10
            # Service query complete.
            self._gattc_service_timeout = False
            t_start = utime.ticks_ms()
            while (not self._gattc_service_result) and (not self._gattc_service_timeout):
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _gattc_service_result')
                if (utime.ticks_ms() - t_start) > (5 * T_WAIT_FOR_IRQ_TERMINATED_MS):
                    print('_gattc_service_result timeout')
                    self._ble.gap_disconnect(self._conn_handle)
                    self._gattc_service_timeout = True
                
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(self._conn_handle, self._start_handle, self._end_handle)
                self._gattc_service_done = True
            else:
                print("Failed to find uart service.")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT: #11
            # Connected device returned a characteristic.
            while not self._gattc_service_done:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _gattc_service_done')
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == _UART_RX_CHAR_UUID[0]:
                self._rx_handle = value_handle
            if conn_handle == self._conn_handle and uuid == _UART_TX_CHAR_UUID[0]:
                self._tx_handle = value_handle
            self._gattc_characteristic_result = True
 
        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE: #12
            # Characteristic query complete.
            while not self._gattc_characteristic_result:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _gattc_characteristic_result')
            if self._tx_handle is not None and self._rx_handle is not None:
                self._gattc_characteristic_done = True
            else:
                print("Failed to find uart rx characteristic.")

    def bytes_to_asc(self, v_bytes):
        return ubinascii.hexlify(bytes(v_bytes)).decode('utf-8')

    def asc_to_bytes(self, v_ascii):
        return ubinascii.unhexlify((v_ascii))
                
    def config_write_conn_info(self, data):
        with open ('config.txt', 'w') as f:
            for d in data:
                if type(d) == int:
                    f.write(str(d) + '\n')
                else:
                    f.write(d + '\n')

    def config_read_conn_info(self):
        with open ('config.txt', 'r') as f:
            data = f.readlines()
            for i, l in enumerate(data):
                if i == 0:
                    self._addr_type = int(l)
                elif i == 1:
                    self._addr = self.asc_to_bytes(l.replace('\n',''))
                elif i == 2:
                    self._name = l.replace('\n','')

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
            return
        self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1 if response else 0)

def restart_ESP32(i, err_msg):
    msg = str(i) + ' - restart_ESP32: ' + err_msg
    print(msg)
    with open('error.txt' , 'a') as f:
        f.write(msg+'\n')
    utime.sleep_ms(1000)
    machine.reset()


def main():
    t_start_total = utime.ticks_ms()
    try:
        print('initializing bluetooth')
        print('----------------------')
        # instanciation of bme280, bmex80 - Pin assignment
        i2c = machine.SoftI2C(scl=machine.Pin(BM_SCL_pin), sda=machine.Pin(BM_SDA_PIN), freq=10000)
        try:
            if CONNECTED_SENSOR_TYPE == 'BME280':
                bmeX = bmex80.BME280(i2c=i2c)
            elif CONNECTED_SENSOR_TYPE == 'BME680':
                bmeX = bmex80.BME680_I2C(i2c=i2c)
            elif CONNECTED_SENSOR_TYPE == 'NO_SENSOR':
                bmeX = None
        except:
            if CONNECTED_SENSOR_TYPE == 'BME280':
                sx = 'bme280'
            elif CONNECTED_SENSOR_TYPE == 'BME680':
                sx ='bme680'
            print('Ce n\'est pas un ' + sx + ' qui est branché?')
            print('Corrigez et relancez le programme!')
            print()
            print('push enter to exit')
            sys.exit()
            
        # instatiation of bluetooth.BLE
        ble = ubluetooth.BLE()
        sensor = BleJmbSensor(ble)
        # initialize the pass counter to 1
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
            

        # read and initialise variable from config file
        sensor.config_read_conn_info()
        addr_type = sensor._addr_type
        addr = sensor._addr

        # main loop
#         while True:
            
        # mesure time for a single pass
        t_start_passe = utime.ticks_ms()
        # blink the blue led
        blink_internal_blue_led(t_on_ms=100, t_off_ms=100, t_pause_ms=2, n_repeat=1)
        # load the pass counter value from file
        try:
            with open ('index.txt', 'r') as f:
                i = int(f.readline()) + 1
        except:
            i = 1
        with open ('index.txt', 'w') as f:
            f.write(str(i))
        
        #connect to the central
        sensor._addr_type, sensor._addr = addr_type, addr
        print('connecting')
        connect_status = sensor.connect(sensor._addr_type, sensor._addr)
        while not connect_status and not sensor._gattc_service_timeout:
            print('----> waiting for connection --> timeaout status =', sensor._gattc_service_timeout)
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
            connect_status = sensor.connect(sensor._addr_type, sensor._addr)
        
        # be sure that all task are terminated before to continue
        while (not sensor.is_connected()
               or not sensor._gattc_service_done
               or not sensor._gattc_characteristic_done):
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
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
        # transmit the data to the central
        for m in data_all:
            msg = " ".join(m)
            sensor.write(msg)
            print(len(msg), msg)
            utime.sleep_ms(T_BETWEEN_2_DATA)
        sensor.write('jmb\n')
        # disconnect from the central
        sensor.disconnect()
        while not sensor._irq_peripheral_disconnect:
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
        # last tasks
        blink_internal_blue_led(t_on_ms=200, t_off_ms=100, t_pause_ms=2, n_repeat=2)
        elapsed = utime.ticks_ms() - t_start_passe
        print()
        print('pass:', i, '-->',  str((utime.ticks_ms() - t_start_total)/1000) + 's', )
        print('going to sleep for ' + str(int((T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)/1000)) + 's')
                
#         print(sensor._irq_list)
        sensor._irq_list = []
        print('======================')
#         utime.sleep_ms(T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)
        
        print('going to deepsleep for: ' + str(int((T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)/1000)) + 's')
        utime.sleep_ms(T_BEFORE_DEEPSLEEP_MS)
        machine.deepsleep(T_DEEPSLEEP_MS - elapsed)
        
    except:
        try:
            with open ('index.txt', 'r') as f:
                i = int(f.readline())
        except:
            i = 1
        restart_ESP32(i, msg)
        msg = str(i) + ' - restart_ESP32: ' 
        print(msg)
        with open('error.txt' , 'a') as f:
            f.write(msg+'\n')
        utime.sleep_ms(2000)
        machine.reset()
        

if __name__ == "__main__":
    main()
