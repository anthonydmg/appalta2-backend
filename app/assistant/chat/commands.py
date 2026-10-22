"""Comandos de consulta rápida del chat: "/ahora", "/temp-suelo ayer", "/max hum-aire mes"…

Un comando se resuelve por código, sin el modelo: se elige la consulta (las mismas
herramientas del asistente) y la respuesta se arma con una plantilla fija. Así es inmediata,
siempre tiene el mismo formato y nunca incluye recomendaciones (el asistente no las da).

El catálogo (`catalog_for`) es la única fuente de la lista de comandos: lo usan /ayuda y la
ruta GET /chat/{estación}/commands con la que la app arma su panel de consultas rápidas.
"""

import difflib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

from app.assistant.chat.planner import COUNT, DIAGNOSIS, LATEST, STATS, PlannedCall
from app.assistant.domain.dates import extract_date_range, normalize_text
from app.assistant.domain.sensors import SENSORS

# --- catálogo -----------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    name: str                        # "/temp-aire"
    usage: str                       # "/temp-aire [periodo]"
    description: str
    example: str
    group: str
    aliases: tuple[str, ...] = ()
    sensor: str | None = None        # sensor fijo del comando (para ocultarlo si la estación no lo tiene)


_GROUPS = ("Clima ahora", "Resúmenes", "Temperatura", "Humedad", "Suelo y aire", "Valores puntuales", "Cultivo",
           "Estación", "Ayuda")  # fmt: skip

COMMANDS: tuple[Command, ...] = (
    Command("/ahora", "/ahora", "Lectura actual de todos los sensores, con alertas si hay valores en exceso.",
            "/ahora", "Clima ahora", ("/actual", "/clima")),
    Command("/hoy", "/hoy", "Resumen de hoy: promedio, máximo y mínimo de cada sensor.", "/hoy", "Resúmenes"),
    Command("/ayer", "/ayer", "Resumen de ayer de cada sensor.", "/ayer", "Resúmenes"),
    Command("/semana", "/semana", "Resumen de los últimos 7 días de cada sensor.", "/semana", "Resúmenes"),
    Command("/mes", "/mes", "Resumen del mes en curso de cada sensor.", "/mes", "Resúmenes"),
    Command("/temp-aire", "/temp-aire [periodo]", "Temperatura del aire (ambiente): promedio, máxima y mínima.",
            "/temp-aire ayer", "Temperatura", ("/temp-ambiente", "/ta"), "temperatura_ambiente"),
    Command("/temp-suelo", "/temp-suelo [periodo]", "Temperatura de la tierra, donde están las raíces.",
            "/temp-suelo semana", "Temperatura", ("/ts",), "temperatura_suelo"),
    Command("/hum-aire", "/hum-aire [periodo]", "Humedad del aire (humedad relativa).",
            "/hum-aire hoy", "Humedad", ("/hum-ambiente", "/ha"), "humedad_ambiente"),
    Command("/hum-suelo", "/hum-suelo [periodo]", "Humedad de la tierra: útil para decidir el riego.",
            "/hum-suelo mes", "Humedad", ("/hs",), "humedad_suelo"),
    Command("/ph", "/ph [periodo]", "pH del suelo (óptimo para palta Hass: 5.5–6.5).",
            "/ph setiembre", "Suelo y aire", ("/ph-suelo",), "ph_suelo"),
    Command("/presion", "/presion [periodo]", "Presión atmosférica.",
            "/presion semana", "Suelo y aire", ("/presión",), "presion_atmosferica"),
    Command("/max", "/max <sensor> [periodo]", "Solo el valor máximo de un sensor, con su fecha y hora.",
            "/max temp-aire mes", "Valores puntuales", ("/maximo", "/máximo")),
    Command("/min", "/min <sensor> [periodo]", "Solo el valor mínimo de un sensor, con su fecha y hora.",
            "/min temp-suelo semana", "Valores puntuales", ("/minimo", "/mínimo")),
    Command("/prom", "/prom <sensor> [periodo]", "Solo el promedio de un sensor en el periodo.",
            "/prom hum-suelo setiembre", "Valores puntuales", ("/promedio",)),
    Command("/alertas", "/alertas [periodo]", "Solo los valores en exceso para la palta y el riesgo que implican.",
            "/alertas", "Cultivo", ("/alerta",)),
    Command("/diagnostico", "/diagnostico [periodo]", "Estado del cultivo: valores de cada sensor y alertas para la palta.",
            "/diagnostico semana", "Cultivo", ("/diagnóstico", "/salud")),
    Command("/estado", "/estado", "Estado de la estación: último envío, lecturas y sensores con falla.",
            "/estado", "Estación"),
    Command("/lecturas", "/lecturas [periodo]", "Cantidad de lecturas enviadas por la estación.",
            "/lecturas setiembre", "Estación", ("/conteo",)),
    Command("/ayuda", "/ayuda", "Muestra esta lista de comandos.", "/ayuda", "Ayuda", ("/comandos", "/help")),
)  # fmt: skip

