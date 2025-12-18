import pynput

# copy/paste commands

copy = (pynput.keyboard.Key.cmd, "c")
paste = (pynput.keyboard.Key.cmd, "v")
cut = (pynput.keyboard.Key.cmd, "x")

# undo/redo commands
undo = (pynput.keyboard.Key.cmd, "z")
redo = (pynput.keyboard.Key.shift, pynput.keyboard.Key.cmd, "z")

# zoom commands
zoom_in = (pynput.keyboard.Key.cmd, "=")
zoom_out = (pynput.keyboard.Key.cmd, "-")

# modifier keys
shift = pynput.keyboard.Key.shift
cmd = pynput.keyboard.Key.cmd
alt = pynput.keyboard.Key.alt

space = pynput.keyboard.Key.space

# arrow keys
left = pynput.keyboard.Key.left
right = pynput.keyboard.Key.right
up = pynput.keyboard.Key.up
down = pynput.keyboard.Key.down
