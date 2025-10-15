from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import subprocess
import os
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="dbt Service API", 
    description="API Gateway üzerinden erişilebilen dbt mikroservisi. Frontend 'Analiz Et' butonu için.",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR", "/opt/dbt")

class DbtCommand(BaseModel):
    command: str  # örn: 'run', 'test', 'seed'
    args: List[str] = []

class DbtAnalysisRequest(BaseModel):
    models: Optional[List[str]] = None  # Hangi modelleri çalıştır (None ise hepsi)
    run_tests: bool = True  # Test'leri de çalıştır mı?

@app.get("/")
def root():
    return {
        "service": "dbt Service",
        "status": "running",
        "description": "dbt transformasyon ve analiz servisi",
        "endpoints": {
            "health": "/health",
            "run_dbt": "/dbt (POST)",
            "analyze": "/analyze (POST) - Frontend için",
            "run_staging": "/staging (POST)",
            "run_intermediate": "/intermediate (POST)",
            "run_marts": "/marts (POST)",
            "run_tests": "/tests (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    """Servis sağlık kontrolü"""
    try:
        # dbt version kontrolü
        result = subprocess.run(
            ["dbt", "--version"], 
            cwd=DBT_PROJECT_DIR, 
            capture_output=True, 
            text=True
        )
        return {
            "status": "healthy",
            "dbt_version": result.stdout.strip(),
            "dbt_project_dir": DBT_PROJECT_DIR,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/dbt")
def run_dbt(cmd: DbtCommand):
    """Genel dbt komut çalıştırma"""
    full_cmd = ["dbt", cmd.command] + cmd.args
    try:
        result = subprocess.run(
            full_cmd, 
            cwd=DBT_PROJECT_DIR, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=300  # 5 dakika timeout
        )
        return {
            "status": "success",
            "command": " ".join(full_cmd),
            "stdout": result.stdout,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "command": " ".join(full_cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="dbt command timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
def analyze_data(request: DbtAnalysisRequest):
    """
    Frontend 'Analiz Et' butonu için ana endpoint.
    Veri transformasyonunu ve testleri çalıştırır.
    """
    results = {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "stages": {}
    }
    
    try:
        # 1. Staging modelleri çalıştır
        select_arg = f"--select {' '.join(request.models)}" if request.models else "--select staging.*"
        staging_cmd = ["dbt", "run", "--select", "staging.*"]
        
        staging_result = subprocess.run(
            staging_cmd,
            cwd=DBT_PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        results["stages"]["staging"] = {
            "status": "success" if staging_result.returncode == 0 else "error",
            "output": staging_result.stdout,
            "errors": staging_result.stderr if staging_result.returncode != 0 else None
        }
        
        # 2. Intermediate modelleri çalıştır
        if staging_result.returncode == 0:
            intermediate_cmd = ["dbt", "run", "--select", "intermediate.*"]
            intermediate_result = subprocess.run(
                intermediate_cmd,
                cwd=DBT_PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results["stages"]["intermediate"] = {
                "status": "success" if intermediate_result.returncode == 0 else "error",
                "output": intermediate_result.stdout,
                "errors": intermediate_result.stderr if intermediate_result.returncode != 0 else None
            }
        
        # 3. Marts modelleri çalıştır
        if staging_result.returncode == 0 and intermediate_result.returncode == 0:
            marts_cmd = ["dbt", "run", "--select", "marts.*"]
            marts_result = subprocess.run(
                marts_cmd,
                cwd=DBT_PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results["stages"]["marts"] = {
                "status": "success" if marts_result.returncode == 0 else "error",
                "output": marts_result.stdout,
                "errors": marts_result.stderr if marts_result.returncode != 0 else None
            }
        
        # 4. Test'leri çalıştır (isteniyorsa)
        if request.run_tests and all(
            results["stages"].get(s, {}).get("status") == "success" 
            for s in ["staging", "intermediate", "marts"]
        ):
            test_cmd = ["dbt", "test"]
            test_result = subprocess.run(
                test_cmd,
                cwd=DBT_PROJECT_DIR,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results["stages"]["tests"] = {
                "status": "success" if test_result.returncode == 0 else "error",
                "output": test_result.stdout,
                "errors": test_result.stderr if test_result.returncode != 0 else None
            }
        
        # Genel durum
        all_success = all(
            stage.get("status") == "success" 
            for stage in results["stages"].values()
        )
        
        results["status"] = "completed" if all_success else "completed_with_errors"
        results["completed_at"] = datetime.utcnow().isoformat()
        
        return results
        
    except subprocess.TimeoutExpired:
        results["status"] = "timeout"
        results["error"] = "Analiz işlemi zaman aşımına uğradı"
        raise HTTPException(status_code=408, detail=results)
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        raise HTTPException(status_code=500, detail=results)

@app.post("/staging")
def run_staging():
    """Staging modellerini çalıştır"""
    try:
        result = subprocess.run(
            ["dbt", "run", "--select", "staging.*"],
            cwd=DBT_PROJECT_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        return {
            "status": "success",
            "stage": "staging",
            "output": result.stdout,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "stage": "staging",
            "stdout": e.stdout,
            "stderr": e.stderr
        }

@app.post("/intermediate")
def run_intermediate():
    """Intermediate modellerini çalıştır"""
    try:
        result = subprocess.run(
            ["dbt", "run", "--select", "intermediate.*"],
            cwd=DBT_PROJECT_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        return {
            "status": "success",
            "stage": "intermediate",
            "output": result.stdout,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "stage": "intermediate",
            "stdout": e.stdout,
            "stderr": e.stderr
        }

@app.post("/marts")
def run_marts():
    """Marts modellerini çalıştır"""
    try:
        result = subprocess.run(
            ["dbt", "run", "--select", "marts.*"],
            cwd=DBT_PROJECT_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        return {
            "status": "success",
            "stage": "marts",
            "output": result.stdout,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "stage": "marts",
            "stdout": e.stdout,
            "stderr": e.stderr
        }

@app.post("/tests")
def run_tests():
    """dbt testlerini çalıştır"""
    try:
        result = subprocess.run(
            ["dbt", "test"],
            cwd=DBT_PROJECT_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=120
        )
        return {
            "status": "success",
            "stage": "tests",
            "output": result.stdout,
            "timestamp": datetime.utcnow().isoformat()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "stage": "tests",
            "stdout": e.stdout,
            "stderr": e.stderr
        }
