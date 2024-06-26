import machine
import time
import vga1_16x32 as font
from st7789py import ST7789, WHITE, BLACK
from victron_ble import VictronBLE

power = machine.Pin(4, machine.Pin.OUT)  # when not powered via USB
power.on()

# setup lcd
rotation = 1
spi = machine.SPI(
    1, baudrate=20000000, polarity=1, sck=machine.Pin(13), mosi=machine.Pin(15)
)
lcd = ST7789(
    spi,
    135,
    240,
    reset=machine.Pin(12, machine.Pin.OUT),
    dc=machine.Pin(14, machine.Pin.OUT),
    cs=machine.Pin(5, machine.Pin.OUT),
    backlight=machine.Pin(27, machine.Pin.OUT),
    rotation=rotation,
)
lcd.fill(BLACK)


CONFIG = {
    b"\xee\xc0\xb8\x8c\x53\xf4": {
        "type": "SOLAR",
        "offset": 8,
        "key": b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    },
    b"\xee\xc0\xb8\x8c\x53\xf3": {
        "type": "DCDC",
        "offset": 52,
        "key": b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    },
    b"\xee\xc0\xb8\x8c\x53\xf2": {
        "type": "MON",
        "offset": 96,
        "key": b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    },
}


def display_func(text, offset):
    lcd.text(font, text, 6, offset, WHITE, BLACK)


victron = VictronBLE(config=CONFIG, display_func=display_func)
victron.start()


# setup buttons
def handle_btn_m5(p):
    print("btn_m5 pressed")


B_M5 = machine.Pin(37, mode=machine.Pin.IN)
B_M5.irq(handler=handle_btn_m5, trigger=machine.Pin.IRQ_FALLING)

# after 24 hours program exit and watchdog reboot
time.sleep(60 * 60 * 24)
