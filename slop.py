"""A lightweight macOS menubar app that starts and stops the g13 service."""

import asyncio
import threading

import rumps
from loguru import logger

from main import main


class G13ServiceController:
    """Run the async g13 service inside a background thread."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._lock = threading.Lock()
        self._last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def start(self) -> bool:
        """Start the g13 service loop if it's not already running."""
        with self._lock:
            if self.running:
                return False
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._run_service, name="g13-service", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> bool:
        """Signal the running service to stop and wait for it to exit."""
        with self._lock:
            if not self.running:
                return False
            stop_event = self._stop_event
            thread = self._thread

        if stop_event and thread:
            stop_event.set()
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning("Timed out while waiting for g13 service to stop")
                return False

        with self._lock:
            self._thread = None
            self._stop_event = None

        return True

    def _run_service(self) -> None:
        try:
            asyncio.run(main(stop_event=self._stop_event))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the UI
            self._last_error = str(exc)
            logger.exception("g13 service crashed")
        finally:
            # ensure future calls see an idle state
            with self._lock:
                self._thread = None
                self._stop_event = None


class G13StatusBarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("g13", quit_button=None)
        self.controller = G13ServiceController()
        self._error_notified: str | None = None

        self.menu = [
            rumps.MenuItem("Start", callback=self._start_service),
            rumps.MenuItem("Stop", callback=self._stop_service),
            rumps.MenuItem("Status", callback=self._show_status),
            None,
            rumps.MenuItem("Quit", callback=self._quit_app),
        ]

        # keep the menu state in sync with the background thread
        self._state_timer = rumps.Timer(self._refresh_state, 3)
        self._state_timer.start()
        self._refresh_state(None)

    def _refresh_state(self, _):
        running = self.controller.running
        self.title = "g13 [on]" if running else "g13 [off]"
        self.menu["Start"].state = running
        self.menu["Stop"].state = not running

        if not running and self.controller.last_error and self.controller.last_error != self._error_notified:
            self._error_notified = self.controller.last_error
            rumps.notification("g13 stopped", "", f"Last error: {self.controller.last_error}")

    def _start_service(self, _):
        if self.controller.start():
            rumps.notification("g13", "", "Service started")
        else:
            rumps.alert("g13 service is already running")
        self._refresh_state(None)

    def _stop_service(self, _):
        if self.controller.stop():
            rumps.notification("g13", "", "Service stopped")
        else:
            rumps.alert("g13 service is not running or refused to stop")
        self._refresh_state(None)

    def _show_status(self, _):
        if self.controller.running:
            rumps.alert("g13 service is running")
        elif self.controller.last_error:
            rumps.alert(f"g13 service is stopped. Last error: {self.controller.last_error}")
        else:
            rumps.alert("g13 service is stopped")

    def _quit_app(self, _):
        self.controller.stop()
        rumps.quit_application()


if __name__ == "__main__":
    G13StatusBarApp().run()
