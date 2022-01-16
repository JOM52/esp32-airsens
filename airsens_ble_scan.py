#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_scan.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

this program scans the bluetooth network to find all the *ble_central* whose name starts with *jmb_*
and lets the user choose the server they want to work with.

informations are saved in the config.txt file and then
used by the esp32_airsens_sensor.py program to connect to the central.

v1.0 : 07.01.2022 --> first prototype
v1.1 : 16.01.2022 --> added all info about central in config.txt
"""

import ubluetooth
import ubinascii
import utime
from lib.ble_advertising import decode_name

T_WAIT_FOR_IRQ_TERMINATED_MS = 100
# IRQ constants
_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
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

class BleAirsensScan:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._scan_done = False
        
        self._central_list = []
        
        self._addr_type = None
        self._addr = None
        self._adv_type = None
        self._rssi = None
        self._adv_data = None

        self.conn_handle = []
        self.start_handle = []
        self.end_handle = []
        self.tx_handle = []
        self.rx_handle = []
        
        self._gattc_characteristic_done = None
        self._irq_peripheral_connect = None
        self._irq_peripheral_disconnect = None
        
    def _reset(self):

        self._gattc_characteristic_done = None
        self._irq_peripheral_connect = None
        self._irq_peripheral_disconnect = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT: #5
            addr_type, addr, adv_type, rssi, adv_data = data
            if decode_name(adv_data)[:4] == 'jmb_':
                # Found serve with name begining with "jmb_".
                in_list = False
                for r in self._central_list:
                    if r[1] == addr:
                        in_list = True
                if not in_list:        
                    self._central_list.append([addr_type, bytes(addr), adv_type, rssi, decode_name(adv_data)])
                    self._addr_type = addr_type
                    self._addr = bytes(addr)
                    self._adv_type = adv_type
                    self._rssi = rssi
                    self._adv_data = decode_name(adv_data)

        elif event == _IRQ_SCAN_DONE: #6
            self._scan_done = True
                    
        if event == _IRQ_PERIPHERAL_CONNECT: #7
            conn_handle, addr_type, addr = data
            # Connect successful.
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self.conn_handle.append(conn_handle)
                self._ble.gattc_discover_services(self._conn_handle)
                self._irq_peripheral_connect = True

        elif event == _IRQ_PERIPHERAL_DISCONNECT: #8
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            
        elif event == _IRQ_GATTC_SERVICE_RESULT: #9
            pass
            # Connected device returned a service.
            while not self._irq_peripheral_connect:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _irq_peripheral_connect')
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _UART_SERVICE_UUID:
                self._start_handle = start_handle
                self._end_handle = end_handle
                self.start_handle.append(start_handle)
                self.end_handle.append(end_handle)
                self._gattc_service_result = True

        elif event == _IRQ_GATTC_SERVICE_DONE: #10
            pass
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
            pass
            # Connected device returned a characteristic.
            while not self._gattc_service_done:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _gattc_service_done')
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == _UART_RX_CHAR_UUID[0]:
                self._rx_handle = value_handle
                self.rx_handle.append(value_handle)
            if conn_handle == self._conn_handle and uuid == _UART_TX_CHAR_UUID[0]:
                self._tx_handle = value_handle
                self.tx_handle.append(value_handle)
            self._gattc_characteristic_result = True
 
        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE: #12
            pass
            # Characteristic query complete.
            while not self._gattc_characteristic_result:
                utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
                print('waiting for _gattc_characteristic_result')
            if self._tx_handle is not None and self._rx_handle is not None:
                self._gattc_characteristic_done = True
            else:
                print("Failed to find uart rx characteristic.")
                
    def config_write_conn_info(self, data):
        with open ('config.txt', 'w') as f:
            if data:
                f.write(data)
            else:
                f.write('')

    def bytes_to_asc(self, v_bytes):
        return ubinascii.hexlify(bytes(v_bytes)).decode('utf-8')

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._ble.gap_scan(2000, 30000, 30000)

    def connect(self, addr_type=None, addr=None, scan_duration_ms=500): #, callback=None):
        self._addr_type = addr_type
        self._addr = addr
        if self._addr_type is None or self._addr is None:
            self._ble.gap_connect(None)
            print('-------> self._ble.gap_connect(None)')
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True
    
    def disconnect(self):
        self._ble.gap_disconnect(self._conn_handle)
        self._irq_peripheral_disconnect = True


def main():
    
    print('initializing bluetooth')
    # instatiation of bluetooth.BLE
    ble = ubluetooth.BLE()
    ble_scan = BleAirsensScan(ble)
    
    # scan for central servers
    print('scanning bluetooth network')
    ble_scan.scan()
    while not ble_scan._scan_done:
        utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
    print('found ' + str(len(ble_scan._central_list)) + ' central\n')
    
    "[addr_type, bytes(addr), adv_type, rssi, decode_name(adv_data)]"
    for nb, c in enumerate(ble_scan._central_list):
        connect_status = ble_scan.connect(c[0], c[1])
        while not connect_status:# and not sensor._gattc_service_timeout:
            print('----> waiting for connection --> timeaout status =', sensor._gattc_service_timeout)
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
            connect_status = ble_scan.connect(sensor._addr_type, sensor._addr)
        while not ble_scan._gattc_characteristic_done:
#             print('waiting for _gattc_characteristic_done')
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
        ble_scan.disconnect()
        while not ble_scan._irq_peripheral_disconnect:
            utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
        
        # "addr_type, bytes(addr), adv_type, rssi, decode_name(adv_data)"
#         print('addr_type:', c[0])
#         print('addr:', ble_scan.bytes_to_asc(c[1]))
#         print('adv_type:', c[2])
#         print('rssi:', c[3])
#         print('name:', c[4])
#         print('conn_handle:', ble_scan.conn_handle[nb])
#         print('start_handle:', ble_scan.start_handle[nb])
#         print('end_handle:', ble_scan.end_handle[nb])
#         print('tx_handle:', ble_scan.tx_handle[nb])
#         print('rx_handle:', ble_scan.rx_handle[nb])
#         print()

        ble_scan._reset()
    
    # choose the one with the higher rssi
    nearest_index = -1
    nearest_level = -1000
    for nb, c in enumerate(ble_scan._central_list):
        rssi = c[3]
        if rssi > nearest_level:
            nearest_level = rssi
            nearest_index = nb
    
    # displa the list of central servers
    nb = len(ble_scan._central_list)
    v_choice = 0
    if nb > 0:
        print('-------------------------------------------------------')
        for nb, c in enumerate(ble_scan._central_list):
            # [addr_type, bytes(addr), adv_type, rssi, decode_name(adv_data)]
            msg = str(nb) + ' --> ' + c[4] + ' - ' + ble_scan.bytes_to_asc(c[1]) + ' - ' + 'rssi:' + str(c[3])
            print(msg)
        print('-------------------------------------------------------')
    
        # ask for client central choice
        print('\nTo witch central one do you want to connect ?')
        v_choice = int(input('Enter the central number (best choice=' +
                       str(nearest_index) + ' - rssi:' + str(nearest_level) + ':')
                       or str(nearest_index))
        if v_choice in(0,nb):
            # writing the choice in the config.txt file
            config_txt = 'addr_type:' + str(ble_scan._central_list[v_choice][0]) + '\n'
            config_txt += 'addr:' + ble_scan.bytes_to_asc(ble_scan._central_list[v_choice][1]) + '\n'
            config_txt += 'adv_type:' + str(ble_scan._central_list[v_choice][2]) + '\n'
            config_txt += 'rssi:' + str(ble_scan._central_list[v_choice][3]) + '\n'
            config_txt += 'name:' + ble_scan._central_list[v_choice][4] + '\n'
            config_txt += 'conn_handle:' + str(ble_scan.conn_handle[v_choice]) + '\n'
            config_txt += 'start_handle:' + str(ble_scan.start_handle[v_choice]) + '\n'
            config_txt += 'end_handle:' + str(ble_scan.end_handle[v_choice]) + '\n'
            config_txt += 'tx_handle:' + str(ble_scan.tx_handle[v_choice]) + '\n'
            config_txt += 'rx_handle:' + str(ble_scan.rx_handle[v_choice]) + '\n'
            ble_scan.config_write_conn_info(config_txt)        
#             print(config_txt)

            print('-------------------------------------------------------')
            print('recorded: ' + ble_scan._central_list[v_choice][4] +
                  ' address ' + ble_scan.bytes_to_asc(ble_scan._central_list[v_choice][1]))
            print('-------------------------------------------------------')
        else:
            print('choix compris entre 0 et ' + str(nb))
            with open('config.txt', 'w'): pass
            print('le programme s\'arrete ici')
    else:
        print('no central found')

        
if __name__ == "__main__":
    main()
