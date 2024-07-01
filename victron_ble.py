import struct
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


class DeviceMeta(type):
    """A Device metaclass that will be used for device class creation."""

    def __instancecheck__(cls, instance):
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        return hasattr(subclass, "parse") and callable(subclass.parse)


class VictronDevice(metaclass=Devicemeta):
    def __init__(self, mac: str, key: str, text_format: str, callback):
        self._mac = mac
        self._key = key
        self._text_format = text_format
        self.callback = callback
        self._offset = offset

    def uncipher(self, adv_data: memoryview) -> str:
        ctr = bytearray(adv_data[12:14])
        ctr.extend(bytes(14))
        ciphertext = bytearray(adv_data[15:])
        if len(adv_data[15:]) < 16:
            ciphertext.extend(bytes(16 - len(adv_data[15:])))
        cipher = aes(self._key, 1)
        cipher.encrypt(ctr, ctr)
        cleartext = bytes(a ^ b for a, b in zip(ciphertext, ctr))
        return cleartext


class VictronSolar(VictronDevice):
    def parse(self, cleartext: str) -> dict:
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
        return {
            "state": state,
            "error": error,
            "battery_voltage": battery_voltage,
            "battery_charging_current": battery_charging_current,
            "yield_today": yield_today,
            "solar_power": solar_power,
            "external_device_load": external_device_load,
        }


class VictronDCDC(VictronDevice):
    def parse(self, cleartext: str) -> dict:
        state, error, input_voltage, output_voltage, off_reason = struct.unpack(
            "BBhhI", cleartext
        )
        mode = MODES[state]
        return {
            "state": state,
            "error": error,
            "input_voltage": input_voltage,
            "output_voltage": output_voltage,
            "off_reason": off_reason,
        }


class VictronMonitor(VictronDevice):
    def parse(self, cleartext: str) -> dict:
        # cannot parse current in 24bit field skipping those bytes with x
        remaining_mins, voltage, alarm, aux, consumed_ah, soc = struct.unpack(
            "HHHHxxxHH", cleartext
        )
        voltage = voltage / 100
        consumed_ah = consumed_ah / 100
        soc = ((soc & 0x3FFF) >> 4) / 10
        # get current
        chunk = bytes(cleartext[4:7])
        current = (
            struct.unpack("<i", chunk + ("\0" if chunk[2] < 128 else "\xff")) / 1000
        )
        remaining_mins = 999 if remaining_mins > 999 else remaining_mins
        return {
            "remaining_mins": remaining_mins,
            "voltage": voltage,
            "consumed_ah": consumed_ah,
            "current": current,
            "soc": soc,
        }


class VictronBLE:
    def __init__(self):
        self._MACS = {}

    def register_device(self, device: VictronDevice):
        self._MACS[device._mac] = device

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
                    device = self._MACS[bytes(addr)]
                    cleartext = device.uncipher(adv_data)
                    data = device.parse(cleartext)
                    text = device.text_format.format(**data)
                    device.callback(text)
