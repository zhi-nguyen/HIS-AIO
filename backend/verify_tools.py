import py_compile
import os

base = "/app"

files = [
    "apps/ai_engine/agents/consultant_agent/tools.py",
    "apps/ai_engine/agents/pharmacist_agent/tools.py",
    "apps/ai_engine/agents/triage_agent/tools.py",
    "apps/ai_engine/agents/paraclinical_agent/tools.py",
    "apps/ai_engine/agents/clinical_agent/tools.py",
    "apps/ai_engine/graph/tools.py",
    "apps/ai_engine/graph/llm_config.py",
]

all_ok = True
for f in files:
    full_path = os.path.join(base, f)
    try:
        py_compile.compile(full_path, doraise=True)
        print(f"OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"FAIL: {f}")
        print(f"  Error: {e}")
        all_ok = False

print()
if all_ok:
    print("ALL SYNTAX CHECKS PASSED!")
else:
    print("SOME FILES FAILED!")
