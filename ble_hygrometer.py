import struct
from ble_common import SensorDevice


class Hygrometer(SensorDevice):
    """Smart Hygrometer Widcomm, inc"""

    def parse(self, data: str) -> dict:
        voltage, temperature_raw, humidity_raw = struct.unpack('HhH', data[19:])
        return self._return_if_changed(
            {
                "temperature": temperature_raw / 16,
                "humidity": humidity_raw / 16,
                "voltage": voltage / 1000
            }
        )