PERIOD_HELP = (
    "Periodos: hoy, ayer, semana (últimos 7 días), mes (mes en curso), mes-pasado, un mes por su nombre "
    "(setiembre), un día (12/09) o un rango (10/09-18/09). Sin periodo se usa la última semana."
)

# Comandos genéricos que no aparecen en el panel: se repregunta "¿aire o suelo?".
_GENERIC = {"/temp": "temperatura", "/temperatura": "temperatura", "/humedad": "humedad", "/hum": "humedad"}
_BY_NAME = {alias: c for c in COMMANDS for alias in (c.name, *c.aliases)}

# Comandos que piden un consejo: AgriSense no da recomendaciones; se indica qué dato consultar.
_NO_ADVICE = "AgriSense no da recomendaciones; solo informa los datos de la estación."
_ADVICE_COMMANDS = {
    "/riego": f"{_NO_ADVICE} Para ver la humedad del suelo usa /hum-suelo [periodo] (ej: /hum-suelo hoy).",
    "/regar": f"{_NO_ADVICE} Para ver la humedad del suelo usa /hum-suelo [periodo] (ej: /hum-suelo hoy).",
    "/fertilizar": f"{_NO_ADVICE} Para ver el pH del suelo usa /ph [periodo] (ej: /ph mes).",
    "/recomendacion": f"{_NO_ADVICE} Usa /alertas para ver los valores en exceso para la palta.",
    "/consejo": f"{_NO_ADVICE} Usa /alertas para ver los valores en exceso para la palta.",
}

# Sensores como argumento de /max, /min, /prom
_SENSOR_ARGS = {
    "temp-aire": "temperatura_ambiente", "temp-ambiente": "temperatura_ambiente", "ta": "temperatura_ambiente",
    "temp-suelo": "temperatura_suelo", "ts": "temperatura_suelo",
    "hum-aire": "humedad_ambiente", "hum-ambiente": "humedad_ambiente", "ha": "humedad_ambiente",
    "hum-suelo": "humedad_suelo", "hs": "humedad_suelo",
    "ph": "ph_suelo", "ph-suelo": "ph_suelo", "presion": "presion_atmosferica",
}  # fmt: skip
_GENERIC_ARGS = {"temp": "temperatura", "temperatura": "temperatura", "hum": "humedad", "humedad": "humedad"}

QUICK_REPLIES = ["Aire (ambiente)", "Suelo", "Ambas"]


def catalog_for(available: set[str] | None = None) -> list[dict[str, Any]]:
    """Comandos agrupados para el panel de la app; sin los de sensores que la estación no tiene."""
    groups = []
    for title in _GROUPS:
        items = [
            {"command": c.name, "usage": c.usage, "description": c.description, "example": c.example,
             "insert": c.name + (" " if "[" in c.usage or "<" in c.usage else "")}
            for c in COMMANDS
            if c.group == title and (c.sensor is None or available is None or c.sensor in available)
        ]  # fmt: skip
        if items:
            groups.append({"title": title, "commands": items})
    return groups


def help_text(available: set[str] | None = None) -> str:
    lines = ["Consultas rápidas (escribe el comando y envía):"]
    for group in catalog_for(available):
        lines.append(f"\n{group['title']}:")
        lines += [f"• {c['usage']} — {c['description']}" for c in group["commands"]]
    return "\n".join(lines) + f"\n\n{PERIOD_HELP}"


# --- interpretación -------------------------------------------------------------


@dataclass
class CommandPlan:
    """Qué hacer con un comando.

    - answer: respuesta fija sin consultar datos (ayuda, comando desconocido, repregunta).
    - calls + render: consultas a ejecutar y plantilla que arma la respuesta con sus resultados.
    - calls + question: consultas cuyo resultado redacta el modelo (con esa pregunta en lenguaje natural).
      Hoy ningún comando lo usa: todos se responden con plantilla.
    """

    calls: list[PlannedCall] = field(default_factory=list)
    render: Callable[[list[dict[str, Any]], datetime], str] | None = None
    question: str | None = None
    answer: str | None = None
    quick_replies: list[str] = field(default_factory=list)
    pending: str | None = None       # comando que espera "aire / suelo / ambas"


