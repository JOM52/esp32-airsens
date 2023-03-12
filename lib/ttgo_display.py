#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_now_ttgo_display.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-now

Driver for the ttgo-t-display st7789

v0.1.0 : 01.01.2023 --> first prototype
v0.1.1 : 18.01.2023 --> added verif on text lenght before displaying
V0.1.2 : 19.01.2023 --> CORRECTED color_...
"""
VERSION = '0.1.2'
PROGRAM_NAME = 'airsens_now_ttgo_display.py' 

from time import sleep
from lib.st7789 import ST7789, color565
from machine import Pin, SoftSPI as SPI
from lib.xglcd_font import XglcdFont

BL_Pin = 4     #backlight pin
SCLK_Pin = 18  #clock pin
MOSI_Pin = 19  #mosi pin
MISO_Pin = 2   #miso pin
DC_Pin = 16    #data/command pin
CS_Pin = 5     #chip select pin

BLK = Pin(BL_Pin, Pin.OUT)
BLK.value(1)
spi = SPI(
    baudrate=20000000,
    polarity=1,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(13))
display = ST7789(
    spi,
    135,
    240,
    rst=Pin(23, Pin.OUT),
    cs=Pin(5, Pin.OUT),
    dc=Pin(16, Pin.OUT),
    backlight=Pin(4, Pin.OUT)) #, rotation=3)

class TtgoTdisplay:
    
    # color565(R, G, B)
    COLOR_BLUE = color565(0, 128, 255)
    COLOR_GREEN = color565(0, 255, 0)
    COLOR_RED = color565(255, 0, 0)
    COLOR_CYAN = color565(0, 255, 255)
    COLOR_ORANGE = color565(255, 128, 0)
    COLOR_YELLOW = color565(248, 229, 101)
    COLOR_BLACK = color565(0, 0, 0)
    COLOR_WHITE = color565(255, 255, 255)
    COLOR_VIOLET = color565(155,38,182)
    BACK_COLOR = color565(0, 0, 0)

    def cls(self):
        display.fill(self.BACK_COLOR)

    def __init__(self):
        display.clear()
        self.espresso_dolce = XglcdFont('lib/EspressoDolce18x24.c', 18, 24)
        self.line_height = int(139 / 5)
        self.x_txt_0 = 240
        self.x_txt_1 = 120
        self.x_txt_2 = 55

    def ok_len_txt(self, txt_0='', txt_1='', txt_2=''):
        err=''
        if self.espresso_dolce.measure_text(txt_2) > self.x_txt_2:
           err = 'txt_2 too long'
        if txt_1 and txt_2:
            if self.espresso_dolce.measure_text(txt_1) > self.x_txt_1 - self.x_txt_2:
                err = 'txt_1 too long'
        else:
            if self.espresso_dolce.measure_text(txt_1) > self.x_txt_1:
                err = 'txt_1 too long'
        if txt_0 and txt_1:
            if self.espresso_dolce.measure_text(txt_0) > self.x_txt_0 - self.x_txt_1:
                err = 'txt_0 too long'
        else:
            if self.espresso_dolce.measure_text(txt_0) > self.x_txt_0:
                err = 'txt_0 too long'
        return err

    def write_centred_line(self, line, txt, color=COLOR_WHITE, color_2=COLOR_YELLOW):
        y = line * self.line_height
        txt_2_long = False
        while self.espresso_dolce.measure_text(txt) >= self.x_txt_0 - 30:
            txt_2_long = True
            txt = txt[:len(txt)-1]
        if txt_2_long : txt += '...'
        x_c = self.x_txt_0 - max(int((self.x_txt_0 - self.espresso_dolce.measure_text(txt)) / 2),0)
#         print(txt,
#               'self.espresso_dolce.measure_text(txt):', self.espresso_dolce.measure_text(txt),
#               'self.x_txt_0:', self.x_txt_0,
#               'x_c:', x_c)
        display.draw_text(y, x_c, txt, self.espresso_dolce, color, landscape=True)


    def write_text(self, line, txt, color=COLOR_WHITE):
        
        y = line * self.line_height
        ok_txt = self.ok_len_txt(txt)
        if not ok:
            display.draw_text(y, self.x_txt_0, txt, self.espresso_dolce, color, landscape=True)
        else:
            display.draw_text(y, self.x_txt_0, ok_txt, self.espresso_dolce, COLOR_RED, landscape=True)

    def write_line(self, line, txt, val_1='', val_2='', color=COLOR_WHITE, color_2=COLOR_YELLOW):
        y = line * self.line_height
        ok_txt = self.ok_len_txt(txt, val_1, val_2)
        if ok_txt == '':
            display.draw_text(y, self.x_txt_0, txt, self.espresso_dolce, color, landscape=True)
            display.draw_text(y, self.x_txt_1, val_1, self.espresso_dolce, color_2, landscape=True)
            display.draw_text(y, self.x_txt_2, val_2, self.espresso_dolce, color_2, landscape=True)
        else:
            display.draw_text(y, self.x_txt_0, ok_txt, self.espresso_dolce, self.COLOR_RED, landscape=True)
            
    def clear_line(self, line):
        self.write_line(line, ' '*21 , color=self.BACK_COLOR, color_2=self.BACK_COLOR)

    def write_line_overview(self, line, txt, val_1='', val_2='', txt_color=COLOR_CYAN, val_color=COLOR_WHITE):
        y = line * self.line_height
        ok_txt = self.ok_len_txt(txt, val_1, val_2)
        if ok_txt == '':
            display.draw_text(y, self.x_txt_0, txt, self.espresso_dolce, txt_color, landscape=True)
            display.draw_text(y, self.x_txt_1, val_1, self.espresso_dolce, val_color, landscape=True)
            display.draw_text(y, self.x_txt_2, val_2, self.espresso_dolce, val_color, landscape=True)
        else:
            display.draw_text(y, self.x_txt_0, ok_txt, self.espresso_dolce, COLOR_RED, landscape=True)

    def write_line_bat(self, line, txt, val_1='', val_2='', txt_color=COLOR_GREEN, bat_color=COLOR_WHITE):
        y = line * self.line_height
        ok_txt = self.ok_len_txt(txt, val_1, val_2)
        if ok_txt == '':
            display.draw_text(y, self.x_txt_0, txt, self.espresso_dolce, txt_color, landscape=True)
            display.draw_text(y, self.x_txt_1, val_1, self.espresso_dolce, bat_color, landscape=True)
            display.draw_text(y, self.x_txt_2, val_2, self.espresso_dolce, bat_color, landscape=True)
        else:
            display.draw_text(y, self.x_txt_0, ok_txt, self.espresso_dolce, COLOR_RED, landscape=True)

    def mark_auto_ecran_change(self, color):
        display.fill_rect(2, 0, 5, 5, color)

def main():
    
    ttgo_tdisp = TtgoTdisplay()   
    
    ttgo_tdisp.cls()
    ttgo_tdisp.write_line(2, 'asdfghjkl', '-txt_1', '-12-fsdgth')
    sleep(1)
    ttgo_tdisp.cls()
    ttgo_tdisp.write_line(0, 'Salon','21.1', '48%', ttgo_tdisp.COLOR_CYAN)        
    ttgo_tdisp.write_line(1, 'Bureau','20.8', '62%', ttgo_tdisp.COLOR_CYAN)        
    ttgo_tdisp.write_line(2, 'Exterieur','-10.3', '55%', ttgo_tdisp.COLOR_CYAN)        
    ttgo_tdisp.write_line(3, 'Pression','1024', 'mHg', ttgo_tdisp.COLOR_BLUE)        
    ttgo_tdisp.write_line(4, 'Batterie','4.1V', '87%', ttgo_tdisp.COLOR_GREEN)
    
if __name__ == '__main__':
    main()
