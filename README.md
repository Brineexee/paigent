# paigent
An autonomous CLI research agent with tool calling, agentic workflows and sandboxed code execution

## Installation
Ensure you have Python installed, then install the dependencies using the requirements file
```
pip install -r requirements.txt
```

Set your keys in .env (OpenRouter API key is free, or you can edit the model provider in agent.py)
EVM_PRIVATE_KEY and SELLER_EVM_ADDRESS are only needed for the pay_and_fetch tool
```
OPENROUTER_API_KEY=openrouter_api_key_here
EVM_PRIVATE_KEY=evm_private_key_here
SELLER_EVM_ADDRESS=seller_evm_address_here
```

## Usage
```
python agent.py "your task here"
```
Give it a task and the agent will plan its own steps.
It has four tools available:

- ```web_search``` Searches the web via DuckDuckGo and returns titles, snippets and source URLs
- ```run_python``` Runs a short Python snippet in an isolated subprocess (No network, nor site packages and there's a 10 second timeout) for calculations or verifying claims
- ```write_file``` Writes the final output to a file in ```agent_output/```. Each filename can only be written once per run, so the agent can't accidentally overwrite its own report.
- ```pay_and_fetch``` Fetches a URL that requires x402 payment. Detects an HTTP 402 response, signs a testnet EURC payment on Base Sepolia and retries automatically. Capped at $0.05 per payment and restricted to an explicit host allowlist (whitelist).

These will be called automatically, if you wish to contribute by creating new tool specifications do feel free to do so (listed in tools.py), **but test them before sending the PR.**

### Flags
```--model``` Pick a specific OpenRouter model instead of the default ```openrouter/free``` router. 
This is primarily useful if you want consistent output instead of a randomly picked free model each run (Check Known Issues #1 to learn why).

```--quiet``` Hides all the extra debug logs and just prints the final answer.

The agent keeps looping, searching, running code, adjusting after failed calls, until it either writes its file and gives a plain text summary or hits the turn limit (20, obviously editable).
In the SYSTEM_PROMPT it's defined so that all cited claims come back in ```[1]``` ```[2]``` style with a Sources list at the end, therefore there should not be any raw HTML links in the middle of the answer.


## Examples
Research any topic and get a cited report:
```
python agent.py "Research the current state of agent to agent payment protocols and write a cited summary to report.md"
```

Use a specific model instead of the random free router (For this option, make sure to check openrouter.ai/collections/free-models for what's currently available as the free ones tend to disappear pretty fast):
```
python agent.py "Research discussions from developer forums and technical video essays regarding core engine performance bottlenecks in Cities: Skylines II. Write a cited 5 paragraph summary to performance_fixes.md on how to resolve rendering and simulation issues at the structural level." --model deepseek/deepseek-v4-flash:free
```

## Payment System
paigent can autonomously pay for gated resources using the [x402 protocol](https://www.x402.org/), which is an open standard that revives the HTTP 402 status code so clients (including AI agents) can pay for a resource in stablecoins over plain HTTP.

This repo includes a small demo paywall server that gates a single endpoint behind a $0.01 equivalent EURC payment on Base Sepolia testnet. To try it you just need to set ```EVM_PRIVATE_KEY``` (the wallet paying) and ```SELLER_EVM_ADDRESS``` (the wallet receiving) in ```.env```, start the paywall server ( ```python paywall_server.py```) and write your task in another terminal, example:
```
python agent.py "Fetch the premium fact from http://localhost:4021/premium-fact, paying for it if required"
```

Spending is limited by a $0.05 individual payment cap via x402's own spend controls, and a host allowlist in ```payments.py``` so the agent can only ever pay hosts you've explicitly listed. Make sure to add your custom hosts to the list if you want the agent to be able to pay on different sites.

## Known issues
These issues should be fixed, but they don't necessarily rely on my end. If you encounter any of the ones in this list during your tests, consider it before opening an issue.
- Smaller free models occasionally hallucinate tools that don't exist, but this problem is caused by the openrouter random free models and the only thing that could be done is to reinforce the SYSTEM_PROMPT (which was done successfully as I did not encounter this issue any further).

## Contributing
Found a bug or want to add a feature? Feel free to open an issue or submit a pull request. If you're adding a new tool specification, **_always test it before sending the PR._**
