import os
import asyncio

from dotenv import load_dotenv
from eth_account import Account

from x402 import x402Client, x402ClientConfig, SchemeRegistration
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmScheme

load_dotenv()

MAX_USD_PER_PAYMENT = "$0.05"

BASE_SEPOLIA_EURC = "0x808456652fdb597867f38412077A9182bf77359F"

# Do keep in mind while editing the code that only these whitelisted hosts can ever receive a payment from the agent. Anything else gets refused before a signer is even touched
ALLOWED_HOSTS = {
    "localhost:4021",
    "127.0.0.1:4021",
}

def _build_client() -> x402Client:
    private_key = os.environ.get("EVM_PRIVATE_KEY")
    if not private_key:
        raise RuntimeError("EVM_PRIVATE_KEY is not set")

    account = Account.from_key(private_key)
    signer = EthAccountSigner(account)

    config = x402ClientConfig(
        schemes=[SchemeRegistration(network="eip155:*", client=ExactEvmScheme(signer))],
        spend_controls={
            "max_amount_per_payment": MAX_USD_PER_PAYMENT,
            "allowed_assets": [
                {"network": "eip155:84532", "asset": BASE_SEPOLIA_EURC},
            ],
        },
    )
    return x402Client.from_config(config)


def _host_allowed(url: str) -> bool:
    from urllib.parse import urlparse
    netloc = urlparse(url).netloc
    return netloc in ALLOWED_HOSTS


async def _pay_and_fetch_async(url: str) -> str:
    if not _host_allowed(url):
        return f"Denied: {url} is not in the allowed host list, add it to ALLOWED_HOSTS if this is expected"

    client = _build_client()

    async with x402HttpxClient(client) as http:
        response = await http.get(url)
        await response.aread()

        if not response.is_success:
            debug_headers = dict(response.headers)
            return (
                f"Request failed: status {response.status_code}, body: {response.text[:500]}\n"
                f"Response headers (check for PAYMENT-REQUIRED / PAYMENT-RESPONSE / X-PAYMENT-ERROR): {debug_headers}"
            )

        return f"Paid and fetched successfully.\nResponse: {response.text}"


def pay_and_fetch(url: str) -> str:
    try:
        return asyncio.run(_pay_and_fetch_async(url))
    except Exception as e:
        return f"Payment flow error: {e}"