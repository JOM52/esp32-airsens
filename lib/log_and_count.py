#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: log_and_count.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

log errors and manage counters
v0.1.0 : 27.01.2022 --> first prototype
"""
from uio import StringIO
from sys import print_exception
class LogAndCount:
    def get_and_log_error_info(self, err_info, i):
        s = StringIO()
        print_exception(err_info, s)
        s1 = s.getvalue().replace('\n', '=+=')
        s2 = s1.split('=+=')
        s3 = s2[1].lstrip()
        s4 = s2[2].lstrip()
        
        # write and print the error message
        msg = ('pass:' + str(i) + ' --> ' + s3 + ' - ' + s4)
        self.log_error(msg)
        
    def log_error(self, msg):
        # error logging
        try:
            with open ('error.txt', 'a') as f:
                f.write(str(msg) + '\n')
        except:
            with open ('error.txt', 'w') as f:
                f.write(str(msg) + '\n')

    def counters(self, counter_name, increase=False):
        with open ('counter.txt', 'r') as f:
            lines = f.readlines()
        if increase:
            with open ('counter.txt', 'w') as f:
                for line in lines:
                    c_name, c_val = line.split(':')
                    c_val = int(c_val)
                    if c_name.strip() == counter_name.strip():
                        c_val += 1
                    f.write(c_name + ':' + str(c_val) + '\n')
                return c_val
        else:
            for line in lines:
                c_name, c_val = line.split(':')
                c_val = int(c_val)
                if c_name == counter_name:
                    return c_val
