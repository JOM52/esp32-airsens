#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: clean_remark.py 

author: jom52
license : GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

delete all remarks and blank lines on the selected python files (.py)
v0.1.0 : 03.02.2022 --> first prototype
v0.1.1 : 16.02.2022 --> 
"""
import os

class CleanUp:
    def clean_up(self, path):
        # list all the files in the directory 'path'
        list_files =  os.listdir(path)
        for file in list_files:
            # work only with python files (.py)
            if file.endswith('py'):
                print(file)
                # read the current file content
                with open (path + file, 'r') as f:
                    lines = f.readlines()
                    
                skip_line = False 
                triple_count = 0
                new_triple = 0
                triple_str = '\"\"\"'
                begin_triple = False
                c_line = 0
                # open the current file to write --> erase the old file
                with open (path + file, 'w') as f:
                    for line in lines:
                        
                        skip_line = False
                        old_triple = new_triple
                        triple_count = line.count(triple_str)
                        new_triple += triple_count
                        
                        if (new_triple % 2) != 0 or triple_count != 0:
                            skip_line = True
                        
                        # check all the condition to reject the line
                        if (not skip_line
                                and not begin_triple
                                and len(line.strip()) != 0
                                and line.strip()[0] != '#'):
                            # all the conditions are ok so write the line in the new file
                            f.write(line)
                            

# test program
def main():
    cu = CleanUp()
    # clean the files in the lib directory
    cu.clean_up('../lib/')
    # and in the root directory
    cu.clean_up('../')
    
if __name__ == '__main__':
    main()