import time
from io import BytesIO

import blinker
from AppKit import NSWorkspace
from loguru import logger
from PIL import Image


def trim_image(image: Image.Image) -> Image.Image:
    """Trim the transparent edges from an image."""
    bbox = image.getbbox()
    if bbox:
        return image.crop(bbox)
    return image  # no content, return as is


class AppMonitor:
    """Sits around and listens for ticks, every 0.1 seconds it checks and
    notifies when the current application changes.

    The `app_changed` signal is essential for SingleAppManager to work.
    """

    current_app: str | None
    last_poll: float

    def __init__(self):
        self.current_app = self.detect_current_application()
        self.last_poll = time.time()

        blinker.signal("tick").connect(self.handle_tick)

    def detect_current_application(self) -> str:
        active_app = NSWorkspace.sharedWorkspace().activeApplication()
        return active_app["NSApplicationName"]

    def get_icon_for_app(self, app_name: str) -> Image.Image | None:
        # print(active_app)
        active_apps = NSWorkspace.sharedWorkspace().runningApplications()
        for app in active_apps:
            if app.localizedName() == app_name:
                icon = app.icon()
                icon_image = Image.open(BytesIO(icon.TIFFRepresentation().bytes()))
                icon_image = trim_image(icon_image)
                icon_image = icon_image.resize((32, 32), Image.LANCZOS)

                return icon_image

    def handle_tick(self, msg) -> bool:
        # if it's been at least a 1/10th second
        if time.time() - self.last_poll < 0.1:
            return False
        return self.notify()

    def notify(self) -> bool:

        try:
            self.last_poll = time.time()
            active_app = self.detect_current_application()
        except Exception as e:
            logger.error("Error detecting current application: {}", e)
            return False
        if active_app != self.current_app:
            self.current_app = active_app
            # Add your notification logic here
            blinker.signal("app_changed").send(active_app)
            icon = self.get_icon_for_app(active_app)
            if icon:

                blinker.signal("current_app_icon").send(icon)
            return True
        return False
