
from app.services.ollama_client import OllamaClient

client = OllamaClient()

prompt = """
Explica brevemente qué es la queresa Fiorinia fioriniae
y cómo afecta al cultivo de palto Hass.
Responde en español.
"""

print("\n===== PRUEBA DE STREAMING =====\n")

for chunk in client.generate_stream(prompt):

    text = chunk.get("response", "")

    if text:
        print(text, end="", flush=True)

    if chunk.get("done"):
        print("\n\n===== GENERACIÓN FINALIZADA =====")

        print("Motivo:", chunk.get("done_reason"))
        print("Tokens generados:", chunk.get("eval_count"))
        print("Tokens de entrada:", chunk.get("prompt_eval_count"))
