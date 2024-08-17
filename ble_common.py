import bluetooth
import struct
from micropython import const
from ble_advertising import decode_services

_BT_MIN_RSSI = const(-85)

_IRQ_SCAN_RESULT = const(5)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_CONNECTION_UPDATE = const(27)


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
        self._CON_HANDLE = {}
        self._CONNECT = {}
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self.handle_ble_scan)

    def register_device(self, device: SensorDevice):
        self._MACS[device._mac] = device

    def start(self):
        self._ble.gap_scan(0, 3000000, 400000)

    def stop(self):
        self._ble.active(False)
        self._ble.BLE().gap_scan(None, 3000000, 400000)

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
            # elif adv_type in (0, 1) and _FRIDGE_SERVICE_UUID in decode_services(
            #     adv_data
            # ):
            #     mac = ':'.join(['{:02X}'.format(b) for b in addr])
            #     print(mac)
            #     print(bytes(addr))
        elif event ==_IRQ_PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data
            device = self._MACS[bytes(addr)]
            self._CON_HANDLE[conn_handle] = device
            device.on_connected(self._ble, conn_handle, addr_type, addr)
        elif event == _IRQ_GATTC_SERVICE_RESULT:
            conn_handle, start_handle, end_handle, uuid = data
            device = self._CON_HANDLE[conn_handle]
            device.on_service_result(self._ble, conn_handle, start_handle, end_handle, uuid)
        elif event == _IRQ_GATTC_SERVICE_DONE:
            conn_handle, status = data
            device = self._CON_HANDLE[conn_handle]
            device.on_service_done(self._ble, conn_handle)
        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn_handle, def_handle, value_handle, properties, uuid = data
            device = self._CON_HANDLE[conn_handle]
            device.on_characteristic_result(self._ble, conn_handle, def_handle, value_handle, properties, uuid)
        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            conn_handle, status = data
            device = self._CON_HANDLE[conn_handle]
            device.on_characteristic_done(self._ble, conn_handle)
        elif event == _IRQ_GATTC_DESCRIPTOR_RESULT:
            conn_handle, dsc_handle, uuid = data
            device = self._CON_HANDLE[conn_handle]
            device.on_descriptor_result(self._ble, conn_handle, dsc_handle, uuid)
        elif event == _IRQ_GATTC_DESCRIPTOR_DONE:
            conn_handle, status = data
            device = self._CON_HANDLE[conn_handle]
            device.on_descriptor_done(self._ble, conn_handle)
        elif event == _IRQ_GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            device = self._CON_HANDLE[conn_handle]
            device.on_notify(self._ble, value_handle, notify_data)
        elif event == _IRQ_GATTC_READ_RESULT:
            conn_handle, value_handle, char_data = data
            device = self._CON_HANDLE[conn_handle]
            device.on_read_result(self._ble, value_handle, char_data)
        elif event == _IRQ_GATTC_WRITE_DONE:
            print("gattc_write event")
        elif event == _IRQ_CONNECTION_UPDATE:
            # The remote device has updated connection parameters.
            conn_handle, conn_interval, conn_latency, supervision_timeout, status = data
            print(f"connection update {conn_handle} {conn_interval} {conn_latency} {status}")
        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            print("disconnected")
            # what to do?
        else:
            print(f"something else? event( {event} )")