#!/usr/bin/env python3
"""
SHRRI Simple Test Suite - Runs each test individually without hanging
"""

import subprocess
import time

def run_single_test(test_name, message):
    """Run a single chat.py session with one message"""
    print("\n" + "="*70)
    print(f"🧪 TEST: {test_name}")
    print(f"📝 Message: {message[:60]}..." if len(message) > 60 else f"📝 Message: {message}")
    print("="*70)
    
    try:
        # Use unbuffered mode and add -u flag
        result = subprocess.run(
            ['python3', '-u', 'chat.py'],
            input=message + '\nexit\n',
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/home/shrridharshan/shrri'
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("="*70 + "\n")
        return result.stdout
        
    except subprocess.TimeoutExpired:
        print("⚠️ TEST TIMEOUT (30 seconds)")
        print("="*70 + "\n")
        return None

# TEST 1: Multi-Agent Routing - CODE AGENT
print("\n" + "█"*70)
print("█ SCENARIO 1: MULTI-AGENT ROUTING - CODE AGENT")
print("█"*70)
test1a = run_single_test(
    "Code Agent",
    "can you debug this python error: list index out of range"
)

# TEST 1: Multi-Agent Routing - PLAN AGENT
print("\n" + "█"*70)
print("█ SCENARIO 1: MULTI-AGENT ROUTING - PLAN AGENT")
print("█"*70)
test1b = run_single_test(
    "Plan Agent",
    "create a 6-month plan to learn machine learning"
)

# TEST 1: Multi-Agent Routing - RESEARCH AGENT
print("\n" + "█"*70)
print("█ SCENARIO 1: MULTI-AGENT ROUTING - RESEARCH AGENT")
print("█"*70)
test1c = run_single_test(
    "Research Agent",
    "what are the differences between REST and GraphQL"
)

# TEST 2: Provider Fallback (Heavy Load)
print("\n" + "█"*70)
print("█ SCENARIO 2: PROVIDER FALLBACK (Heavy Request)")
print("█"*70)
test2 = run_single_test(
    "Heavy Load - React Todo App",
    "write a 300-line todo app in React with hooks and CSS"
)

# TEST 3: Memory & Learning - TEACH
print("\n" + "█"*70)
print("█ SCENARIO 3: MEMORY & LEARNING - TEACH")
print("█"*70)
test3a = run_single_test(
    "Memory - Teach SHRRI",
    "my name is Shrridharshan, I work on AI agents in Tamil Nadu"
)

time.sleep(1)

# TEST 3: Memory & Learning - RECALL
print("\n" + "█"*70)
print("█ SCENARIO 3: MEMORY & LEARNING - RECALL")
print("█"*70)
test3b = run_single_test(
    "Memory - Recall",
    "what do you know about me?"
)

# TEST 4: Experience Logging - ASK
print("\n" + "█"*70)
print("█ SCENARIO 4: EXPERIENCE LOGGING - ASK")
print("█"*70)
test4a = run_single_test(
    "Experience - Ask",
    "can you explain quantum computing"
)

time.sleep(1)

# TEST 4: Experience Logging - LOG SUCCESS
print("\n" + "█"*70)
print("█ SCENARIO 4: EXPERIENCE LOGGING - LOG SUCCESS")
print("█"*70)
test4b = run_single_test(
    "Experience - Log Success",
    "worked: explained quantum computing clearly"
)

# TEST 5: RAG & Knowledge Indexing - INDEX
print("\n" + "█"*70)
print("█ SCENARIO 5: RAG & KNOWLEDGE INDEXING - INDEX")
print("█"*70)
test5a = run_single_test(
    "RAG - Index Documents",
    "index"
)

time.sleep(1)

# TEST 5: RAG & Knowledge Indexing - QUERY
print("\n" + "█"*70)
print("█ SCENARIO 5: RAG & KNOWLEDGE INDEXING - QUERY")
print("█"*70)
test5b = run_single_test(
    "RAG - Query Knowledge",
    "what documents do you have?"
)

# FINAL SUMMARY
print("\n" + "█"*70)
print("█ ALL TESTS COMPLETE")
print("█"*70)
print("""
✅ VALIDATION CHECKLIST:

TEST 1 - Multi-Agent Routing:
  ✓ Code agent: [SHRRI] Agent: code visible?
  ✓ Plan agent: [SHRRI] Agent: plan visible?
  ✓ Research agent: [SHRRI] Agent: research visible?
  ✓ Different response styles for each?

TEST 2 - Provider Fallback:
  ✓ Multiple [SHRRI] Used: lines (provider rotation)?
  ✓ No 401/404/410 errors?
  ✓ Response completes?

TEST 3 - Memory & Learning:
  ✓ Second run remembers name "Shrridharshan"?
  ✓ Recalls "Tamil Nadu" location?
  ✓ Mentions "AI agents" work?

TEST 4 - Experience Logging:
  ✓ "worked: ..." logs successfully?
  ✓ Shows task logged?

TEST 5 - RAG / Knowledge Indexing:
  ✓ "index" finds documents?
  ✓ Can recall documents in response?

If all checks pass ✓, SHRRI is ready for UI layer.
""")
