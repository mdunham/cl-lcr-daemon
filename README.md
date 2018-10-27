# Bluetooth to Serial Communications Daemon

This is NodeJS application sets up a Bluetooth service that allows the Cleveland Drivers mobile application to communicate with a Liquid Controls LCR-II meter via usb-serial.
 
__Note:__ macOS / Mac OS X, Linux, FreeBSD and Windows are currently are supported, but the instructions below are for a Raspberry Pi.

## Prerequisites

 * install [bleno]()
 * install [serialport]()

### Bleno on Linux

 * Kernel version 3.6 or above
 * ```libbluetooth-dev```
 * ```bluetoothd``` disabled, if BlueZ 5.14 or later is installed. Use ```sudo hciconfig hci0 up``` to power Bluetooth adapter up after stopping or disabling ```bluetoothd```.
    * ```System V```:
      * ```sudo service bluetooth stop``` (once)
      * ```sudo update-rc.d bluetooth remove``` (persist on reboot)
    * ```systemd```
      * ```sudo systemctl stop bluetooth``` (once)
      * ```sudo systemctl disable bluetooth``` (persist on reboot)

#### Ubuntu/Debian/Raspbian

```sh
sudo apt-get install bluetooth bluez libbluetooth-dev libudev-dev
```

Make sure ```node``` is on your path, if it's not, some options:
 * symlink ```nodejs``` to ```node```: ```sudo ln -s /usr/bin/nodejs /usr/bin/node```
 * [install Node.js using the NodeSource package](https://nodejs.org/en/download/package-manager/#debian-and-ubuntu-based-linux-distributions)

## Installation

 * Clone this repository: ```git clone https://github.com/mdunham/cl-lcr-deamon.git```
 * Change to the cl-lcr-daemon directory: ```cd cl-lcr-daemon/```
 * Install dependancies: ```npm install```
 * Start the daemon: ```npm start```