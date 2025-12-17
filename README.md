# G13 Slop

A hackable skeleton to use a Logitech G13 with minimal overhead on macOS.

The support for the Logitech G13 is at an end, but did we really like the Logitech software anyway? Nah. We'd rather 
roll our own and script it using full-powered Python.

So here's the basics in Python and you can roll your own application support.

## Unfortunate Aspects

Currently requires running as root using `sudo`! This is really not great! Sorry! I haven't figured out how to make the USB device access work without root privs. 

It does drop root privs after device initialization, so it's not entirely horrible.

## Other Stuff

Includes the 5x8 version of the monospaced bitmap Spleen font. We gotta use something
to write text to the tiny little LCD screen.