def is_command(text: str) -> bool:
    return text.lstrip().startswith("/")


def plan_command(text: str, today: date, available: set[str] | None = None) -> CommandPlan:
    tokens = normalize_text(text.strip()).split()
    head, rest = tokens[0], tokens[1:]
    if head in _ADVICE_COMMANDS:
        return CommandPlan(answer=_ADVICE_COMMANDS[head])
    if head in _GENERIC:
        return _sensor_command(_GENERIC[head], rest, text, today, available)

    command = _BY_NAME.get(head) or _closest(head)
    if command is None:
        hint = _suggestion(head)
        return CommandPlan(answer=f"No reconozco el comando {head}.{hint} Escribe /ayuda para ver la lista completa.")

    if command.sensor:
        return _stats_plan(command.sensor, None, rest, today, available)
    match command.name:
        case "/ahora":
            return CommandPlan(calls=[PlannedCall(LATEST)], render=_render_latest)
        case "/hoy" | "/ayer" | "/semana" | "/mes":
            period = {"/hoy": "hoy", "/ayer": "ayer", "/semana": "ultimos_7_dias", "/mes": "este_mes"}[command.name]
            return CommandPlan(calls=[PlannedCall(DIAGNOSIS, {"periodo": period})], render=_render_summary)
        case "/max" | "/min" | "/prom":
            return _metric_plan(command.name, rest, text, today, available)
        case "/alertas":
            period = _period(rest, today, "ultimos_7_dias")
            return CommandPlan(calls=[PlannedCall(DIAGNOSIS, period)], render=_render_alerts)
        case "/diagnostico":
            period = _period(rest, today, "ultimos_7_dias")
            return CommandPlan(calls=[PlannedCall(DIAGNOSIS, period)], render=_render_summary)
        case "/estado":
            calls = [PlannedCall(LATEST), PlannedCall(COUNT, {"periodo": "ultimos_7_dias"}),
                     PlannedCall(DIAGNOSIS, {"periodo": "ultimos_7_dias"})]  # fmt: skip
            return CommandPlan(calls=calls, render=_render_status)
        case "/lecturas":
            return CommandPlan(calls=[PlannedCall(COUNT, _period(rest, today, "este_mes"))], render=_render_direct)
        case _:  # /ayuda
            return CommandPlan(answer=help_text(available))


def _sensor_command(kind: str, rest: list[str], text: str, today: date, available: set[str] | None) -> CommandPlan:
    """/temp o /humedad: el lugar va en el texto ("/temp suelo ayer") o se repregunta con botones."""
    places = _places(rest)
    if not places:
        return CommandPlan(
            answer=f"¿Qué {kind} quieres consultar: del aire (ambiente) o del suelo?",
            quick_replies=QUICK_REPLIES,
            pending=normalize_text(text.strip()),
        )
    sensors = [f"{kind}_{p}" for p in places]
    return _stats_plan(sensors, None, rest, today, available)


def _metric_plan(name: str, rest: list[str], text: str, today: date, available: set[str] | None) -> CommandPlan:
    metric = {"/max": "max", "/min": "min", "/prom": "prom"}[name]
    sensor = next((_SENSOR_ARGS[t] for t in rest if t in _SENSOR_ARGS), None)
    if sensor:
        return _stats_plan(sensor, metric, rest, today, available)
    kind = next((_GENERIC_ARGS[t] for t in rest if t in _GENERIC_ARGS), None)
    if kind and (places := _places(rest)):
        return _stats_plan([f"{kind}_{p}" for p in places], metric, rest, today, available)
    if kind:
        return CommandPlan(
            answer=f"¿Qué {kind} quieres consultar: del aire (ambiente) o del suelo?",
            quick_replies=QUICK_REPLIES,
            pending=normalize_text(text.strip()),
        )
    return CommandPlan(
        answer=f"Indica el sensor. Por ejemplo: {name} temp-aire mes, {name} hum-suelo semana o {name} ph ayer."
    )


