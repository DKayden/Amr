from robot import Robot
from threading import Thread
from control import RobotAPI
from config import HOST_ROBOT

robot_api = RobotAPI(HOST_ROBOT)

if __name__ == '__main__':
    robot_api.connect_all()

    status_thread = Thread(target=Robot.check_robot_location)
    status_thread.start()