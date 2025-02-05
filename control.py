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
    def __init__(self, host:str):
        self.host = host
        self.api_robot_navigation = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.api_robot_status = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.api_robot_control = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.data_status = {}
        self.keys = {
            "keys":["confidence","DI","DO","current_station","charging","last_station","vx","vy","blocked","block_reason","battery_level","task_status","target_id","emergency","reloc_status","fatals","errors","warnings","notices","current_ip",'x','y','fork_height','area_ids', "angle", "target_dist", "path", "unfinished_path"],
            "return_laser":False,
            "return_beams3D":False
        }
        self.mode = 'auto'
        self.message = ""
        self.conveyor = {
            'type' : Dir.stop,
            'height' : 0.00
        }

    def connect_all(self):
        self.api_robot_status.settimeout(10)
        self.api_robot_status.connect((self.host,19204))
        self.api_robot_navigation.settimeout(10)
        self.api_robot_navigation.connect((self.host,19206))
        self.api_robot_control.settimeout(10)
        self.api_robot_control.connect((self.host,19205))

    def connect_status(self):
        self.api_robot_status.settimeout(10)
        self.api_robot_status.connect((self.host,19204))

    def connect_navigation(self):
        self.api_robot_navigation.settimeout(10)
        self.api_robot_navigation.connect((self.host,19206))

    def connect_control(self):
        self.api_robot_control.settimeout(10)
        self.api_robot_control.connect((self.host,19205))

    def navigation(self,json_string:dict):
        result = tranmit.sendAPI(self.api_robot_navigation, navigation.robot_task_go_target_req, json_string)
        logging.info("Result's navigation: "  + str(result))

    def nav_cancel(self):
        return tranmit.sendAPI(self.api_robot_navigation, navigation.robot_task_cancel_req,{})
    
    def nav_pause(self):
        return tranmit.sendAPI(self.api_robot_navigation, navigation.robot_task_pause_req,{})
    
    def nav_resume(self):
        return tranmit.sendAPI(self.api_robot_navigation, navigation.robot_task_resume_req,{})

    def status(self):
        result = tranmit.sendAPI(self.api_robot_status, status.robot_status_all1_req, self.keys)
        logging.info("Result's status: " + str(result))
        return result
    
    def confirm_local(self):
        return tranmit.sendAPI(self.api_robot_control, control.robot_control_comfirmloc_req,{})
    
    def relocation(self, data_position:True):
        return tranmit.sendAPI(self.api_robot_control, control.robot_control_reloc_req,data_position)

    def control_conveyor(self, type:str):
        if type == 'stop':
            modbus.datablock_input_register.setValues(address=0x05,values=Dir.stop)
            print("STOP")
            self.message = "Dừng băng tải"
        elif type == 'cw':
            modbus.datablock_input_register.setValues(address=0x05, values=Dir.cw_out)
            print("CW")
            self.message = "Quay băng tải"
        elif type == 'ccw':
            modbus.datablock_input_register.setValues(address=0x05, values=Dir.ccw_out)
            print("CCW")
            self.message = "Quay băng tải"
        else:
            self.message = "Hành động băng tải không hợp lệ"

    def check_conveyor(self, type: str):
        if type == 'cw':
            print("CW")
            return modbus.datablock_holding_register.getValues(address=0x04, count=1)[0] == Dir.cw_out
        elif type == 'ccw':
            print("CCW")
            return modbus.datablock_holding_register.getValues(address=0x04, count=1)[0] == Dir.ccw_out
        print("Truyền sai hành động!!!")
        return False
        
    def control_stopper(self, status:str):
        if status == "open":
            modbus.datablock_input_register.setValues(address=0x04,values=[Stopper.all_on])
            self.message = "Mở tất cả Stopper"
        elif status == "close":
            modbus.datablock_input_register.setValues(address=0x04, values=[Stopper.all_off])
            self.message = "Đóng tất cả Stopper"
        else:
            self.message = "Hành động không hợp lệ"

    def control_lift(self, height:int):
        try:
            modbus.datablock_input_register.setValues(address=0x03,values=[height])
            return ({'result':True})
        except Exception as E:
            return ({'result':False})
