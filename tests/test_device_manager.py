import unittest.mock as mock
from typing import Sequence

import pytest

from g13lib.device_manager import G13Manager


def test_joy_position_parsing():
    manager = G13Manager(g13_usb_device=mock.MagicMock())

    # Test joystick centered
    codes = list(manager.joy_position_to_codes(0x80, 0x80))
    assert codes == ["JOY_X_ZERO_0", "JOY_Y_ZERO_0"]

    # Test joystick moved to top-right
    codes = list(manager.joy_position_to_codes(0xC5, 0x20))
    assert codes == ["JOY_X_POS_3", "JOY_Y_POS_3"]

    # Test joystick moved to bottom-left
    codes = list(manager.joy_position_to_codes(0x10, 0xE0))
    assert codes == ["JOY_X_NEG_3", "JOY_Y_NEG_3"]


def test_determine_held_keycodes():
    manager = G13Manager(g13_usb_device=mock.MagicMock())

    # G1-G8 are in byte 3
    # G9-G16 are in byte 4
    # G17-G22 are in byte 5
    # BD, L1-L4, M1-M3 are in byte 6
    # MR, THUMB_LEFT, THUMB_RIGHT, THUMB_STICK are in byte 7

    # G11 alone
    bytes_ = [0, 0, 0, 0, 0b00000100, 0, 0, 0]
    keys = set(manager.determine_held_keycodes(bytes_))
    assert keys == {"G11"}

    # G1, G5, M2 held
    bytes_ = [0, 0, 0, 0b00010001, 0, 0, 0b01000000, 0]
    keys = set(manager.determine_held_keycodes(bytes_))
    assert keys == {"G1", "G5", "M2"}

    # g22 plus joystick moved off center
    bytes_ = [0, 0xC0, 0x20, 0, 0, 0b00100000, 0, 0]
    keys = set(manager.determine_held_keycodes(bytes_))
    assert keys == {"G22"}

    # test across all five bytes
    # G2, G10, G15, G19, L2, THUMB_RIGHT
    bytes_ = [0, 0, 0, 0b00000010, 0b01000010, 0b00000100, 0b000000100, 0b00000100]
    keys = set(manager.determine_held_keycodes(bytes_))
    assert keys == {"G2", "G10", "G15", "G19", "L2", "THUMB_RIGHT"}
