import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from control import RobotAPI
from config import HOST_ROBOT
from robot import Robot

control = RobotAPI(HOST_ROBOT)
robot = Robot()

app = FastAPI(
    title="AMR API",
    openapi_url="/openapi.json",
    docs_url="/docs",
    description="AMR API documentation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

class StringModel(BaseModel):
    data: str


@app.post("/navigation")
async def navigate(content: StringModel):
    print(content)
    print(content.data)
    content_dict = content.model_dump()
    print(content_dict)
    # control.navigation(content_dict)
    return {"message": "Robot đã nhận thông tin điểm tới"}

@app.get("/status")
async def get_status():
    return control.status()

@app.post("/conveyor")
async def control_conveyor(content: StringModel):
    # print(content.data)
    control.control_conveyor(content.data)
    return {"message": "Robot đã nhận lệnh điều khiển conveyor"}

@app.get("/conveyor")
async def status_conveyor(type: str):
    control.check_conveyor(type)
    return {"message": "Robot đã kiểm tra trạng thái conveyor"}

@app.post("/stopper")
async def control_stopper(content: StringModel):
    # print(content.data)
    control.control_stopper(content.data)
    return {"message": "Robot đã nhận lệnh điều khiển stopper"}

@app.get("/checklocation")
async def check_location(content: StringModel):
    print(content.data)
    return robot.check_robot_location(content.data)
