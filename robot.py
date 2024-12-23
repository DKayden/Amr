from control import RobotAPI, Color
from config import HOST_ROBOT
from modbus_server import ModbusServer

class Robot():
    def __init__(self) -> None:
        self.robot_api = RobotAPI(HOST_ROBOT)
        self.server_modbus = ModbusServer()
        self.color = Color()
        

    def check_robot_location(self, location: str) -> bool:
        for _ in range(5):
            data_status = self.robot_api.status()
            if data_status['current_station'] == location:
                print(f'Robot is at {location}')
                return True
            else:
                print(f'Robot is not at {location}')
        return False
    # def poll_status(self):
    #     while True:
    #         self.robot_api.status()
    #         self._update_led_status()
    #         self._update_robot_status()

    # def _update_led_status(self) -> None:
    #     if self._is_error_state():
    #         self._set_led('red')
    #     elif self._is_battery_low():
    #         self._handle_battery_status()
    #     else:
    #         self._set_led('green')

    # def _is_error_state(self) -> bool:
    #     return (self.robot_api.data_status['blocked'] or
    #             self.robot_api.data_status['emergency'] or
    #             self.error)
    
    # def _is_battery_low(self) -> bool:
    #     return (self.robot_api.data_status['battery_level'] < 0.2 or
    #             self.robot_api.data_status['charging'])
    
    # def _handle_battery_status(self) -> None:
    #     self._set_led('yellow')
    
    # def _set_led(self, color: str) -> None:
    #     self.server_modbus.datablock_input_register.setValues(1, getattr(self.color, color))
    #     self.led = color

    # def _update_robot_status(self) -> None:
    #     self.robot_api.data_status.update({
    #         'led': self.led,
    #         'mode' : self.robot_api.mode,
    #         'message' : self.robot_api.message,
    #     })