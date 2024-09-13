from displayio import release_displays
release_displays()

from time import mktime, sleep, monotonic
import math

import microcontroller
import supervisor

# from adafruit_pcf8523.pcf8523 import PCF8523
from adafruit_ds3231 import DS3231

import displayio
import board

from adafruit_lsm6ds.lsm6dso32 import LSM6DSO32
import dotclockframebuffer 
from framebufferio import FramebufferDisplay
import adafruit_imageload
from adafruit_display_text.bitmap_label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_bitmap_font import bitmap_font

from adafruit_datetime import datetime, timezone, timedelta

import wifi
import socketpool
import adafruit_ntp 

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.button_packet import ButtonPacket


def last_sunday_of_month(year, month):
    """Find the last Sunday of a given month and year."""
    # Start from the last day of the month
    last_day = datetime(year, month, 1) + timedelta(days=32)
    last_day = last_day.replace(day=1) - timedelta(days=1)
    
    # Calculate the last Sunday
    last_sunday = last_day - timedelta(days=last_day.weekday() + 1)
    
    return last_sunday

def is_in_uk_dst(date):
    """Determine if a given date is within UK Daylight Savings Time."""
    year = date.year
    
    # Get the last Sunday of March (start of DST)
    dst_start = last_sunday_of_month(year, 3)
    
    # Get the last Sunday of October (end of DST)
    dst_end = last_sunday_of_month(year, 10)
    
    # Check if the given date is within the DST period
    return dst_start <= date < dst_end

def getTimeCorrectTimezone(rtc, timezonevar):
    rtcTime = rtc.datetime
    rtcDatetime = datetime.fromtimestamp(mktime(rtcTime)) # Read the time from the RTC

    tzCorrectedTime = rtcDatetime + timezonevar.utcoffset(rtcDatetime)

    return tzCorrectedTime

def attemptWifiConnection():
    try:
        print("\nAttempting to Connect to wifi")
        wifi.radio.connect("35 Blackberry", "Langridge1!")
        print("\nConnected")
        print("\nMy IP address: {wifi.radio.ipv4_address}")

        pool = socketpool.SocketPool(wifi.radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600) 

        ntpTime = ntp.datetime
        print("\nNTP time:", ntpTime)

        wifi.radio.enabled = False

        return ntpTime

    except Exception as e:
        print("Unable to connect to wifi, using RTC:", e)

        return None

def setupClock(ntpTime):
    sleep(0.1)

    try:
        # Try to create the RTC object
        rtc = DS3231(i2c)

        if (ntpTime != None):
            print("\nNTP time available, updating RTC!")
            updateRTCWithNtp(rtc, ntpTime)

        return rtc, getTimeZone(rtc)

    except Exception as e: # TODO: Maybe make this display an error on the screen
        print("\nUnable to read from RTC!! Holding...", e)

        while True:
            pass

def configureGyroscope(i2c):
    gyro = LSM6DSO32(i2c)

    return gyro

def updateRTCWithNtp(rtc, ntpTime):
    rtc.datetime = ntpTime # Update the RTC with the NTP time

def getTimeZone(rtc):
    rtcTime = rtc.datetime
    rtcDatetime = datetime.fromtimestamp(mktime(rtcTime)) # Read the time from the RTC

    if (is_in_uk_dst(rtcDatetime)):
        timezonevar = timezone(timedelta(hours=1), "London/UK DST") # Setup the timezone *need to account for DST*
    else:
        timezonevar = timezone(timedelta(hours=0), "London/UK")

    print("Current timezone: ", timezonevar)

    tzCorrectedTime = rtcDatetime + timezonevar.utcoffset(rtcDatetime) # Add the timezone offset

    print("\nThe corrected time is: ", tzCorrectedTime.time(), tzCorrectedTime.date())  

    return timezonevar

