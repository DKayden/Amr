from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext
)
from pymodbus.server import StartAsyncSerialServer

from pymodbus import __version__ as pymodbus_version
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.framer import ModbusRtuFramer

class ModbusServer():
    def __init__(self) -> None:
        self.datablock_holding_register = ModbusSequentialDataBlock(0x00, [0] * 30)
        self.datablock_input_register = ModbusSequentialDataBlock(0x00, [0] * 30)
        self.context_serial = ModbusServerContext(slaves={
                0x01: ModbusSlaveContext(
                    hr=self.datablock_holding_register,
                    ir=self.datablock_input_register,
                ),
            },single=False)
    
    async def run_server_serial(self):
        print("run modbus server")
        server = await StartAsyncSerialServer(
            context=self.context_serial,  # Data storage
            identity=self.identity,  # server identify
            # timeout=1,  # waiting time for request to complete
            port='/dev/ttyUSB0',  # serial port
            # custom_functions=[],  # allow custom handling
            framer=ModbusRtuFramer,  # The framer strategy to use
            stopbits=1,  # The number of stop bits to use
            bytesize=8,  # The bytesize of the serial messages
            parity="N",  # Which kind of parity to use
            baudrate=115200,  # The baud rate to use for the serial device
            # handle_local_echo=False,  # Handle local echo of the USB-to-RS485 adaptor
            # ignore_missing_slaves=True,  # ignore request to a missing slave
            # broadcast_enable=False,  # treat slave_id 0 as broadcast address,
            # strict=True,  # use strict timing, t1.5 for Modbus RTU
        )

        # return server
