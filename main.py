from robot import Robot
from threading import Thread
from control import RobotAPI
from config import HOST_ROBOT, APP_HOST, APP_PORT
import uvicorn
from app import app


robot_api = RobotAPI(HOST_ROBOT)

if __name__ == '__main__':
    # robot_api.connect_all()

    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")
