import pynput


class InputManager:

    direct_mapping: dict[str, str] = {"G12": "a"}
    keyboard: pynput.keyboard.Controller

    def __init__(self):
        self.keyboard = pynput.keyboard.Controller()

    def handle_input(self, code: str):
        # code will end in either '_PRESSED' or '_RELEASED'
        # split and handle accordingly
        action = code.split("_")[-1]
        key_code = "_".join(code.split("_")[:-1])
        output_key = self.direct_mapping.get(key_code)
        if output_key:
            if action == "PRESSED":
                self.keyboard.press(output_key)
            elif action == "RELEASED":
                self.keyboard.release(output_key)
