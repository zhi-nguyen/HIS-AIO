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

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
try:
    django.setup()
except Exception as e:
    print(f"Django setup warning: {e}")

# Inject dummy key if needed
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "DUMMY_KEY_FOR_TESTS"

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from chatbot.apps.ai_engine.graph.graph_builder import build_agent_graph

# Adjust import path if needed based on project structure
try:
    from apps.ai_engine.graph.graph_builder import build_agent_graph
except ImportError:
    # Fallback/Retry with different path assumptions if the above fails
    # But based on previous file reads, apps.ai_engine... is correct
    pass

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

async def trace_agent_execution(query: str):
    print(f"\n{Colors.HEADER}======================================={Colors.ENDC}")
    print(f"{Colors.BOLD}TEST QUERY: '{query}'{Colors.ENDC}")
    print(f"{Colors.HEADER}======================================={Colors.ENDC}")

    try:
        graph = build_agent_graph()
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "next_agent": "SUPERVISOR",
        }
        
        config = {"configurable": {"thread_id": f"debug-{int(time.time())}"}}
        
        print(f"{Colors.BLUE}[*] Starting Graph Execution...{Colors.ENDC}")
        
        # Use astream to see events as they happen
        async for event in graph.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                print(f"\n{Colors.CYAN}--- Node: {node_name} ---{Colors.ENDC}")
                
                if "messages" in state_update:
                    messages = state_update["messages"]
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            print(f"{Colors.GREEN}[AI Response]{Colors.ENDC}: {msg.content}")
                            if msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    print(f"{Colors.YELLOW}[TOOL CALL] id={tool_call['id']} name={tool_call['name']} args={tool_call['args']}{Colors.ENDC}")
                        elif isinstance(msg, ToolMessage):
                            print(f"{Colors.YELLOW}[TOOL OUTPUT] id={msg.tool_call_id}{Colors.ENDC}: {msg.content}")
                
                if "next_agent" in state_update:
                    print(f"{Colors.BLUE}[ROUTING] Next Agent: {state_update['next_agent']}{Colors.ENDC}")
    
    except Exception as e:
        print(f"{Colors.RED}[ERROR] {e}{Colors.ENDC}")

async def main():
    # Test case that requires tool usage
    test_queries = [
        "Tôi đang uống Aspirin thì có uống được Panadol không?", # Pharmacist tool
    ]
    
    for query in test_queries:
        await trace_agent_execution(query)

if __name__ == "__main__":
    asyncio.run(main())
