#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Using BOARD pin numbering to stay compatible with your Adeept code
ADC_CS  = 11   # Physical pin 11  (BCM 17)
ADC_DIO = 12   # Physical pin 12  (BCM 18)
ADC_CLK = 13   # Physical pin 13  (BCM 27)

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(ADC_CS, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ADC_CLK, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(ADC_DIO, GPIO.OUT, initial=GPIO.LOW)

def destroy():
    GPIO.cleanup()

def getResult():
    """Read 8‑bit value from ADC0832 (Pi‑5‑compatible implementation)."""

    # Start communication
    GPIO.output(ADC_CS, GPIO.LOW)
    GPIO.output(ADC_CLK, GPIO.LOW)

    # Start bit + SGL/DIFF + ODD/SIGN (CH0)
    for bit in (1, 1, 0):
        GPIO.output(ADC_DIO, bit)
        time.sleep(0.000002)
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(0.000002)
        GPIO.output(ADC_CLK, GPIO.LOW)

    # Prepare to read data
    GPIO.setup(ADC_DIO, GPIO.IN)

    # Read MSB first
    dat1 = 0
    for _ in range(8):
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(0.000002)
        dat1 = (dat1 << 1) | GPIO.input(ADC_DIO)
        GPIO.output(ADC_CLK, GPIO.LOW)
        time.sleep(0.000002)

    # Read LSB second (for validation)
    dat2 = 0
    for i in range(8):
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(0.000002)
        dat2 |= GPIO.input(ADC_DIO) << i
        GPIO.output(ADC_CLK, GPIO.LOW)
        time.sleep(0.000002)

    # End communication
    GPIO.setup(ADC_DIO, GPIO.OUT)
    GPIO.output(ADC_CS, GPIO.HIGH)

    return dat1 if dat1 == dat2 else 0
