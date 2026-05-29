from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import time
import wave
from array import array
from pathlib import Path
from typing import Protocol


class StartInput(Protocol):
    def wait_for_start(self) -> None:
        ...


class VolumeReader(Protocol):
    def read_volume(self) -> int:
        ...


class LedController(Protocol):
    def idle(self) -> None:
        ...

    def countdown(self, step: str) -> None:
        ...

    def main_active(self, progress: float) -> None:
        ...

    def garnish_active(self, progress: float) -> None:
        ...

    def victory(self) -> None:
        ...

    def off(self) -> None:
        ...


class AudioController(Protocol):
    def set_volume(self, volume: int) -> None:
        ...

    def countdown(self, step: str) -> None:
        ...

    def victory(self) -> None:
        ...


class ConsoleStartInput:
    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start

    def wait_for_start(self) -> None:
        if self.auto_start:
            print("[start] auto-start")
            return
        input("Press Enter to start Chef Station session...")


class FixedVolumeReader:
    def __init__(self, volume: int) -> None:
        self.volume = max(0, min(30, volume))

    def read_volume(self) -> int:
        return self.volume


class NullLedController:
    def idle(self) -> None:
        print("[led dry-run] idle warm glow")

    def countdown(self, step: str) -> None:
        print(f"[led dry-run] countdown pulse {step}")

    def main_active(self, progress: float) -> None:
        return

    def garnish_active(self, progress: float) -> None:
        return

    def victory(self) -> None:
        print("[led dry-run] victory flourish")

    def off(self) -> None:
        print("[led dry-run] off")


class BeepAudioController:
    def __init__(self, volume: int = 18) -> None:
        self.volume = max(0, min(30, volume))
        self._aplay = shutil.which("aplay")

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(30, volume))

    def countdown(self, step: str) -> None:
        tones = {"3": 660, "2": 740, "1": 830, "GO": 1046}
        self._play_tone(tones.get(step, 880), 0.18 if step != "GO" else 0.35)

    def victory(self) -> None:
        for hz in (523, 659, 784, 1046, 784, 1046):
            self._play_tone(hz, 0.12)

    def _play_tone(self, hz: int, seconds: float) -> None:
        if not self._aplay:
            print(f"[audio dry-run] {hz}Hz for {seconds:.2f}s")
            return

        sample_rate = 22050
        frame_count = int(sample_rate * seconds)
        amplitude = int(9000 * (self.volume / 30))
        samples = array(
            "h",
            (
                int(amplitude * math.sin(2 * math.pi * hz * (frame / sample_rate)))
                for frame in range(frame_count)
            ),
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            with wave.open(str(tmp_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(samples.tobytes())
            subprocess.run([self._aplay, "-q", str(tmp_path)], check=False)
        finally:
            tmp_path.unlink(missing_ok=True)


class RpiGpioStartInput:
    def __init__(self, pin: int) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install RPi.GPIO on the Raspberry Pi to use GPIO start input") from exc

        self._gpio = GPIO
        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def wait_for_start(self) -> None:
        print(f"[start] waiting for active-LOW button on GPIO{self.pin}")
        was_released = False
        while True:
            pressed = self._gpio.input(self.pin) == self._gpio.LOW
            if not pressed:
                was_released = True
            elif was_released:
                time.sleep(0.03)
                if self._gpio.input(self.pin) == self._gpio.LOW:
                    print("[start] button pressed")
                    while self._gpio.input(self.pin) == self._gpio.LOW:
                        time.sleep(0.01)
                    return
            time.sleep(0.01)


class ADS1115VolumeReader:
    def __init__(self, min_volume: int = 0, max_volume: int = 30) -> None:
        try:
            import board  # type: ignore
            import busio  # type: ignore
            import adafruit_ads1x15.ads1115 as ADS  # type: ignore
            from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Install adafruit-circuitpython-ads1x15 to use the ADS1115 volume knob"
            ) from exc

        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        self._channel = AnalogIn(ads, ADS.P0)
        self.min_volume = min_volume
        self.max_volume = max_volume

    def read_volume(self) -> int:
        ratio = max(0.0, min(1.0, self._channel.voltage / 3.3))
        return int(round(self.min_volume + (self.max_volume - self.min_volume) * ratio))


class NeoPixelLedController:
    def __init__(self, gpio: int, count: int, brightness: float) -> None:
        try:
            import board  # type: ignore
            import neopixel  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install adafruit-circuitpython-neopixel to drive the LED strip") from exc

        pin = getattr(board, f"D{gpio}")
        self._pixels = neopixel.NeoPixel(pin, count, brightness=brightness, auto_write=False)
        self.count = count

    def idle(self) -> None:
        self._fill((28, 10, 0))

    def countdown(self, step: str) -> None:
        colors = {"3": (60, 0, 0), "2": (80, 35, 0), "1": (80, 80, 0), "GO": (0, 90, 18)}
        self._fill(colors.get(step, (60, 60, 60)))
        time.sleep(0.12)
        self.idle()

    def main_active(self, progress: float) -> None:
        red = 45 + int(20 * math.sin(progress * math.pi * 6))
        self._fill((red, 18, 0))

    def garnish_active(self, progress: float) -> None:
        if progress > 0.83:
            self._fill((110, 0, 0) if int(time.monotonic() * 8) % 2 else (0, 0, 0))
        elif progress > 0.66:
            self._fill((95, 50, 0))
        else:
            self._fill((80, 80, 80))

    def victory(self) -> None:
        for offset in range(self.count * 2):
            for index in range(self.count):
                hue = (index + offset) % 6
                color = (
                    (120, 0, 0),
                    (120, 55, 0),
                    (80, 80, 0),
                    (0, 100, 20),
                    (0, 45, 120),
                    (90, 0, 120),
                )[hue]
                self._pixels[index] = color
            self._pixels.show()
            time.sleep(0.025)

    def off(self) -> None:
        self._fill((0, 0, 0))

    def _fill(self, color: tuple[int, int, int]) -> None:
        self._pixels.fill(color)
        self._pixels.show()
