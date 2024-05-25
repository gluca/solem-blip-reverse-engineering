import struct
import binascii
import time
from bluepy3 import btle
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

class SolemBLIP:

    class BLIPNotification(btle.DefaultDelegate):
        def __init__(self, params, debug=False):
            btle.DefaultDelegate.__init__(self)
            self.__debug = debug
            if self.__debug:
                print(f"Created delegate for handle {params}")
            # ... initialise here

        def handleNotification(self, cHandle, data):       
            # ... perhaps check cHandle
            # ... process 'data'
            btle.DefaultDelegate.__init__(self)       
            if self.__debug:
                print(f"Notification from {cHandle}: {binascii.hexlify(data)}")


    def __handleNotifications(self,num):
        while num and self.__notificationsEnabled:
            if self.__blConnection.waitForNotifications(0.5):
                # handleNotification() was called
                num = num - 1
            else:
                if self.__debug:
                    print("Waiting...")

    def __init__(self,address):
        self.__debug = False
        self.connected = False     
        self.address = address
        self.__blConnection = btle.Peripheral()
        self.name = None
        self.preferredParams =  b'0x00'
        self.__notifyier = None
        self.__writer = None
        self.__notificationsEnabled = False
        
    def __writeCommand(self,cmd):
        if self.__debug:
            print(f"Sending command:{binascii.hexlify(cmd)}")
        self.__writer.write(cmd)
        self.__handleNotifications(3)
        if self.__debug:
            print("Committing (command:0x3b00)")
        self.__writer.write(struct.pack(">H",0x3b00))
        self.__handleNotifications(3)
    
    def on(self):
        self.__writeCommand(struct.pack(">HBHH",0x3105,0xa0,0x0001,0x0000))

    def off(self):
        self.__writeCommand(struct.pack(">HBHH",0x3105,0xc0,0x0000,0x0000))

    def stopWatering(self):
        self.__writeCommand(struct.pack(">HBHH",0x3105,0x15,0x00ff,0x0000))

    def offDays(self,days):
        self.__writeCommand(struct.pack(">HBHH",0x3105,0xc0,days,0x0000))

    def startWateringAll(self,minutes):
        secs=minutes*60
        self.__writeCommand(struct.pack(">HBHH",0x3105,0x11,0x0000,secs))

    def startWatering(self,station,minutes):
        secs=minutes*60
        self.__writeCommand(struct.pack(">HBBBH",0x3105,0x12,station,0x00,secs))

    def runProgram(self,program):
        self.__writeCommand(struct.pack(">HBHH",0x3105,0x14,program,0x0000))
    
    def enableNotifications(self):
        self.__blConnection.setDelegate(self.BLIPNotification(self.__notifyier.getHandle(), self.__debug))
        self.__blConnection.writeCharacteristic(self.__notifyier.getHandle()+1, b"\x01\x00")
        self.__notificationsEnabled = True
        
    def disableNotifications(self):
        self.__blConnection.setDelegate(
                    self.BLIPNotification(self.__notifyier.getHandle(), self.__debug))
        self.__blConnection.writeCharacteristic(self.__notifyier.getHandle()+1, b"\x00\x00")                
        self.__notificationsEnabled = False


    def connect(self, retries, sleep = 2):
        self.connected = False
        if self.__debug:
            print("Connecting")
        
        while retries:
            try:
                self.__blConnection=btle.Peripheral(self.address,btle.ADDR_TYPE_RANDOM)
                self.connected = True
                break
            except btle.BTLEException as e:
                retries = retries - 1
                if self.__debug:
                    print("BLE Exception:", e)
                    print(f"Remaining: {retries} tentatives")
                if retries > 0:
                    time.sleep(sleep)

        if not self.connected:
            raise btle.BTLEException("Unable to connect after reties")
        else:    
            if self.__debug:
                print("Connected!");
            characteristics = self.__blConnection.getCharacteristics()
            
            for characteristic in characteristics:
                #print("{}, hnd={}, supports {}".format(characteristic, hex(characteristic.handle), characteristic.propertiesToString()))
                if characteristic.handle == 0x02:
                    self.name=characteristic.read().decode("utf-8")
                elif characteristic.handle == 0x04:
                    app = characteristic.read()
                elif characteristic.handle == 0x06:
                    self.preferredParams = characteristic.read()
                elif characteristic.handle == 0x0d:
                    self.__notifyier = characteristic
                elif characteristic.handle == 0x10:
                    self.__writer = characteristic

    def disconnect(self):
        if self.connected:
            try:
                self.__blConnection.disconnect();
            except btle.BTLEException as e:
                if self.__debug:
                    print("BLE Exception while disconnecting:", e)
        self.connected = False
try:
    irrigatore=SolemBLIP("C8:B9:61:0A:47:FD")
    print("Connecting...")
    irrigatore.connect(10)
    irrigatore.enableNotifications();
    print(f"Name: {irrigatore.name}")
    print("Water brain on")
    irrigatore.on()
    print("Stop Watering")
    irrigatore.stopWatering();
    print("Stopped")
except btle.BTLEException as e:
    print("BLE Exception:", e)

finally:
    irrigatore.disconnect()
    print("Done.")
