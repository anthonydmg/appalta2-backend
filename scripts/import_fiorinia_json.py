#!/usr/bin/env python3
"""Importador inicial del bundle Fiorinia fioriniae a PostgreSQL.

Modo seguro predeterminado: valida y hace ROLLBACK. Para guardar, usar --apply.
Requiere: pip install "psycopg[binary]"
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from typing import Any

DATABASE_URL="postgresql://postgres:admin@localhost:5432/develop_appalta2"

VALIDATION_STATUS = "EXTRACTED_PENDING_AGRONOMIC_VALIDATION"
STUDY_TYPE_BY_DOCUMENT = {
    "F01": "controlled_laboratory_experiment",
    "F02": "laboratory_observational_study",
    "F03": "field_observational_study",
    "F05": "field_observational_and_statistical_study",
}
CONTROLLED_ENVIRONMENT_BY_DOCUMENT = {"F01": True, "F02": True, "F03": False, "F05": False}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_bundle(data: Any) -> None:
    require(isinstance(data, dict), "La raíz del JSON debe ser un objeto")
    require(data.get("schema_version") in {"1.0", "1.1"}, "schema_version no soportada")
    species = data.get("pest_species")
    require(isinstance(species, dict) and species.get("scientific_name"), "Falta pest_species.scientific_name")
    sources, evidence = data.get("source_documents"), data.get("evidence")
    require(isinstance(sources, list) and len(sources) == 4, "Se esperan las cuatro fuentes F01, F02, F03 y F05")
    require(isinstance(evidence, list) and len(evidence) == 20, "Se esperan 20 registros de evidencia")
    source_ids = set()
    for src in sources:
        code = src.get("document_id")
        require(code and code not in source_ids, f"document_id vacío o duplicado: {code}")
        source_ids.add(code)
        require(src.get("title") and isinstance(src.get("authors"), list), f"Metadatos incompletos en {code}")
        require(src.get("study_location"), f"Falta study_location en {code}")
        locations = src.get("locations")
        require(isinstance(locations, list) and locations, f"Faltan locations en {code}")
        for loc in locations:
            require(loc.get("role") and loc.get("place_name"), f"Ubicación sin role/place_name en {code}")
    evidence_ids = set()
    for ev in evidence:
        code = ev.get("evidence_id")
        require(code and code not in evidence_ids, f"evidence_id vacío o duplicado: {code}")
        evidence_ids.add(code)
        require(ev.get("document_id") in source_ids, f"Fuente inexistente en {code}")
        for field in ("climate_variable", "biological_response", "finding"):
            require(ev.get(field) is not None and str(ev[field]).strip(), f"{code}: falta {field}")
        require(isinstance(ev.get("conditions", {}), dict), f"{code}: conditions debe ser objeto")
        require(isinstance(ev.get("result", {}), dict), f"{code}: result debe ser objeto")


def import_bundle(conn, data: dict[str, Any], apply: bool) -> dict[str, int]:
    from psycopg.types.json import Jsonb
    counts = {"species": 0, "sources": 0, "studies": 0, "conditions": 0, "evidence": 0}
    try:
        with conn.cursor() as cur:
            pest = data["pest_species"]
            cur.execute("""INSERT INTO agronomic_knowledge.pest_species
                (scientific_name, common_name, pest_family, host_crop)
                VALUES (%s,%s,%s,%s) RETURNING id""",
                (pest["scientific_name"], pest.get("common_name"), pest.get("pest_family", "Diaspididae"), "palto (Persea americana)"))
            pest_id = cur.fetchone()[0]
            counts["species"] = 1
            source_map = {s["document_id"]: s for s in data["source_documents"]}
            study_ids = {}
            for code, src in source_map.items():
                cur.execute("""INSERT INTO agronomic_knowledge.scientific_sources
                    (document_code,title,authors,publication_year,institution,document_type,country,extraction_status,raw_metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (code,src["title"],src.get("authors",[]),src.get("year"),src.get("institution"),
                     "thesis", "Perú", VALIDATION_STATUS, Jsonb(src)))
                source_id = cur.fetchone()[0]
                counts["sources"] += 1
                cur.execute("""INSERT INTO agronomic_knowledge.scientific_studies
                    (source_id,pest_id,study_type,crop,crop_variety,study_location,study_locations,raw_metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (source_id,pest_id,STUDY_TYPE_BY_DOCUMENT.get(code),"palto (Persea americana)","Hass",
                     src.get("study_location"),Jsonb(src.get("locations",[])),
                     Jsonb({"document_id":code,"location_extraction_status":src.get("location_extraction_status"),
                            "location_note":src.get("location_note")})))
                study_ids[code] = cur.fetchone()[0]
                counts["studies"] += 1
            for ev in data["evidence"]:
                study_id = study_ids[ev["document_id"]]
                code = ev["evidence_id"]
                cur.execute("""INSERT INTO agronomic_knowledge.study_conditions
                    (study_id,condition_code,controlled_environment,conditions_data)
                    VALUES (%s,%s,%s,%s) RETURNING id""",
                    (study_id,code,CONTROLLED_ENVIRONMENT_BY_DOCUMENT.get(ev["document_id"]),Jsonb(ev.get("conditions") or {})))
                condition_id = cur.fetchone()[0]
                counts["conditions"] += 1
                cur.execute("""INSERT INTO agronomic_knowledge.scientific_evidence
                    (study_id,condition_id,evidence_code,climate_variable,biological_response,finding,result_data,
                     evidence_type,statistical_support,source_location,interpretation_limit,validation_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (study_id,condition_id,code,ev["climate_variable"],ev["biological_response"],ev["finding"],
                     Jsonb(ev.get("result") or {}),ev.get("evidence_type"),ev.get("statistical_support"),
                     Jsonb(ev.get("source_location") or {}),ev.get("interpretation_limit"),VALIDATION_STATUS))
                counts["evidence"] += 1
        if apply:
            conn.commit()
        else:
            conn.rollback()
        return counts
    except Exception:
        conn.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa desde cero las evidencias de Fiorinia fioriniae")
    parser.add_argument("--json", default="fiorinia_fioriniae_evidence_bundle.json")
    parser.add_argument("--apply", action="store_true", help="Confirma inserción; sin esta opción hace ROLLBACK")
    parser.add_argument("--database-url", default=DATABASE_URL)
    args = parser.parse_args()
    path = Path(args.json)
    if not path.is_file():
        print(f"ERROR: No existe el JSON: {path}", file=sys.stderr); return 2
    if not args.database_url:
        print("ERROR: configura DATABASE_URL o --database-url", file=sys.stderr); return 2
    try:
        import psycopg
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_bundle(data)
        with psycopg.connect(args.database_url) as conn:
            counts = import_bundle(conn, data, args.apply)
        print("IMPORTACIÓN CONFIRMADA" if args.apply else "SIMULACIÓN CORRECTA (ROLLBACK; no se guardó nada)")
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())
