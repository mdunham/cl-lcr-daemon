#!/usr/bin/env python2

# pip2 install pynmea2
# pip2 install geopy
# pip2 install serial

import os, sys, time, serial, pynmea2, zlib, base64, datetime
from daemon import Daemon
from Hologram.HologramCloud import HologramCloud
from geopy import distance
from subprocess import call


class GPSD(Daemon):
    """
    This is the main communications controller this collects GPS
    data and if we have moved more than 0.75 miles from the last 
    GPS location it gets sent to the back-end API.
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.location = (0, 0)
        truckFile = open("/etc/cl-lcr-truck", "r")
        uuidFile = open("/etc/cl-lcr-uuid", "r")
        self.truck = truckFile.readline().rstrip()
        self.uuid = uuidFile.readline().rstrip()
        uuidFile.close()
        truckFile.close()
        self.multiplier = 1
        currentDT = datetime.datetime.now()
        if currentDT.hour > 18 or currentDT.hour < 8:
            self.multiplier = 4
        else:
            self.multiplier = 1
    
    def addLocation(self, lat, lon):
        try:
            elapsed_time = time.time() - self.start_time
            if lat is None or lon is None:
                if elapsed_time > (230 * self.multiplier):
                    self.start_time = time.time()
                    self.callGps(True)
                return False
            moved = distance.distance(self.location, (lat, lon)).km
            if elapsed_time > (118 * self.multiplier):
                if moved > 0.50:
                    self.location = (lat, lon)
                    self.start_time = time.time()
                    self.compressGps(lat, lon)
                elif elapsed_time > (880 * self.multiplier):
                    self.start_time = time.time()
                    self.compressGps(lat, lon)
        except:
            sys.stderr.write("Add Location Error")
            pass
    
    def compressGps(self, lat, lon):
        try:
            currentDT = datetime.datetime.now()
            if currentDT.hour > 18 or currentDT.hour < 8:
                self.multiplier = 4
            else:
                self.multiplier = 1
            elapsed_time = time.time() - self.start_time
            moved = distance.distance(self.location, (lat, lon)).km
            if moved > 0.50 or elapsed_time > (880 * self.multiplier):
                self.start_time = time.time()
                gpsFile = open("/root/gps.in", "w")
                gpsFile.write((str(lat)+":"+str(lon)).encode('utf8'));
                gpsFile.close()
                call("/usr/local/bin/node /root/cl-lcr-daemon/gpsd/convert.js", shell=True)
                time.sleep(2)
                gpsFile2 = open("/root/gps.out", "r")
                message = gpsFile2.readline().rstrip()
                gpsFile2.close()
                self.hologram.sendMessage(message, topics=["gps"], timeout=20)
        except:
            sys.stderr.write("Compress GPS Error")
            pass
    
    def callGps(self, forceHologram=None):
        try:
            if self.location is None or self.location[0] is None or self.location[1] is None or forceHologram is not None:
                location = self.hologram.network.location
                i=0
                while location is None and i < 10:
                    location = self.hologram.network.location
                    time.sleep(1)
                    if location is None:
                        i += 1
                    else:
                        i = 10

                if location is not None:
                    self.location = (location.latitude,location.longitude)
                    self.start_time = time.time()
                    self.compressGps(self.location[0], self.location[1])
            else:
                self.start_time = time.time()
                self.compressGps(self.location[0], self.location[1])
        except:
            sys.stderr.write("Call GPS Error")
            pass
    
    def run(self):
        self.serialPort = serial.Serial("/dev/ttyAMA0", 9600, timeout=5)
        self.start_time = time.time() - 200
        self.hologram = HologramCloud({'devicekey':'ujk{]5pX'}, network='cellular')
        if self.hologram.network.getConnectionStatus() != 1:
            self.hologram.network.disconnect()
        try:
            result = self.hologram.network.connect()
            if result == False:
                sys.stderr.write("Failed to connect to cell network\n")
            else:
                self.hologram.openReceiveSocket()
                self.hologram.event.subscribe('message.received', self.receivedMessage)
        except:
            sys.stderr.write("connection error\n")
        gpsIn = ""
        while True:
            while gpsIn.find('GGA') == -1:
                elapsed_time = time.time() - self.start_time
                gpsIn = self.serialPort.readline()
                if elapsed_time > (1200 * self.multiplier):
                    self.start_time = time.time()
                    self.callGps()
            if gpsIn.find('GGA') != -1:
                try:
                    location = pynmea2.parse(gpsIn)
                    self.addLocation(location.latitude, location.longitude)
                    gpsIn = self.serialPort.readline()
                except:
                    gpsIn = self.serialPort.readline()
                    sys.stderr.write("Main Loop 2 Error")
                    pass
            
    def tail(self, f, n, offset=0):
        data = ""
        try:
            with open(f, 'r') as myfile:
                data=myfile.read()
                myfile.close()
            if data != "":
                n = int(n) * -1
                data = data[n:]
        except:
            data = "error"
        return data
    
    def receivedMessage(self):
        try:
            message = self.hologram.popReceivedMessage()
        except:
            message = hologram.popReceivedMessage()
        if ":" in message:
            parts = message.split(':')
        else:
            message = zlib.decompress(message)
            if ":" in message:
                parts = message.split(':')
            else:
                sys.stderr.write("Invalid message\n")
                return False
        if parts[0] == "gps":
            self.callGps()
        elif parts[0] == "gpsd":
            self.callGps(True)
        elif parts[0] == "cmd":
            try:
                sys.stderr.write("Running CMD: "+str(parts[1])+"\n")
                call(parts[1], shell=True)
            except:
                sys.stderr.write("Failed CMD"+str(parts[1])+"\n")
        elif parts[0] == "tail":
            message = self.tail(parts[2], parts[1])
            message = base64.b64encode(zlib.compress(("tail:"+parts[2]+":"+str(message)).encode('utf8'), 9))
            self.hologram.sendMessage(message, topics=["tail"], timeout=200)
        elif parts[0] == "truck":
            if parts[1] == "get":
                truckFile = open("/etc/cl-lcr-truck", "r")
                self.truck = truckFile.readline().rstrip()
                truckFile.close()
            elif parts[1] == "set":
                truckFile = open("/etc/cl-lcr-truck", "w")
                truckFile.truncate()
                truckFile.write(parts[2])
                truckFile.close()
                self.truck = parts[2]
            self.hologram.sendMessage(base64.b64encode(zlib.compress(("truck:"+self.truck).encode('utf8'), 9)), topics=["tail"])

if __name__ == "__main__":
    daemon = GPSD('/tmp/daemon-py-gpsd.pid', '/dev/null', '/var/log/gpsd.log', '/var/log/gpsd.err')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
