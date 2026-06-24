import sys
sys.path.insert(0, '/home/shrridharshan/shrri')
from engine import SHRRIEngine
from engine.experience import Experience


def main():
    print("=" * 50)
    print("  SHRRI — Personal AI Assistant")
    print("  Type 'exit' or 'quit' to stop")
    print("  Type 'status' to see engine status")
    print("  Type 'facts' to see what SHRRI knows about you")
    print("  Type 'worked: <task>' to log a success")
    print("  Type 'failed: <task> | <detail>' to log a failure")
    print("  Type 'experiences' to see what SHRRI remembers trying")
    print("  Type 'index' to scan ~/shrri/knowledge/ for new documents")
    print("  Type 'learned' to see what SHRRI has learned about you")
    print("=" * 50)
    sys.stdout.flush()

    e = SHRRIEngine()
    exp = Experience()
    last_task = {"text": None}

    while True:
        try:
            print("\nYou: ", end="", flush=True)
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSHRRI: Goodbye, Shrridharshan!", flush=True)
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("SHRRI: Goodbye, Shrridharshan!", flush=True)
            break

        if user_input.lower() == "status":
            e.status()
            sys.stdout.flush()
            continue

        if user_input.lower() == "learned":
            e.learned()
            sys.stdout.flush()
            continue

        if user_input.lower().startswith("worked:"):
            task = user_input[len("worked:"):].strip()
            exp.log(task, "success")
            last_task["text"] = task
            print(f"SHRRI: Got it, logged as success — '{task}'", flush=True)
            continue

        if user_input.lower().startswith("failed:"):
            parts = user_input[len("failed:"):].strip().split("|", 1)
            task = parts[0].strip()
            detail = parts[1].strip() if len(parts) > 1 else ""
            exp.log(task, "failure", detail)
            print(f"SHRRI: Got it, logged as failure — '{task}' ({detail})", flush=True)
            continue

        if user_input.lower() == "experiences":
            items = exp.all()
            if items:
                print("\nWhat SHRRI remembers trying:")
                for i in items:
                    tag = "✅" if i["outcome"] == "success" else "❌"
                    print(f"  {tag} {i['task']}" + (f" — {i['detail']}" if i['detail'] else ""))
            else:
                print("No experiences logged yet.")
            sys.stdout.flush()
            continue

        if user_input.lower() == "index":
            print("SHRRI: Indexing knowledge folder, one moment...", flush=True)
            e.rag.index_all()
            sys.stdout.flush()
            continue

        if user_input.lower() == "facts":
            facts = e.memory.get_all_facts()
            if facts:
                print("\nWhat SHRRI knows about you:")
                for k, v in facts.items():
                    print(f"  - {k}: {v}")
            else:
                print("SHRRI doesn't know any facts about you yet.")
            sys.stdout.flush()
            continue

        # Process the message
        response = e.chat(user_input)
        print(f"\nSHRRI: {response}", flush=True)


if __name__ == "__main__":
    main()
