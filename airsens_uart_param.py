import os

def put_param_in_sensor_prg(sce_file, param, value):
    
#     dest_file = 'dest_' + sce_file
#     f_dest = open(sce_file, 'w')  
    with open (sce_file, 'r') as f_sce:
        content= f_sce.readlines()
    with open (sce_file, 'w') as f_dest:
        for l_sce in content:
            if param in l_sce:
                if l_sce.index(param) == 0:
                    print(l_sce)
                    parts = l_sce.replace(' ' , '').split('=')
                    print(parts)
                    parts[1] = "'" + value + "'\r\n"
                    print(parts)
                    txt = ' = '.join(parts)
                    print(txt)
                    f_dest.write(txt)
            else:
                f_dest.write(l_sce)
        
def main():
    put_param_in_sensor_prg('sens.py', 'PARAM_UART_ADDR_x', 'bliblibli')
    
if __name__ == '__main__':
    main()
        
    
