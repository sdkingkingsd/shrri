#!/usr/bin/env python3
"""SHRRI CLI — talk to your personal AI from the terminal."""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/shrri"))

from engine import SHRRIEngine

def main():
    engine = SHRRIEngine()

    # One-shot mode: shrri what is the capital of France
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(engine.chat(question))
        return

    # Interactive mode: just type shrri
    print("SHRRI is ready. Type your message (or 'exit' to quit).")
    print("-" * 50)
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break
        response = engine.chat(user_input)
        print(f"SHRRI: {response}\n")

if __name__ == "__main__":
    main()
