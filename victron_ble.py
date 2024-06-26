import machine
import struct
import time
from micropython import const
from bluetooth import BLE
from cryptolib import aes

_BT_MIN_RSSI = const(-85)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

MODES = {
    0: "off",
    3: "bulk",
    4: "absorb",
    5: "float",
}


class VictronBLE:
    def __init__(self, config={}, display_func=None):
        self.config = config
        self._display_func = display_func
        self._MACS = list(config.keys())

    def start(self):
        BLE().active(True)
        BLE().irq(self.handle_ble_scan)
        BLE().gap_scan(0, 3000000, 400000)

    def stop(self):
        BLE().active(False)
        BLE().gap_scan(None, 3000000, 400000)

    def handle_ble_scan(self, ev, data):
        if ev == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if (
                rssi > _BT_MIN_RSSI
                and adv_data[5:8] == b"\xE1\x02\x10"
                and (adv_type == 0 or adv_type == 2)
                and adv_data[1:2] == b"\x01"
            ):
                if addr in self._MACS:
                    config = self.config[bytes(addr)]
                    ctr = bytearray(adv_data[12:14])
                    ctr.extend(bytes(14))
                    ciphertext = bytearray(adv_data[15:])
                    if len(adv_data[15:]) < 16:
                        ciphertext.extend(bytes(16 - len(adv_data[15:])))
                    cipher = aes(config["key"], 1)
                    cipher.encrypt(ctr, ctr)
                    cleartext = bytes(a ^ b for a, b in zip(ciphertext, ctr))
                    if config["type"] == "SOLAR":
                        (
                            state,
                            error,
                            battery_voltage,
                            battery_charging_current,
                            yield_today,
                            solar_power,
                            external_device_load,
                        ) = struct.unpack("BBhhHHH", cleartext)
                        mode = MODES[state]
                        battery_charging_current = battery_charging_current / 10
                        external_device_load = (
                            0 if external_device_load == 0x1FF else external_device_load
                        )
                        self._display_func(
                            f"{mode:<7} {solar_power:>5.0f}W",
                            config["offset"],
                        )
                    elif config["type"] == "DCDC":
                        state, error, input_voltage, output_voltage, off_reason = (
                            struct.unpack("BBhhI", cleartext)
                        )
                        mode = MODES[state]
                        self._display_func(f"{mode:<7}", config["offset"])
                    elif config["type"] == "MON":
                        # cannot parse current in 24bit field skipping those bytes with x
                        remaining_mins, voltage, alarm, aux, consumed_ah, soc = (
                            struct.unpack("HHHHxxxHH", cleartext)
                        )
                        voltage = voltage / 100
                        consumed_ah = consumed_ah / 100
                        soc = ((soc & 0x3FFF) >> 4) / 10
                        # get current
                        chunk = bytes(cleartext[4:7])
                        current = (
                            struct.unpack(
                                "<i", chunk + ("\0" if chunk[2] < 128 else "\xff")
                            )
                            / 1000
                        )
                        remaining_mins = 999 if remaining_mins > 999 else remaining_mins
                        self._display_func(
                            f"{remaining_mins:<3}M {current:>3+.0f}A {soc:>3}%",
                            config["offset"],
                        )
