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
"""
from uio import StringIO
from sys import print_exception 

class LogAndCount:

    def counters(self, counter_name, add1=False):
        increment = 1 if add1 else 0
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
            
            
    def log_error(self, err_info, more_info=''):
        cpl = ""
        if more_info:
            cpl = ' - ' + self.error_handling(more_info)
        if isinstance(err_info, list):  
            s = StringIO()
            print_exception(err_info, s)
            s1 = s.getvalue().replace('\n', '=+=')
            s2 = s1.split('=+=')
            s3 = s2[1].lstrip()
            s4 = s2[2].lstrip()
            # write and print the error message
            msg = (s3 + ' - ' + s4 + cpl)
        elif isinstance(err_info, str):
            msg = (err_info + cpl)
        else:
            msg = (str(err_info) + cpl)
        msg = msg.replace(':', '->')
        
        return self.counters(msg, True)
    
    def error_handling(self, e):
        
        try:
            s=StringIO()
            print_exception(e, s)  
            s=s.getvalue()
            s=s.split('\n')
            line=s[1].split(',')
            line=line[1]
            error=s[2]
            err=error+line
        except:
            err = None
        return err
        

def main():
    # instantie the class
    count_and_log = LogAndCount()
    
    # test the counters
    counter_name = ['test', 'test1', 'test2', 'test3', 'test4']
    add1 = True
#     print('counters test\n-------------')
    for c_name in counter_name:
        v = count_and_log.counters(c_name, add1)
        add1 = not add1
        
    # test get_and_log_error_info
    err_txt_list = ['error_cpteur_0', 'error_cpteur_1', 'error_cpteur_2']
    for e_txt in err_txt_list:
        count_and_log.log_error(e_txt)
    
    print('\ncounters and errors test\n----------')
    with open('counter.txt', 'r') as f:
        lines = f.readlines()
        for l in lines:
            print(l.replace('\n', ''))
    
if __name__ == '__main__':
    main()