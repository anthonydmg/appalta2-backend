
from typing import Any

from sqlalchemy.orm import Session

from app.services.scientific_knowledge import (
    ScientificKnowledgeService
)

from app.services.scientific_context_builder import (
    ScientificContextBuilder
)

from app.services.ollama_client import (
    OllamaClient
)


class ScientificAssistantService:

    def __init__(self, db: Session):

        self.knowledge_service = (
            ScientificKnowledgeService(db)
        )

        self.context_builder = (
            ScientificContextBuilder()
        )

        self.llm = OllamaClient()

    def answer(
        self,
        question: str,
        scientific_name: str | None = None,
        climate_variable: str | None = None,
        biological_response: str | None = None,
        location: str | None = None,
        study_type: str | None = None,
        validation_status: str | None = None,
        limit: int = 20
    ) -> dict[str, Any]:

        # 1. Recuperar evidencia científica
        retrieval = self.knowledge_service.search_evidence(
            scientific_name=scientific_name,
            climate_variable=climate_variable,
            biological_response=biological_response,
            location=location,
            study_type=study_type,
            validation_status=validation_status,
            limit=limit
        )

        # No llamar al modelo si no existe evidencia
        if not retrieval["evidence"]:

            return {
                "question": question,
                "answer": (
                    "No se encontró evidencia científica "
                    "que coincida con los filtros de búsqueda. "
                    "No es posible elaborar una respuesta "
                    "fundamentada con los registros disponibles."
                ),
                "retrieval": retrieval["retrieval"],
                "references": []
            }

        # 2. Construir contexto científico
        context = self.context_builder.build_context(
            retrieval
        )

        context_json = self.context_builder.to_json(
            context
        )

        # 3. Construir prompt
        prompt = self._build_prompt(
            question,
            context_json
        )

        # 4. Consultar Gemma mediante Ollama
        llm_response = self.llm.generate(prompt)

        answer = llm_response.get("response", "").strip()

        # 5. Construir referencias trazables
        references = []

        for evidence in retrieval["evidence"]:

            references.append({
                "evidence_code": evidence["evidence_code"],
                "document_code": evidence["document_code"],
                "source_title": evidence["source_title"],
                "publication_year": evidence["publication_year"],
                "source_location": evidence["source_location"],
                "matched_locations": evidence["matched_locations"],
                "validation_status": evidence["validation_status"]
            })

        return {
            "question": question,
            "answer": answer,
            "retrieval": retrieval["retrieval"],
            "references": references,
            "model": self.llm.model
        }

    @staticmethod
    def _build_prompt(
        question: str,
        context_json: str
    ) -> str:

        return f"""
Eres un asistente especializado en conocimiento
científico y agronómico del cultivo de palto Hass.

Tu tarea es responder preguntas utilizando la evidencia
científica proporcionada en el contexto.

PREGUNTA DEL USUARIO:
{question}

CONTEXTO CIENTÍFICO RECUPERADO:
{context_json}

REGLAS OBLIGATORIAS:

1. Fundamenta las afirmaciones científicas en las
   evidencias proporcionadas.

2. No inventes temperaturas, porcentajes, fechas,
   ubicaciones ni resultados.

3. Diferencia los estudios de laboratorio de los
   estudios realizados en campo.

4. Distingue el lugar de ejecución del estudio,
   la procedencia del material biológico y el lugar
   de observación.

5. No interpretes una correlación como causalidad.

6. Respeta las limitaciones metodológicas descritas
   en cada evidencia.

7. Las evidencias con estado
   EXTRACTED_PENDING_AGRONOMIC_VALIDATION todavía
   requieren validación agronómica. Indícalo cuando
   corresponda y no las presentes como conocimiento
   científicamente aprobado.

8. Incluye los códigos de evidencia entre corchetes
   cuando utilices un hallazgo. Ejemplo: [F01-E02].

9. Si los estudios presentan resultados diferentes,
   explica las diferencias y no fuerces una conclusión
   única.

10. Si la información recuperada no permite responder
    una parte de la pregunta, indícalo expresamente.

FORMATO DE RESPUESTA:

- Respuesta directa.
- Explicación basada en los estudios recuperados.
- Limitaciones de la evidencia.
- Códigos de las evidencias utilizadas.

No afirmes que consultaste estudios que no aparecen
en el contexto proporcionado.
"""
