class ConfigParser:
    def __init__(self):
        self.config_dict = {}

    def read(self, filename=None):
        """Read and parse a filename or a list of filenames."""
        with open (filename, 'r') as f:
            content = f.read()
            
        self.config_dict = {line.replace('[','').replace(']',''):{} for line in content.split('\n')\
                if line.startswith('[') and line.endswith(']')
                }
        
        striped_content = [line.strip() for line in content.split('\n')]
        
        for section in self.config_dict.keys():
            start_index = striped_content.index('[%s]' % section)
           
            end_flag = [line for line in striped_content[start_index + 1:] if line.startswith('[')]
            if not end_flag:
                end_index = None
            else:
                end_index = striped_content.index(end_flag[0])
            
            block = striped_content[start_index + 1 : end_index]
            options = [line.split('=')[0].strip() for line in block if '=' in line]
            
            for option in options:
                start_flag = [line for line in block if line.startswith(option) and '=' in line]
                start_index = block.index(start_flag[0])
                end_flag = [line for line in block[start_index + 1:] if '=' in line]
                if not end_flag:
                    end_index = None
                else:
                    end_index = block.index(end_flag[0])
                values = [value.split('=',1)[-1].strip() for value in block[start_index:end_index] if value]
                if not values:
                    values = None
                elif len(values) == 1:
                    values = values[0]
                self.config_dict[section][option] = values

def main():
    f_name = 'config_airsens.txt'
    cp = ConfigParser()
    cp.read(f_name)

    for key, value in cp.config_dict.items():
        print('%s:%s' % (key, value))

if __name__ == '__main__':
    main()
