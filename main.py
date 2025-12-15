import time

import blinker
from loguru import logger

from g13lib.apps.davinci_resolve import DavinciInputManager
from g13lib.device_manager import G13Manager, G13USBError
from g13lib.input_manager import EndProgram, GeneralManager
from g13lib.monitors.current_app import AppMonitor


def read_data_loop(device_manager: G13Manager, app_monitor: AppMonitor):
    """Currently this is a loop that reads data from the USB device."""
    # probably we should be using an interrupt?
    error_count = 0
    while True:
        if error_count > 5:
            # give up
            break
        time.sleep(0.001)

        blinker.signal("tick").send()
        for result in device_manager.get_codes():
            if isinstance(result, G13USBError):
                error_count += 1
                logger.error("USB Error: %s", result)


if __name__ == "__main__":
    m = G13Manager()
    processor = DavinciInputManager()
    a = AppMonitor()
    general = GeneralManager()
    m.start()

    try:

        read_data_loop(m, a)
    except EndProgram:
        blinker.signal("g13_clear_status").send()
        blinker.signal("g13_print").send("That's all!\n \n ")
        logger.success("Exiting...")
    finally:
        m.close()
