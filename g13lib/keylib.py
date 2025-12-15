import pynput

undo = (pynput.keyboard.Key.cmd, "z")
redo = (pynput.keyboard.Key.shift, pynput.keyboard.Key.cmd, "z")
copy = (pynput.keyboard.Key.cmd, "c")
paste = (pynput.keyboard.Key.cmd, "v")
cut = (pynput.keyboard.Key.cmd, "x")

zoom_in = (pynput.keyboard.Key.cmd, "=")
zoom_out = (pynput.keyboard.Key.cmd, "-")

shift = pynput.keyboard.Key.shift
cmd = pynput.keyboard.Key.cmd
alt = pynput.keyboard.Key.alt
space = pynput.keyboard.Key.space
