#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: encode_decode.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

coding the values in a string of 20 char len

v0.1.0 : 07.01.2022 --> first prototype
v0.1.1 : 29.01.2022 --> removed gas mesurement
v0.1.2 : 31.01.2022 --> added crc function, adapted decode for crc
v0.1.3 : 02.02.2022 --> moved to class
"""

class EncodeDecode:
    def _get_str(self, val, nb_char): 
        val = int(abs(val))
        str_format = '{:0>' + str(nb_char) + '}'
        return str_format.format(int(val))

    def encode_msg(self, jmb_id, piece, temp, hum, pres, bat):
        
        temp = float(temp)
        hum = float(hum)
        pres = float(pres)
        bat = float(bat)
        if temp < 0 :
            sign = '-'
        else :
            sign = '+'
        msg = jmb_id + piece
        msg += str(sign)
        msg += self._get_str(temp*10, 3)
        msg += self._get_str(hum, 2)
        msg += self._get_str(pres, 3)
        msg += self._get_str(bat*100, 3)
        return msg

    def decode_msg(self, msg):
        jmb_id = msg[0:3]
        piece = msg[3:5]
        temp = int(msg[6:9])/10
        hum = int(msg[9:11])
        pres = int(msg[11:14])
        bat = int(msg[14:17])/100
        rx_crc = msg[17:19]
        return jmb_id, piece, temp, hum, pres, bat, rx_crc
        
    def get_crc(self, msg):
        crc_0 = 0
        crc_1 = 0
        for i, char in enumerate(msg):
            if (i %2) == 0:
                crc_0 += ord(char)
            else:
                crc_1 += ord(char)
        crc = crc_0 + crc_1 * 3
        if crc < 10 : crc *= 10
        return str(crc)[-2:]
