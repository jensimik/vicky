import machine
import time
import micropython
import vga1_16x32 as font
from st7789py import ST7789, BLACK, WHITE
from victron_ble import VictronBLE, VictronSolar, VictronDCDC, VictronMonitor

# allocate buffer for irq exceptions
# micropython.alloc_emergency_exception_buf(100)

# setup m5stick
power = machine.Pin(4, machine.Pin.OUT)  # when not powered via USB
power.on()

# setup lcd on the m5stick
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
# set backlight off to preserve battery
backlight = machine.PWM(lcd.backlight)
backlight.freq(750)
backlight.duty(512)


# generic display function display is about 14 chars wide and 3 lines high with 16x32 monospace font
def display_func(text_format, offset):
    def display_func_inner(toggle, data):
        if data:
            lcd.text(font, text_format.format(**data), 6, offset)
        # show data has been received
        if toggle:
            lcd.vline(0, offset, 32, WHITE)
            lcd.vline(1, offset, 32, WHITE)
        else:
            lcd.vline(0, offset, 32, BLACK)
            lcd.vline(1, offset, 32, BLACK)

    return display_func_inner


# setup Victron devices, you can find mac and encryption keys in the victron mobile app
solar = VictronSolar(
    mac=b"\xee\xc0\xb8\x8c\x53\xf4",
    key=b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    callback=display_func(
        text_format="{mode:<3}  {battery_charging_current:>4.1f} {solar_power:>3.0f}W",
        offset=8,
    ),
)
dcdc = VictronDCDC(
    mac=b"\xcd\x73\xa1\x0f\x95\x99",
    key=b"\x9f\xea\xf4\x0c\x53\xdb\xd0\xff\x1c\x26\xb9\xba\xe6\xf3\xb7\xce",
    callback=display_func(text_format="{mode:<3}", offset=52),
)
monitor = VictronMonitor(
    mac=b"\xc7\x83\xfd\xca\xca\x06",
    key=b"\xe3\x39\xd2\xf5\x2c\xed\x10\x2f\x1c\x2c\xe9\x0e\x94\xa1\x70\x09",
    callback=display_func(
        text_format="{r_hours:00}:{r_mins:00} {current: >4.1f} {soc:>2.0f}%", offset=96
    ),
)

# setup Victron Bluetooth scanner
victron = VictronBLE()
victron.register_device(solar)
victron.register_device(dcdc)
victron.register_device(monitor)
victron.start()


# setup buttons
def handle_btn_m5(p):
    print("btn_m5 pressed")
    victron.stop()


B_M5 = machine.Pin(37, mode=machine.Pin.IN)
B_M5.irq(handler=handle_btn_m5, trigger=machine.Pin.IRQ_FALLING)

# after 24 hours program exit and watchdog reboot
time.sleep(60 * 60 * 24)
