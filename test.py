import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

from engine import SHRRIEngine

engine = SHRRIEngine()

# Show status
engine.status()

# Test a simple message
print("\nTesting chat...")
response = engine.chat("hello, who are you? answer in one line.")
print(f"\nResponse: {response}")
