# acquisitions
SENSOR_LOCATION = 'Sensor' 
T_DEEPSLEEP_MS = 15000
# sensor
# SENSOR_TYPE = 'bme280'
SENSOR_TYPE = 'hdc1080'
# power supply
ON_BATTERY = True
UBAT_100 = 4.2
UBAT_0 = 3.2
# I2C hardware config
BME_SDA_PIN = 21
BME_SCL_PIN = 22
# analog voltage measurement
R1 = 977000 # first divider bridge resistor
R2 = 312000 # second divider bridge resistor
ADC1_PIN = 35 # Measure of analog voltage (ex: battery voltage following)
#averaging of measurements
AVERAGING_BAT = 5
AVERAGING_BME = 5
# ESP-now
PROXY_MAC_ADRESS = b'<a\x05\rg\xcc'


