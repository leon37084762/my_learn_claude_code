from argparse import ArgumentDefaultsHelpFormatter
import os
import subprocess

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if not os.getenv("ANTHROPIC_API_KEY"):
    print("Anthropic API Key not found")
base_model_url = os.getenv("ANTHROPIC_BASE_URL")
print(base_model_url)
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.getenv("ANTHROPIC_MODEL")
print(MODEL)

SYSTEM = f"you are a coding agent at {os.getcwd()},use bash to solve tasks.Act, don't explain."

TOOLS = [
    {
        "name": "bash",
        "description":"run a shell command",
        "input_schema":{
            "type":"object",
            "properties":{
                "command":{
                    "type":"string"             
                }
            },
            "required":["command"]
        }
    }
]


# ── Tool execution ────────────────────────────────────────
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


def agent_loop(messages:list):
    while True:
        response = client.messages.create(
            model = MODEL,
            system = SYSTEM,
            messages = messages,
            tools = TOOLS,
            max_tokens = 8000,
        )
        messages.append({"role":"assistant","content":response.content})
        if response.stop_reason  != "tool_call":
            return
        
        results = []
        for block in response.content:
            if block.type=="tool_use":
                print(f"\033[33m$ {block.input['command']} \033[0m")
                output = run_bash(block.input["command"])
                print(output[:200])
                results.append(
                    {
                        "type":"tool_result",
                        "tool_use_id":block.id,
                        "content":output
                    }
                )
        messages.append({"role":"user","content":results})

if __name__ =="__main__":
    print("s01:Agent Loop")
    print("input question,enter to send,press q to quit\n")

    history=[]
    while True:
        try:
            query = input()
        except(EOFError,KeyboardInterrupt):
            break
        if query.strip().lower() in ("q","quit","exit",""):
            break
        history.append({"role":"user","content":query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content,list):
            for block in response_content:
                if getattr(block,"type",None) == "text":
                    print(block.text)
        print()

