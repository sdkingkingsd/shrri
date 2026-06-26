#!/bin/bash
echo "===================================="
echo "SHRRI FULL DIAGNOSTIC TEST"
echo "===================================="

run_test() {
    echo ""
    echo "--- TEST: $1 ---"
    shrri "$1" 2>&1
}

run_test "what time is it"
run_test "what is today's date"
run_test "what is 347 multiplied by 23"
run_test "weather in Chennai"
run_test "save note: diagnostic test run"
run_test "show my notes"
run_test "find all pdfs in my downloads"
run_test "volume up"
run_test "check my email"
run_test "what's on my calendar today"
run_test "check my whatsapp"
run_test "summarize never gonna give you up rick astley"
run_test "good morning"
run_test "remind me at 9pm to test reminders"
run_test "hi"
run_test "tell about me"

echo ""
echo "===================================="
echo "TEST COMPLETE — scan above for:"
echo "  - 'GAP:' (tool-level failure)"
echo "  - 'Traceback' (Python crash)"
echo "  - Tamil text where English expected"
echo "  - 'ERROR: All providers failed'"
echo "===================================="
