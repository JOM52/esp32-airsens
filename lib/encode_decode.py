#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: encode_decode.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

coding the values ina message of 20 char len

v1.0 : 07.01.2022 --> first prototype
"""

def _get_str(val, nb_char): 
    val = int(abs(val))
    str_format = '{:0>' + str(nb_char) + '}'
    return str_format.format(int(val))

def encode_msg(jmb_id, piece, temp, hum, pres, gas, bat):
    
    temp = float(temp)
    hum = float(hum)
    pres = float(pres)
    gas = float(gas)
    bat = float(bat)
    if temp < 0 :
        sign = '-'
    else :
        sign = '+'
    msg = jmb_id + piece
    msg += str(sign)
    msg += _get_str(temp*10, 3)
    msg += _get_str(hum, 2)
    msg += _get_str(pres, 3)
    msg += _get_str(gas*10, 3)
    msg += _get_str(bat*100, 3)
    return msg

def decode_msg(msg):
    jmb_id = msg[0:3]
    piece = msg[3:5]
    temp = int(msg[6:9])/10
    hum = int(msg[9:11])
    pres = int(msg[11:14])
    gas = int(msg[14:17])/10
    bat = int(msg[17:])/100
    return jmb_id, piece, temp, hum, pres, gas, bat
    
          
if __name__ == '__main__':
    msg = encode_msg('jmb', 'bu', 23.7, 56, 947, 0, 4.05)
    print(msg)
    jmb_id, piece, temp, hum, pres, gas, bat = decode_msg(msg)
    print(jmb_id, piece, temp, hum, pres, gas, bat)
