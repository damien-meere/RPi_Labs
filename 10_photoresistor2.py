#!/usr/bin/env python3
# Replacement for ADC0832 version -- works with PCF8591 used in Adeept kits

import smbus
import time

# PCF8591 info
I2C_BUS = 1
PCF8591_ADDR = 0x48
CHAN_A0 = 0x40  # Channel 0

bus = smbus.SMBus(I2C_BUS)

def init():
    # No setup needed for PCF8591, but we keep this for compatibility
    print("PCF8591 ready")

def getValue():
    # Select channel A0
    bus.write_byte(PCF8591_ADDR, CHAN_A0)
    bus.read_byte(PCF8591_ADDR)       # Dummy read required
    value = bus.read_byte(PCF8591_ADDR)
    return value

def loop():
    while True:
        raw = getValue()              # 0–255
        res = raw - 80                # mimic your original logic

        if res < 0:
            res = 0
        if res > 100:
            res = 100

        print(f"res = {res}")
        time.sleep(0.2)

def destroy():
    bus.close()
    print("The end!")

if __name__ == '__main__':
    init()
    try:
        loop()
    except KeyboardInterrupt:
        destroy()