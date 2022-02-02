#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
file: ble_advertising.py 
imported from https://github.com/micropython/micropython/tree/master/examples/bluetooth/ble_advertising.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/jom52/esp32-airsens

advertising for ble
v0.1.0 : 27.01.2022 --> original version
v0.1.1 : 31.01.2022 --> convert ed into a class and use of ustruct and ubluetooth insted of struct and bluetooth
"""

from micropython import const
import ustruct
import ubluetooth

# Advertising payloads are repeated packets of the following form:
#   1 byte data length (N + 1)
#   1 byte type (see constants below)
#   N bytes type-specific data

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)


class Advertising:
    
    # Generate a payload to be passed to gap_advertise(adv_data=...).
    def advertising_payload(self, limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
        payload = bytearray()

        def _append(adv_type, value):
            nonlocal payload
            payload += ustruct.pack("BB", len(value) + 1, adv_type) + value

        _append(
            _ADV_TYPE_FLAGS,
            ustruct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
        )

        if name:
            _append(_ADV_TYPE_NAME, name)

        if services:
            for uuid in services:
                b = bytes(uuid)
                if len(b) == 2:
                    _append(_ADV_TYPE_UUID16_COMPLETE, b)
                elif len(b) == 4:
                    _append(_ADV_TYPE_UUID32_COMPLETE, b)
                elif len(b) == 16:
                    _append(_ADV_TYPE_UUID128_COMPLETE, b)

        # See org.bluetooth.characteristic.gap.appearance.xml
        if appearance:
            _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

        return payload


    def decode_field(self, payload, adv_type):
        i = 0
        result = []
        while i + 1 < len(payload):
            if payload[i + 1] == adv_type:
                result.append(payload[i + 2 : i + payload[i] + 1])
            i += 1 + payload[i]
        return result


    def decode_name(self, payload):
        n = self.decode_field(payload, _ADV_TYPE_NAME)
        return str(n[0], "utf-8") if n else ""


    def decode_services(self, payload):
        services = []
        for u in self.decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
            services.append(ubluetooth.UUID(ustruct.unpack("<h", u)[0]))
        for u in self.decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
            services.append(ubluetooth.UUID(ustruct.unpack("<d", u)[0]))
        for u in self.decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
            services.append(ubluetooth.UUID(u))
        return services


def demo():
    advert = Advertising()
    payload = advert.advertising_payload(
        name="micropython",
        services=[ubluetooth.UUID(0x181A), ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")],
    )
    print(payload)
    print(advert.decode_name(payload))
    print(advert.decode_services(payload))


if __name__ == "__main__":
    demo()
