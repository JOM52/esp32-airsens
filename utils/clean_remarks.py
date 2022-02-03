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
                    
                triple_found = False # for the """ remarks """
                # open the current file to write --> erase the old file
                with open (path + file, 'w') as f:
                    for line in lines:
                    # check tif the line must be writed in the new file
                        if line.strip()[:3] == '\"\"\"' and line.strip()[-3:] != '\"\"\"':
                            triple_found = not triple_found
                        elif line.strip()[-3:] == '\"\"\"':
                            triple_found = False
                        # check all the condition to reject the line
                        if (not triple_found
                                and len(line.strip()) != 0
                                and line.strip()[0] != '#'
                                and line.strip()[:3] != '\"\"\"'
                                and line.strip()[-3:] != '\"\"\"'):
                            # all the conditions are ok so write the line in the new file
                            f.write(line)

# test program
def main():
    cu = CleanUp()
    # clean the files in the current directory
    cu.clean_up('../')
    # clean the files in the lib directory
    cu.clean_up('../lib/')
    
if __name__ == '__main__':
    main()