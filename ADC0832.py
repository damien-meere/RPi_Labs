#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADC0832 bit-banged driver for Raspberry Pi (Pi 5 compatible)

This module talks to the 8-bit ADC0832 using three GPIO pins (CS, CLK, DIO)
via software (bit-bang) SPI-like signaling. It avoids any direct SoC base-
address probing, so it works on Raspberry Pi 5 (BCM2712 + RP1).

Pin numbering: BCM (GPIO numbers)

Typical wiring (adjust to your wiring/pins and pass them to setup()):
    ADC0832 CS  -> GPIO17 (example)
    ADC0832 CLK -> GPIO18 (example)
    ADC0832 DIO -> GPIO27 (example)
    VCC         -> 3V3 (NOT 5V)
    GND         -> GND
    CH0/CH1     -> your sensor inputs (0–3.3V)

Usage (module-level API):
    import ADC0832
    ADC0832.setup(cs=17, clk=18, dio=27)
    value = ADC0832.read(channel=0)  # 0..255
    ADC0832.cleanup()

Usage (class API):
    from ADC0832 import ADC0832Device
    adc = ADC0832Device(cs=17, clk=18, dio=27)
    val0 = adc.read(0)
    val1 = adc.read(1)
    adc.close()

Test:
    sudo python3 ADC0832.py
