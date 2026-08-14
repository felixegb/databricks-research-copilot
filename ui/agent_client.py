import os
import requests
from databricks.sdk.core import Config

AGENT_APP_URL = os.environ["AGENT_APP_URL"]

_cfg = Config()


def ask_agent(messages: list[dict]) -> str:
    headers = _cfg.authenticate()
    headers["Content-Type"] = "application/json"
    resp = requests.post(
        f"{AGENT_APP_URL}/invocations",
        headers=headers,
        json={"input": messages},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    texts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    texts.append(block.get("text", ""))
    return "\n".join(texts) if texts else "(sin respuesta)"