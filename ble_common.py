from micropython import const
from bluetooth import BLE

_BT_MIN_RSSI = const(-85)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)


class SensorDevice:
    """A SensorDevice base class"""

    def __init__(self, mac: str, key: str, callback):
        self._mac = mac
        self._key = key
        self.callback = callback
        self._toggle = False
        self._data = {}

    def _return_if_changed(self, data: dict):
        if self._data == data:
            return None
        self._data = data
        return self._data


class GenericBLE:
    """Generic Bluetooth scanner"""

    def __init__(self):
        self._MACS = {}

    def register_device(self, device: SensorDevice):
        self._MACS[device._mac] = device

    def start(self):
        BLE().active(True)
        BLE().irq(self.handle_ble_scan)
        BLE().gap_scan(0, 3000000, 400000)

    def stop(self):
        BLE().active(False)
        BLE().gap_scan(None, 3000000, 400000)

    def handle_ble_scan(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
#            mac = ':'.join(['{:02X}'.format(b) for b in addr])
#            print(mac)
            if (
                rssi > _BT_MIN_RSSI
                and adv_data[5:8] == b"\xE1\x02\x10"
                and (adv_type == 0 or adv_type == 2)
                and adv_data[1:2] == b"\x01"
            ):
                baddr = bytes(addr)
                if baddr in self._MACS:
                    device = self._MACS[baddr]
                    cleartext = device.uncipher(adv_data)
                    device_data = device.parse(cleartext)
                    device._toggle = False if device._toggle else True
                    device.callback(device._toggle, device_data)
            elif (
                rssi > _BT_MIN_RSSI
                and adv_data[5:8] == b"\xF0\xFF\x15"
                and (adv_type == 0 or adv_type == 2)
                and adv_data[1:2] == b"\x01"
            ):
                baddr = bytes(addr)
                if baddr in self._MACS:
                    device = self._MACS[baddr]
                    device_data = device.parse(adv_data)
                    device._toggle = False if device._toggle else True
                    device.callback(device._toggle, device_data)