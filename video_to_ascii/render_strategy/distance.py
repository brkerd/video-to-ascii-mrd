import traceback
import serial
import struct

class distance:
    ser = serial.Serial('/dev/tty.usbserial-1130', 115200)

    def check_distance():
        bites = distance.ser.read(4)
        return struct.unpack('f',bites)[0]
        # Output line from serial