def _stats_plan(
    sensors: str | list[str], metric: str | None, rest: list[str], today: date, available: set[str] | None
) -> CommandPlan:
    sensors = [sensors] if isinstance(sensors, str) else sensors
    missing = [s for s in sensors if available is not None and s not in available]
    if missing:
        names = " ni ".join(SENSORS[s].label.lower().replace("ph ", "pH ") for s in missing)
        return CommandPlan(answer=f"Esta estación no tiene sensor de {names}.")
    period = _period(rest, today, "ultimos_7_dias")
    calls = [PlannedCall(STATS, {"sensor": s, **period}) for s in sensors]
    return CommandPlan(calls=calls, render=lambda outs, now: _render_stats(outs, metric))


def resolve_command_reply(reply: str, pending: str) -> str | None:
    """Completa "/temp ayer" con la respuesta a la repregunta: "suelo" → "/temp suelo ayer"."""
    text = normalize_text(reply)
    place = (
        "ambas" if re.search(r"\b(?:ambas|ambos|las dos|los dos|todas?)\b", text)
        else "suelo" if re.search(r"\b(?:suelo|tierra)\b", text)
        else "aire" if re.search(r"\b(?:aire|ambient\w*)\b", text)
        else None
    )  # fmt: skip
    if place is None or len(text.split()) > 6:
        return None
    return f"{pending} {place}"  # el orden de las palabras del comando no importa


def _places(rest: list[str]) -> list[str]:
    words = set(rest)
    if words & {"ambas", "ambos", "todas", "todos"}:
        return ["ambiente", "suelo"]
    places = []
    if words & {"aire", "ambiente", "ambiental"}:
        places.append("ambiente")
    if words & {"suelo", "tierra"}:
        places.append("suelo")
    return places


_KEYWORD_PERIODS = {"hoy": "hoy", "ayer": "ayer", "semana": "ultimos_7_dias", "mes": "este_mes",
                    "mes-pasado": "mes_anterior", "mespasado": "mes_anterior"}  # fmt: skip


def _period(rest: list[str], today: date, default: str) -> dict[str, Any]:
    text = " ".join(rest)
    if explicit := extract_date_range(text, today):
        start, end = explicit
        return {"periodo": "rango", "fecha_inicio": start.isoformat(), "fecha_fin": end.isoformat()}
    if "mes pasado" in text or "mes anterior" in text:
        return {"periodo": "mes_anterior"}
    for token in rest:
        if token in _KEYWORD_PERIODS:
            return {"periodo": _KEYWORD_PERIODS[token]}
    return {"periodo": default}


def _closest(head: str) -> Command | None:
    match = difflib.get_close_matches(head, list(_BY_NAME), n=1, cutoff=0.8)
    return _BY_NAME[match[0]] if match else None


def _suggestion(head: str) -> str:
    match = difflib.get_close_matches(head, [c.name for c in COMMANDS] + list(_GENERIC), n=2, cutoff=0.5)
    return f" ¿Quisiste decir {' o '.join(match)}?" if match else ""


# --- plantillas de respuesta ----------------------------------------------------


