#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: exec_time_mes.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

record the execution time
v0.1.0 : 27.01.2022 --> first prototype
v0.1.1 : 26.04.2022 --> minors changes
v0.1.2 : 03.05.2022 --> total_time modified as self._total_time
v0.1.3 : 06.05.2022 --> add time stats
"""

from utime import ticks_ms
class exec_time_mes:
    def __init__(self, stat_mes= False, filename='exec_time.txt', stat_filename = "exe_time_stat.csv"):
        self._start_time = None
        self._old_time = None
        self._total_time = None
        self._time_list = []
        self._filename = filename
        self._stat_mes = stat_mes
        self._stat_new = False
        self._stat_data = []
        self._stat_filename = stat_filename
        self._stat_file_exist = False

    def time_step(self, step):
        if step == 'start':
            self._start_time = ticks_ms()
        elif step == 'stop':
            self._total_time = ticks_ms() - self._start_time
            len_name = 0
            for line in self._time_list:
                step_name,value = line.split(':')
                if len(step_name) > len_name : len_name = len(step_name)
            len_name += 1
            file_open_mode = 'w'
            with open (self._filename, file_open_mode) as f:
                old_time = self._start_time
                for line in self._time_list:
                    step_name,value = line.split(':')
                    step_name += ' '*(len_name-len(step_name))
                    step_time = '{:.0f}'.format(float(value) - old_time)
                    old_time = float(value)
                    f.write(step_name + ': ' + step_time + ' ms\n')
                f.write('-'*(len_name + 10) + '\n')
                step_name = 'total execution time'
                f.write(step_name + ' '*(len_name-len(step_name)) + ': ' + str(self._total_time) + ' ms\n')
                
                if self._stat_mes:
                    # stats
                    if not self._stat_file_exist:
                        # create titles
                        with open (self._stat_filename, 'w') as f_stat:
                            title = ''
                            for line in self._time_list:
                                step_name,value = line.split(':')
                                title += step_name + ';'
                            txt = title + '\n'
                            f_stat.write(txt)
                            self._stat_file_exist = True
                    # add times
                    old_time = self._start_time
                    with open (self._stat_filename, 'a') as f_stat:
                        data = ''
                        for line in self._time_list:
                            step_name,value = line.split(':')
                            step_time = '{:.0f}'.format(float(value) - old_time)
                            data += step_time + ';'
                            old_time = float(value)
                        txt = data + '\n'
                        f_stat.write(txt)
                        
                    
                        
                    
        else:
            self._time_list.append(step + ':' + str(ticks_ms()))
            self._old_time = ticks_ms()
            
        if not self._stat_new:
            try:
                f = open(self._stat_filename, "r")
                f.close()
                self._stat_file_exist = True
            except:
                self._stat_file_exist = False
