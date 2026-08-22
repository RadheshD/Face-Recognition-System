import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

app = FastAPI()
_templates_dir = os.path.join(os.path.dirname(__file__), "backend", "templates")
templates = Jinja2Templates(directory=_templates_dir)

@app.get("/login_old")
async def login_old(request: Request):
    try:
        return templates.TemplateResponse("login.html", {"request": request})
    except Exception as e:
        return {"error": str(e)}

@app.get("/login_new")
async def login_new(request: Request):
    try:
        return templates.TemplateResponse(request=request, name="login.html")
    except Exception as e:
        return {"error": str(e)}

client = TestClient(app)
print("Old style:", client.get("/login_old").json())
print("New style:", client.get("/login_new").status_code)