def loadCustomFont():
    large_numbers = []
    tiny_numbers = []

    large_characters = {
        "A": loadTemplate("/characters/large/A.bmp"), # A
        "D": loadTemplate("/characters/large/D.bmp"), # D
        "E": loadTemplate("/characters/large/E.bmp"), # E
        "F": loadTemplate("/characters/large/F.bmp"), # F
        "H": loadTemplate("/characters/large/H.bmp"), # H
        "I": loadTemplate("/characters/large/I.bmp"), # I
        "M": loadTemplate("/characters/large/M.bmp"), # M
        "N": loadTemplate("/characters/large/N.bmp"), # N
        "O": loadTemplate("/characters/large/O.bmp"), # O
        "R": loadTemplate("/characters/large/R.bmp"), # R
        "S": loadTemplate("/characters/large/S.bmp"), # S
        "T": loadTemplate("/characters/large/T.bmp"), # T
        "U": loadTemplate("/characters/large/U.bmp"), # U
        "W": loadTemplate("/characters/large/W.bmp"), # W
        "slash": loadTemplate("/characters/large/slash.bmp")
    }

    tiny_numbers.append(loadTemplate("/characters/tiny/0.bmp")) # Only need the tiny 0

    for i in range(0, 10):
        large_numbers.append(loadTemplate("/characters/large/" + str(i) + ".bmp"))
        # tiny_numbers.append(loadTemplate("/characters/tiny/" + str(i) + ".bmp"))

    return large_numbers, tiny_numbers, large_characters

def loadTemplate(file_path):
    bitmap, palette = adafruit_imageload.load(file_path, bitmap=displayio.Bitmap, palette=displayio.Palette)

    return bitmap, palette

def formatDate(datetime):
    return "{:02}/{:02}/{}".format(
        datetime.day,
        datetime.month,
        datetime.year
    )

def formatTime(datetime):
    return "{:02}:{:02}:{:02}".format(
        datetime.hour,
        datetime.minute,
        datetime.second,
    )

def formatDay(datetime):
    intToDay = {
        0: "MON",
        1: "TUE",
        2: "WED",
        3: "THU",
        4: "FRI",
        5: "SAT",
        6: "SUN"
    }

    return intToDay[datetime.weekday()]

def calculateFPS(start_time, frame_count, showFPS):
    # FPS counter --------------------------------------------
    frame_count += 1

    # Calculate the elapsed time
    elapsed_time = monotonic() - start_time

    # Calculate FPS every second
    if elapsed_time >= 1.0:
        fps = frame_count / elapsed_time

        if (showFPS):
            print(f"FPS: {fps:.2f}")

        # Reset the frame counter and start time
        frame_count = 0
        start_time = monotonic()

    return start_time, frame_count

def setupGroup(group, groupItems):
    # Pack the labels in the group
    group.append(groupItems.master_tile_grid)

    # Heading, Altitude and Airspeed Tapes
    group.append(groupItems.heading_tile_grid)
    group.append(groupItems.spd_tile_grid)
    group.append(groupItems.alt_tile_grid)

    # Redraw the alt and spd tape borders to hide the overscan from the heading tape
    group.append(groupItems.SpdTapeWhiteBorder)
    group.append(groupItems.SpdTapeBlackPixelBorder)

    group.append(groupItems.altTapeWhiteBorder)
    group.append(groupItems.altTapeBlackPixelBorder)

    # Redraw the spd box to hide the spd tape behind the readout box
    group.append(groupItems.blackAirspeedCoverRectBackground)
    group.append(groupItems.whiteAirspeedCoverRectOutline)
    group.append(groupItems.blackAirspeedCoverRectForeground)

    group.append(groupItems.airspeed_hundred) # Add the Airspeed readout
    group.append(groupItems.airspeed_ten)
    group.append(groupItems.airspeed_digit)

    # Redraw the alt box to hide the alt tape behind the readout box
    group.append(groupItems.blackAltCoverRectBackground)
    group.append(groupItems.whiteAltCoverRectOutline)
    group.append(groupItems.blackAltCoverRectUpForeground)
    group.append(groupItems.blackAltCoverRectDownForeground)

    group.append(groupItems.climb_rate_tile_grid)

    group.append(groupItems.altitude_ten_thousand) # Add the Altitude readout
    group.append(groupItems.altitude_thousand)
    group.append(groupItems.altitude_hundred)
    group.append(groupItems.altitude_ten)
    group.append(groupItems.altitude_digit) 

    # Redraw the top bar to hide the alt and spd tape overscan
    group.append(groupItems.blackTopBarBackground)
    group.append(groupItems.whiteTopBoxOutline)
    group.append(groupItems.blackTopBoxForeground)

    group.append(groupItems.day_first_letter) # Add the Day of the week in the Mach box
    group.append(groupItems.day_second_letter)
    group.append(groupItems.day_third_letter)

    group.append(groupItems.date_day_first) # Add the date to the Baroset
    group.append(groupItems.date_day_second)
    group.append(groupItems.date_day_slash)
    group.append(groupItems.date_month_first)
    group.append(groupItems.date_month_second)
    group.append(groupItems.date_month_slash)
    group.append(groupItems.date_year_first)
    group.append(groupItems.date_year_second)
    group.append(groupItems.date_year_third)
    group.append(groupItems.date_year_fourth)

    return group

