from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os

router = APIRouter()

class ValidationMetricModel(BaseModel):
    name: str
    status: str
    value: str = ""

class ValidationReportModel(BaseModel):
    verdict: str
    metrics: List[ValidationMetricModel]

@router.get("/report", response_model=ValidationReportModel)
def get_validation_report():
    """Parses VALIDATION_PIPELINE_REPORT.md and returns structured status."""
    report_path = os.path.join(os.getcwd(), "docs", "phase2", "VALIDATION_PIPELINE_REPORT.md")
    
    response = ValidationReportModel(verdict="UNKNOWN", metrics=[])
    
    if not os.path.exists(report_path):
        # Fallback if running from a different directory
        report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "docs", "phase2", "VALIDATION_PIPELINE_REPORT.md")
        
    if not os.path.exists(report_path):
        return response
        
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if "Verdict:" in line:
            # Extract GO or NO-GO
            if "NO-GO" in line:
                response.verdict = "NO-GO"
            elif "GO" in line:
                response.verdict = "GO"
        elif line.startswith("- **") or line.startswith("* **"):
            # Format usually: - **Metric Name**: value [STATUS]
            # Try to extract STATUS (PENDING, PASSED, FAILED)
            status = "UNKNOWN"
            if "[PENDING]" in line:
                status = "PENDING"
            elif "[PASSED]" in line:
                status = "PASSED"
            elif "[FAILED]" in line:
                status = "FAILED"
                
            # Naive name extraction
            try:
                name_part = line.split("**")[1]
                response.metrics.append(ValidationMetricModel(
                    name=name_part.strip(": "),
                    status=status
                ))
            except IndexError:
                pass
                
    return response
