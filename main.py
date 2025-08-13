from threading import Thread
from control import modbus
from config import APP_HOST, APP_PORT
import uvicorn
from app import app, control
import asyncio
import time


def run_app():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")


def get_status():
    while True:
        control.status()
        if control.data_status:
            if control.data_status["blocked"] or control.data_status["emergency"]:
                control.set_led("red")
            elif (
                control.data_status["current_station"] == "LM101"
                or control.data_status["battery_level"] < 0.2
            ):
                control.set_led("yellow")
            else:
                control.set_led("green")
        sensor = control.check_sensor()
        data_sensor = [sensor[5], sensor[6]]
        control.data_status["sensor"] = data_sensor
        time.sleep(0.5)


if __name__ == "__main__":
    control.connect_all()
    Thread(target=run_app, args=()).start()
    Thread(target=get_status, args=()).start()
    asyncio.run(modbus.run_server_serial())
