from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional
from .services import create_lab_order, get_patient_lab_history

class CreateLabOrderInput(BaseModel):
    visit_id: str = Field(..., description="The ID of the current visit")
    test_codes: List[str] = Field(..., description="List of lab test codes to order (e.g. ['CBC', 'GLUCOSE'])")
    doctor_id: str = Field(..., description="The ID of the ordering doctor")
    note: Optional[str] = Field(None, description="Clinical note for the lab technician")

@tool("create_lab_order", args_schema=CreateLabOrderInput)
def create_lab_order_tool(visit_id: str, test_codes: List[str], doctor_id: str, note: str = None) -> str:
    """
    Creates a laboratory order for a patient.
    Use this tool when the doctor requests lab tests (e.g., blood test, urine test).
    Returns the Order ID and status.
    """
    try:
        order = create_lab_order(visit_id, test_codes, doctor_id, note)
        return f"Order created successfully. Order ID: {order.id}. Status: {order.status}"
    except Exception as e:
        return f"Error creating order: {str(e)}"

class GetLabHistoryInput(BaseModel):
    patient_id: str = Field(..., description="The ID of the patient")
    category: Optional[str] = Field(None, description="Optional category filter (e.g., 'Hematology')")

@tool("get_patient_lab_history", args_schema=GetLabHistoryInput)
def get_patient_lab_history_tool(patient_id: str, category: str = None) -> str:
    """
    Retrieves historical lab results for a patient.
    Useful for checking trends or previous results.
    """
    try:
        history = get_patient_lab_history(patient_id, category)
        if not history:
            return "No lab history found for this patient."
        
        # Format as a readable string
        output = "Lab History:\n"
        for item in history:
            output += f"- {item['date']}: {item['test_name']} = {item['value']} {item['unit']} (Abnormal: {item['is_abnormal']})\n"
        return output
    except Exception as e:
        return f"Error retrieving history: {str(e)}"
