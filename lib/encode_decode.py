#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: encode_decode.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

coding the values ina message of 20 char len

v0.1.0 : 07.01.2022 --> first prototype
v0.1.1 : 29.01.2022 --> removed gas mesurement
v0.1.2 : 31.01.2022 --> added crc function, adapted decode for crc
"""

def _get_str(val, nb_char): 
    val = int(abs(val))
    str_format = '{:0>' + str(nb_char) + '}'
    return str_format.format(int(val))

def encode_msg(jmb_id, piece, temp, hum, pres, bat):
    
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
    msg += _get_str(temp*10, 3)
    msg += _get_str(hum, 2)
    msg += _get_str(pres, 3)
    msg += _get_str(bat*100, 3)
    return msg

def decode_msg(msg):
    jmb_id = msg[0:3]
    piece = msg[3:5]
    temp = int(msg[6:9])/10
    hum = int(msg[9:11])
    pres = int(msg[11:14])
    bat = int(msg[14:17])/100
    rx_crc = msg[17:19]
    return jmb_id, piece, temp, hum, pres, bat, rx_crc
    
def crc(msg):
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

# def xor(a, b): 
#     result = [] 
#     for i in range(1, len(b)):
#         if a[i] == b[i]: 
#             result.append('0') 
#         else: 
#             result.append('1') 
#     return ''.join(result) 
#    
# def mod2div(divident, divisor): 
#     pick = len(divisor) 
#     tmp = divident[0 : pick] 
#     while pick < len(divident): 
#         if tmp[0] == '1': 
#             tmp = xor(divisor, tmp) + divident[pick] 
#         else:   
#             tmp = xor('0'*pick, tmp) + divident[pick] 
#         pick += 1
#     if tmp[0] == '1': 
#         tmp = xor(divisor, tmp) 
#     else: 
#         tmp = xor('0'*pick, tmp) 
#     checkword = tmp 
#     return checkword 
#    
# def get_crc(msg, key='101'):
# #     data = map(bin,bytearray(msg, encoding='utf-8'))
#     data = ''.join(['{0:08b}'.format(ord(x)) for x in msg]) 
#     remainder = mod2div(data + '0'*(len(key)-1), key) 
# #     print('data:', data, 'remainder:', remainder)
#     return remainder     


if __name__ == '__main__':
    # encode msf ans add crc
    msg = encode_msg('jmb', 'bu', 22.2, 55, 999, 4.44)
    crc_tx = get_crc(msg)
    msg += crc_tx
    print('send msg:', msg)
    # decode msg and verify crc
    jmb_id, piece, temp, hum, pres, bat, crc_rx = decode_msg(msg)
    if crc_tx == crc_rx:
        print(jmb_id, piece, temp, hum, pres, bat)
    else:
        print('Transmission error bad crc')
