#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: airsens_utils.py 

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

utils for airsens app

v0.1.0 : 26.01.2022 --> first prototype
"""

def get_and_log_error_info(err_info, i):
    
    s = StringIO()
    print_exception(err_info, s)
    s1 = s.getvalue().replace('\n', '=+=')
    s2 = s1.split('=+=')
    s3 = s2[1].lstrip()
    
    # write and print the error message
    msg = ('pass:' + str(i) + ' --> ' + s3)
    log_error(msg)
    
def log_error(msg):
    # error logging
    try:
        with open ('error.txt', 'a') as f:
            f.write(str(msg) + '\n')
    except:
        with open ('error.txt', 'w') as f:
            f.write(str(msg) + '\n')
            
def time_mesurement(process_info, t_old):
    t = ticks_ms() - t_old
    with open ('process_mes.txt', 'a') as f:
        if process_info == 'total':
            f.write('---------------\n')
        f.write(process_info + ' ---> ' + str(t) + '\n')
            
def get_and_increase_pass_counter():
    # load the pass counter value from file
    try:
        with open ('index.txt', 'r') as f:
            i = int(f.readline()) + 1
    except:
        i = 1
    with open ('index.txt', 'w') as f:
        f.write(str(i))
    return i
            
def get_and_increase_error_counter():
    # load the pass counter value from file
    try:
        with open ('err_count.txt', 'r') as f:
            i = int(f.readline()) + 1
    except:
        i = 1
    with open ('err_count.txt', 'w') as f:
        f.write(str(i))
    return i
            
def get_error_counter():
    # load the pass counter value from file
    try:
        with open ('err_count.txt', 'r') as f:
            i = int(f.readline())
    except:
        i = 1
    return i
