import subprocess
import tempfile
import os
from pathlib import Path
from ddgs import DDGS
from payments import pay_and_fetch

# SIMPLE SETTINGS GENERAL GUIDE (Written internally for those who are going to skip the README.)
## OUTPUT_DIR is where write_file saves everything the agent produces
## CODE_TIMEOUT_SECONDS caps how long run_python is allowed to run before it gets killed

OUTPUT_DIR = Path("./agent_output")
OUTPUT_DIR.mkdir(exist_ok=True)

CODE_TIMEOUT_SECONDS = 10


def web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        lines.append(f"[{i}] {title}\n{body}\nsource: {href}")
    return "\n\n".join(lines)


def write_file(filename: str, content: str) -> str:
    safe_name = os.path.basename(filename)
    if not safe_name:
        return "Error: invalid filename."

    target = OUTPUT_DIR / safe_name
    try:
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"Write failed: {e}"

    return f"Wrote {len(content)} chars to {target}"


def run_python(code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        script_path = f.name

    try:
        result = subprocess.run(
            ["python3", "-I", "-S", script_path],
            capture_output=True,
            text=True,
            timeout=CODE_TIMEOUT_SECONDS,
            cwd=tempfile.gettempdir(),
        )
        stdout = result.stdout[-4000:]
        stderr = result.stderr[-2000:]
        output = f"Exit code: {result.returncode}\nStdout:\n{stdout}"
        if stderr:
            output += f"\nStderr:\n{stderr}"
        return output
    except subprocess.TimeoutExpired:
        return f"Execution timed out after {CODE_TIMEOUT_SECONDS}s."
    finally:
        os.unlink(script_path)


# Tool definitions handed to the model, plus the lookup table used to actually run them once the model picks one.
# P.S. If you wish to contribute by creating new tool specifications do feel free to do so, but test them before sending the PR.

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a topic. Returns titles, snippets and source URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "search query"},
                    "max_results": {"type": "integer", "description": "number of results, default 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file in the agent output directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "name of the file, no path components"},
                    "content": {"type": "string", "description": "the text content to write"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a short Python snippet in an isolated subprocess and return stdout/stderr. Use this for calculations, data processing or verifying numeric claims. No network or file access inside the sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "python source code to execute"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pay_and_fetch",
            "description": "Fetch a URL that requires x402 payment. Detects an HTTP 402 response, signs a testnet EURC payment on Base Sepolia, and retries automatically. Capped at $0.05 per payment and restricted to an explicit host allowlist for safety.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "the full URL of the paid resource"},
                },
                "required": ["url"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "web_search": web_search,
    "write_file": write_file,
    "run_python": run_python,
    "pay_and_fetch": pay_and_fetch,
}