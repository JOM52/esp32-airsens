#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_ble_sensor.py 

version: 1.0
date: 7.1.2022
author: jom52

email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

The sensors are made with an ESP32 microcontroller and can be powered by battery or by USB.
They transmit the data to a central also realized with an ESP32 by a bluetooth
low energy communication (BLE)

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

# Choose the type of sensor connected
BME_280_680 = 680
if BME_280_680 == 280:
    import lib.bme280 as bmex80
elif BME_280_680 == 680:
    import lib.bme680 as bmex80
else:
    print('ERROR\nNo know sensor defined. Correct that and restart the program')
    print('Possibilities are 280 or 680')
    print()
    print('push <ENTER> to exit')
    input()
    sys.exit()
# sensor pins and init
BM_VCC_PIN = 17
BM_GND_PIN = 16
BM_SDA_PIN = 21
BM_SCL_pin = 22
BM_VCC_PIN = machine.Pin(BM_VCC_PIN, machine.Pin.OUT)
BM_GND_PIN = machine.Pin(BM_GND_PIN, machine.Pin.OUT)
BM_VCC_PIN.on()
BM_GND_PIN.off()

# Constants
T_DEEPSLEEP_MS = 10000
T_BEFORE_DEEPSLEEP_MS = 100
T_WAIT_FOR_IRQ_TERMINATED_MS = 100

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
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)

_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)

_UART_SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_CHAR_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX_CHAR_UUID = ubluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

#==== under test begin ==================================================================
NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
    
_UART_SERVICE_UUID = ubluetooth.UUID(NUS_UUID)
_UART_RX_CHAR_UUID = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
_UART_TX_CHAR_UUID = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY)
# BLE_NUS = ubluetooth.UUID(NUS_UUID)
# BLE_RX = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
# BLE_TX = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_NOTIFY)
#==== under test end ==================================================================

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

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
#         self._scan_callback = None
#         self._conn_callback = None
#         self._read_callback = None

        # Persistent callback for when new data is notified from the device.
#         self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._tx_handle = None
        self._rx_handle = None
        
        self._connect_status = False
        self._uart_central_found = False
        self._gattc_service_done = False
        self._gattc_characteristic_done = False
        self._irq_peripheral_connect = False
        self._irq_peripheral_disconnect = False
        
    def _irq(self, event, data):
        
        self._irq_list.append(event)

        if event == _IRQ_PERIPHERAL_CONNECT: #7
            conn_handle, addr_type, addr = data
#             print('---> 7_IRQ_PERIPHERAL_CONNECT', conn_handle, addr_type, self.bytes_to_asc(bytes(addr)))
            # Connect successful.
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)
                self._irq_peripheral_connect = True
#                 print('_IRQ_PERIPHERAL_CONNECT done')

        elif event == _IRQ_PERIPHERAL_DISCONNECT: #8
#             print('---> 8_IRQ_PERIPHERAL_DISCONNECT')
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            self._irq_peripheral_disconnect = True
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT: #9
#             print('---> 9_IRQ_GATTC_SERVICE_RESULT')
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _UART_SERVICE_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle

        elif event == _IRQ_GATTC_SERVICE_DONE: #10
#             print('---> 10_IRQ_GATTC_SERVICE_DONE')
            # Service query complete.
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(self._conn_handle, self._start_handle, self._end_handle)
                self._gattc_service_done = True
            else:
                print("Failed to find uart service.")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT: #11
#             print('---> 11_IRQ_GATTC_CHARACTERISTIC_RESULT')
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data
#             print(uuid, _UART_RX_CHAR_UUID, value_handle)
            if conn_handle == self._conn_handle and uuid == _UART_RX_CHAR_UUID[0]:
                self._rx_handle = value_handle
            if conn_handle == self._conn_handle and uuid == _UART_TX_CHAR_UUID[0]:
                self._tx_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE: #12
#             print('---> 12_IRQ_GATTC_CHARACTERISTIC_DONE')
            # Characteristic query complete.
            if self._tx_handle is not None and self._rx_handle is not None:
                # We've finished connecting and discovering device, fire the connect callback.
#                 if self._conn_callback:
#                     self._conn_callback()
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

    # Find a device advertising the environmental sensor service.
#     def scan(self, callback=None):
#         self._addr_type = None
#         self._addr = None
#         self._scan_callback = callback
#         self._ble.gap_scan(2000, 30000, 30000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None): #, callback=None):
#         print('---> connect', addr_type, addr)
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
#         self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
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

    # Set handler for when data is received over the UART.
#     def on_notify(self, callback):
#         self._notify_callback = callback

def restart_ESP32(i, err_msg):
    msg = str(i) + ' - restart_ESP32: ' + err_msg
    print(msg)
    with open('error.txt' , 'a') as f:
        f.write(msg+'\n')
    utime.sleep_ms(1000)
    machine.reset()


