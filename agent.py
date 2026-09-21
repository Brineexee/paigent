import argparse
import json
import os
import sys

from openai import OpenAI
from tools import TOOL_FUNCTIONS, TOOL_SPECS

DEFAULT_MODEL = "openrouter/free"
MAX_TURNS = 20

SYSTEM_PROMPT = """You are a research agent with access to web_search, write_file, and run_python. These are the ONLY three tools that exist. Do not call any tool by another name that does not exist.

Break the user's task into logical steps and execute them sequentially.

Rules:
1. Cite sources using bracketed numbers like [1] [2] inline in the text. At the end of the file, include a "Sources" section listing each number with its full URL on its own line. Do not use HTML tags of any kind, including <a> links.
2. If a tool fails, inspect the error and adjust your approach. Do not repeat failed calls identically.
3. Write to a given filename at most ONCE. Never rewrite or overwrite an existing output file.
4. After writing your report file, reply with a concise plain text sumary to complete the run. Do not invoke further tools."""

def get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY is missing!")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def run_agent(task: str, model: str, verbose: bool = True) -> str:
    client = get_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    written_files = set()

    for turn in range(1, MAX_TURNS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SPECS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content or ""

        for call in message.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            if verbose:
                print(f"Step n.{turn}: {name}({args})", file=sys.stderr)

            if name == "write_file" and args.get("filename") in written_files:
                result = (
                    f"refused: {args.get('filename')} was already written this run. "
                    "The file is complete. Do not rewrite it. Reply with a plain text "
                    "summary of your results to finish."
                )
            else:
                func = TOOL_FUNCTIONS.get(name)
                if func is None:
                    result = (
                        f"Unknown tool: {name}. Your only available tools are "
                        "web_search, write_file, and run_python. Use one of those."
                    )
                else:
                    try:
                        result = func(**args)
                        if name == "write_file" and not result.lower().startswith("error"):
                            written_files.add(args.get("filename"))
                    except Exception as e:
                        result = f"Tool Exception: {e}"

            if verbose:
                preview = result if len(result) < 300 else result[:300] + "..."
                print(f"   Result: {preview}", file=sys.stderr)

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

    return "Reached maximum step count without a final answer"


def main():
    parser = argparse.ArgumentParser(
        description="Web research CLI agent"
    )
    parser.add_argument("task", help="research task or query")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model ID")
    parser.add_argument("--quiet", action="store_true", help="suppress step logging")
    args = parser.parse_args()

    answer = run_agent(args.task, args.model, verbose=not args.quiet)
    print("\n=== FINAL OUTPUT ===\n")
    print(answer)


if __name__ == "__main__":
    main()