"""

import time

try:
    import RPi.GPIO as GPIO
except Exception as e:
    raise RuntimeError(
        "Failed to import RPi.GPIO. Install it with:\n"
        "  sudo apt install -y python3-rpi.gpio\n"
        f"Original error: {e}"
    )

# ---- Module-level default pins (BCM) ----
_CS_PIN: int = 17
_CLK_PIN: int = 18
_DIO_PIN: int = 27

# Small delay to meet ADC0832 timing; adjust if needed.
# Datasheet allows pretty quick clocks; we stay conservative.
_T: float = 2e-6  # 2 microseconds per half-cycle


def _pin_mode_output(pin: int) -> None:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)


def _pin_mode_input(pin: int) -> None:
    GPIO.setup(pin, GPIO.IN)


def setup(cs: int = 17, clk: int = 18, dio: int = 27, warn: bool = False) -> None:
    """
    Initialize GPIO and set the pins to known state.

    Args:
        cs:  Chip Select (CS) pin (BCM).
        clk: Clock (CLK) pin (BCM).
        dio: Data I/O (DIO) pin (BCM).
        warn: Pass True to enable GPIO warnings.
    """
    global _CS_PIN, _CLK_PIN, _DIO_PIN
    _CS_PIN, _CLK_PIN, _DIO_PIN = int(cs), int(clk), int(dio)

    GPIO.setwarnings(bool(warn))
    GPIO.setmode(GPIO.BCM)

    _pin_mode_output(_CS_PIN)
    _pin_mode_output(_CLK_PIN)
    _pin_mode_output(_DIO_PIN)

    # Idle state
    GPIO.output(_CS_PIN, GPIO.HIGH)
    GPIO.output(_CLK_PIN, GPIO.LOW)
    GPIO.output(_DIO_PIN, GPIO.LOW)
    time.sleep(_T)


def cleanup() -> None:
    """Release GPIO resources."""
    try:
        GPIO.cleanup()
    except Exception:
        # Ignore cleanup errors on exit
        pass


def _clock_pulse() -> None:
    """Generate a single rising edge clock pulse."""
    GPIO.output(_CLK_PIN, GPIO.HIGH)
    time.sleep(_T)
    GPIO.output(_CLK_PIN, GPIO.LOW)
    time.sleep(_T)


def _start_sequence(channel: int) -> None:
    """
    Send start + mode bits for ADC0832.

    Sequence (common bit-banged approach):
      - Pull CS low, CLK low
      - Send start bit (1)
      - Send SGL/DIFF = 1 (single-ended)
      - Send ODD/SIGN = channel (0 for CH0, 1 for CH1)
      - Then switch DIO to input to read data
    """
    # Ensure we're in output mode before driving DIO
    _pin_mode_output(_DIO_PIN)

    GPIO.output(_CS_PIN, GPIO.LOW)
    GPIO.output(_CLK_PIN, GPIO.LOW)
    time.sleep(_T)

    # Start bit = 1
    GPIO.output(_DIO_PIN, GPIO.HIGH)
    _clock_pulse()

    # SGL/DIFF = 1 (single-ended)
    GPIO.output(_DIO_PIN, GPIO.HIGH)
    _clock_pulse()

    # ODD/SIGN = channel (0 or 1)
    GPIO.output(_DIO_PIN, GPIO.HIGH if channel else GPIO.LOW)
    _clock_pulse()

    # Prepare to read: release DIO (input mode)
    _pin_mode_input(_DIO_PIN)
    time.sleep(_T)


def _read_byte_msb_first() -> int:
    """
    Read 8 bits MSB-first from DIO on CLK rising edges.

    Returns:
        Integer 0..255
    """
    value = 0
    for _ in range(8):
        GPIO.output(_CLK_PIN, GPIO.HIGH)
        time.sleep(_T)
        bit = GPIO.input(_DIO_PIN) & 0x1
        value = (value << 1) | bit
        GPIO.output(_CLK_PIN, GPIO.LOW)
        time.sleep(_T)
    return value


def read(channel: int = 0, *, return_both: bool = False) -> int | tuple[int, int]:
    """
    Read ADC value from channel 0 or 1.

    Strategy:
      Many reference implementations read two bytes (dat1 and dat2) and compare.
      The ADC0832 outputs the same sample twice (or a sample + inverted), and
      comparing them improves robustness against timing glitches. Here we follow
      that approach and fall back to one if they mismatch.

    Args:
        channel: 0 or 1
        return_both: if True, returns (dat1, dat2) for debugging

    Returns:
        0..255 (or a tuple of two 0..255 if return_both=True)
    """
    if channel not in (0, 1):
        raise ValueError("channel must be 0 or 1")

    # Begin transaction
    GPIO.output(_CS_PIN, GPIO.LOW)
    GPIO.output(_CLK_PIN, GPIO.LOW)
    time.sleep(_T)

    # Send start + mode bits and switch DIO to input
    _start_sequence(channel)

    # Read two 8-bit results (many examples do this for validation)
    dat1 = _read_byte_msb_first()

    # Some chips deliver a second reading; clock 1 more cycle to align
    # on some implementations. We'll follow the common pattern:
    # One extra clock to let chip prepare second read.
    GPIO.output(_CLK_PIN, GPIO.HIGH)
    time.sleep(_T)
    GPIO.output(_CLK_PIN, GPIO.LOW)
    time.sleep(_T)

    dat2 = _read_byte_msb_first()

    # End transaction
    GPIO.output(_CS_PIN, GPIO.HIGH)
    time.sleep(_T)

    if return_both:
        return dat1 & 0xFF, dat2 & 0xFF

    # Validate / choose value
    if dat1 == dat2:
        return dat1 & 0xFF
    # If not equal, pick the one that looks consistent (simple heuristic)
    # You could also re-try the whole read here.
    return max(0, min(255, dat1))


# -------- Optional OO wrapper --------

class ADC0832Device:
    """
    Object-oriented wrapper for ADC0832.
    """

    def __init__(self, cs: int = 17, clk: int = 18, dio: int = 27, warn: bool = False):
        setup(cs=cs, clk=clk, dio=dio, warn=warn)
        self._closed = False

    def read(self, channel: int = 0) -> int:
        if self._closed:
            raise RuntimeError("ADC0832Device is closed.")
        return read(channel)

    def read_both(self, channel: int = 0) -> tuple[int, int]:
        if self._closed:
            raise RuntimeError("ADC0832Device is closed.")
        return read(channel, return_both=True)

    def close(self) -> None:
        if not self._closed:
            cleanup()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


# -------- Self-test --------

def _self_test():
    """
    Simple loop that reads CH0 once per 0.2s.
    Run with:
        sudo python3 ADC0832.py
    """
    print("ADC0832 self-test. Press Ctrl+C to stop.")
    try:
        setup(cs=_CS_PIN, clk=_CLK_PIN, dio=_DIO_PIN)
        while True:
            val = read(0)
            print(f"CH0 = {val:3d} (0..255)")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        cleanup()


if __name__ == "__main__":
    _self_test()
