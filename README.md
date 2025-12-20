# G13 Slop

A hackable skeleton to use a Logitech G13 with minimal overhead on macOS.

The support for the Logitech G13 is at an end, but did we really like the Logitech software anyway? Nah. We'd rather 
roll our own and script it using full-powered Python.

So here's the basics in Python and you can roll your own application support.

## How it works

Well, it uses a signal-based architecture to allow components to be relatively independent. The main loop checks the device for input changes every 1ms (or so, it's blocking with 100 ms timeout)
and then sends those key codes out as signals. There's also separate async tasks for everything that needs to update regularly, like updating the LCD if it's changed every 33ms or so.

Haven't run into any latency issues yet, but a real gamer might? I haven't tested (or thought much about how to test) how long it takes a keypress on the G13 to turn into a keystroke passed to the OS.

The LCD content is handled by setting a LCDCompositor (using the `set_compositor` signal) for the DeviceManager to ask for updated frames every 10ms. There'a also a little "terminal emulator" in `lcd/terminal.py` which support stuff like setting a status line and "printing" to the LCD.

## Unfortunate Aspects

Currently requires running as root using `sudo`! This is really not great! Sorry! I haven't figured out how to make the USB device access work without root privs. 

It does drop root privs after device initialization, so it's not entirely horrible.

## Other Stuff

Includes the 5x8 version of the monospaced bitmap Spleen font. We gotta use something
to write text to the tiny little LCD screen.

