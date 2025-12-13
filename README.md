# G13 Slop

A very hackish framework to use a Logitech G13 with minimal overhead.

The support for the G13 is at an end, but did we really like the Logitech software anyway?

Here's a Python framework that lets you write all your own code!

## Unfortunate Aspects

Currently requires running as root! This is not great, but I haven't figured out how to make the 
USB device access work without root privs. Probably we should drop the root privs once we have
the device.

## Other Stuff

Includes the 5x8 version of the monospaced bitmap Spleen font. We gotta use something
to write text to the tiny little LCD screen.

