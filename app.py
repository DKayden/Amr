import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    control.navigation(content["id"])
    return {"message": "Robot đã nhận thông tin điểm tới"}

@app.get("/action")
async def action(type: str):
    match type:
        case "cancel":
            control.nav_cancel()
            return {"message": "Đã hủy điều khiển robot tới vị trí"}
        case "resume":
            control.nav_resume()
            return {"message": "Đã tiếp tục điều khiển robot tới vị trí"}
        case "pause":
            control.nav_pause()
            return {"message": "Đã tạm dừng điều khiển robot tới vị trí"}
        case _:
            return {"message": "Hành động không hợp lệ"}
    

@app.get("/status")
async def get_status():
    return control.status()

@app.post("/conveyor")
async def control_conveyor(content: dict):
    control.control_conveyor(content["type"])
    return {"message": "Robot đã nhận lệnh điều khiển conveyor"}

@app.post("/conveyor")
async def status_conveyor(type: str):
    control.check_conveyor(type)
    return {"message": "Robot đã kiểm tra trạng thái conveyor"}

@app.post("/stopper")
async def control_stopper(content: dict):
    control.control_stopper(content["action"])
    return {"message": "Robot đã nhận lệnh điều khiển stopper"}

@app.post("/checklocation")
async def check_location(content: dict):
    return control.check_location(content["location"])

@app.post("/lift")
async def lift(content: dict):
    control.control_lift(content["height"])
    return {"message": "Robot đã nhận lệnh điều khiển lifting"}

@app.post("/relocation")
def relocation(content: dict):
    control.relocation(data_position=content['data'])
    return {'result':True}

@app.get("/confirm")
def confirm_local():
    control.confirm_local()
    return {'result':True}

