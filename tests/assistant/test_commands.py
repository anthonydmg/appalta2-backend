"""Consultas rápidas con comandos: /ahora, /temp-suelo ayer, /max hum-aire mes…"""

from datetime import date

import pytest

from app.assistant.chat.commands import (
    QUICK_REPLIES,
    catalog_for,
    help_text,
    is_command,
    plan_command,
    resolve_command_reply,
)
from app.assistant.chat.memory import InMemoryConversationStore
from app.assistant.chat.service import ChatService
from app.assistant.config import get_settings
from app.assistant.llm.base import LLMChunk
from tests.assistant.conftest import NOW, FakeRepository, ScriptedLLM

pytestmark = pytest.mark.anyio
TODAY = date(2026, 9, 25)
SEPT = {"periodo": "rango", "fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-30"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def calls(text, available=None):
    plan = plan_command(text, TODAY, available)
    return [(c.name, c.arguments) for c in plan.calls]


# --- interpretación ----------------------------------------------------------------


def test_only_slash_messages_are_commands():
    assert is_command("/ahora") and is_command("  /temp-aire ayer")
    assert not is_command("¿cuál fue la temperatura de ayer?")


@pytest.mark.parametrize(
    "text, sensor, period",
    [
        ("/temp-aire ayer", "temperatura_ambiente", {"periodo": "ayer"}),
        ("/temp-ambiente semana", "temperatura_ambiente", {"periodo": "ultimos_7_dias"}),
        ("/ts setiembre", "temperatura_suelo", SEPT),
        ("/hum-aire hoy", "humedad_ambiente", {"periodo": "hoy"}),
        ("/hum-suelo mes", "humedad_suelo", {"periodo": "este_mes"}),
        ("/ph mes-pasado", "ph_suelo", {"periodo": "mes_anterior"}),
        ("/presion", "presion_atmosferica", {"periodo": "ultimos_7_dias"}),  # sin periodo: última semana
        ("/PH Setiembre", "ph_suelo", SEPT),  # mayúsculas
        ("/temp-suelo setimbre", "temperatura_suelo", SEPT),  # mes mal escrito
    ],
)
def test_sensor_commands(text, sensor, period):
    assert calls(text) == [("estadisticas_sensor", {"sensor": sensor, **period})]


def test_day_and_range_periods():
    assert calls("/ph 12/09") == [("estadisticas_sensor", {"sensor": "ph_suelo", "periodo": "rango",
                                                         "fecha_inicio": "2026-09-12", "fecha_fin": "2026-09-12"})]  # fmt: skip
    assert calls("/prom ph 10/09-18/09")[0][1] == {"sensor": "ph_suelo", "periodo": "rango",
                                                   "fecha_inicio": "2026-09-10", "fecha_fin": "2026-09-18"}  # fmt: skip


@pytest.mark.parametrize("text", ["/temp ayer", "/temperatura ayer", "/temperatrua ayer", "/humedad", "/max temp mes"])
def test_generic_temperature_or_humidity_asks_with_buttons(text):
    plan = plan_command(text, TODAY)
    assert plan.calls == [] and plan.quick_replies == QUICK_REPLIES
    assert "del aire (ambiente) o del suelo" in plan.answer
    assert plan.pending


@pytest.mark.parametrize(
    "reply, sensors",
    [("Suelo", ["temperatura_suelo"]), ("Aire (ambiente)", ["temperatura_ambiente"]),
     ("Ambas", ["temperatura_ambiente", "temperatura_suelo"])],
)  # fmt: skip
def test_button_reply_completes_the_pending_command(reply, sensors):
    pending = plan_command("/temp ayer", TODAY).pending
    resolved = resolve_command_reply(reply, pending)
    assert [(c[1]["sensor"], c[1]["periodo"]) for c in calls(resolved)] == [(s, "ayer") for s in sensors]
    assert resolve_command_reply("¿cuánto llovió ayer?", pending) is None


def test_metric_commands():
    assert calls("/max hum-aire setiembre") == [("estadisticas_sensor", {"sensor": "humedad_ambiente", **SEPT})]
    assert calls("/min temp suelo semana")[0][1]["sensor"] == "temperatura_suelo"
    assert "Indica el sensor" in plan_command("/max", TODAY).answer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("/ahora", [("lecturas_actuales", {})]),
        ("/hoy", [("diagnostico_palta", {"periodo": "hoy"})]),
        ("/ayer", [("diagnostico_palta", {"periodo": "ayer"})]),
        ("/semana", [("diagnostico_palta", {"periodo": "ultimos_7_dias"})]),
        ("/mes", [("diagnostico_palta", {"periodo": "este_mes"})]),
        ("/alertas", [("diagnostico_palta", {"periodo": "ultimos_7_dias"})]),
        ("/lecturas setiembre", [("conteo_lecturas", SEPT)]),
        ("/estado", [("lecturas_actuales", {}), ("conteo_lecturas", {"periodo": "ultimos_7_dias"}),
                     ("diagnostico_palta", {"periodo": "ultimos_7_dias"})]),
    ],
)  # fmt: skip
def test_summary_and_crop_commands(text, expected):
    assert calls(text) == expected


def test_no_command_uses_the_model():
    for text in ("/ahora", "/semana", "/diagnostico", "/alertas", "/estado", "/temp-aire ayer"):
        plan = plan_command(text, TODAY)
        assert plan.question is None and plan.render is not None, text


