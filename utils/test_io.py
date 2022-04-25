from machine import Pin
from time import sleep

PPK_0_PIN = 5
PPK_1_PIN = 25
PPK_2_PIN = 32
PPK_3_PIN = 26
PPK_4_PIN = 33
PPK_5_PIN = 4

PPK_0 = Pin(PPK_0_PIN, Pin.OUT)
PPK_1 = Pin(PPK_1_PIN, Pin.OUT)
PPK_2 = Pin(PPK_2_PIN, Pin.OUT)
PPK_3 = Pin(PPK_3_PIN, Pin.OUT)
PPK_4 = Pin(PPK_4_PIN, Pin.OUT)
PPK_5 = Pin(PPK_5_PIN, Pin.OUT)

PPK_0.off()
PPK_1.off()
PPK_2.off()
PPK_3.off()
PPK_4.off()
PPK_5.off()

sleep_time = 0.5
while True:
    PPK_0.on()
    sleep(sleep_time)
    PPK_0.off()
    
    PPK_1.on()
    sleep(sleep_time)
    PPK_1.off()
    
    PPK_2.on()
    sleep(sleep_time)
    PPK_2.off()
    
    PPK_3.on()
    sleep(sleep_time)
    PPK_3.off()
    
    PPK_4.on()
    sleep(sleep_time)
    PPK_4.off()
    
    