# Function to calculate pitch and roll from accelerometer data
def calculate_pitch_and_roll(accel_data):
    ax, ay, az = accel_data
    pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2)) * (180.0 / math.pi)
    roll = math.atan2(ay, az) * (180.0 / math.pi)
    return pitch, roll

# # Calibration: Average sensor readings for 5 seconds to find zero-point offset
# def calibrate_sensor(gyro, statusString, duration=5):
#     total_accel = [0.0, 0.0, 0.0]
#     total_gyro = [0.0, 0.0, 0.0]

#     start_time = monotonic()
#     num_samples = 0

#     while ((monotonic() - start_time) < float(duration)):
#         if (num_samples % 100 == 0):
#             statusString.text = "Configuring\nGyroscope\n3/10\n\nCalibrating"
#         elif (num_samples % 100 == 25):
#             statusString.text = " Configuring\n Gyroscope\n 3/10\n \n Calibrating."
#         elif (num_samples % 100 == 50):
#             statusString.text = "  Configuring\n  Gyroscope\n  3/10\n  \n  Calibrating.."
#         elif (num_samples % 100 == 75):
#             statusString.text = "   Configuring\n   Gyroscope\n   3/10\n   \n   Calibrating..."

#         accelData = gyro.acceleration  # Get accelerometer data (m/s^2)
#         gyroData = gyro.gyro  # Get gyroscope data (rad/s)
        
#         # Sum up the values for averaging
#         total_accel[0] += accelData[0]
#         total_accel[1] += accelData[1]
#         total_accel[2] += accelData[2]
#         total_gyro[0] += gyroData[0]
#         total_gyro[1] += gyroData[1]
#         total_gyro[2] += gyroData[2]
        
#         num_samples += 1

#     # Compute the average to determine zero-point offset
#     zero_accel = [total_accel[i] / num_samples for i in range(3)]
#     zero_gyro = [total_gyro[i] / num_samples for i in range(3)]

#     print("Calibration complete.")

#     return zero_accel, zero_gyro

# # fuse the accelerometer and gyroscope data together and calculate the pitch and roll
# def gyroSensorFusion(lastTime, gryo, pitch, roll, alpha, dt):
#     current_time = monotonic()
#     dt = current_time - lastTime
#     lastTime = current_time

#     # Get accelerometer and gyroscope data and subtract zero-point offsets
#     accel = gryo.acceleration
#     gyro = gryo.gyro
#     adjusted_accel = [accel[i] - zero_accel[i] for i in range(3)]
#     adjusted_gyro = [gyro[i] - zero_gyro[i] for i in range(3)]

#     # Calculate pitch and roll from the accelerometer
#     accel_pitch, accel_roll = calculate_pitch_and_roll(adjusted_accel)

#     # Integrate the gyroscope data to calculate the angular change (in degrees)
#     gyro_pitch_rate = adjusted_gyro[0] * (180.0 / math.pi)  # Convert from rad/s to degrees/s
#     gyro_roll_rate = adjusted_gyro[1] * (180.0 / math.pi)  # Convert from rad/s to degrees/s
    
#     # Complementary filter to fuse accelerometer and gyroscope data
#     pitch = alpha * (pitch + gyro_pitch_rate * dt) + (1 - alpha) * accel_pitch
#     roll = alpha * (roll + gyro_roll_rate * dt) + (1 - alpha) * accel_roll

