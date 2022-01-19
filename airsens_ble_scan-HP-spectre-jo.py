#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_scan.py 

version: 1.1
date: 7.1.2022
author: jom52

version 1.0 : 13.01.2022 --> first proto
version 1.1 : 13.01.2022 --> logic corrected, input improved

email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

this program scans the bluetooth network to find all the *ble_central* whose name starts with *jmb_*
and lets the user choose the server they want to work with.

address, type address and name are saved in the config.txt file and then
used by the esp32_airsens_sensor.py program to connect to the central.
"""

import ubluetooth
import ubinascii
import utime
from lib.ble_advertising import decode_name

T_WAIT_FOR_IRQ_TERMINATED_MS = 100
_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6


class BleJmbScan:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._scan_done = False
        self._central_list = list()
        
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

        elif event == _IRQ_SCAN_DONE: #6
            self._scan_done = True
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                    self._scan_done = True
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)
                
    def config_write_conn_info(self, data):
        with open ('config.txt', 'w') as f:
            if data:
                for d in data:
                    if type(d) == int:
                        f.write(str(d) + '\n')
                    else:
                        f.write(d + '\n')
            else:
                f.write('')

    def bytes_to_asc(self, v_bytes):
        return ubinascii.hexlify(bytes(v_bytes)).decode('utf-8')

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        self._ble.gap_scan(2000, 30000, 30000)


def main():
    
    print('initializing bluetooth')
    # instatiation of bluetooth.BLE
    ble = ubluetooth.BLE()
    central_scan = BleJmbScan(ble)
    
    # scan for central servers
    print('scanning bluetooth network')
    central_scan.scan()
    while not central_scan._scan_done:
        utime.sleep_ms(T_WAIT_FOR_IRQ_TERMINATED_MS)
    print('found ' + str(len(central_scan._central_list)) + ' central\n')
    
    # choose the one with the higher rssi
    nearest_index = -1
    nearest_level = -1000
    for nb, c in enumerate(central_scan._central_list):
        rssi = c[3]
        if rssi > nearest_level:
            nearest_level = rssi
            nearest_index = nb
    
    # displa the list of central servers
    nb = len(central_scan._central_list)
    v_choice = 0
    if nb > 0:
        print('-------------------------------------------------------')
        for nb, c in enumerate(central_scan._central_list):
            # [addr_type, bytes(addr), adv_type, rssi, decode_name(adv_data)]
            msg = str(nb) + ' --> ' + c[4] + ' - ' + central_scan.bytes_to_asc(c[1]) + ' - ' + 'rssi:' + str(c[3])
            print(msg)
        print('-------------------------------------------------------')
    
        # ask for client central choice
        print('\nTo witch central one do you want to connect ?')
        v_choice = int(input('Enter the central number (default=' +
                       str(nearest_index) + ' rssi:' + str(nearest_level) + ') :')
                       or str(nearest_index))
        if v_choice in(0,nb):
            # writing the choice in the config.txt file
            print('writing config.txt --> central:' + str(v_choice))
            addr_type = central_scan._central_list[v_choice][0]
            addr = ubinascii.hexlify(bytes(central_scan._central_list[v_choice][1])).decode('utf-8')
            name = central_scan._central_list[v_choice][4]
            central_scan.config_write_conn_info([addr_type, addr, name])        

            print('-------------------------------------------------------')
            print('recorded: ' + central_scan._central_list[v_choice][4] +
                  ' address ' + central_scan.bytes_to_asc(central_scan._central_list[v_choice][1]))
            print('-------------------------------------------------------')
        else:
            print('choix compris entre 0 et ' + str(nb))
            with open('config.txt', 'w'): pass
            print('le programme s\'arrete ici')
    else:
        print('no central found')

        
if __name__ == "__main__":
    main()
