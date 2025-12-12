import time

from loguru import logger

from g13lib.device_manager import G13Manager, G13USBError
from g13lib.input_manager import EndProgram, InputManager


def read_data_loop(device_manager: G13Manager, input_manager: InputManager):
    """Currently this is a loop that reads data from the USB device."""
    # probably we should be using an interrupt?
    error_count = 0
    while True:
        if error_count > 5:
            # give up
            break
        time.sleep(0.001)
        for result in device_manager.get_codes():
            if isinstance(result, G13USBError):
                error_count += 1
                logger.error("USB Error: %s", result)
            else:
                input_manager.handle_input(result)
                device_manager.print(result)


if __name__ == "__main__":
    m = G13Manager()
    processor = InputManager(m)
    m.start()

    try:

        read_data_loop(m, processor)
    except EndProgram:
        m.print("That's all!")
        logger.success("Exiting...")
    finally:
        m.close()
