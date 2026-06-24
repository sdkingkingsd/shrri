#!/usr/bin/env python3
"""
SHRRI Full Scenario Test Suite
Tests: Multi-agent routing, Provider fallback, Memory & Learning, Experience logging, RAG/Knowledge
"""

import subprocess
import sys
import time

def run_chat_test(test_name, messages):
    """Run a chat test with multiple messages"""
    print("\n" + "="*70)
    print(f"🧪 TEST: {test_name}")
    print("="*70)
    
    process = subprocess.Popen(
        ['python3', 'chat.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd='/home/shrridharshan/shrri'
    )
    
    # Send all messages with delays
    input_text = '\n'.join(messages) + '\nexit\n'
    stdout, _ = process.communicate(input=input_text, timeout=120)
    
    print(stdout)
    print("="*70 + "\n")
    return stdout

# Test 1: Multi-Agent Routing
print("\n" + "█"*70)
print("█ SCENARIO 1: MULTI-AGENT ROUTING")
print("█"*70)
test1_messages = [
    "can you debug this python error: list index out of range",
    "create a 6-month plan to learn machine learning",
    "what are the differences between REST and GraphQL"
]
output1 = run_chat_test("Multi-Agent Routing (code, plan, research)", test1_messages)

# Test 2: Provider Fallback (Heavy Load)
print("\n" + "█"*70)
print("█ SCENARIO 2: PROVIDER FALLBACK (Heavy Request)")
print("█"*70)
test2_messages = [
    "write a complete 500-line todo app in React with hooks, state management, and CSS styling"
]
output2 = run_chat_test("Provider Fallback Under Load", test2_messages)

# Test 3: Memory & Learning
print("\n" + "█"*70)
print("█ SCENARIO 3: MEMORY & LEARNING")
print("█"*70)
test3_messages = [
    "my name is Shrridharshan, I work on AI agents in Tamil Nadu",
    "what do you know about me?",
    "facts"
]
output3 = run_chat_test("Memory & Learning (Remember Personal Info)", test3_messages)

# Test 4: Experience Logging
print("\n" + "█"*70)
print("█ SCENARIO 4: EXPERIENCE LOGGING")
print("█"*70)
test4_messages = [
    "can you explain quantum computing",
    "worked: explained quantum computing clearly",
    "experiences"
]
output4 = run_chat_test("Experience Logging (Success Tracking)", test4_messages)

# Test 5: RAG / Knowledge Indexing
print("\n" + "█"*70)
print("█ SCENARIO 5: RAG & KNOWLEDGE INDEXING")
print("█"*70)
test5_messages = [
    "index",
    "what documents do you have in your knowledge base?"
]
output5 = run_chat_test("RAG / Knowledge Indexing", test5_messages)

# Summary
print("\n" + "█"*70)
print("█ ALL TESTS COMPLETE")
print("█"*70)
print("""
✅ Check each test output for:

TEST 1 - Multi-Agent Routing:
  ✓ First message shows [SHRRI] Agent: code
  ✓ Second message shows [SHRRI] Agent: plan
  ✓ Third message shows [SHRRI] Agent: research
  ✓ Response styles are different (code-focused, structured plan, research explanation)

TEST 2 - Provider Fallback:
  ✓ Multiple [SHRRI] Used: lines (provider rotation)
  ✓ No 401/404/410 errors
  ✓ Response completes without hanging

TEST 3 - Memory & Learning:
  ✓ SHRRI confirms it learned your name "Shrridharshan"
  ✓ SHRRI recalls "Tamil Nadu" location
  ✓ SHRRI mentions "AI agents" work
  ✓ "facts" command shows your stored profile

TEST 4 - Experience Logging:
  ✓ "worked: ..." command logs successfully
  ✓ "experiences" shows the logged task with timestamp
  ✓ Status shows "success" or similar

TEST 5 - RAG / Knowledge Indexing:
  ✓ "index" command scans ~/shrri/knowledge/ successfully
  ✓ Shows number of documents found
  ✓ Can recall and reference documents in responses

If all 5 tests pass cleanly, SHRRI is production-ready for UI layer.
""")
