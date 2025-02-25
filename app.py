import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from control import RobotAPI
from config import HOST_ROBOT

control = RobotAPI(HOST_ROBOT)

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


@app.post("/navigation")
async def navigate(content: dict):
    control.navigation(content)
    return {"message": "Robot đã nhận thông tin điểm tới"}

@app.get("/action")
async def navigate_action(type: str):
    if (type == "pause"):
        control.nav_pause()
    elif (type == "resume"):
        control.nav_resume()
    elif (type == "cancel"):
        control.nav_cancel()
    return {"message": f"Robot đã nhận lệnh {type} di chuyển"}

@app.get("/status")
async def get_status():
    return control.status()

@app.post("relocation")
async def relocation(content: dict):
    try:
        control.relocation(content['data'])
        return {"message" : "Gửi lệnh lấy lại vị trí cho robot thành công"}
    except Exception as e:
        return {"message" : f"Có lỗi xảy ra khi gửi lệnh lấy lại vị trí cho robot {e}"}
    
@app.post("/lift")
def lift(content: dict):
    return control.control_lift(content["height"])
    
@app.post("/conveyor")
async def control_conveyor(content: dict):
    control.control_conveyor(content["data"])
    return {"message": "Robot đã nhận lệnh điều khiển conveyor"}

@app.get("/conveyor")
async def status_conveyor(type: str):
    result = control.check_conveyor(type)
    return {"message": "Robot đã kiểm tra trạng thái conveyor", "result" : result}

@app.post("/stopper")
async def control_stopper(content: dict):
    control.control_stopper(content)
    return {"message": "Robot đã nhận lệnh điều khiển stopper"}

@app.get("/stopper")
async def check_stopper(content: dict):
    return control.check_stopper(content["status"], content["action"])

@app.get("/checklocation")
async def check_location(content: dict):
    return control.check_robot_location(content['location'])

@app.get("/lift")
def check_height(height: int):
    return control.check_conveyor_height(height)

@app.post("/color")
def color(content: dict):
    return control.set_led(content["color"])

@app.get("/sensor")
def sensor():
    return control.check_sensor()
