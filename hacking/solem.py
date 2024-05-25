import struct
import binascii
import time
from bluepy import btle
'''
Identified commands
--------------------------------
off permanently | 3105c000000000
off today       | 3105c000010000
off 2 days      | 3105c000020000
...             |
off 15 days:    | 3105c0000f0000
--------------------------------
on:             | 3105a000000000
--------------------------------
all stations XXXX seconds | 3105110000XXXX | XXXX: number of seconds, max 0xa8c0 = 12h
--------------------------------
31051400010000 dimi seara
31051400020000 avarie


3105120100012c spate 5 min
3105120200012c fata 5 min
3105120300012c intrare 5 min
31051203000268 intrare 10 min
stop manual:    | 31051500ff0000
--------------------------------
transmit:       | 3b00
'''

class BLIPNotification(btle.DefaultDelegate):
    def __init__(self, params):
        btle.DefaultDelegate.__init__(self)
        print(f"Created delegate for handle {params}")
        # ... initialise here

    def handleNotification(self, cHandle, data):       
        # ... perhaps check cHandle
        # ... process 'data'
        btle.DefaultDelegate.__init__(self)       
        print(f"Notification from {cHandle}: {binascii.hexlify(data)} {data}")

def handleNotifications(per, wait):
    while wait:
        if per.waitForNotifications(0.3):
            # handleNotification() was called
            continue
        else:
            print("Waiting...")
            wait = wait - 1


def irrigatorOn():
    return struct.pack(">HBHH",0x3105,0xa0,0x0001,0x0000)

def irrigatorOff():
    return struct.pack(">HBHH",0x3105,0xc0,0x0000,0x0000)

def stopWatering():
    return struct.pack(">HBHH",0x3105,0x15,0x00ff,0x0000)

def commit():
    return struct.pack(">H",0x3b00)

def irrigatorOffDays(days):
    return struct.pack(">HBHH",0x3105,0xc0,days,0x0000)

def startWateringAll(minutes):
    secs=minutes*60
    return struct.pack(">HBHH",0x3105,0x11,0x0000,secs)

def startWatering(station,minutes):
    secs=minutes*60
    return struct.pack(">HBBBH",0x3105,0x12,station,0x00,secs)

def runProgram(program):
    return struct.pack(">HBHH",0x3105,0x14,program,0x0000)

def resilientConnect(address, retries):
    global per
    while retries:
        try:
            per=btle.Peripheral(address,btle.ADDR_TYPE_RANDOM)
            return True
        except btle.BTLEException as e:
            print(f"BLE Exception:", e)
            retries = retries - 1
            if retries > 0:
                time.sleep(3)
    return False

per = btle.Peripheral()

try:
    if not resilientConnect("C8:B9:61:0A:47:FD",10):
        print(f"Failed to connect")
        exit
    print(f"Connected to Solem")
    characteristics = per.getCharacteristics()
    print(f"charachteristics read")
    for characteristic in characteristics:
        print("{}, hnd={}, supports {}".format(characteristic, hex(characteristic.handle), characteristic.propertiesToString()))
        #if characteristic.uuid == '00002a04-0000-1000-8000-00805f9b34fb':
        #    bytes = characteristic.read()
        #    print("Read {}", struct.unpack('BBBBBBH', bytes))

        if characteristic.uuid == '108b0002-eab5-bc09-d0ea-0b8f467ce8ee':
            characteristicWrite = characteristic

        elif characteristic.uuid == '108b0003-eab5-bc09-d0ea-0b8f467ce8ee':
            characteristicNotify = characteristic

    per.setDelegate(BLIPNotification(characteristicNotify.getHandle()))

    # Setup to turn notifications on, e.g.
    per.writeCharacteristic(characteristicNotify.getHandle()+1, b"\x01\x00")

    #3105-15-00ff-0000 - stop any manual watering program
    print(f"writing command")
    characteristicWrite.write(stopWatering())
    handleNotifications(per, 1)
    print(f"committing")
    characteristicWrite.write(commit())
    handleNotifications(per, 3)
    
    
except btle.BTLEException as e:
    print(f"BLE Exception:", e)

finally:
    per.disconnect() 
    print(f"Done.")
s