def _fmt_dt(value: str) -> str:
    """'2026-09-29 11:58' → '29/09/2026 11:58'."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")


def _span(out: dict[str, Any]) -> str:
    start, end = out["desde"][:10], out["hasta"][:10]
    fmt = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")  # noqa: E731
    return fmt(start) if start == end else f"{fmt(start)} al {fmt(end)}"


def _value(value: float, unit: str) -> str:
    return f"{value}" if unit == "pH" else f"{value} {unit}"


def _extras(outs: list[dict[str, Any]], *, alerts: bool = True) -> str:
    """Alertas de la palta y avisos de calidad de datos, sin repetir."""
    parts = []
    if alerts and (items := list(dict.fromkeys(a for o in outs for a in o.get("alertas_palta", [])))):
        parts.append("Alertas para la palta:\n" + "\n".join(f"• {a}" for a in items))
    if items := list(dict.fromkeys(w for o in outs for w in o.get("avisos", []))):
        parts.append("\n".join(f"Aviso: {w}" for w in items))
    return "".join(f"\n\n{p}" for p in parts)


def _adjusted(outs: list[dict[str, Any]]) -> str:
    notes = list(dict.fromkeys(o["periodo_ajustado"] for o in outs if o.get("periodo_ajustado")))
    return "".join(f"{n}\n\n" for n in notes)


def _render_stats(outs: list[dict[str, Any]], metric: str | None) -> str:
    blocks = []
    for o in outs:
        if o.get("sin_datos"):
            blocks.append(o.get("respuesta_directa") or o.get("mensaje", "No hay datos en ese periodo."))
            continue
        unit, label = o["unidad"], o["sensor"]
        mx = f"{_value(o['maximo']['valor'], unit)} ({_fmt_dt(o['maximo']['fecha'])})"
        mn = f"{_value(o['minimo']['valor'], unit)} ({_fmt_dt(o['minimo']['fecha'])})"
        avg = _value(o["promedio"], unit)
        if metric == "max":
            blocks.append(f"Máximo de {_lower(label)} ({_span(o)}): {mx}.")
        elif metric == "min":
            blocks.append(f"Mínimo de {_lower(label)} ({_span(o)}): {mn}.")
        elif metric == "prom":
            blocks.append(f"Promedio de {_lower(label)} ({_span(o)}): {avg}.")
        else:
            blocks.append(f"{label} · {_span(o)}\n• Promedio: {avg}\n• Máximo: {mx}\n• Mínimo: {mn}")
    return _adjusted(outs) + "\n\n".join(blocks) + _extras(outs)


def _render_latest(outs: list[dict[str, Any]], now: datetime) -> str:
    o = outs[0]
    if o.get("respuesta_directa"):  # sin datos o lecturas que no son de hoy: ya viene redactada
        return o["respuesta_directa"]
    when = _fmt_dt(max(r["fecha"] for r in o["lecturas"]))
    lines = [f"• {r['sensor']}: {_value(r['valor'], r['unidad'])}" for r in o["lecturas"]]
    return f"Lectura actual de {o['estacion']} ({when}):\n" + "\n".join(lines) + _extras(outs)


def _render_summary(outs: list[dict[str, Any]], now: datetime) -> str:
    o = outs[0]
    if o.get("sin_datos"):
        return o["respuesta_directa"]
    lines = "\n".join(f"• {line}" for line in o["sensores"])
    return f"{_adjusted(outs)}Resumen de {o['estacion']} · {_span(o)}:\n{lines}" + _extras(outs)


def _render_alerts(outs: list[dict[str, Any]], now: datetime) -> str:
    o = outs[0]
    if o.get("sin_datos"):
        return o["respuesta_directa"]
    if not o.get("alertas_palta"):
        return f"{_adjusted(outs)}Sin alertas ({_span(o)}): los valores están dentro de lo normal para la palta Hass."
    items = "\n".join(f"• {a}" for a in o["alertas_palta"])
    return f"{_adjusted(outs)}Alertas para la palta ({_span(o)}):\n{items}"


def _render_status(outs: list[dict[str, Any]], now: datetime) -> str:
    latest, count, diag = outs
    if not latest.get("lecturas"):
        return latest.get("respuesta_directa") or "Esta estación todavía no ha enviado datos."
    last = datetime.strptime(max(r["fecha"] for r in latest["lecturas"]), "%Y-%m-%d %H:%M")
    days = (now.date() - last.date()).days
    since = "hoy" if days == 0 else "ayer" if days == 1 else f"hace {days} días"
    lines = [f"• Último envío: {last:%d/%m/%Y %H:%M} ({since})"]
    if days >= 2:
        lines.append("• La estación no está enviando datos.")
    lines.append(f"• Envíos en los últimos 7 días: {count.get('envios', 0)}")
    problems = diag.get("avisos", [])
    lines += [f"• {p}" for p in problems] if problems else ["• Sensores: sin fallas detectadas en los últimos datos."]
    return f"Estado de {latest['estacion']}:\n" + "\n".join(lines)


def _render_direct(outs: list[dict[str, Any]], now: datetime) -> str:
    return "\n\n".join(o.get("respuesta_directa", "") for o in outs).strip()


def _lower(label: str) -> str:
    return label if label.startswith("pH") else label[0].lower() + label[1:]


def render_executions(executions: list[tuple[str, dict[str, Any]]], now: datetime) -> str:
    """Respuesta con plantilla para resultados de cualquier herramienta (p. ej. tras pedir un consejo)."""
    renderers = {LATEST: _render_latest, DIAGNOSIS: _render_summary, COUNT: _render_direct}
    parts = []
    stats = [out for name, out in executions if name == STATS]
    if stats:
        parts.append(_render_stats(stats, None))
    for name, out in executions:
        if name in renderers:
            parts.append(renderers[name]([out], now))
    return "\n\n".join(p for p in parts if p)
