from socket import socket
from frame import tranmit
from api import navigation, status, control
from modbus_server import ModbusServer

import logging
import socket


class Color:
    red = 8
    green = 2
    yellow = 10
    green_blink = 11


class Dir:
    stop = 0
    cw_in = 1
    ccw_in = 2
    cw_out = 3
    ccw_out = 4


class Stopper:
    back_off = 1
    back_on = 2
    front_off = 3
    front_on = 4
    all_off = 5
    all_on = 6


modbus = ModbusServer()


class RobotAPI:
    def __init__(self, host: str):
        self.host = host
        self.api_robot_navigation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.api_robot_status = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.api_robot_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.data_status = None
        self.keys = {
            "keys": [
                "confidence",
                "DI",
                "DO",
                "current_station",
                "charging",
                "last_station",
                "vx",
                "vy",
                "blocked",
                "block_reason",
                "battery_level",
                "task_status",
                "target_id",
                "emergency",
                "reloc_status",
                "fatals",
                "errors",
                "warnings",
                "notices",
                "current_ip",
                "x",
                "y",
                "fork_height",
                "area_ids",
                "angle",
                "target_dist",
                "path",
                "unfinished_path",
            ],
            "return_laser": False,
            "return_beams3D": False,
        }
        self.conveyor = {"type": Dir.stop, "height": 0.00}
        self.stopper_actions = {
            ("open", "cw"): Stopper.back_on,
            ("open", "ccw"): Stopper.front_on,
            ("open", "all"): Stopper.all_on,
            ("close", "cw"): Stopper.back_off,
            ("close", "ccw"): Stopper.front_off,
            ("close", "all"): Stopper.all_off,
        }

    def connect_all(self):
        self.api_robot_status.settimeout(10)
        self.api_robot_status.connect((self.host, 19204))
        self.api_robot_navigation.settimeout(10)
        self.api_robot_navigation.connect((self.host, 19206))
        self.api_robot_control.settimeout(10)
        self.api_robot_control.connect((self.host, 19205))

    def connect_status(self):
        self.api_robot_status.settimeout(10)
        self.api_robot_status.connect((self.host, 19204))

    def connect_navigation(self):
        self.api_robot_navigation.settimeout(10)
        self.api_robot_navigation.connect((self.host, 19206))

    def connect_control(self):
        self.api_robot_control.settimeout(10)
        self.api_robot_control.connect((self.host, 19205))

    def navigation(self, json_string: dict):
        result = tranmit.sendAPI(
            self.api_robot_navigation, navigation.robot_task_go_target_req, json_string
        )
        logging.info("Result's navigation: " + str(result))

    def nav_cancel(self):
        return tranmit.sendAPI(
            self.api_robot_navigation, navigation.robot_task_cancel_req, {}
        )

    def nav_pause(self):
        return tranmit.sendAPI(
            self.api_robot_navigation, navigation.robot_task_pause_req, {}
        )

    def nav_resume(self):
        return tranmit.sendAPI(
            self.api_robot_navigation, navigation.robot_task_resume_req, {}
        )

    def status(self):
        self.data_status = tranmit.sendAPI(
            self.api_robot_status, status.robot_status_all1_req, self.keys
        )

    def confirm_local(self):
        return tranmit.sendAPI(
            self.api_robot_control, control.robot_control_comfirmloc_req, {}
        )

    def relocation(self, data_position: True):
        return tranmit.sendAPI(
            self.api_robot_control, control.robot_control_reloc_req, data_position
        )

    def control_conveyor(self, type: str):
        if type == "stop":
            modbus.datablock_input_register.setValues(address=0x05, values=Dir.stop)
        elif type == "cw":
            modbus.datablock_input_register.setValues(address=0x05, values=Dir.cw_out)
        elif type == "ccw":
            modbus.datablock_input_register.setValues(address=0x05, values=Dir.ccw_out)
        else:
            pass

    def check_conveyor(self, type: str):
        if type == "cw":
            return (
                modbus.datablock_holding_register.getValues(address=0x04, count=1)[0]
                == Dir.cw_out
            )
        elif type == "ccw":
            return (
                modbus.datablock_holding_register.getValues(address=0x04, count=1)[0]
                == Dir.ccw_out
            )
        elif type == "stop":
            return (
                modbus.datablock_holding_register.getValues(address=0x04, count=1)[0]
                == Dir.stop
            )
        print("Truyền sai hành động!!!")
        return False

    def control_stopper(self, data):
        status = data["status"]

        if status == "true":
            action_value = Stopper.all_on
        elif status == "false":
            action_value = Stopper.all_off
        else:
            action = data["action"]
            action_value = self.stopper_actions.get((status, action))
        if action_value is not None:
            modbus.datablock_input_register.setValues(
                address=0x04, values=[action_value]
            )
        else:
            pass

    def check_stopper(self, status, action):
        action_value = self.stopper_actions.get((status, action))
        if action_value is not None:
            return (
                modbus.datablock_holding_register.getValues(address=0x03, count=1)[0]
                == action_value
            )

    def control_lift(self, height: int):
        try:
            modbus.datablock_input_register.setValues(address=0x03, values=[height])
            return {"result": True}
        except Exception as E:
            return {"result": False}

    def check_conveyor_height(self, height: int):
        return (
            modbus.datablock_holding_register.getValues(address=0x02, count=1)[0]
            == height
        )

    def check_robot_location(self, location: str):
        if self.data_status["task_status"] == 4:
            if (self.data_status["current_station"]) == location:
                return True
        return False

    def check_sensor(self):
        return modbus.datablock_holding_register.getValues(address=0x0A, count=10)

    def set_led(self, color: str):
        if color == "red":
            modbus.datablock_input_register.setValues(1, Color.red)
        elif color == "yellow":
            modbus.datablock_input_register.setValues(1, Color.yellow)
        elif color == "green":
            modbus.datablock_input_register.setValues(1, Color.green)
        else:
            print("Color error")

    def monitor(self, data: dict):
        return tranmit.sendAPI(
            self.api_robot_control, control.robot_control_motion_req, data
        )

    def change_emergency(self, status):
        if status == "true":
            self.data_status["emergency"] = True
            return {"result": True, "status": status}
        elif status == "false":
            self.data_status["emergency"] = False
            return {"result": False, "status": status}
