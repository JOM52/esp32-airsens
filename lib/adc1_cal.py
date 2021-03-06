from machine import ADC, mem32

# Constant from
# https://github.com/espressif/esp-idf/blob/master/components/soc/esp32/include/soc/soc.h
_DR_REG_EFUSE_BASE      = const(0x3ff5A000)

# Constants from 
# https://github.com/espressif/esp-idf/blob/master/components/soc/esp32/include/soc/efuse_reg.h
_EFUSE_ADC_VREF         = const(0x0000001F)
_EFUSE_BLK0_RDATA4_REG  = (_DR_REG_EFUSE_BASE + 0x010)

# Constants from
# esp_adc_cal_esp32.c
_ADC_12_BIT_RES         = const(4096)
_LIN_COEFF_A_SCALE      = const(65536)
_LIN_COEFF_A_ROUND      = const(32768) # LIN_COEFF_A_SCALE/2
_ADC1_VREF_ATTEN_SCALE  = [57431, 76236, 105481]
_ADC1_VREF_ATTEN_OFFSET = [75, 78, 107]
_VREF_REG               = _EFUSE_BLK0_RDATA4_REG
_VREF_OFFSET            = const(1100)
_VREF_STEP_SIZE         = const(7)
_VREF_FORMAT            = const(0)
_VREF_MASK              = const(0x1F)


#################################################################################
# ADC1Cal class - ADC voltage output using V_ref calibration value and averaging
#################################################################################
class ADC1Cal(ADC):
    """
    Extension of ADC class for using V_ref calibration value and averaging

    Attributes:
        name (string):      instance name (for debugging)
        _pin (int):         ADC input pin no.
        _div (float):       voltage divider (V_in = V_meas * div)
        _width (int):       encoded width of ADC result (0...3)
        _samples (int):     number of ADC samples for averaging
        vref (int):         ADC reference voltage in mV (from efuse calibration data or supplied by programmer)
        _coeff_a (float):   conversion function coefficient 'a'
        _coeff_b (float):   conversion function coefficient 'b'
    """
    def __init__(self, pin, div, vref=None, samples=10, name=""):
        """
        The constructor for Battery class.

        Parameters:
            pin (machine.Pin):      ADC input pin
            div (float):            voltage divider (V_in = V_meas * div)
            vref (int):             reference voltage (optionally supplied by programmer)
            samples (int):          number of ADC samples for averaging
            name (string):          instance name
        """
        super().__init__(pin)
        self.name     = name
        self._div     = div
        self._width   = 3
        self._atten   = None
        self._samples = samples
        self.vref     = self.read_efuse_vref() if (vref is None) else vref
        print('self.vref:', self.vref)

    def atten(self, attenuation):
        """
        Select attenuation of input signal
        
        Parameter identical to ADC.atten()
        
        Currently ADC.ATTN_11DB is not supported!

        Parameters:
            attenuation (int): ADC.ATTN_0DB / ADC.ATTN_2_5DB / ADC.ATTN_6DB /  ADC.ATTN_11DB
        """        
        assert (attenuation != ADC.ATTN_11DB), "Currently ADC.ATTN_11DB is not supported!"
        super().atten(attenuation)
        self._coeff_a = self.vref * _ADC1_VREF_ATTEN_SCALE[attenuation] / _ADC_12_BIT_RES
        self._coeff_b = _ADC1_VREF_ATTEN_OFFSET[attenuation]
        self._atten = attenuation
        
    def width(self, adc_width):
        """
        Select bit width of conversion result
        
        Parameter identical to ADC.width()

        Parameters:
            adc_width (int): ADC.WIDTH_9BIT / ADC.WIDTH_10BIT / BITADC.WIDTH_11BIT / ADC.WIDTH_12BIT
        """        
        assert (adc_width >= 0 and adc_width < 4), "Expecting ADC_WIDTH9 (0), ADC_WIDTH10 (1), ADC_WIDTH11 (2), or ADC_WIDTH (3)"
        super().width(adc_width)
        self._width = adc_width
            
    def read_efuse_vref(self):
        """
        Read V_ref calibration value from efuse (i.e. read SOC hardware register)

        Returns:
            int: calibrated ADC reference voltage (V_ref) in mV
        """        
        # eFuse stores deviation from ideal reference voltage
        ret = _VREF_OFFSET  # Ideal vref
        
        # GET_REG_FIELD():
        # https://github.com/espressif/esp-idf/blob/master/components/soc/esp32/include/soc/soc.h
        # Bit positions:
        # https://github.com/espressif/esp-idf/blob/master/components/soc/esp32/include/soc/efuse_reg.h
        # EFUSE_RD_ADC_VREF : R/W ;bitpos:[12:8] ;default: 5'b0
        bits = (mem32[_VREF_REG] >> 8) & _VREF_MASK
        ret += self.decode_bits(bits, _VREF_MASK, _VREF_FORMAT) * _VREF_STEP_SIZE
        
        return ret # ADC Vref in mV

    def decode_bits(self, bits, mask, is_twos_compl):
        """
        Decode bit value from two's complement or sign-magnitude to integer

        Parameters:
            bits (int):                bit-field value
            mask (int):                bit mask
            is_twos_complement (bool): True - two's complement / False: sign-magnitude
            
        Returns:
            int: decoded value
        """      
        if (bits & ~(mask >> 1) & mask): # Check sign bit (MSB of mask)
            # Negative
            if (is_twos_compl):
                ret = -(((~bits) + 1) & (mask >> 1))  # 2's complement
            else:
                ret = -(bits & (mask >> 1))     # Sign-magnitude
        else: 
            # Positive
            ret = bits & (mask >> 1)
    
        return ret

    
    @property
    def voltage(self):
        """
        Get voltage measurement [mV].

        Returns:
            float: voltage [mV]
        """
        assert (self._atten is not None), "Currently ADC.ATTN_11DB is not supported!"
        
        raw_val = 0
        
        # Read and accumulate ADC samples
        for i in range(self._samples):
            raw_val += self.read()
        # Calculate average
        raw_val = int(round(raw_val / self._samples))
        
        # Extend result to 12 bits (required by calibration function)
        raw_val <<= (3 - self._width)
        
        # Apply calibration function
        voltage = (((self._coeff_a * raw_val) + _LIN_COEFF_A_ROUND) / _LIN_COEFF_A_SCALE) + self._coeff_b
        
        # Apply external input voltage divider
        voltage = voltage / self._div
        
        return voltage

    
    def __str__(self):
        
        _atten = ["0dB", "2.5dB", "6dB"] #, "11dB"]
        if (self.name != ""):
            name_str = "Name: {} ".format(self.name)
        else:
            name_str = ""
        
        raw_val = self.read()
        
        return ("{} width: {:2}, attenuation: {:>5}, raw value: {:4}, value: {}"
                .format(name_str, 9+self._width, _atten[self._atten], raw_val, self.voltage))
