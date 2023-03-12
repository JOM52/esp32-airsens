#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_central.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-airsens-class

v0.4.0 : 05.02.2023 --> first prototype
v0.4.1 : 26.02.2023 --> optimisation du fichier conf
v0.4.2 : 27.02.2023 --> amelioration de la boucle Main
v0.4.3 : 28.02.2023 --> grand nettoyage
v0.4.4 : 01.03.2022 --> button_1_action simplified
v0.4.5 : 05.03.2023 --> small changes Venezia
v1.0.0 : 11.03.2023 --> first production version
"""
VERSION = '1.0.0'
PROGRAM_NAME = 'airsens_central.py'

from ubinascii import hexlify
from machine import Pin, Timer, reset
from espnow import ESPNow
from utime import sleep_ms, localtime, time
from network import WLAN, STA_IF, AP_IF, WIFI_PS_NONE

from lib.log_and_count import LogAndCount
from lib.ttgo_display import TtgoTdisplay
from lib.umqttsimple import MQTTClient
import airsens_central_conf as conf


class GlobalVar:
    data_pointer = None
    current_page = None
    current_mode = None


class Show:

    def __init__(self,
                 ttgo_display, # classes
                 datas, data_time  # lists to store the datas
                 ):
        self.ttgo_display = ttgo_display
        self.datas = datas
        self.data_time = data_time
        self.refresh_screen_timer = Timer(0)  # timer to switch to the next ecran

    # called by the timer because he give a not usefull param
    # and the procedure refresh_screen don't use it
    def refresh_screen_from_timer(self, z):
        self.refresh_screen()

    # refresh the screen for any mode
    def refresh_screen(self):
        self.ttgo_display.cls()
        if GlobalVar.current_mode == 0:
            'mode auto'
            GlobalVar.data_pointer = self.manage_data_pointer(GlobalVar.data_pointer, len(self.datas))
            self.display_auto(self.datas, GlobalVar.data_pointer)
            self.refresh_screen_timer.init(period=conf.REFRESH_SCREEN_TIMER_MS, mode=Timer.ONE_SHOT,
                                           callback=self.refresh_screen_from_timer)
        elif GlobalVar.current_mode == 1:
            'mode overview'
            self.display_overview(title='OVERVIEW ', n_row=4, n_col=1, data_list=self.datas,
                                       current_page=GlobalVar.current_page, current_mode=GlobalVar.current_mode)
        elif GlobalVar.current_mode == 2:
            'mode batteries status'
            self.display_overview(title='BATTERY ', n_row=4, n_col=1, data_list=self.datas,
                                       current_page=GlobalVar.current_page, current_mode=GlobalVar.current_mode)
            

    # display the data for the modes auto
    def display_auto(self, datas, data_pointer):
        if datas:
            location, temp_f, hum_f, pres_f, bat_val, bat_f, bat_pc_f, bat_color = datas[data_pointer]
            self.ttgo_display.write_line(0, location, color=self.ttgo_display.COLOR_WHITE)
            self.ttgo_display.write_line(1, 'Temp = ' + str(temp_f) + '"C', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_line(2, 'Hum  = ' + str(hum_f) + '%', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_line(3, 'Pres = ' + str(pres_f) + 'hPa', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_line(4, 'Batt = ' + str(bat_f) + 'V ' + str(bat_pc_f) + '%', color=bat_color)
        else:
            self.ttgo_display.write_line(1, 'No datas', color=self.ttgo_display.COLOR_RED)
            

    def display_overview(self, title, n_row, n_col, data_list, current_page, current_mode):
        self.ttgo_display.cls()
        if data_list:
            len_data_list = len(data_list)
            self.ttgo_display.write_line(0, title
                                         + str(current_page * n_row) + '...'
                                         + str((current_page + n_col) * n_row) + ' / '
                                         + str(len_data_list),
                                         color=self.ttgo_display.COLOR_WHITE)
            for i in range(0, len(data_list)):
                if (current_page * n_row) <= i < ((current_page + 1) * n_row):
                    row = i - current_page * n_row + 1
                    location, temp_f, hum_f, pres_f, bat_val, bat_f, bat_pc_f, bat_color = data_list[i]
                    if current_mode == 1:
                        self.ttgo_display.write_line_overview(row, location, temp_f + 'C', hum_f + '%',
                                                              txt_color=self.ttgo_display.COLOR_CYAN,
                                                              val_color=self.ttgo_display.COLOR_YELLOW)
                    elif current_mode == 2:
                        self.ttgo_display.write_line_bat(row, location, bat_f + 'V', bat_pc_f + '%',
                                                         txt_color=self.ttgo_display.COLOR_CYAN, bat_color=bat_color)
        else:
            self.ttgo_display.write_line(1, 'No datas', color=self.ttgo_display.COLOR_RED)
            
    def manage_data_pointer(self, pointer, len_data_list):
        if pointer < len_data_list - 1:
            pointer += 1
        else:
            pointer = 0
        return pointer


class Menu:

    def __init__(self,
                 show, ttgo_display, # classes
                 datas, data_time  # lists to store the datas
                 ):
        self.interrupt_pin = None
        self.show = show
        self.ttgo_display = ttgo_display
        self.choice_ok_timer = Timer(0)  # timer to valid the mode choice
        self.button_debounce_timer = Timer(0)  # timer to debounce the switches
        self.datas = datas
        self.data_time = data_time

    # callback procedure for any button pressed
    # execute the action corresponding to the pressed button
    def on_button_pressed(self, z):
        if self.interrupt_pin == Pin(conf.BUTTON_MODE_PIN):
            self.button_1_action()
        elif self.interrupt_pin == Pin(conf.BUTTON_PAGE_PIN):
            self.button_2_action()

    # debounce any button pressed 
    def button_debounce(self, pin):
        self.interrupt_pin = pin
        self.button_debounce_timer.init(mode=Timer.ONE_SHOT,
                                        period=conf.BUTTON_DEBOUNCE_TIMER_MS, callback=self.on_button_pressed)

    # execute actions selected by the button 1 (executed from the timer choice_ok_timer)
    def choice_ok(self, z):
        # after any change in the modes reinit the refresh timer
        if GlobalVar.current_mode == 0:
            'mode auto'
            GlobalVar.data_pointer = -1
        else:
            'mode overview'
            GlobalVar.current_page = 0
        self.show.refresh_screen()

    # change the current mode
    def button_1_action(self):
        self.ttgo_display.cls()
        self.choice_ok_timer.deinit()
        # increment ttgo_curent_mode and reset if too big
        GlobalVar.current_mode += 1
        if GlobalVar.current_mode > len(conf.MODES) - 1:
            GlobalVar.current_mode = 0
        # display the menu with the active line in yellow
        for i in range(0, len(conf.MODES), 1):
            if GlobalVar.current_mode == i:
                color = self.ttgo_display.COLOR_YELLOW
            else:
                color = self.ttgo_display.COLOR_CYAN
            self.ttgo_display.write_line(i, conf.MODES[i], color=color)
        # init timer to do action of the select menu entry
        self.choice_ok_timer.init(mode=Timer.ONE_SHOT, period=conf.CHOICE_TIMER_MS, callback=self.choice_ok)

    # change the current page
    def button_2_action(self):
        if GlobalVar.current_mode == 0:
            'mode auto'
            pass
        else:
            'mode overview'
            current_page_inc = 1
            len_liste = 4
            GlobalVar.current_page = self.get_next_page(self.datas, len_liste, GlobalVar.current_page, current_page_inc)
        self.show.refresh_screen()

    def get_next_page(self, datas, len_liste, current_page, current_page_inc):
        current_page += current_page_inc
        n_pages_entieres = (len(datas) // len_liste) * current_page_inc
        if len(datas) % len_liste > 0:
            n_pages_partielles = 1
        else:
            n_pages_partielles = 0
        if current_page >= n_pages_entieres + n_pages_partielles:
            current_page = 0
        return current_page


class Central:

    def __init__(self):
        self.log = LogAndCount()
        self.ttgo_display = TtgoTdisplay()
        self.ttgo_display.cls()

        GlobalVar.current_mode = conf.DEFAULT_MODE  # default state
        GlobalVar.current_page = 0
        GlobalVar.data_pointer = -1  # start value

        # initialisation listes
        self.datas = []
        self.data_time = []

        # instantiation classes
        self.show = Show(self.ttgo_display, self.datas, self.data_time)
        self.menu = Menu(self.show, self.ttgo_display, self.datas, self.data_time)

        # instantiation ESPNow
        self.espnow = ESPNow()
        self.espnow.active(True)

    def get_formated_time(self, time=None):
        if time is None:
            dt = localtime()
        else:
            dt = localtime(int(time))
        year = '{:04d}'.format(dt[0])
        month = '{:02d}'.format(dt[1])
        day = '{:02d}'.format(dt[2])
        hour = '{:02d}'.format(dt[3])
        minute = '{:02d}'.format(dt[4])
        second = '{:02d}'.format(dt[5])
        return day + '.' + month + '.' + year + ' ' + hour + ':' + minute + ':' + second

    def wifi_reset(self):  # Reset Wi-FI to AP_IF off, STA_IF on and disconnected
        sta = WLAN(STA_IF)
        sta.active(False)
        ap = WLAN(AP_IF)
        ap.active(False)
        sta.active(True)
        return sta, ap
    
    def mqtt_connect_and_subscribe(self):
        try:
            client = MQTTClient(conf.BROKER_CLIENT_ID, conf.BROKER_IP)
            client.connect(True)
            return client
        except Exception as err:
            self.log.log_error('MQTT_connect_and_subscribe', self.log.error_detail(err), to_print=True)
            reset()

    def format_string_number(self, string, n_dec=0):
        # check if it's a number
        try:
            s = float(string)
        except:
            return 'error: the received string dont represent a number'
        # it's a number
        try:
            dot_pos = string.index('.') # get the dot position
        except:
            # no dot so return the received string
            return string
        # round and format the number
        if n_dec > 0:
            return str(round(float(string), n_dec))
        else:
            return string[:dot_pos]
        # no decimals so return the received string

    def add_new_measurment(self, new_data):
        location_exist = False
        for i, d in enumerate(self.datas):
            if d[0] == new_data[0]:
                self.datas[i] = new_data
                self.data_time[i] = time()
                location_exist = True
                break
        # append new location
        if not location_exist:
            self.datas.append(new_data)
            self.data_time.append(time())
        # refresh the display
        if GlobalVar.current_mode != 0:
            self.show.refresh_screen()

    def main(self):
        try:
            self.ttgo_display.cls()
            self.ttgo_display.write_centred_line(0, '... Initialazing ...', color=self.ttgo_display.COLOR_CYAN)
            self.ttgo_display.write_centred_line(2, PROGRAM_NAME, color=self.ttgo_display.COLOR_YELLOW)
            self.ttgo_display.write_centred_line(3, 'Version:' + VERSION, color=self.ttgo_display.COLOR_YELLOW)
            print('-----------------------------------------------------------------------')
            print(PROGRAM_NAME + ' - Version:' + VERSION)
            print("now date and time :", self.get_formated_time())
            sta, ap = self.wifi_reset()  # Reset Wi-FI to AP off, STA on and disconnected
            wlan_mac = sta.config('mac')
            sta.connect(conf.WIFI_WAN, conf.WIFI_PW)
            while not sta.isconnected():
                sleep_ms(200)
            sta.config(ps_mode=WIFI_PS_NONE)  # ..then disable power saving
            print("MAC Address:", wlan_mac, '>>',
                  hexlify(wlan_mac, ':').decode().upper())  # wlan_mac.decode('ascii'))  # Show MAC for peering
            print("main running on channel:", sta.config("channel"))
            print('ESPNow active:', self.espnow)
            print('MQTT broker IP:' + conf.BROKER_IP + ' topic: ' + conf.TOPIC)
            print('-----------------------------------------------------------------------')
            # Setup the button input pin with a pull-up resistor.
            button_mode = Pin(conf.BUTTON_MODE_PIN, Pin.IN, Pin.PULL_UP)
            button_ecran = Pin(conf.BUTTON_PAGE_PIN, Pin.IN, Pin.PULL_UP)
            # Register an interrupt on rising button input.
            button_ecran.irq(self.menu.button_debounce, Pin.IRQ_RISING)
            button_mode.irq(self.menu.button_debounce, Pin.IRQ_RISING)

            for peer, msg in self.espnow:
                if peer and msg:
                    '''New message received'''
                    #                 print('new message received')
                    jmb_id, location, temp, hum, pres, bat = msg.decode('utf-8').split(',')
                    
                    # format the numbers for the small display
                    temp_f = '{:.1f}'.format(float(temp))
                    hum_f = '{:.0f}'.format(float(hum))
                    pres_f = '{:.0f}'.format(float(pres))
                    bat_f = '{:.2f}'.format(float(bat))
                    bat_pc = min(((float(bat) * 111.11) - 355.55), 100)  # ubat min = 3.2 => 0%, ubat max = 4.2 => 100%
                    bat_pc_f = '{:.0f}'.format(bat_pc)
                    
                    # change the color for the battery to indicate the charge state
                    if float(bat) < conf.BAT_LOW:
                        color_bat = self.ttgo_display.COLOR_RED
                    elif conf.BAT_LOW <= float(bat) <= conf.BAT_OK:
                        color_bat = self.ttgo_display.COLOR_ORANGE
                    elif float(bat) > conf.BAT_OK:
                        color_bat = self.ttgo_display.COLOR_GREEN
                    else:
                        color_bat = self.ttgo_display.COLOR_WHITE
                        
                    self.add_new_measurment([location, temp_f, hum_f, pres_f, bat, bat_f, bat_pc_f, color_bat])
                    
                    # check if connected to Wi-FI and if not reconnect 
                    if not sta.isconnected():
                        sta, ap = self.wifi_reset()  # Reset Wi-FI to AP off, STA on and disconnected
                        wlan_mac = sta.config('mac')
                        sta.connect(conf.WIFI_WAN, conf.WIFI_PW)
                        while not sta.isconnected():
                            sleep_ms(200)
                        self.log.log_error('WIFI connection lost, reconnecting', to_print = True)
                        sta.config(ps_mode=WIFI_PS_NONE)  # ..then disable power saving

                    # has the message the right identificator
                    if jmb_id == 'jmb':
                        passe = self.log.counters('passe', True)
                        try:
                            client = self.mqtt_connect_and_subscribe()  # conf.BROKER_CLIENT_ID, conf.BROKER_IP, conf.TOPIC)
                            sleep_ms(250)
                            if client is not None:
                                msg = (str(passe) + ','
    #                                    + location + ','
                                       + 'v1_test' + ','
                                       + str(temp) + ','
                                       + str(hum) + ','
                                       + str(pres) + ','
                                       + str(bat))
                                client.publish(conf.TOPIC, msg)
                                client.disconnect()
                            else:
                                self.log.log_error('MQTT client is None', to_print = True)

                        except Exception as err:
                            self.log.log_error('MQTT publish', self.log.error_detail(err), to_print = True)
                            reset()

                        print(str(passe) + ' - '
                              + self.get_formated_time() + ' - '
                              + location
                              + ' - temp: ' + '{:4.2f}'.format(float(temp))  # str(temp)
                              + ' - hum: ' + '{:4.1f}'.format(float(hum))  # str(hum)
                              + ' - pres: ' + '{:4.1f}'.format(float(pres))  # str(pres)
                              + ' - bat: ' + '{:4.3f}'.format(float(bat))  # str(bat)
                              + ' - errors: ' + str(self.log.counters('error'))
                              + ' - RSSI: ' + str(sta.status('rssi')))
                    else:
                        self.log.log_error('wrong message received', to_print = True)

        except Exception as err:
            self.log.log_error('Main', self.log.error_detail(err), to_print = True)
            reset()

def main():
    central = Central()
    central.main()

if __name__ == '__main__':
    main()
