from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import subprocess
import os

app = FastAPI(title="dbt Service API", description="API Gateway üzerinden erişilebilen dbt mikroservisi.")

DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR", "/opt/dbt")

class DbtCommand(BaseModel):
    command: str  # örn: 'run', 'test', 'seed'
    args: list = []

@app.get("/")
def root():
    return {"message": "dbt-service API çalışıyor. /docs ile Swagger arayüzüne erişebilirsiniz."}

@app.post("/dbt")
def run_dbt(cmd: DbtCommand):
    full_cmd = ["dbt", cmd.command] + cmd.args
    try:
        result = subprocess.run(full_cmd, cwd=DBT_PROJECT_DIR, capture_output=True, text=True, check=True)
        return {"status": "success", "stdout": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "stdout": e.stdout, "stderr": e.stderr}