#     # Print the results
#     # print(f"Pitch: {pitch:.2f}°, Roll: {roll:.2f}°")

#     return pitch, roll, alpha, dt, lastTime

def strptime(date_string, format_string):
    # Supported format specifiers
    format_specifiers = {
        "%Y": 2,  # Year without century
        "%m": 2,  # Month as zero-padded decimal number
        "%d": 2,  # Day of the month as zero-padded decimal number
        "%H": 2,  # Hour (24-hour clock) as zero-padded decimal number
        "%M": 2,  # Minute as zero-padded decimal number
        "%S": 2   # Second as zero-padded decimal number
    }

    # Map positions of the format specifiers to extract data from date_string
    positions = {}
    position = 0
    for part in format_string.split():
        for fmt in format_specifiers:
            if fmt in part:
                positions[fmt] = position
                position += format_specifiers[fmt]
                part = part.replace(fmt, '')  # Remove specifier to handle separators
        position += len(part)  # Account for separators in the format

    # Extract date components from the date_string
    year = int(date_string[positions["%Y"]:positions["%Y"] + format_specifiers["%Y"]])
    month = int(date_string[positions["%m"]:positions["%m"] + format_specifiers["%m"]])
    day = int(date_string[positions["%d"]:positions["%d"] + format_specifiers["%d"]])
    hour = int(date_string[positions["%H"]:positions["%H"] + format_specifiers["%H"]])
    minute = int(date_string[positions["%M"]:positions["%M"] + format_specifiers["%M"]])
    second = int(date_string[positions["%S"]:positions["%S"] + format_specifiers["%S"]])

    # Create and return an adafruit_datetime.Datetime object
    return datetime.datetime(year, month, day, hour, minute, second)

def setupMode(statusString):
    statusString.text = "Config mode!"

    disconnectedText = "Awaiting BLE\nconnection"
    connectedText = "1 - Set WiFi SSID\n2 - Set WiFi Pwd\n3 - Update RTC\n4 - Update\n\nR - Restart"
    uartText = "1 - Set WiFi SSID\n2 - Set WiFi Pwd\n3 - Set RTC (format 'DD/MM/YYYYHH:MM:SS')\n4 - Update\n\nR - Restart\n\nTo issue command, type '#:<data>, for example: 1:ExampleSSID\n"

    ble = BLERadio()
    uart = UARTService()
    advertisement = ProvideServicesAdvertisement(uart)

    while True:
        ble.start_advertising(advertisement)
        while not ble.connected:
            if (statusString.text != disconnectedText): # Update the text to show you can connect to the device
                statusString.text = disconnectedText

        # Now we're connected

        uart.reset_input_buffer()

        uartUpdateString = ""

        while ble.connected:
            if (statusString.text != connectedText):
                statusString.text = connectedText
                uart.write(str("\n" + str(uartUpdateString)) + "\n" + str(uartText))

                uartUpdateString = "\n" # Reset the string

            # print(uart.in_waiting)

            if (uart.in_waiting > 0):
                print("Message recieved!")
                data = []

                data = uart.readline()
                data = data.decode("utf-8")

                print()
                print("Recieved:", data)
                print(data[0])
                
                if (data[0] == '1'): # Update SSID
                    if (data[1] == ':'):
                        ssid = []
                        
                        count = 2

                        while (data[count] != '\n'):
                            ssid.append(data[count])
                            count += 1

                        ssid = b''.join(ssid).decode("utf-8")

                        # TODO - clear the old SSID and write the new one to NVM
                        # Perhaps with a bit flag to say if an SSID has been set or not?

                        statusString.text = "SSID updated!"
                        uartUpdateString = "SSID Updated!\n"
                        sleep(2) # Sleep to avoid the screen instantly switching

                    else:
                        pass # Invalid sequence, ignore

                elif(data[0] == '2'): # Update Password
                    if (data[1] == ':'):
                        wifiPassword = []
                        
                        count = 2

                        while (data[count] != '\n'):
                            wifiPassword.append(data[count])
                            count += 1

                        wifiPassword = b''.join(wifiPassword).decode("utf-8")   

                        # TODO - clear the old password and write the new one to NVM
                        # Perhaps with a bit flag to say if an password has been set or not?

                        statusString.text = "Password\nupdated!"
                        uartUpdateString = "Password Updated!\n"
                        sleep(2) # Sleep to avoid the screen instantly switching

                elif (data[0] == '3'): # Update RTC
                    if (data[1] == ':'):
                        timeString = []
                        
                        count = 2

                        while (data[count] != '\n'):
                            timeString.append(data[count])
                            count += 1

                        timeString = ''.join(timeString)

                        timeObject = strptime(timeString, "%Y/%m/%d%H:%M:%S")    
                        print(timeObject.ctime())                    

                        statusString.text = "RTC\nupdated!"
                        uartUpdateString = "RTC Updated with - " + timeString + "!\n"
                        sleep(2) # Sleep to avoid the screen instantly switching

                elif (data[0] == b'4'): # Check for updates
                    uart.write("Not yet implemented...")

                    statusString.text = "Not yet\nimplemented..."
                    sleep(2) # Sleep to avoid the screen instantly switching

                elif (data[0] == b'R'):
                    supervisor.reload() # TODO: Check stability

        # If we got here, we lost the connection. Go up to the top and start
        # advertising again and waiting for a connection.


