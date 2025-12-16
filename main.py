import time

import blinker
from loguru import logger

from g13lib.apps.davinci_resolve import DavinciInputManager
from g13lib.device_manager import G13Manager, G13USBError
from g13lib.input_manager import EndProgram, GeneralManager
from g13lib.monitors.current_app import AppMonitor


def read_data_loop(device_manager: G13Manager):
    """Currently this is a loop that reads data from the USB device."""
    # probably we should be using an interrupt?
    error_count = 0
    while True:
        if error_count > 5:
            # give up
            break

        # check for input every 1ms
        time.sleep(0.001)

        # send a tick signal to all listeners
        blinker.signal("tick").send()

        for result in device_manager.get_codes():
            if isinstance(result, G13USBError):
                error_count += 1
                logger.error("USB Error: %s", result)


if __name__ == "__main__":
    m = G13Manager()

    # load all the things that listen for signals
    # probaby this should be more configurable
    # and allow for reload of application managers

    listeners = [DavinciInputManager(), AppMonitor(), GeneralManager()]

    m.start()

    try:

        read_data_loop(m)
    except EndProgram:
        blinker.signal("g13_clear_status").send()
        blinker.signal("g13_print").send("That's all!\n \n ")
        logger.success("Exiting...")
    finally:
        m.close()
