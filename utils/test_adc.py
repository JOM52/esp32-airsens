from machine import Pin, ADC
from time import sleep

R1 = 100e3 # first divider bridge resistor
R2 = 33e3 # second divider bridge resistor
DIV = R2 / (R1 + R2) # (R2 / R1 + R2) -> V_meas = V(R1 + R2); V_adc = V(R2)  
ADC1_PIN = 35

pot = ADC(Pin(ADC1_PIN))            
pot.atten(ADC.ATTN_6DB)
pot.width(ADC.WIDTH_12BIT)

while True:
    val = 0
    for a in range(10):
        val += pot.read() * (1.95 / 4095) / DIV 
    val = val /10
    print(round(val, 2), "V ")
    sleep(0.5)

