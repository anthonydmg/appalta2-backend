
import os
import httpx
import json

class OllamaClient:
    """
    Cliente para consumir modelos desplegados mediante Ollama.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "http://localhost:11434"
        ).rstrip("/")

        self.model = os.getenv(
            "LLM_MODEL",
            "gemma4:e2b"
        )

        self.timeout = int(
            os.getenv("LLM_TIMEOUT", "300")
        )

        self.keep_alive = os.getenv(
            "LLM_KEEP_ALIVE",
            "20m"
        )

        self.temperature = float(
            os.getenv("LLM_TEMPERATURE", "0.2")
        )

        self.num_ctx = int(
            os.getenv("LLM_NUM_CTX", 32768)
        )

        # Espacio reservado para la respuesta JSON.
        self.num_predict = int(
            os.getenv("LLM_NUM_PREDICT", 4096)
        )

    
    def generate(
        self,
        prompt: str,
        format_schema: dict | str | None = None
    ) -> dict:

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict
            }
        }

        # Solicitar respuesta JSON estructurada.
        if format_schema is not None:
            payload["format"] = format_schema

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)

            if response.status_code != 200:
                print("ERROR OLLAMA:")
                print("Status:", response.status_code)
                print("Response:", response.text)

            response.raise_for_status()
            result = response.json()

        metrics = {
            "prompt_tokens": result.get("prompt_eval_count"),
            "generated_tokens": result.get("eval_count"),

            "load_duration_ns": result.get("load_duration"),
            "prompt_eval_duration_ns": result.get(
                "prompt_eval_duration"
            ),
            "eval_duration_ns": result.get("eval_duration"),
            "total_duration_ns": result.get("total_duration"),

            "prompt_tokens_per_second": (
                result["prompt_eval_count"]
                / (result["prompt_eval_duration"] / 1e9)
                if result.get("prompt_eval_duration", 0) > 0
                else None
            ),

            "generation_tokens_per_second": (
                result["eval_count"]
                / (result["eval_duration"] / 1e9)
                if result.get("eval_duration", 0) > 0
                else None
            ),

            "done_reason": result.get("done_reason")
        }

        result["metrics"] = metrics

        return result


    def generate_stream(
        self,
        prompt: str,
        format_schema: dict | str | None = None
    ):
        """
        Genera una respuesta mediante streaming desde Ollama.

        Retorna fragmentos NDJSON como diccionarios.
        Cada fragmento puede contener texto parcial o
        información de finalización.
        """

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict
            }
        }

        # Solicitar respuesta JSON estructurada.
        if format_schema is not None:
            payload["format"] = format_schema

        with httpx.Client(timeout=self.timeout) as client:

            with client.stream(
                "POST",
                url,
                json=payload
            ) as response:

                response.raise_for_status()

                for line in response.iter_lines():

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            "Ollama devolvió un fragmento JSON inválido."
                        ) from exc

                    # Errores reportados por Ollama.
                    if chunk.get("error"):
                        raise RuntimeError(
                            f"Error de Ollama: {chunk['error']}"
                        )

                    yield chunk
    
    def count_prompt_tokens(self, prompt: str) -> int:
        """
        Mide los tokens de entrada procesados por Ollama.
        Utiliza prompt_eval_count de /api/generate.
        """

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0,
                "num_ctx": self.num_ctx,
                "num_predict": 1
            }
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)

            if response.status_code != 200:
                    print("HTTP:", response.status_code)
                    print("Respuesta de Ollama:", response.text)
    
            response.raise_for_status()
            result = response.json()

        token_count = result.get("prompt_eval_count")

        if token_count is None:
            raise RuntimeError(
                "Ollama no devolvió prompt_eval_count."
            )

        return int(token_count)


