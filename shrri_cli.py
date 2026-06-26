#!/usr/bin/env python3
"""SHRRI CLI — talk to your personal AI from the terminal."""
import sys
import os

sys.path.insert(0, os.path.expanduser("~/shrri"))

from engine import SHRRIEngine

def main():
    engine = SHRRIEngine()

    # Special commands
    if len(sys.argv) == 2 and sys.argv[1].lower() == "diagnose":
        engine.diagnose()
        return
    if len(sys.argv) == 2 and sys.argv[1].lower() == "status":
        engine.status()
        return
    if len(sys.argv) == 2 and sys.argv[1].lower() == "learned":
        engine.learned()
        return

    # Voice mode: shrri voice
    if len(sys.argv) == 2 and sys.argv[1].lower() == "voice":
        from tools.voice_input import listen
        text = listen()
        if text:
            print(engine.chat(text))
        return

    # One-shot mode: shrri what is the capital of France
    if len(sys.argv) > 1:
        # Join args safely — no shell evaluation
        question = " ".join(sys.argv[1:])
        # Strip any accidental shell metacharacters from leaking
        import shlex
        question = question.replace("\x00", "")  # null bytes
        response = engine.chat(question)
        if response.startswith("WHATSAPP_NAME_PENDING|"):
            _, name, text = response.split("|", 2)
            print(f"SHRRI: Ready to send to '{name}' (searching contacts):")
            print(f'       "{text}"')
            confirm = input("SHRRI: Send this message? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                from tools.whatsapp_tool import send_by_name
                print(send_by_name(name, text))
            else:
                print("SHRRI: Message cancelled.")
        elif response.startswith("WHATSAPP_PENDING|"):
            _, phone, text = response.split("|", 2)
            print(f"SHRRI: Ready to send to {phone}:")
            print(f'       "{text}"')
            confirm = input("SHRRI: Send this message? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                from tools.whatsapp_tool import send_whatsapp_now
                print(send_whatsapp_now(phone, text))
            else:
                print("SHRRI: Message cancelled.")
        else:
            print(response)
        return

    # Interactive mode: just type shrri
    print("SHRRI is ready. Type your message (or 'exit' to quit).")
    print("-" * 50)
    while True:
        try:
            line1 = input("You: ").strip()
            tick3 = chr(96) * 3
            if tick3 in line1 or line1.strip() in ("run this", "run", "execute this", "exec this"):
                parts = [line1]
                while True:
                    try:
                        nxt = input("... ")
                        parts.append(nxt)
                        if nxt.strip() == tick3:
                            break
                    except EOFError:
                        break
                # Wrap in python fence so pyexec tool triggers
                code_lines = parts[1:]  # skip "run this" line
                if code_lines and code_lines[-1].strip() == tick3:
                    code_lines = code_lines[:-1]  # remove closing fence
                user_input = tick3 + "python\n" + "\n".join(code_lines) + "\n" + tick3
            else:
                user_input = line1
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() == "voice":
            from tools.voice_input import listen
            user_input = listen()
            if not user_input:
                continue
            print(f"You said: {user_input}")
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break
        response = engine.chat(user_input)
        # WhatsApp confirmation flow
        if response.startswith("WHATSAPP_NAME_PENDING|"):
            _, name, text = response.split("|", 2)
            print(f"SHRRI: Ready to send to '{name}' (searching contacts):")
            print(f'       "{text}"')
            confirm = input("SHRRI: Send this message? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                from tools.whatsapp_tool import send_by_name
                print(send_by_name(name, text))
            else:
                print("SHRRI: Message cancelled.")
        elif response.startswith("WHATSAPP_PENDING|"):
            _, phone, text = response.split("|", 2)
            print(f"SHRRI: Ready to send to {phone}:")
            print(f'       "{text}"')
            confirm = input("SHRRI: Send this message? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                from tools.whatsapp_tool import send_whatsapp_now
                result = send_whatsapp_now(phone, text)
                print(f"SHRRI: {result}\n")
            else:
                print("SHRRI: Message cancelled.\n")
        else:
            print(f"SHRRI: {response}\n")

if __name__ == "__main__":
    main()