tft_pins = dict(board.TFT_PINS)

tft_timings = {
    "frequency": 16000000,
    "width": 480,
    "height": 480,
    "hsync_pulse_width": 20,
    "hsync_front_porch": 40,
    "hsync_back_porch": 40,
    "vsync_pulse_width": 10,
    "vsync_front_porch": 40,
    "vsync_back_porch": 40,
    "hsync_idle_low": False,
    "vsync_idle_low": False,
    "de_idle_high": False,
    "pclk_active_high": False,
    "pclk_idle_high": False,
}

init_sequence_tl034wvs05 = bytes((
    b'\xff\x05w\x01\x00\x00\x13'
    b'\xef\x01\x08'
    b'\xff\x05w\x01\x00\x00\x10'
    b'\xc0\x02;\x00'
    b'\xc1\x02\x12\n'
    b'\xc2\x02\x07\x03'
    b'\xc3\x01\x02'
    b'\xcc\x01\x10'
    b'\xcd\x01\x08'
    b'\xb0\x10\x0f\x11\x17\x15\x15\t\x0c\x08\x08&\x04Y\x16f-\x1f'
    b'\xb1\x10\x0f\x11\x17\x15\x15\t\x0c\x08\x08&\x04Y\x16f-\x1f'
    b'\xff\x05w\x01\x00\x00\x11'
    b'\xb0\x01m'
    b'\xb1\x01:'
    b'\xb2\x01\x01'
    b'\xb3\x01\x80'
    b'\xb5\x01I'
    b'\xb7\x01\x85'
    b'\xb8\x01 '
    b'\xc1\x01x'
    b'\xc2\x01x'
    b'\xd0\x01\x88'
    b'\xe0\x03\x00\x00\x02'
    b'\xe1\x0b\x07\x00\t\x00\x06\x00\x08\x00\x0033'
    b'\xe2\r\x11\x1133\xf6\x00\xf6\x00\xf6\x00\xf6\x00\x00'
    b'\xe3\x04\x00\x00\x11\x11'
    b'\xe4\x02DD'
    b'\xe5\x10\x0f\xf3=\xff\x11\xf5=\xff\x0b\xef=\xff\r\xf1=\xff'
    b'\xe6\x04\x00\x00\x11\x11'
    b'\xe7\x02DD'
    b'\xe8\x10\x0e\xf2=\xff\x10\xf4=\xff\n\xee=\xff\x0c\xf0=\xff'
    b'\xe9\x026\x00'
    b'\xeb\x07\x00\x01\xe4\xe4D\xaa\x10'
    b'\xec\x02<\x00'
    b'\xed\x10\xffEg\xfa\x01+\xcf\xff\xff\xfc\xb2\x10\xafvT\xff'
    b'\xef\x06\x10\r\x04\x08?\x1f'
    b'\xff\x05w\x01\x00\x00\x00'
    b'5\x01\x00'
    b':\x01f'
    b'\x11\x80x'
    b')\x802'
))

