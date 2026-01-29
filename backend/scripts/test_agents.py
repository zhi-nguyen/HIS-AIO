import os
import sys
import asyncio
import time
from typing import List, Dict, Any

# Force UTF-8 for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

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
from apps.ai_engine.graph.graph_builder import build_agent_graph
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.nodes import summarize_node, triage_node_with_escalation

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

async def test_agent_flow(query: str, expected_agent: str = None):
    print(f"\n{Colors.BOLD}{Colors.CYAN}Item Test: '{query}'{Colors.ENDC}")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "DUMMY_KEY_FOR_TESTS":
        print(f"{Colors.WARNING}[!] Skipping LLM call (No valid GOOGLE_API_KEY){Colors.ENDC}")
        return

    try:
        graph = build_agent_graph()
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "next_agent": "SUPERVISOR",
            "error": None
        }
        
        print(f"[*] Sending to Supervisor...")
        start_time = time.time()
        
        # Generate a thread_id for this conversation
        config = {"configurable": {"thread_id": f"test-thread-{int(time.time())}"}}
        
        final_state = await graph.ainvoke(initial_state, config=config)
        
        duration = time.time() - start_time
        messages = final_state.get("messages", [])
        last_message = messages[-1].content if messages else "No response"
        agent_path = final_state.get("next_agent", "Unknown")
        
        print(f"{Colors.GREEN}[+] Response ({duration:.2f}s):{Colors.ENDC}")
        print(f"{last_message}\n")
        
    except Exception as e:
        print(f"{Colors.FAIL}[x] Error: {e}{Colors.ENDC}")

async def main():
    print(f"{Colors.BOLD}[*] STARTING AGENT TEST SUITE{Colors.ENDC}")
    print("=======================================")

    
    test_cases = [
        # Consultant Tests
        ("Bệnh viện mở cửa mấy giờ?", "CONSULTANT"),
        ("Tôi muốn đặt lịch khám tim mạch ngày mai", "CONSULTANT"),
        
        # Clinical Tests
        ("Tôi bị đau ngực trái lan xuống cánh tay, kèm khó thở", "CLINICAL"),
        ("Bác sĩ ơi, tôi bị nổi ban đỏ sau khi ăn hải sản, hơi ngứa", "CLINICAL"),
        
        # Triage Tests
        ("Người nhà tôi ngất xỉu, mạch yếu, gọi cấp cứu giúp tôi!", "TRIAGE"),
        ("Huyết áp 190/110, đau đầu dữ dội", "TRIAGE"),
        
        # Pharmacist Tests
        ("Tôi đang uống Aspirin thì có uống được Panadol không?", "PHARMACIST"),
        ("Kiểm tra tương tác thuốc Warfarin và Ibuprofen", "PHARMACIST")
    ]
    
    for query, expected in test_cases:
        await test_agent_flow(query, expected)
        await asyncio.sleep(1) # Rate limit protection

    async def simulate_triage_flow(patient_data: Dict[str, Any], expected_outcome: str):
        print(f"\n{Colors.BOLD}{Colors.CYAN}--- Triage Simulation Test ---{Colors.ENDC}")
        print(f"Patient ID: {patient_data.get('patient_id')}")
        print(f"Condition: {patient_data.get('reason_for_visit')}")
        print(f"Expected: {expected_outcome}")
        
        # 1. Prepare Initial State with Patient Context
        # Simulate that the reception/system has already gathered this info
        initial_message = f"Patient {patient_data['patient_id']} ({patient_data['age']} yo) presents with: {patient_data['reason_for_visit']}. History: {patient_data['medical_history']}."
        
        state = {
            "messages": [HumanMessage(content=initial_message)],
            "patient_context": {
                "patient_id": patient_data['patient_id'],
                "patient_name": "Test Patient",
                "emr_data": {},
                "vitals": patient_data.get('vitals', {}),
                "medical_history": [{"condition": h} for h in patient_data['medical_history']],
                "current_medications": [],
                "allergies": []
            },
            "next_agent": "SUMMARIZE"
        }
        
        # 2. Run Summarize Node
        print(f"\n{Colors.BLUE}[*] Running Summarize Node...{Colors.ENDC}")
        try:
            summary_result = summarize_node(state)
            summary_message = summary_result["messages"][0]
            print(f"{Colors.GREEN}Summary:{Colors.ENDC} {summary_message.content}")
            
            # Update state for next node
            state["messages"].append(summary_message)
        except Exception as e:
            print(f"{Colors.FAIL}Summarize Failed: {e}{Colors.ENDC}")
            return

        # 3. Transfer to Triage Node
        print(f"\n{Colors.BLUE}[*] Transferring to Triage Node...{Colors.ENDC}")
        try:
            # Triage usually looks at the last message. The summary is now the last message.
            triage_result = triage_node_with_escalation(state)
            triage_response = triage_result["messages"][0]
            
            print(f"{Colors.GREEN}Triage Response:{Colors.ENDC}")
            print(triage_response.content)
            
            # Check for tool calls (Escalation)
            if hasattr(triage_response, 'tool_calls') and triage_response.tool_calls:
                for tool in triage_response.tool_calls:
                     print(f"{Colors.RED}[!] TOOL CALL DETECTED: {tool['name']} (Args: {tool['args']}){Colors.ENDC}")

        except Exception as e:
            print(f"{Colors.FAIL}Triage Failed: {e}{Colors.ENDC}")

    # =========================================================================
    # Triage Specific Test Cases
    # =========================================================================
    
    # CASE 1: Hard Case (Emergency)
    hard_case = {
        "patient_id": "PT-999-EMERGENCY",
        "age": 65,
        "reason_for_visit": "Đau ngực dữ dội vùng trước tim, vã mồ hôi lạnh, khó thở, buồn nôn.",
        "medical_history": ["Hypertension (Cao huyết áp)", "Diabetes Type 2 (Tiểu đường tuýp 2)", "Smoking (Hút thuốc)"],
        "vitals": {"bp": "160/95", "hr": 110, "spo2": 94} # Optional, implied in text
    }
    expected_hard = "CODE_RED (Myocardial Infarction suspicion) -> Emergency Dept -> Trigger Alert"
    
    await simulate_triage_flow(hard_case, expected_hard)
    
    # CASE 2: Easy Case (Routine)
    easy_case = {
        "patient_id": "PT-123-ROUTINE",
        "age": 25,
        "reason_for_visit": "Đau lưng dưới nhẹ do ngồi làm việc lâu, không lan xuống chân, không tê bì.",
        "medical_history": ["None"],
    }
    expected_easy = "CODE_GREEN -> General Internal Medicine / Physical Therapy -> Advice & Appointment"
    
    await simulate_triage_flow(easy_case, expected_easy)

if __name__ == "__main__":
    asyncio.run(main())
