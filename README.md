# esp32-airsens
Air sensor on ESP32 with Micropython BLE

## description

This project aims to produce wireless sensors for environmental data (temperature, humidity, atmospheric pressure and if possible air quality) with data transmission by bluetooth to an MQTT broker then in a database.

At a defined time interval, the sensors wake up from deep sleep, measure the values, connect to the central, transmit the measured values and then go back to deep sleep mode.

The expected autonomy on a lithium-ion battery of 4000 mAh should reach a year.

Data visualization will be done later with a standard application (jeedom, domoticz, ...)

### sensors:

the sensors are made with an ESP32 microcontroller and can be powered by battery or by USB. They transmit the data to a central also realized with an ESP32 by a bluetooth low energy communication (BLE). The sensors connect to the server, transmit the data and then go into deepsleep mode (very low energy consumption) for a period chosen by the user (recommended between 5 and 10 minutes)

### central

the *central* is always in listening mode (advertising). It accepts the connections of the sensors, receives the data and then transmits them to MQTT by WIFI. The *central* must be powered by the USB port because it is never put to sleep.

### raspberry pi 4

the RPI performs several functions:

- runs the MQTT broker server
- run the Maria db database
- runs the home automation solution server (jeedom, domoticz, ...)

## schematic diagram

<img src="C:\Users\jmetr\OneDrive\technique\_projets\esp32-micropython\esp32-jmb-sensor\doc\schema de principe.png" alt="schema de principe" style="zoom: 45%;" />

## programs in ESP32

### ESP32 sensor:

*  **airsens_ble_scan.py**: this program scans the bluetooth network to find all the *ble_central* whose name starts with *jmb_* and lets the user choose the server they want to work with.
*  **airsens_ble_sensor.py**: this program controls the BME280 or BME689 environmental data sensors and transmits the measured data to the central unit whose address and name have been recorded in the *config.txt* file by the*jmb_ble_scan.py* program.
*  **config.txt**: this file contains the data necessary for connecting the sensor to the central unit. It is created or modified by the program *jmb_ble_scan.py*
*  **index.txt**: this file is used to keep a functional pass counter even when the sensor ESP32 goes into *deepsleep* mode
*  **airsens_ble_main.py**: this file is used to keep a functional pass counter even when the sensor ESP32 goes into *deepsleep* mode useful during development and debugging phases.
*  **directory <lib>** : contains the libraries useful for the operation of the programs

### ESP32 central:

*  **airsens_ble_central.py**: this program functions as a central server for the sensors. It is still in *advertising* mode and waits for connections from the sensors, receives their data and transmits them to the server *mqt* by wifi.
*  **MQTT publisher**:  
*  **directory <lib>** : contains the libraries useful for the operation of the programs

### RPI4

- **MQTT broker**: 

- **MQTT subscriber**:

- **python prg mqtt-db**:

- **Maria db**:

  

  