def main():
#     try:
        print('initializing bluetooth')
        print('----------------------------------------------------------------------------')
        # instanciation of bme280, bmex80 - Pin assignment
        i2c = machine.SoftI2C(scl=machine.Pin(BM_SCL_pin), sda=machine.Pin(BM_SDA_PIN), freq=10000)
        try:
            if BME_280_680 == 280:
                bmeX = bmex80.BME280(i2c=i2c)
            elif BME_280_680 == 680:
                bmeX = bmex80.BME680_I2C(i2c=i2c)
        except:
            if BME_280_680 == 280:
                sx = 'bme280'
            else:
                sx ='bme680'
            print('Ce n\'est pas un ' + sx + ' qui est branché?')
            print('Corrigez et relancez le programme!')
            print()
            print('push enter to exit')
            sys.exit()
        # instatiation of bluetooth.BLE
        ble = ubluetooth.BLE()
        sensor = BleJmbSensor(ble)
        # initialize the pass counter to 0
        with open ('index.txt', 'w') as f:
            f.write(str(0))
        # read and initialise variable for sensor from config from file
        sensor.config_read_conn_info()
        addr_type = sensor._addr_type
        addr = sensor._addr
            
#         sensor.scan()
#         while not sensor._scan_done:
#             utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
#         if not sensor._uart_central_found:
#             print('No uart central found. Active it and then restart this program')
#             import sys
#             sys.exit()
#             print('server found:',str((utime.ticks_ms()-t_start)/1000) + 's --> ',
#                   'sensor._addr_type:', sensor._addr_type,
#                   'sensor._name:', sensor._name,
#                   'sensor:_addr:', ubinascii.hexlify(bytes(sensor._addr)).decode('utf-8'))
        while True:
            # mesure time for a single pass
            t_start_total = utime.ticks_ms()
            # blink the blue led
            blink_internal_blue_led(100, 100, 2, 5)
            # load the pass counter value from file
            try:
                with open ('index.txt', 'r') as f:
                    i = int(f.readline()) + 1
            except:
                i = 1
            with open ('index.txt', 'w') as f:
                f.write(str(i))
            
            
            #connect to the central
#             v_nc = 1
            sensor._addr_type, sensor._addr = addr_type, addr
            connect_status = sensor.connect(sensor._addr_type, sensor._addr)
#             print('connect demand done')
            while not connect_status:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                connect_status = sensor.connect(sensor._addr_type, sensor._addr)
#                 print(v_nc, "::::::::::")
#                 v_nc += 1
#             print('connect status ok')
            
            
            while (not sensor.is_connected()
                   or not sensor._gattc_service_done
                   or not sensor._gattc_characteristic_done):
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
#             print('connect ok')
                
    #         while not sensor.is_connected():
    #             utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
    #         print("Connected")
    # 
    #         while not sensor._gattc_service_done:
    #             utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
    #      
    #         while not sensor._gattc_characteristic_done:
    #             utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)


        #         if WIFI_CONNECT:
        #             my_wifi = wifi_esp32.WifiEsp32('jmb-guest', 'pravidondaz')  # initialize the class
        #             my_wifi.connect_wifi()  # connect to the wifi network
        #             
        #             if RTC_SYNC:
        #                 my_rtc = rtc_esp32.RtcEsp32()  # initialize the class
        #                 my_rtc.rtc_init()  # initialize the rtc with local date and time
                
        #         # extract the date and time values in str format and print it
        #         if WIFI_CONNECT and RTC_SYNC:
        #             now = my_rtc.rtc_now()  # get date and time
        #             datetime_formated = my_rtc.format_datetime(now)
        #             print("now date and time :", datetime_formated)

#             print(bmeX.temperature)
#             print(bmeX.humidity)
#             print(bmeX.pressure)

            temp = bmeX.temperature #bme68.temperature
            hum = bmeX.humidity #bme68.humidity
            pres = bmeX.pressure #bme68.pressure
#             gas68 = int(bme68.gas / 1000)
#             gaspc = int(100*gas68/75)
            alt = int(bmeX.altitude)

            print('temperature -->', temp, '°C') #, 'temp 280 -->', temp28, '°C')
            print('humidite ----->', hum, '%') #, 'hum 280 -->', hum28, '%')
            print('pression ----->', pres, 'hPa') #, 'pres 280 -->', pres28, 'hPa')
#             print('gaz ---------->', gas68, 'Kohms', '=^=', gaspc, '%')
            print('altitude ----->', alt, 'm')
            print('bat ---------->', '{:.2f}'.format(ubatt.voltage / 1000), 'V')

            
            msg = 'jmb ' + str(temp) + ' ' + str(hum) + ' ' + str(pres) + ' ' + str(i)
            sensor.write(msg)
                
            elapsed = utime.ticks_ms() - t_start_total
            print('pass:', i, '-->',  str((utime.ticks_ms() - t_start_total)/1000) + 's', )
            print('going to sleep for ' + str(int((T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)/1000)) + 's')
            

            sensor.disconnect()
            while not sensor._irq_peripheral_disconnect:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                
#             print(sensor._irq_list)
            sensor._irq_list = []
            
            print('============================================================================')
            utime.sleep_ms(T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)
        
#         print('going to deepsleep for: ' + str(int((T_BEFORE_DEEPSLEEP_MS + T_DEEPSLEEP_MS - elapsed)/1000)) + 's')
#         utime.sleep_ms(T_BEFORE_DEEPSLEEP_MS)
#         machine.deepsleep(T_DEEPSLEEP_MS - elapsed)
        
#     except:
#         try:
#             with open ('index.txt', 'r') as f:
#                 i = int(f.readline())
#         except:
#             i = 1
# #         restart_ESP32(i, msg)
#         msg = str(i) + ' - restart_ESP32: ' 
#         print(msg)
#         with open('error.txt' , 'a') as f:
#             f.write(msg+'\n')
#         utime.sleep_ms(10000)
#         machine.reset()
        

if __name__ == "__main__":
    main()
