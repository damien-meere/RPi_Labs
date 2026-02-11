#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# Using BOARD pin numbering to stay compatible with your Adeept code
ADC_CS  = 11   # Physical pin 11  (BCM 17)
ADC_DIO = 12   # Physical pin 12  (BCM 18)
ADC_CLK = 13   # Physical pin 13  (BCM 27)

_DELAY = 0.000002  # 2 microseconds

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(ADC_CS,  GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(ADC_CLK, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(ADC_DIO, GPIO.OUT, initial=GPIO.LOW)

def destroy():
    try:
        GPIO.cleanup()
    except Exception:
        pass

def getResult(channel=0):
    """
    Read 8‑bit value from ADC0832.
    channel = 0 or 1 (default 0). If your LDR is on CH1, call getResult(1).
    """

    if channel not in (0, 1):
        raise ValueError("channel must be 0 or 1")

    # Begin transaction
    GPIO.output(ADC_CS, GPIO.LOW)
    GPIO.output(ADC_CLK, GPIO.LOW)
    time.sleep(_DELAY)

    # Control bits: Start(1), SGL/DIFF(1=single-ended), ODD/SIGN(channel)
    GPIO.setup(ADC_DIO, GPIO.OUT)
    for bit in (1, 1, channel):
        GPIO.output(ADC_DIO, GPIO.HIGH if bit else GPIO.LOW)
        time.sleep(_DELAY)
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(_DELAY)
        GPIO.output(ADC_CLK, GPIO.LOW)
        time.sleep(_DELAY)

    # Switch DIO to input to read data
    GPIO.setup(ADC_DIO, GPIO.IN)

    # Read MSB-first
    dat1 = 0
    for _ in range(8):
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(_DELAY)
        dat1 = (dat1 << 1) | (GPIO.input(ADC_DIO) & 1)
        GPIO.output(ADC_CLK, GPIO.LOW)
        time.sleep(_DELAY)

    # Read LSB-first (validation sample)
    dat2 = 0
    for i in range(8):
        GPIO.output(ADC_CLK, GPIO.HIGH)
        time.sleep(_DELAY)
        dat2 |= (GPIO.input(ADC_DIO) & 1) << i
        GPIO.output(ADC_CLK, GPIO.LOW)
        time.sleep(_DELAY)

    # End transaction and return DIO to idle (output low)
    GPIO.setup(ADC_DIO, GPIO.OUT)
    GPIO.output(ADC_DIO, GPIO.LOW)
    GPIO.output(ADC_CS, GPIO.HIGH)

    return dat1 if dat1 == dat2 else 0

# Optional: quick self-test if you run this file directly
if __name__ == "__main__":
    try:
        setup()
        while True:
            v0 = getResult(0)
            v1 = getResult(1)
            print(f"CH0={v0:3d} | CH1={v1:3d}")
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        destroy()
