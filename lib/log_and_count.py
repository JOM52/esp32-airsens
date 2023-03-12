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
v0.1.5 : 05.02.2022 --> modified log and count to log the count of the same error
v0.1.6 : 08.02.2022 --> correction of error introduced in v0.1.5
v0.1.7 : 08.02.2022 --> no more file error.txt. All counter in are now in the file counter.txt
v0.1.8 : 23.02.2022 --> addd file name and line number on error
v0.1.9 : 22.06.2022 --> log_error modified for 'more_info'
v0.1.10 : 27.06.2022 --> log_error modified presnetations of recorded data
v0.1.11 : 27.06.2022 --> log_error modified for display cpl correctly
-----------------------------------------------------------------------------------------
v0.2.0 : 07.09.2022 --> log_error modified for display line error number ---> no more compatible with previous versions
-----------------------------------------------------------------------------------------
v0.3.0 : 12.03.2023 --> ajout de la date et heure de la survenance d'une erreur
"""
from sys import print_exception 
from io import StringIO
from utime import localtime
counter_file_name = 'counter.txt'
error_file_name = 'errors.txt'

class LogAndCount:

    def counters(self, counter_name, add1=False):
        increment = 1 if add1 else 0
        try: # test if the file exist, if yes read the data's
            with open (counter_file_name, 'r') as f:
                lines = f.readlines()
                # the file exist check if the counter exist    
                c_exist = False
                for line in lines:
                    try:
                        c_name, _ = line.split(':')
                        if c_name.strip() == counter_name.strip():
                            c_exist = True
                    except:
                        pass
        except: # file do not exist --> create and initialise the counter
            with open(counter_file_name, 'w') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment
              
        if c_exist:
            # the counter exist
            if add1:
                # incease and record new value
                with open (counter_file_name, 'w') as f:
                    for line in lines:
                        try:
                            c_name, c_val = line.split(':')
                            c_val = int(c_val)
                            if c_name.strip() == counter_name.strip():
                                c_val += increment
                                v_ret = c_val
                            f.write(c_name + ':' + str(c_val) + '\n')
                        except:
                            pass
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
            with open(counter_file_name, 'a') as f:
                f.write(counter_name + ':' + str(increment) + '\n')
                return increment
            
            
    def log_error(self, info, err_info='', to_print = False):
        
        if err_info is not None:
            err_info = err_info.replace(':','->')
        msg = self.get_formated_time() + ' ' + info + ' - ' + err_info if err_info else info
        
        try: # test if the file exist, if yes read the data's
            with open (error_file_name, 'a') as f:
                f.write(msg + '\n')
        except: # file not exist --> create and initialise the counter to increment value
            with open(error_file_name, 'w') as f:
                if msg is not str:
                    msg = str(msg)
                f.write(msg + '\n')
        if to_print: print(msg)
        self.counters('error', True)

    def error_detail(self, err_info):
        s=StringIO()
        print_exception(err_info, s)  
        s=s.getvalue()
        s=s.split('\n')                                                                   
        line=s[1].split(',')
        line=line[1];
        error=s[2]
        err=error+line;
        return err

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

def main():
    logandcount = LogAndCount()
    
    try:
        a=1/0
    except Exception as err:
        logandcount.log_error('test division par zero', logandcount.error_detail(err), to_print = True)
        
    print('test counters', logandcount.counters('test counters', True))

if __name__ == '__main__':
    main()
