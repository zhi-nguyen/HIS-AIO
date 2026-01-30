import os
import sys
import asyncio
import time
from typing import Dict, Any

# Force UTF-8 for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Redirect stdout to a file for capture
output_file = open("test_results.log", "w", encoding="utf-8")
sys.stdout = output_file
sys.stderr = output_file

print("Starting test script...")


# Configure Django settings if needed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
try:
    django.setup()
except Exception as e:
    print(f"Django setup warning: {e}")

# Inject dummy API key if missing to avoid Import Error from LangChain
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "DUMMY_KEY_FOR_TESTS"
    print("[!] Injected DUMMY_KEY_FOR_TESTS to allow module imports.")

from langchain_core.messages import HumanMessage
from apps.ai_engine.graph.tools import (
    receive_clinical_order, 
    check_contraindications, 
    track_sample_status, 
    check_critical_values, 
    analyze_trend, 
    normalize_lab_result, 
    extract_imaging_conclusions
)
from apps.ai_engine.agents.paraclinical_agent.workflow import paraclinical_node

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_step(step_name: str, content: str):
    print(f"\n{Colors.HEADER}=== {step_name} ==={Colors.ENDC}")
    print(content)

def test_tools():
    """Unit test for Paraclinical Tools"""
    print_step("UNIT TEST", "Testing Paraclinical Tools")
    
    # 1. Test receive_clinical_order
    print(f"{Colors.CYAN}[1] receive_clinical_order{Colors.ENDC}")
    res = receive_clinical_order.invoke({
        "order_type": "Blood Test", 
        "patient_id": "PT-001", 
        "order_details": "CBC, BMP"
    })
    print(res)
    assert "Y LỆNH ĐÃ ĐƯỢC TIẾP NHẬN" in res, "Failed: receive_clinical_order"
    
    # 2. Test check_contraindications
    print(f"\n{Colors.CYAN}[2] check_contraindications{Colors.ENDC}")
    res_ct = check_contraindications.invoke({
        "patient_id": "PT-002", 
        "procedure_type": "CT with contrast"
    })
    print(res_ct)
    assert "KIỂM TRA CHỐNG CHỈ ĐỊNH" in res_ct, "Failed: check_contraindications (Contrast)"
    
    res_safe = check_contraindications.invoke({
        "patient_id": "PT-003", 
        "procedure_type": "Ultrasound"
    })
    print(res_safe)
    assert "KHÔNG CÓ CHỐNG CHỈ ĐỊNH" in res_safe, "Failed: check_contraindications (Safe)"

    # 3. Test check_critical_values
    print(f"\n{Colors.CYAN}[3] check_critical_values{Colors.ENDC}")
    res_crit = check_critical_values.invoke({
        "test_type": "Potassium",
        "value": 7.0,
        "unit": "mEq/L"
    })
    print(res_crit)
    assert "CẢNH BÁO GIÁ TRỊ NGUY KỊCH" in res_crit, "Failed: check_critical_values (High)"
    
    res_norm = check_critical_values.invoke({
        "test_type": "Glucose",
        "value": 100,
        "unit": "mg/dL"
    })
    print(res_norm)
    assert "GIÁ TRỊ BÌNH THƯỜNG" in res_norm, "Failed: check_critical_values (Normal)"

    # 4. Test analyze_trend
    print(f"\n{Colors.CYAN}[4] analyze_trend{Colors.ENDC}")
    res_trend = analyze_trend.invoke({
        "patient_id": "PT-004", 
        "test_type": "HbA1c", 
        "days": 90
    })
    print(res_trend)
    assert "PHÂN TÍCH XU HƯỚNG" in res_trend, "Failed: analyze_trend"

    print(f"\n{Colors.GREEN}[SUCCESS] All tool unit tests passed!{Colors.ENDC}")

async def test_agent_logic():
    """Integration test for Paraclinical Agent Node"""
    print_step("INTEGRATION TEST", "Testing Paraclinical Agent Logic (LLM)")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "DUMMY_KEY_FOR_TESTS":
        print(f"{Colors.WARNING}[!] Skipping LLM Agent Test (No valid GOOGLE_API_KEY){Colors.ENDC}")
        return

    test_queries = [
        "Đặt y lệnh xét nghiệm máu tổng quát (CBC) cho bệnh nhân PT-12345",
        "Kiểm tra xem bệnh nhân PT-999 có chụp CT cản quang được không?",
        "Bệnh nhân có kết quả Kali máu 7.2, kiểm tra xem có nguy hiểm không"
    ]

    for query in test_queries:
        print(f"\n{Colors.BOLD}{Colors.CYAN}Query: '{query}'{Colors.ENDC}")
        state = {
            "messages": [HumanMessage(content=query)],
            "next_agent": "PARACLINICAL",
            "error": None
        }
        
        try:
            print("[*] Invoking paraclinical_node...")
            result = paraclinical_node(state)
            response_msg = result["messages"][0]
            
            print(f"{Colors.GREEN}Response:{Colors.ENDC}")
            print(f"Content: {response_msg.content}")
            
            if hasattr(response_msg, 'tool_calls') and response_msg.tool_calls:
                 for tool in response_msg.tool_calls:
                     print(f"{Colors.RED}[!] TOOL CALL: {tool['name']} (Args: {tool['args']}){Colors.ENDC}")
            else:
                print(f"{Colors.WARNING}[!] No tool calls generated.{Colors.ENDC}")
                
        except Exception as e:
            print(f"{Colors.FAIL}[x] Error: {e}{Colors.ENDC}")

if __name__ == "__main__":
    test_tools()
    asyncio.run(test_agent_logic())
