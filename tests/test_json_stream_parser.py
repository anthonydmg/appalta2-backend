
from app.services.json_stream_parser import (
    TopLevelJSONStreamParser
)

parser = TopLevelJSONStreamParser()

fragments = [
    '{"climate_interpretations":',
    '[{"period_days":7,',
    '"sensor_code":"ambient_temperature",',
    '"interpretation":"Temperatura media de 27 °C."}]',
    ',"scientific_evidence":"Evidencia científica disponible."',
    ',"recommendations":[{"action":"Inspeccionar hojas"}]}'
]

print("===== PRUEBA DEL PARSER =====")

for fragment in fragments:

    completed = parser.feed(fragment)

    for key, value in completed:
        print(f"\nSección completada: {key}")
        print(value)

parser.finish()

print("\nJSON completo correctamente recibido.")
