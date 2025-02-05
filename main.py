from threading import Thread
from control import modbus
from config import APP_HOST, APP_PORT
import uvicorn
from app import app,control
import asyncio

def run_app():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")


if __name__ == '__main__':
    control.connect_all()
    Thread(target=run_app,args=()).start()
    Thread(target=control.status(), args=()).start()
    asyncio.run(modbus.run_server_serial())
