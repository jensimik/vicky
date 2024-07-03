import machine
import time
import micropython
import vga1_16x32 as font
from st7789py import ST7789, BLACK
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
backlight = machine.PWM(lcd.backlight)
backlight.freq(750)
backlight.duty(512)


# generic display function to write white text on black background
def display_func(text, offset):
    lcd.text(font, text, 6, offset)


# setup Victron devices, you can find mac and encryption keys in the victron mobile app
solar = VictronSolar(
    mac=b"\xee\xc0\xb8\x8c\x53\xf4",
    key=b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    callback=lambda data: display_func(
        "{mode:<7} {solar_power:>5.0f}W".format(**data), 8
    ),
)
dcdc = VictronDCDC(
    mac=b"\xee\xc0\xb8\x8c\x53\xf3",
    key=b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    callback=lambda data: display_func("{mode:<7}".format(**data), 52),
)
monitor = VictronMonitor(
    mac=b"\xee\xc0\xb8\x8c\x53\xf2",
    key=b"\x10\x63\x76\x13\x6f\xf4\xd0\x8c\x6a\x01\x99\x15\xfd\xee\xc0\x11",
    callback=lambda data: display_func(
        "{remaining_mins:<3}M {current:>3+.0f}A {soc:>3}%".format(**data), 96
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


B_M5 = machine.Pin(37, mode=machine.Pin.IN)
B_M5.irq(handler=handle_btn_m5, trigger=machine.Pin.IRQ_FALLING)

# after 24 hours program exit and watchdog reboot
time.sleep(60 * 60 * 24)
