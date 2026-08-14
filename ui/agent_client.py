import os
import requests
from databricks.sdk.core import Config

AGENT_APP_URL = os.environ["AGENT_APP_URL"]

_cfg = Config()


def ask_agent(messages: list[dict]) -> tuple[str, list[dict]]:
    """Llama a /invocations. Devuelve (texto_para_mostrar, output_items_crudos).

    output_items_crudos hay que agregarlos tal cual al historial que se manda
    en el siguiente turno -- no reconstruir un {"role": "assistant", ...} a mano,
    porque el servidor espera la forma estructurada exacta que el mismo devolvio.
    """
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
    output_items = data.get("output", [])
    texts = []
    for item in output_items:
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    texts.append(block.get("text", ""))
    reply_text = "\n".join(texts) if texts else "(sin respuesta)"
    return reply_text, output_items
