import sys
import asyncio
from pathlib import Path
from uuid import UUID

# Ensure backend folder is in PYTHONPATH
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.append(str(backend_dir))

from app.chat.orchestrator import orchestrate_chat_turn

async def main():
    thread_id = UUID("0245873d-d844-4000-b974-61a63e668ad0")
    user_id = "76e6dad3-3aed-4969-819c-08f15558eff2"
    query = "how has apple's revenue mix shifted between 2023 and 2025?"
    messages = [{"role": "user", "content": query}]
    
    print("Starting turn orchestration...")
    try:
        async for event in orchestrate_chat_turn(thread_id, user_id, messages):
            print(f"Event: {event.strip()}")
    except Exception as e:
        print("\n--- CRITICAL ORCHESTRATOR ERROR ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
