#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
ser_cmd.py

Send commands to hw.

Requires...see requirements.txt
pip install -r requirements.txt

Tested with python 3.7

Test communication with (if more than one port, enter the one connected to the unit):
$ python ser_cmd.py -c version
Available port(s):
Port 0: /dev/ttyACM0
Port 1: /dev/ttyS4
Port 2: /dev/ttyS0
Enter port number to use: 1
The port seems not to be connected to the unit. Try another port.
Enter port number to use: 0
cpufw 1.0 4798 dspfw 1.0 BAP96k2i8oDynBSurrCustXo 4797
fphw none fpfw none 0
200 OK

If port is known:
$ python ser_cmd.py -p /dev/ttyACM0 -c version
...
'''

import argparse
import glob
import logging
import serial
import serial.tools.list_ports
import sys
import time


class SerialPorts(object):
    def __init__(self):
        self._ports = []

    def get_ports(self):
        self.scan_ports()
        return self._ports

    def scan_ports(self):
        # Try to find the serial port
        # ref: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
        logger = logging.getLogger('scan_ports')
        logger.setLevel(logging.CRITICAL)
        logger.info('Starting...')
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        else:
            logger.error('Unsupported OS')
            return None

        available_ports = []
        logger.info('Scanning ports...')
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                available_ports.append(port)
            except serial.SerialException:
                pass

        logger.info('Available ports:')
        for port in available_ports:
            logger.info(port)

        self._ports = available_ports


def request_bap(com, cmd):
    if not isinstance(cmd, str):
        raise TypeError('cmd must be str')

    # Flush
    _ = b''
    while com.inWaiting():
        _ += com.read(com.inWaiting())
        time.sleep(0.01)

    com.write(''.join([cmd, '\n']).encode())
    r = b''
    timeout = 2
    sleeptime = 0.01
    t0 = time.time()
    while True:
        while com.inWaiting():
            r += com.read(com.inWaiting())
            time.sleep(sleeptime)
        if b'\n\n' in r:
            break
        if (time.time() - t0) > timeout:
            raise Exception('timeout before end of message.')
        time.sleep(sleeptime)
    return r.decode('utf-8')

def send(com, cmd):
    try:
        return request_bap(com, cmd)
    except Exception as e:
        logger.error(e)
        return 'error'

def print_resp(resp):
    try:
        print('{}'.format(resp.strip()))
    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    # Handle arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--command",
                        help="Execute command and exit")
    parser.add_argument("-p", "--port",
                        help="Set serial port, e.g. /dev/ttyACM0")
    parser.add_argument("-v", "--verbosity",
                        action="count",
                        default=0,
                        help="Increase logging information, -v=INFO, -vv=DEBUG")
    args = parser.parse_args()

    log_level = logging.CRITICAL  # default
    if args.verbosity >= 2:
        log_level = logging.DEBUG
    elif args.verbosity >= 1:
        log_level = logging.INFO

    logging.basicConfig(level=log_level)
    logger = logging.getLogger('ser_cmd')
    logger.info('Setting logging level to {}'.format(repr(log_level)))

    if args.command:
        logger.info("cmd: {}".format(args.command))

    com = None
    if args.port:
        com = serial.Serial(port=args.port, baudrate=115200, timeout=0.01, rtscts=True)
    else:
        # Check ports
        ports = []
        while not ports:
            ports = SerialPorts().get_ports()
            if not ports:
                logger.critical('Cant find usb port. Check connection cable and press ENTER...')
                input()
            else:
                break

        print('Available port(s):')
        for n in range(len(ports)):
            print('Port {}: {}'.format(n, ports[n]))
        if len(ports) > 1:
            i = 0
            logger.info('Which port? Give number.')
            for port in ports:
                logger.info('{}: {}'.format(i, ports[i]))
                i += 1
            while True:
                port_num = input('Enter port number to use: ')
                port = ports[int(port_num)]
                com = serial.Serial(port=port, baudrate=115200, timeout=0.01, rtscts=True)
                resp = send(com, 'version')
                if 'error' in resp:
                    print('The port seems not to be connected to the unit. Try another port.')
                elif '200 OK' in resp:
                    break
                else:
                    break
        else:
            port = ports[0]

        if not com:
            com = serial.Serial(port=port, baudrate=115200, timeout=0.01, rtscts=True)

    try:
        if args.command:
            print_resp(send(com, args.command))
        else:
            print_resp(send(com, 'version'))
            print('')
            print("Enter command or (q)uit.")

            while True:
                cmd = input('> ')
                if cmd == 'q':
                    raise KeyboardInterrupt
                resp = send(com, cmd)
                print_resp(resp)
    except KeyboardInterrupt:
        print('Finished')
    com.close()
    exit(0)