class GroupItems:
    def __init__(self, large_numbers, tiny_numbers, large_characters):
        self.SpdTapeGreyForeground = Rect(x=0, y=54, width=74, height=426, fill=0x8b8b8b)
        self.SpdTapeWhiteBorder = Rect(x=74, y=278, width=2, height=202, fill=0xFFFFFF)
        self.SpdTapeBlackPixelBorder = Rect(x=76, y=278, width=1, height=202, fill=0x0)

        self.altTapeGreyForeground = Rect(x=378, y=54, width=102, height=426, fill=0x8b8b8b)
        self.altTapeWhiteBorder = Rect(x=376, y=317, width=2, height=163, fill=0xFFFFFF)
        self.altTapeBlackPixelBorder = Rect(x=375, y=317, width=1, height=163, fill=0x0)

        self.blackAirspeedCoverRectBackground = Rect(x=0, y=202, width=89, height=76, fill=0x0)
        self.whiteAirspeedCoverRectOutline = Rect(x=1, y=203, width=87, height=74, fill=0xFFFFFF)
        self.blackAirspeedCoverRectForeground = Rect(x=6, y=208, width=77, height=64, fill=0x0)

        self.blackAltCoverRectBackground = Rect(x=361, y=202, width=119, height=115, fill=0x0)
        self.whiteAltCoverRectOutline = Rect(x=362, y=203, width=117, height=113, fill=0xFFFFFF)
        self.blackAltCoverRectUpForeground = Rect(x=367, y=208, width=107, height=64, fill=0x0)
        self.blackAltCoverRectDownForeground = Rect(x=367, y=277, width=107, height=34, fill=0x0)

        self.blackTopBarBackground = Rect(x=0, y=0, width=480, height=54, fill=0x0)
        self.whiteTopBoxOutline = Rect(x=1, y=1, width=104, height=52, fill=0xFFFFFF)
        self.blackTopBoxForeground = Rect(x=4, y=4, width=98, height=46, fill=0x0)

        self.master_tile_grid = displayio.TileGrid(masterBitmap, pixel_shader=masterPalette) # Create a TileGrid to hold the bitmap

        # Setup the Altitude and Airspeed numbers
        self.airspeed_hundred = displayio.TileGrid(large_numbers[0][0], pixel_shader=large_numbers[0][1], x=10, y=225) # This will always be zero!
        self.airspeed_ten = displayio.TileGrid(large_numbers[0][0], pixel_shader=large_numbers[0][1], x=34, y=225)
        self.airspeed_digit = displayio.TileGrid(large_numbers[0][0], pixel_shader=large_numbers[0][1], x=58, y=225)

        self.altitude_ten_thousand = displayio.TileGrid(large_numbers[0][0], pixel_shader=large_numbers[0][1], x=372, y=222) # (415, 240)
        self.altitude_thousand = displayio.TileGrid(large_numbers[0][0], pixel_shader=large_numbers[0][1], x=396, y=222)
        self.altitude_hundred = displayio.TileGrid(tiny_numbers[0][0], pixel_shader=tiny_numbers[0][1], x=420, y=227)
        self.altitude_ten = displayio.TileGrid(tiny_numbers[0][0], pixel_shader=tiny_numbers[0][1], x=438, y=227)
        self.altitude_digit = displayio.TileGrid(tiny_numbers[0][0], pixel_shader=tiny_numbers[0][1], x=456, y=227)

        self.day_first_letter = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=10, y=10) # (50, 25)
        self.day_second_letter = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=42, y=10) # TODO: This needs changing to large characters when available
        self.day_third_letter = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=74, y=10)

        self.date_day_first = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=240, y=5) # (350, 25)
        self.date_day_second = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=262, y=5)
        self.date_day_slash = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=284, y=5)
        self.date_month_first = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=306, y=5)
        self.date_month_second = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=328, y=5) 
        self.date_month_slash = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=350, y=5)
        self.date_year_first = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=372, y=5)
        self.date_year_second = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=394, y=5)
        self.date_year_third = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=416, y=5)
        self.date_year_fourth = displayio.TileGrid(large_characters["slash"][0], pixel_shader=large_characters["slash"][1], x=438, y=5)

        # Setup and position the tile grids for the tapes
        self.heading_tile_grid = displayio.TileGrid(headingBitmap, pixel_shader=headingPalette, y=410)
        self.spd_tile_grid = displayio.TileGrid(iasTapeBitmap, pixel_shader=iasTapePalette, x=0)
        self.alt_tile_grid = displayio.TileGrid(altTapeBitmap, pixel_shader=altTapePalette, x=378)

        self.climb_rate_tile_grid = displayio.TileGrid(climbRateBitmap, pixel_shader=climbRatePalette, x=372, y=281)


