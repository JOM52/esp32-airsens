class ConfigParser:
    
    def __init__(self):
        self.config_dict = {}
        
    def get(self, section, option):
        """Get value of a givenoption in a given section."""
        if not self.has_section(section) \
                or not self.has_option(section,option):
                    raise
        return self.config_dict[section][option]

    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        to_return = [section for section in self.config_dict.keys() if not section in "DEFAULT"]
        return to_return

    def add_section(self, section):
        """Create a new section in the configuration."""
        self.config_dict[section] = {}

    def has_section(self, section):
        """Indicate whether the named section is present in the configuration."""
        if section in self.config_dict.keys():
            return True
        else:
            return False

    def add_option(self, section, option, value):
        """Create a new option in the configuration."""
        if self.has_section(section) and not option in self.config_dict[section]:
            self.config_dict[section][option] = value
        else:
            raise

    def options(self, section):
        """Return a list of option names for the given section name."""
        if not section in self.config_dict:
            raise
        return self.config_dict[section].keys()

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

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        if not section in self.config_dict:
            raise
        if option in self.config_dict[section].keys():
            return True
        else:
            return False

    def write(self, filename = None, fp = None):
        """Write an .ini-format representation of the configuration state."""
        if not fp and not filename:
            print("ERROR : no filename and no fp")
            raise
        elif not fp and filename:
            fp = open(filename,'w')

        for section in self.config_dict.keys():
            fp.write('[%s]\n' % section)
            for option in self.config_dict[section].keys():
                fp.write('\n%s =' % option)
                values = self.config_dict[section][option]
                if type(values) == type([]):
                    fp.write('\n    ')
                    values = '\n    '.join(values)
                else:
                    fp.write(' ')
                fp.write(values)
                fp.write('\n')
            fp.write('\n')


    def remove_option(self, section, option):
        """Remove an option."""
        if not self.has_section(section) \
                or not self.has_option(section,option):
                    raise
        del self.config_dict[section][option]

    def remove_section(self, section):
        """Remove a file section."""
        if not self.has_section(section):
            raise
        del self.config_dict[section]

def main():
    f_name = 'config_airsens.txt'
    cp = ConfigParser()
    cp.read(f_name)
    cp.add_option('MQTT', 'USERNAME', 'jmb')
    cp.write(f_name)

    for key, value in cp.config_dict.items():
        print('%s:%s' % (key, value))
    print()
    
    print(cp.get('MQTT', 'TOPIC'))
    print(float(cp.get('SENSOR', 'UBAT_0')))

if __name__ == '__main__':
    main()