@pytest.mark.parametrize("text", ["/riego", "/regar hoy", "/consejo", "/fertilizar"])
def test_advice_commands_explain_there_are_no_recommendations(text):
    plan = plan_command(text, TODAY)
    assert plan.answer.startswith("AgriSense no da recomendaciones") and plan.calls == []


def test_unknown_command_suggests_similar():
    plan = plan_command("/temp-sulo ayer", TODAY)  # error de tipeo cercano: se corrige
    assert calls("/temp-sulo ayer") == [("estadisticas_sensor", {"sensor": "temperatura_suelo", "periodo": "ayer"})]
    plan = plan_command("/zzz", TODAY)
    assert plan.answer.startswith("No reconozco el comando /zzz.") and "/ayuda" in plan.answer


def test_station_without_a_sensor():
    plan = plan_command("/ph ayer", TODAY, available={"temperatura_ambiente"})
    assert plan.answer == "Esta estación no tiene sensor de pH del suelo." and plan.calls == []


# --- catálogo ------------------------------------------------------------------------


def test_catalog_lists_every_command_with_usage_example_and_insert_text():
    groups = catalog_for()
    commands = {c["command"]: c for g in groups for c in g["commands"]}
    assert {"/ahora", "/temp-aire", "/temp-suelo", "/hum-aire", "/hum-suelo", "/ph", "/presion", "/max",
            "/alertas", "/diagnostico", "/estado", "/lecturas", "/ayuda"} <= set(commands)  # fmt: skip
    assert "/riego" not in commands
    assert not any("recomend" in c["description"].lower() for c in commands.values())
    assert commands["/temp-aire"]["insert"] == "/temp-aire "  # lleva periodo: queda listo para completar
    assert commands["/ahora"]["insert"] == "/ahora"
    assert all(c["description"] and c["example"].startswith(c["command"]) for c in commands.values())


def test_catalog_hides_sensors_the_station_does_not_have():
    commands = {c["command"] for g in catalog_for({"temperatura_ambiente", "humedad_ambiente"}) for c in g["commands"]}
    assert "/temp-aire" in commands and "/temp-suelo" not in commands and "/ph" not in commands
    assert "/ahora" in commands  # los generales siempre aparecen


def test_help_text_lists_commands_and_periods():
    text = help_text()
    assert "/temp-suelo [periodo]" in text and "Periodos:" in text


# --- en el chat ---------------------------------------------------------------------


def make_service(llm, repo, memory=None):
    memory = memory or InMemoryConversationStore(max_turns=4, ttl_seconds=60, max_sessions=10)
    return ChatService(get_settings(), llm, repo, memory, clock=lambda: NOW)


async def test_command_answer_is_built_without_the_model(repo):
    llm = ScriptedLLM([])
    result = await make_service(llm, repo).ask("EST002-PALTAS", "/temp-aire ayer", "u", "s")
    assert llm.requests == []  # sin modelo
    assert result.answer.startswith("Temperatura ambiente · 24/09/2026\n• Promedio: 24.5 °C\n• Máximo: 28.0 °C")


async def test_command_clarification_then_button(repo):
    memory = InMemoryConversationStore(max_turns=4, ttl_seconds=60, max_sessions=10)
    service = make_service(ScriptedLLM([]), repo, memory)
    first = await service.ask("EST002-PALTAS", "/temp ayer", "u", "s")
    assert first.quick_replies == QUICK_REPLIES and first.tools == []
    second = await service.ask("EST002-PALTAS", "Suelo", "u", "s")
    assert [(t.arguments["sensor"], t.arguments["periodo"]) for t in second.tools] == [("temperatura_suelo", "ayer")]
    assert second.answer.startswith("Temperatura del suelo")
    assert memory.get_context("u:EST002-PALTAS:s").pending_question is None


async def test_follow_up_in_natural_language_after_a_command(repo):
    llm = ScriptedLLM([LLMChunk(text="La temperatura del suelo mínima fue 21.0 °C.")])
    service = make_service(llm, repo)
    await service.ask("EST002-PALTAS", "/temp-suelo ayer", "u", "s")
    result = await service.ask("EST002-PALTAS", "¿y el mínimo?", "u", "s")
    assert result.tools[0].arguments["sensor"] == "temperatura_suelo"


async def test_diagnostico_is_built_without_the_model(repo):
    llm = ScriptedLLM([])
    result = await make_service(llm, repo).ask("EST002-PALTAS", "/diagnostico", "u", "s")
    assert [t.name for t in result.tools] == ["diagnostico_palta"] and llm.requests == []
    assert result.answer.startswith("Resumen de ESTACIÓN 2")


async def test_natural_language_clarification_also_offers_buttons(repo):
    result = await make_service(ScriptedLLM([]), repo).ask("EST002-PALTAS", "cual fue la temperatura de ayer", "u", "s")
    assert result.quick_replies == QUICK_REPLIES


async def test_commands_catalog_for_station(repo):
    repo.sensor_codes = {"ambient_temperature"}
    catalog = await make_service(ScriptedLLM([]), repo).commands_for("EST002-PALTAS")
    commands = {c["command"] for g in catalog["groups"] for c in g["commands"]}
    assert "/temp-aire" in commands and "/temp-suelo" not in commands
    assert catalog["periods"].startswith("Periodos:")
