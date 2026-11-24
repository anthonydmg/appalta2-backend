
import json
from pathlib import Path

from app.services.agroclimatic_response_enricher import (
    AgroclimaticResponseEnricher,
)

from app.schemas.agroclimatic_reasoning import (
    AgroclimaticReasoningResponse,
)

from app.schemas.agroclimatic_report import (
    AgroclimaticReport,
)
from app.services.json_stream_parser import TopLevelJSONStreamParser

class AgroclimaticReasoningService:

    def __init__(
        self,
        ollama_client,
        prompt_builder,
        response_enricher=None,
    ):
        self.ollama_client = ollama_client
        self.prompt_builder = prompt_builder

        self.response_enricher = (
            response_enricher
            or AgroclimaticResponseEnricher()
        )

    def analyze(
        self,
        agronomic_context: dict,
    ) -> dict:

        # 1. Construir prompt.
        prompt = self.prompt_builder.build(
            agronomic_context
        )

        # 2. Obtener esquema JSON de salida de Gemma.
        output_schema = (
            AgroclimaticReasoningResponse.model_json_schema()
        )

        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        prompt_file = output_dir / "prompt_preview_final.txt"

        with prompt_file.open("w", encoding="utf-8") as file:
            file.write(prompt)

        # 3. Ejecutar modelo.
        result = self.ollama_client.generate(
            prompt=prompt,
            format_schema=output_schema,
        )

        # 4. Verificar finalización.
        if result.get("done") is not True:
            raise RuntimeError(
                "La generación no finalizó correctamente."
            )

        if result.get("done_reason") == "length":
            raise RuntimeError(
                "La generación alcanzó el límite de tokens."
            )

        # 5. Obtener texto.
        response_text = result.get("response", "")

        if not response_text.strip():
            raise RuntimeError(
                "Ollama devolvió una respuesta vacía."
            )

        # 6. Convertir JSON.
        try:
            response_data = json.loads(response_text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemma devolvió JSON inválido."
            ) from exc

        # 7. Validar respuesta de Gemma.
        validated_response = (
            AgroclimaticReasoningResponse.model_validate(
                response_data
            )
        )

        # 8. Construir informe agroclimático final.
        report: AgroclimaticReport = (
            self.response_enricher.enrich(
                response=validated_response,
                agronomic_context=agronomic_context,
            )
        )

        return {
            "analysis": report,
            "metrics": result.get("metrics", {}),
            "model": result.get("model"),
            "done": result.get("done"),
            "done_reason": result.get("done_reason"),
        }

    def analyze_stream(
        self,
        agronomic_context: dict,
    ):
        """
        Genera el informe agroclimático mediante streaming.

        Emite:
        - section: cuando una propiedad JSON está completa.
        - report_completed: cuando el informe final fue validado
          y enriquecido correctamente.

        Cada evento es un diccionario.
        """

        # 1. Construir prompt.
        prompt = self.prompt_builder.build(
            agronomic_context
        )

        # 2. Obtener esquema JSON de salida.
        output_schema = (
            AgroclimaticReasoningResponse.model_json_schema()
        )

        # 3. Guardar prompt para inspección.
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        prompt_file = output_dir / "prompt_preview_final.txt"

        with prompt_file.open("w", encoding="utf-8") as file:
            file.write(prompt)

        # 4. Inicializar parser y acumulador.
        parser = TopLevelJSONStreamParser()
        response_text = ""

        final_chunk = None

        # 5. Consumir fragmentos de Ollama.
        for chunk in self.ollama_client.generate_stream(
            prompt=prompt,
            format_schema=output_schema,
        ):

            fragment = chunk.get("response", "")

            if fragment:
                response_text += fragment

                # 6. Detectar propiedades JSON completas.
                completed_sections = parser.feed(fragment)

                for section_name, section_data in completed_sections:
                    yield {
                        "event": "section",
                        "section": section_name,
                        "data": section_data,
                    }

            # Guardar el último fragmento con métricas.
            if chunk.get("done") is True:
                final_chunk = chunk

        # 7. Verificar finalización.
        if final_chunk is None:
            raise RuntimeError(
                "La generación de Ollama no finalizó correctamente."
            )

        if final_chunk.get("done") is not True:
            raise RuntimeError(
                "La generación no finalizó correctamente."
            )
        
        if final_chunk.get("done_reason") == "length":
            raise RuntimeError(
                "La generación alcanzó el límite de tokens."
            )

        if not response_text.strip():
            raise RuntimeError(
                "Ollama devolvió una respuesta vacía."
            )

        # 8. Verificar que el JSON esté completo.
        parser.finish()

        # 9. Convertir JSON completo.
        try:
            response_data = json.loads(response_text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Gemma devolvió JSON inválido."
            ) from exc

        # 10. Validar respuesta de Gemma.
        validated_response = (
            AgroclimaticReasoningResponse.model_validate(
                response_data
            )
        )

        # 11. Construir informe agroclimático definitivo.
        report: AgroclimaticReport = (
            self.response_enricher.enrich(
                response=validated_response,
                agronomic_context=agronomic_context,
            )
        )

        # 12. Recuperar métricas de Ollama.
        prompt_tokens = final_chunk.get("prompt_eval_count")
        generated_tokens = final_chunk.get("eval_count")

        prompt_duration = final_chunk.get(
            "prompt_eval_duration", 0
        )

        eval_duration = final_chunk.get(
            "eval_duration", 0
        )

        metrics = {
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,

            "load_duration_ns": final_chunk.get(
                "load_duration"
            ),
            "prompt_eval_duration_ns": prompt_duration,
            "eval_duration_ns": eval_duration,
            "total_duration_ns": final_chunk.get(
                "total_duration"
            ),

            "prompt_tokens_per_second": (
                prompt_tokens / (prompt_duration / 1e9)
                if prompt_tokens is not None and prompt_duration > 0
                else None
            ),

            "generation_tokens_per_second": (
                generated_tokens / (eval_duration / 1e9)
                if generated_tokens is not None and eval_duration > 0
                else None
            ),

            "done_reason": final_chunk.get("done_reason"),
        }

        # 13. Emitir informe definitivo.
        yield {
            "event": "report_completed",
            "analysis": report,
            "metrics": metrics,
            "model": final_chunk.get("model"),
            "done": final_chunk.get("done"),
            "done_reason": final_chunk.get("done_reason"),
        }
