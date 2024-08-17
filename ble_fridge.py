import struct
import bluetooth
from ble_common import SensorDevice

_CCCD_UUID = bluetooth.UUID(0x2902)
_NOTIFY_ENABLE = const(1)

_SERVICE_UID = bluetooth.UUID(0x1234)
_CMD_UID = bluetooth.UUID(0x1235)
_NOTIFI_UID = bluetooth.UUID(0x1236)

def create_packet(data: bytes) -> bytes:
    '''Create a packet for sending to a fridge'''
    pkt = b'\xFE\xFE' + struct.pack('B', len(data) + 2) + data
    pkt += struct.pack('>H', sum(int(v) for v in pkt))
    return pkt

class Fridge(SensorDevice):
    """Alpicool/Vevor generic fridge"""

    def connect(self, ble):
        ble.gap_connect(0x0, self._mac)

    def disconnect(self, ble):
        ble.gap_disconnect(self._mac)

    def query(self, ble):
        pkt = create_packet(struct.pack('B', 1))
        ble.gattc_write(self._conn_handle, self._cmd_desc_handle, pkt, 0)
        print("ping")

    def on_connected(self, ble, conn_handle, addr_type, addr):
        self._conn_handle = conn_handle
        ble.gattc_discover_services(conn_handle, _SERVICE_UID)

    def on_service_result(self, ble, conn_handle, start_handle, end_handle, uuid):
        self._start_handle = start_handle
        self._end_handle = end_handle

    def on_service_done(self, ble, conn_handle):
        print("service_done")
        ble.gattc_discover_characteristics(conn_handle, self._start_handle, self._end_handle)
        print(f"discover start_handle {self._start_handle} end_handle: {self._end_handle}")
        ble.gattc_discover_descriptors(conn_handle, self._start_handle, self._end_handle)

    def on_characteristic_result(self, ble, conn_handle, def_handle, value_handle, properties, uuid):
        if uuid == _NOTIFI_UID:
            self._def_handle = def_handle
            self._notifi_value_handle = value_handle
            self._properties = properties
            print(f"NOTIFI_UID: {uuid} {conn_handle} {def_handle} {value_handle} {properties}")
        elif uuid == _CMD_UID:
            self._cmd_def_handle = def_handle
            self._cmd_value_handle = value_handle
            self._properties = properties
            print(f"CMD_UID: {uuid} {conn_handle} {def_handle} {value_handle} {properties}")
        else:
            print(f"OTHER: {uuid} {value_handle} {properties}")

    def on_characteristic_done(self, ble, conn_handle):
        pass

    def on_descriptor_result(self, ble, conn_handle, dsc_handle, uuid):
        print(f"descriptor uuid {uuid}")
        if uuid == _CCCD_UUID:
            print(f"enable notify {dsc_handle} {uuid}")
            ble.gattc_write(conn_handle, dsc_handle, struct.pack('<H', _NOTIFY_ENABLE), 1)
        elif uuid == _CMD_UID:
            print(f"settings cmd handle {uuid}")
            self._cmd_desc_handle = dsc_handle

    def on_descriptor_done(self, ble, conn_handle):
        pass

    def on_notify(self, ble, value_handle, notify_data):
        if notify_data[:2] == b"\xFE\xFE":
            rawdata = ':'.join(['{:02X}'.format(b) for b in notify_data])
            print(rawdata)
            run_mode, target_temperature, current_temperature = struct.unpack_from('>xxbxbxxxxxxxxxb', notify_data, 4)
            run_mode = "E" if run_mode == 1 else "*"
            print(f"target: {target_temperature:.1f}C current: {current_temperature:.1f}C")
            self._toggle = False if self._toggle else True
            self.callback(self._toggle, {"target_temperature": target_temperature, "current_temperature": current_temperature, "run_mode": run_mode})