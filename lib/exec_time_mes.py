#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: exec_time_mes.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

record the execution time
v0.1.0 : 27.01.2022 --> first prototype
"""
from utime import sleep_ms, ticks_ms
class exec_time_mes:
    def __init__(self):
        self._start_time = None
        self._old_time = None
        self._time_list = []

    def time_step(self, stage):
        if stage == 'start':
            self._start_time = ticks_ms()
        elif stage == 'stop':
            total_time = ticks_ms() - self._start_time
            len_name = 0
            for line in self._time_list:
                step_name,value = line.split(':')
                if len(step_name) > len_name : len_name = len(step_name)
            len_name += 1
            with open ('process_mes.txt', 'w') as f:
                old_time = self._start_time
                for line in self._time_list:
                    step_name,value = line.split(':')
                    step_name += ' '*(len_name-len(step_name))
                    step_time = '{:.0f}'.format(float(value) - old_time)
                    old_time = float(value)
                    f.write(step_name + ': ' + step_time + ' ms\n')
                f.write('-'*(len_name + 10) + '\n')
                step_name = 'total execution time'
                f.write(step_name + ' '*(len_name-len(step_name)) + ': ' + str(total_time) + ' ms\n')
        else:
            self._time_list.append(stage + ':' + str(ticks_ms()))
            self._old_time = ticks_ms()
