import asyncio
import sys
import threading
import time

import blinker
from loguru import logger

from g13lib.apps.davinci_resolve import DavinciInputManager
from g13lib.apps.general import GeneralManager
from g13lib.apps.vscode import VSCodeInputManager
from g13lib.device.g13_input import G13DeviceInputManager
from g13lib.device.g13_output import G13DeviceOutputManager
from g13lib.device.g13_usb_device import FatalG13USBError, G13USBDevice, G13USBError
from g13lib.input_manager import EndProgram
from g13lib.monitors.current_app import AppMonitor


async def main(stop_event: threading.Event | None = None):

    # load all the things that listen for signals
    # probably this should be more configurable
    # and allow for reload of application managers

    usb_device_manager = G13USBDevice()

    device_input_manager = G13DeviceInputManager(usb_device_manager)
    device_output_manager = G13DeviceOutputManager(usb_device_manager)

    # we're trying to avoid USB errors on startup
    # if we try to read too soon after opening the device
    # we seek to get spurious I/O and Permission Denied errors
    # so just wait a bit

    time.sleep(0.5)  # use a blocking sleep here to be sure nothing happens too soon

    _listeners = [
        device_input_manager,
        device_output_manager,
        DavinciInputManager(),
        VSCodeInputManager(),
        AppMonitor(),
        GeneralManager(),
    ]
    logger.debug("Initialized {} listeners", len(_listeners))

    try:

        # Run core loops and periodic tasks concurrently
        async with asyncio.TaskGroup() as tg:
            tg.create_task(read_data_loop(device_input_manager, stop_event))
            for listener in _listeners:
                if hasattr(listener, "start_tasks"):
                    logger.debug("Starting tasks for {}", listener.__class__.__name__)
                    listener.start_tasks(tg)
            blinker.signal("release_focus").send()
    except* EndProgram:
        blinker.signal("g13_clear_status").send()
        blinker.signal("g13_print").send("That's all!\n \n ")
        logger.success("Exiting...")

    finally:
        logger.success("Closing device manager...")
        usb_device_manager.close()


async def read_data_loop(
    device_manager: G13DeviceInputManager, stop_event: threading.Event | None = None
):
    """Currently this is a loop that reads data from the USB device."""
    # probably we should be using an interrupt?
    error_count = 0
    while True:
        if stop_event and stop_event.is_set():
            raise EndProgram()
        if error_count > 5:
            # give up
            raise EndProgram()

        # check for input every 1ms
        await asyncio.sleep(0.001)

        # read any data waiting for us at the device
        return_value = await device_manager.get_codes()

        if isinstance(return_value, FatalG13USBError):
            logger.error("Fatal USB Error: {}", return_value)

            raise EndProgram()
        if isinstance(return_value, G13USBError):
            error_count += 1
            logger.error("USB Error: {}", return_value)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
