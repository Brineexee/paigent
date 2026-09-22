from x402.schemas.base import AssetAmount
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.schemas import Network
from x402.server import x402ResourceServer

import os

load_dotenv()

app = FastAPI()

SELLER_EVM_ADDRESS = os.environ.get("SELLER_EVM_ADDRESS")
if not SELLER_EVM_ADDRESS:
    raise SystemExit("You must set SELLER_EVM_ADDRESS to the wallet that should receive payments")

# Base Sepolia
EVM_NETWORK: Network = "eip155:84532"

# On Base Sepolia EURC.
# Name/version form the EIP-712 signing domain and must match the contract's own values exactly. 
# These are inferred from Base Sepolia USDC's domain (name="USDC", version="2", symbol form not full name), since EURC is deployed the same way on the same testnet. 
# If signing fails with an invalid signature type of error rather than a clean message, then this pairing is the first thing to suspect.

EURC_BASE_SEPOLIA = "0x808456652fdb597867f38412077A9182bf77359F"
EURC_EIP712_NAME = "EURC"
EURC_EIP712_VERSION = "2"

# Testnet facilitator, DO NOT reuse this for mainnet routes
facilitator = HTTPFacilitatorClient(FacilitatorConfig(url="https://x402.org/facilitator"))

server = x402ResourceServer(facilitator)
server.register(EVM_NETWORK, ExactEvmServerScheme())

routes: dict[str, RouteConfig] = {
    "GET /premium-fact": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=SELLER_EVM_ADDRESS,
                price=AssetAmount(
                    amount="10000", # Taking 0.01 EURC, 6 decimals
                    asset=EURC_BASE_SEPOLIA,
                    extra={"name": EURC_EIP712_NAME, "version": EURC_EIP712_VERSION},
                ),
                network=EVM_NETWORK,
            ),
        ],
        mime_type="application/json",
        description="A gated fact endpoint, used to demo agent-to-agent x402 payments.",
    ),
}

app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


@app.get("/premium-fact")
async def premium_fact() -> dict[str, Any]:
    return {
        "fact": "The x402 protocol revives the dormant HTTP 402 Payment Required status code.", # Output test message
        "paid": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4021)