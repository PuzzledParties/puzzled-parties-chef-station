from __future__ import annotations

from pathlib import Path

from .config import MasterConfig
from .controller import ControllerHardware, MasterController
from .hardware import (
    ADS1115VolumeReader,
    BeepAudioController,
    ConsoleStartInput,
    FixedVolumeReader,
    NeoPixelLedController,
    NullLedController,
    RpiGpioStartInput,
)
from .module_bus import DryRunTransport, ModuleBus, UdpLineTransport
from .receipt import make_receipt_printer


def build_controller(config: MasterConfig) -> MasterController:
    if config.dry_run:
        transport = DryRunTransport()
        start_input = ConsoleStartInput(auto_start=config.auto_start)
        volume = FixedVolumeReader(config.fixed_volume)
        leds = NullLedController()
    else:
        transport = UdpLineTransport(config.module_udp_host, config.module_udp_port, config.module_udp_bind_host)
        start_input = RpiGpioStartInput(config.start_button_gpio)
        volume = ADS1115VolumeReader(config.volume_min, config.volume_max)
        leds = NeoPixelLedController(config.led_gpio, config.led_count, config.led_brightness)

    audio = BeepAudioController(config.fixed_volume)
    printer = make_receipt_printer(
        config.printer_mode,
        Path(config.receipt_output_dir),
        usb_vendor_id=config.printer_usb_vendor_id,
        usb_product_id=config.printer_usb_product_id,
        network_host=config.printer_network_host,
        network_port=config.printer_network_port,
        dry_run=config.dry_run,
    )
    hardware = ControllerHardware(
        start_input=start_input,
        volume=volume,
        leds=leds,
        audio=audio,
        printer=printer,
    )
    return MasterController(config=config, bus=ModuleBus(transport), hardware=hardware)
