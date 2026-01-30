@echo off
python backend\scripts\test_paraclinical_agent.py > results.txt 2>&1
echo Done > done.txt
