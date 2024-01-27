import serial

from config import config

debug = config['debug']

if debug == False:
    class Talker:
        TERMINATOR = '\r'.encode('UTF8')

        def __init__(self, name, timeout=1):
            self.name = name
            self.serial = serial.Serial(name, 115200, timeout=timeout)

        def send(self, text: str):
            line = '%s\r\f' % text
            self.serial.write(line.encode('utf-8'))
            reply = self.receive()
            reply = reply.replace('>>> ','') # lines after first will be prefixed by a propmt

        def receive(self) -> str:
            line = self.serial.read_until(self.TERMINATOR)
            return line.decode('UTF8').strip() + ' ' + self.name

        def close(self):
            self.serial.close()