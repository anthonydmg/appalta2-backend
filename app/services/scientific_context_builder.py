
import json

from typing import Any


class ScientificContextBuilder:
    """
    Construye un contexto científico estructurado
    a partir de los resultados de ScientificKnowledgeService.

    No realiza inferencias agronómicas ni modifica
    los resultados originales.
    """

    def build_context(
        self,
        retrieval_response: dict[str, Any]
    ) -> dict[str, Any]:

        query = retrieval_response.get("query", {})
        retrieval = retrieval_response.get("retrieval", {})
        evidences = retrieval_response.get("evidence", [])

        structured_evidences = []

        for evidence in evidences:

            structured_evidence = {
                "evidence_code": evidence.get("evidence_code"),

                "finding": evidence.get("finding"),

                "climate_variable": evidence.get(
                    "climate_variable"
                ),

                "biological_response": evidence.get(
                    "biological_response"
                ),

                "evidence_type": evidence.get(
                    "evidence_type"
                ),

                "statistical_support": evidence.get(
                    "statistical_support"
                ),

                "conditions": evidence.get(
                    "conditions", {}
                ),

                "result": evidence.get(
                    "result", {}
                ),

                "study": {
                    "study_type": evidence.get("study_type"),

                    "study_location": evidence.get(
                        "study_location"
                    ),

                    "study_locations": evidence.get(
                        "study_locations", []
                    )
                },

                "geographic_match": {
                    "matched_locations": evidence.get(
                        "matched_locations", []
                    )
                },

                "source": {
                    "document_code": evidence.get(
                        "document_code"
                    ),

                    "title": evidence.get(
                        "source_title"
                    ),

                    "authors": evidence.get(
                        "authors"
                    ),

                    "publication_year": evidence.get(
                        "publication_year"
                    ),

                    "source_location": evidence.get(
                        "source_location"
                    )
                },

                "interpretation_limit": evidence.get(
                    "interpretation_limit"
                ),

                "validation_status": evidence.get(
                    "validation_status"
                )
            }

            structured_evidences.append(
                structured_evidence
            )

        context = {
            "context_type": "scientific_evidence",

            "context_version": "1.0",

            "query": query,

            "retrieval": {
                "total_evidences": retrieval.get(
                    "total_evidences", 0
                ),

                "limit": retrieval.get("limit"),

                "has_results": retrieval.get(
                    "has_results", False
                )
            },

            "evidences": structured_evidences,

            "instructions": [
                "Utilizar exclusivamente la evidencia recuperada como fundamento de las afirmaciones científicas.",

                "No inventar resultados, valores, ubicaciones ni referencias bibliográficas.",

                "Diferenciar el lugar de ejecución del estudio, la procedencia del material biológico y el lugar de observación de campo.",

                "No interpretar una coincidencia geográfica como prueba de que el experimento se realizó en esa localidad.",

                "No establecer causalidad cuando el estudio solamente reporta asociaciones o correlaciones.",

                "Considerar las limitaciones de interpretación de cada evidencia.",

                "Indicar cuando la evidencia se encuentre pendiente de validación agronómica.",

                "Conservar los códigos de evidencia y las fuentes para permitir la trazabilidad."
            ]
        }

        return context

    @staticmethod
    def to_json(
        context: dict[str, Any]
    ) -> str:

        return json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
            default=str
        )
