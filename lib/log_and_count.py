#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: log_and_count.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

log errors and manage counters
v0.1.0 : 27.01.2022 --> first prototype
v0.1.1 : 31.01.2022 --> get_and_log_error_info added logic for simple str messages
v0.1.2 : 01.02.2022 --> added automatic management of the counters (if necessary creaate file and new counter)
v0.1.3 : 02.02.2022 --> corection on the function couters
v0.1.4 : 02.02.2022 --> correction on the function log error
"""
from uio import StringIO
from sys import print_exception 

class LogAndCount:
    def get_and_log_error_info(self, err_info, i=0):
        if isinstance(err_info, list): 
            s = StringIO()
            print_exception(err_info, s)
            s1 = s.getvalue().replace('\n', '=+=')
            s2 = s1.split('=+=')
            s3 = s2[1].lstrip()
            s4 = s2[2].lstrip()
            # write and print the error message
            msg = ('pass:' + str(i) + ' --> ' + s3 + ' - ' + s4)
        elif isinstance(err_info, str):
            msg = ('pass:' + str(i) + ' --> ' + str(err_info))
        else:
            msg = ('pass:' + str(i) + ' --> ' + str(err_info))
            
        self.log_error(msg)
        
    def log_error(self, msg):
        # error logging
        try:
            with open ('error.txt', 'a') as f:
                f.write(str(msg) + '\n')
        except:
            with open ('error.txt', 'w') as f:
                f.write(str(msg) + '\n')

    def counters(self, counter_name, add1=False):
        increment = 1 if add1 else 0
#         print(increment)
        try: # test if the file exist, if yes read the data's
            with open ('counter.txt', 'r') as f:
                lines = f.readlines()
        except: # file not exist --> create and initialise the counter to increment value
            with open('counter.txt', 'w') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment
        # the file exist check if the counter exist    
        c_exist = False
        for line in lines:
            c_name, _ = line.split(':')
            if c_name.strip() == counter_name.strip():
                c_exist = True
              
        if c_exist:
            # the counter exist
            if add1:
                # incease and record new value
                with open ('counter.txt', 'w') as f:
                    for line in lines:
                        c_name, c_val = line.split(':')
                        c_val = int(c_val)
                        if c_name.strip() == counter_name.strip():
                            c_val += increment
                            v_ret = c_val
                        f.write(c_name + ':' + str(c_val) + '\n')
                    return v_ret
            else:
                # just return the value
                for line in lines:
                    c_name, c_val = line.split(':')
                    c_val = int(c_val)
                    if c_name == counter_name:
                        return c_val
        else:
            # the counter dont exist so create it and initialise to increment value
            with open('counter.txt', 'a') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment

def main():
    count = LogAndCount()
    counter_name = ['test', 'test1', 'test2', 'test3', 'test4']
    add1 = True
    for c_name in counter_name:
        v = count.counters(c_name, add1)
        print(c_name, add1, v)
        add1 = not add1
    
if __name__ == '__main__':
    main()