print("\n\n\n\n")


# Configure the board and display
board.I2C().deinit()
i2c = board.I2C()
nvm = microcontroller.nvm

tft_io_expander = dict(board.TFT_IO_EXPANDER)

dotclockframebuffer.ioexpander_send_init_sequence(i2c, init_sequence_tl034wvs05, **tft_io_expander) 

fb = dotclockframebuffer.DotClockFramebuffer(**tft_pins, **tft_timings)
display = FramebufferDisplay(fb, auto_refresh=False)

print("\nLoading the font")
font = bitmap_font.load_font("/fonts/courB24.bdf") # TODO - Cut down the font.....
print("Finished loading the font")

print("\nConfiguring setupgroup")
# Configure the status string during setup
configurationGroup = displayio.Group()
statusString = Label(font, text="Restart to\nenter config\nmode", color=0xFFFFFF)
statusString.anchor_point = (0.5, 0.5)
statusString.anchored_position = (200, 200)
configurationGroup.append(statusString)

display.root_group = configurationGroup
display.auto_refresh = True
print("Finished configuring setupgroup")

# setupMode(statusString) # TODO - Comment when finished debugging

print("\nChecking for setup mode...")
setupRequest = nvm[:1] # Check the first byte of NVM to see if we should enter setup mode of not
setupRequest = setupRequest[0] == 0x01 # Convert to True False
if (setupRequest): 
    print("Setup mode requested!")
    nvm[0:1] = bytes([0]) # Clear the setupMode flag in NVM
    setupMode(statusString)

print("3 second grace period for setup power cycle")
nvm[0:1] = bytes([1]) # Set the setupMode flag in NVM
configStartTime = monotonic()

while(monotonic() - configStartTime < 3.0):
    pass # Do nothing for 3 seconds, were waiting for a power cycle

nvm[0:1] = bytes([0]) # Clear the setupMode flag in NVM
print("No setup requested. Continue with setup")

# Attempt to fetch the NTP time by connecting to wifi
print("\nConfiguring Wifi")
statusString.text = "Attempting\nwifi\nconnection\n1/10"
ntpTime = attemptWifiConnection()
print("Finished configuring wifi")

print("\nConfiguring RTC")
statusString.text = "Configuring\nRTC\n2/10"
rtc, timezonevar = setupClock(ntpTime) # Configure the RTC (update if NTP available) and calculate the timezone offset
print("Finished configuring RTC")

print("\nConfiguring gyroscope")
statusString.text = "Configuring\nGyroscope\n3/10"
# gyro = configureGyroscope(i2c)
# zero_accel, zero_gyro = calibrate_sensor(gyro, statusString) # Calibrate the sensors

# pitch = 0.0 # Variables required for sensor fusion calculation
# roll = 0.0
# alpha = 0.98  # A higher alpha (e.g., 0.98) relies more on the gyroscope, while a lower value (e.g., 0.95) relies more on the accelerometer.
# dt = 0.01  # Time step (10ms for 100Hz)
print("Finished configuring the gyroscope")

print("\nLoading master template")
statusString.text = "Loading\nBackground\nTemplate\n4/10"
masterBitmap, masterPalette = loadTemplate("/templates/ISIS_Background.bmp")
print("Finished loading master template")

print("\nLoading heading template")
statusString.text = "Loading\nHeading\nTape\n5/10"
headingBitmap, headingPalette = loadTemplate("/templates/Heading_Tape.bmp")
print("Finished loading heading template")

