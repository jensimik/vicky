import struct
from cryptolib import aes
from ble_common import SensorDevice

MODES = {
    0: "off",
    3: "blk",  # bulk
    4: "abs",  # absorb
    5: "flt",  # float
}


class VictronDevice(SensorDevice):
    """A VictronDevice base class"""

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
    """Victron MPPT Smart Solar charger"""

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
        return self._return_if_changed(
            {
                "mode": mode,
                "state": state,
                "error": error,
                "battery_voltage": battery_voltage,
                "battery_charging_current": battery_charging_current,
                "yield_today": yield_today,
                "solar_power": solar_power,
                "external_device_load": external_device_load,
            }
        )


class VictronDCDC(VictronDevice):
    """Victron Orion Smart DCDC charger"""

    def parse(self, cleartext: str) -> dict:
        state, error, input_voltage, output_voltage, off_reason = struct.unpack(
            "BBhhI", cleartext
        )
        mode = MODES[state]
        return self._return_if_changed(
            {
                "mode": mode,
                "state": state,
                "error": error,
                "input_voltage": input_voltage,
                "output_voltage": output_voltage,
                "off_reason": off_reason,
            }
        )


class VictronMonitor(VictronDevice):
    """Victron Battery Monitor"""

    def parse(self, cleartext: str) -> dict:
        remaining_mins, voltage, alarm, aux = struct.unpack("HHHH", cleartext)
        voltage = voltage / 100
        consumed_ah = struct.unpack("H", bytes(cleartext[11:13]))[0] / 100
        soc = float(
            ((struct.unpack("H", bytes(cleartext[13:15]))[0] & 0x3FFF) >> 4) / 10
        )
        # get current
        chunk = bytes(cleartext[8:11])
        current = float(
            (
                (
                    struct.unpack(
                        "<i", chunk + (b"\ff" if chunk[2] == 0x80 else b"\x00")
                    )[0]
                    >> 2
                )
                / 1000
            )
        )
        r_hours = remaining_mins // 60
        r_mins = remaining_mins % 60
        if r_hours > 99:
            r_hours = 99
            r_mins = 99
        remaining_mins = 999 if remaining_mins > 999 else remaining_mins
        return self._return_if_changed(
            {
                "remaining_mins": remaining_mins,
                "r_hours": r_hours,
                "r_mins": r_mins,
                "voltage": voltage,
                "consumed_ah": consumed_ah,
                "current": current,
                "soc": soc,
            }
        )
