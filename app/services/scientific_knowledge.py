
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class ScientificKnowledgeService:
    """
    Servicio para recuperar evidencia científica desde PostgreSQL.

    Utiliza la función:
    agronomic_knowledge.search_scientific_evidence()
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------
    # Consulta SQL
    # -------------------------------------------------

    SEARCH_EVIDENCE_QUERY = text("""
        SELECT *
        FROM agronomic_knowledge.search_scientific_evidence(
            :p_scientific_name,
            :p_climate_variable,
            :p_biological_response,
            :p_location,
            :p_study_type,
            :p_validation_status,
            :p_limit
        )
    """)

    SEARCH_TEMPORAL_PATTERNS_QUERY = text("""
        SELECT
            tp.id AS pattern_id,
            tp.pattern_type,
            tp.period_label,
            tp.months,
            tp.seasonal_context,

            e.id AS evidence_id,
            e.evidence_code,
            e.biological_response,
            e.finding,
            e.result_data,
            e.evidence_type,
            e.statistical_support,
            e.interpretation_limit,
            e.validation_status,

            s.id AS study_id,
            s.study_type,
            s.study_location,
            s.study_locations,

            p.scientific_name,
            p.common_name

        FROM agronomic_knowledge.scientific_temporal_patterns tp

        JOIN agronomic_knowledge.scientific_evidence e
            ON e.id = tp.evidence_id

        JOIN agronomic_knowledge.scientific_studies s
            ON s.id = e.study_id

        JOIN agronomic_knowledge.pest_species p
            ON p.id = s.pest_id

        WHERE
            (
                CAST(:p_scientific_name AS TEXT) IS NULL
                OR LOWER(p.scientific_name) =
                   LOWER(CAST(:p_scientific_name AS TEXT))
            )

            AND (
                CAST(:p_month AS SMALLINT) IS NULL
                OR CAST(:p_month AS SMALLINT) = ANY(tp.months)
            )

            AND (
                CAST(:p_location AS TEXT) IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        COALESCE(s.study_locations, '[]'::jsonb)
                    ) AS loc(value)
                    WHERE CONCAT_WS(
                        ' ',
                        loc.value ->> 'country',
                        loc.value ->> 'department',
                        loc.value ->> 'province',
                        loc.value ->> 'district',
                        loc.value ->> 'site'
                    ) ILIKE
                    '%' || CAST(:p_location AS TEXT) || '%'
                )
            )

            AND (
                CAST(:p_validation_status AS TEXT) IS NULL
                OR e.validation_status =
                   CAST(:p_validation_status AS TEXT)
            )

        ORDER BY
            CASE
                WHEN CAST(:p_month AS SMALLINT) IS NOT NULL
                     AND CAST(:p_month AS SMALLINT) = ANY(tp.months)
                THEN 0
                ELSE 1
            END,
            tp.id

        LIMIT :p_limit
    """)


    # -------------------------------------------------
    # Recuperar evidencia científica
    # -------------------------------------------------
    
    def search_temporal_patterns(
        self,
        scientific_name: Optional[str] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        validation_status: Optional[str] = None,
        limit: int = 20
    ) -> dict[str, Any]:

        if not 1 <= limit <= 100:
            raise ValueError(
                "El límite debe estar entre 1 y 100."
            )

        if month is not None and not 1 <= month <= 12:
            raise ValueError(
                "El mes debe estar entre 1 y 12."
            )

        params = {
            "p_scientific_name": scientific_name,
            "p_month": month,
            "p_location": location,
            "p_validation_status": validation_status,
            "p_limit": limit
        }

        result = self.db.execute(
            self.SEARCH_TEMPORAL_PATTERNS_QUERY,
            params
        )

        rows = result.mappings().all()

        patterns = [
            dict(row)
            for row in rows
        ]

        return {
            "query": {
                "scientific_name": scientific_name,
                "month": month,
                "location": location,
                "validation_status": validation_status
            },
            "retrieval": {
                "total_patterns": len(patterns),
                "limit": limit,
                "has_results": len(patterns) > 0
            },
            "patterns": patterns
        }
    
    def search_evidence(
        self,
        scientific_name: Optional[str] = None,
        climate_variable: Optional[str] = None,
        biological_response: Optional[str] = None,
        location: Optional[str] = None,
        study_type: Optional[str] = None,
        validation_status: Optional[str] = None,
        limit: int = 20
    ) -> dict[str, Any]:

        # Validar límite
        if not 1 <= limit <= 100:
            raise ValueError(
                "El límite debe estar entre 1 y 100."
            )

        # Parámetros de consulta
        params = {
            "p_scientific_name": scientific_name,
            "p_climate_variable": climate_variable,
            "p_biological_response": biological_response,
            "p_location": location,
            "p_study_type": study_type,
            "p_validation_status": validation_status,
            "p_limit": limit
        }

        # Ejecutar función PostgreSQL
        result = self.db.execute(
            self.SEARCH_EVIDENCE_QUERY,
            params
        )

        # Convertir resultados SQLAlchemy a diccionarios
        rows = result.mappings().all()

        evidences = [
            dict(row)
            for row in rows
        ]

        # Construir respuesta estructurada
        response = {
            "query": {
                "scientific_name": scientific_name,
                "climate_variable": climate_variable,
                "biological_response": biological_response,
                "location": location,
                "study_type": study_type,
                "validation_status": validation_status
            },

            "retrieval": {
                "total_evidences": len(evidences),
                "limit": limit,
                "has_results": len(evidences) > 0
            },

            "evidence": evidences
        }

        return response