print("\nLoading IAS template")
statusString.text = "Loading\nIAS\nTape\n6/10"
iasTapeBitmap, iasTapePalette = loadTemplate("/templates/IAS_Tape.bmp")
print("Finished loading IAS template")

print("\nLoading Altitude template")
statusString.text = "Loading\nAltitude\nTape\n7/10"
altTapeBitmap, altTapePalette = loadTemplate("/templates/Alt_Tape.bmp")
print("Finished loading Altitude template")

print("\nLoading climb-rate template")
statusString.text = "Loading\climb-rate\nTape\n8/10"
climbRateBitmap, climbRatePalette = loadTemplate("/templates/climb_rate.bmp")
print("Finished loading climb-rate template")

print("\nLoading the numbers")
statusString.text = "Loading\nCustom\nFont\n9/10"
large_numbers, tiny_numbers, large_characters = loadCustomFont()
print("Finished loading the numbers")

print("\nSetting up the group")
statusString.text = "Configuring\nDisplay\n10/10"

groupItems = GroupItems(large_numbers, tiny_numbers, large_characters)
group = displayio.Group()
group = setupGroup(group, groupItems)

print("Finished setting up the group")

# Add the Group to the Display
display.root_group = group

AIRSPEED_TAPE_BASE = -230 # Correct
ALTITUDE_TAPE_BASE = -3195 # Correct
HEADING_TAPE_BASE = 16 # Correct

AIRSPEED_TAPE_OFFSET = 3.4 # 3.4 - Knots. 7.5 - kph 
ALTITUDE_TAPE_OFFSET = 45 # 45 - Knots. TBD - kph - This is using the wrong scale for the AltTape currently. Might need to update in the future
HEADING_TAPE_OFFSET = -10 # Correct

frame_count = 0
start_time = monotonic()

while True:
    # Calculate and show (if requested) the FPS
    start_time, frame_count = calculateFPS(start_time, frame_count, showFPS=False)

    # Updating the time labels --------------------------------------------

    # Fetch the time at the start of each frame
    rtcTime = getTimeCorrectTimezone(rtc, timezonevar)

    # Airspeed - No need to update the hundreds. It will always be 0
    groupItems.airspeed_ten.bitmap = large_numbers[(rtcTime.hour // 10 % 10)][0]
    groupItems.airspeed_digit.bitmap = large_numbers[(rtcTime.hour % 10)][0]

    # Altitude
    groupItems.altitude_ten_thousand.bitmap = large_numbers[(rtcTime.minute // 10 % 10)][0]
    groupItems.altitude_thousand.bitmap = large_numbers[(rtcTime.minute % 10)][0]

    # Day
    day = formatDay(rtcTime)
    groupItems.day_first_letter.bitmap = large_characters[day[0]][0]
    groupItems.day_second_letter.bitmap = large_characters[day[1]][0]
    groupItems.day_third_letter.bitmap = large_characters[day[2]][0]

    # Date
    date = formatDate(rtcTime)
    groupItems.date_day_first.bitmap = large_numbers[int(date[0])][0]
    groupItems.date_day_second.bitmap = large_numbers[int(date[1])][0]
    groupItems.date_month_first.bitmap = large_numbers[int(date[3])][0]
    groupItems.date_month_second.bitmap = large_numbers[int(date[4])][0]
    groupItems.date_year_first.bitmap = large_numbers[int(date[6])][0]
    groupItems.date_year_second.bitmap = large_numbers[int(date[7])][0]
    groupItems.date_year_third.bitmap = large_numbers[int(date[8])][0]
    groupItems.date_year_fourth.bitmap = large_numbers[int(date[9])][0]

    # Update the tape positions to align them with the time
    groupItems.heading_tile_grid.x = HEADING_TAPE_BASE + (rtcTime.second * HEADING_TAPE_OFFSET)
    groupItems.spd_tile_grid.y = int(AIRSPEED_TAPE_BASE + (rtcTime.hour * AIRSPEED_TAPE_OFFSET))
    groupItems.alt_tile_grid.y = int(ALTITUDE_TAPE_BASE + (rtcTime.minute * ALTITUDE_TAPE_OFFSET))
