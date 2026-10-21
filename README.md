<div align="center">

# 🥑 Backend Services API - Proyecto Paltas

**API para el monitoreo y diagnóstico de cultivos de palta Hass**

Usuarios · Estaciones agrometeorológicas IoT · Asistente IA por estación

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Desarrollado por el **equipo de [INICTEL-UNI](https://github.com/pdsiia-inictel-uni)**

</div>

---

## ✨ Funcionalidades

- 👤 **Cuentas de usuario**: registro con DNI, verificación por correo, login con JWT,
  recuperación de contraseña y protección contra fuerza bruta.
- 📡 **Estaciones IoT**: recepción de mediciones firmadas (HMAC-SHA256) de 6 sensores y batería,
  historial por sensor y transmisión en tiempo real (SSE).
- 🤖 **Asistente IA**: chat por estación que responde con los datos reales de la estación y
  alertas para la palta Hass (modelo local con Ollama, sin servicios de pago).

App móvil: [appalta2](https://github.com/pdsiia-inictel-uni/appalta2) (Android).

## 🧱 Tecnologías

FastAPI · SQLAlchemy · PostgreSQL · Pydantic · JWT + bcrypt · Jinja2 · SSE · Ollama · Docker

## 🚀 Inicio rápido

**Windows (desarrollo local)**

```powershell
git clone https://github.com/pdsiia-inictel-uni/appalta2-backend.git
cd appalta2-backend
.\run.ps1          # crea venv y .env, crea/migra la BD (PostgreSQL local) y levanta la API
```

Completa `.env` (marcado `REEMPLAZAR_…`), vuelve a ejecutar `.\run.ps1` y abre
http://localhost:8000/docs.

**Docker (producción)**

```bash
cp .env.example .env.production     # completar los valores [PROD]
docker compose --env-file .env.production up -d --build   # API + Ollama; migra la BD al arrancar
```

Guía completa, diagramas y checklist: **[DEPLOY.md](DEPLOY.md)** ·
Servicios internos y externos: **[SERVICES.md](SERVICES.md)**.

## ⚙️ Configuración

| Archivo | Uso |
|---|---|
| `.env.example` | Plantilla documentada (en git) |
| `.env` | Desarrollo local |
| `.env.production` | Servidor |

```bash
python -m scripts.check_env .env              # valida sin mostrar secretos
python -m scripts.check_env .env --connect    # además prueba PostgreSQL y SMTP
```

## 📁 Estructura

```
app/
├── main.py          # app FastAPI y routers (/api/v1)
├── config/          # environment.py (variables validadas) · constants.py
├── routes/          # endpoints: usuarios, estaciones, mediciones
├── services/        # auth, correo, firma HMAC, SSE, límite de intentos
├── database/        # consultas SQLAlchemy
├── models/ schemas/ # tablas ORM y modelos de entrada/salida
├── templates/       # páginas web y correos
└── assistant/       # asistente IA (ver app/assistant/README.md)
sql/                 # migraciones (se aplican con scripts/setup_db.py)
scripts/             # setup_db (migraciones), check_env, evaluación del asistente
tests/               # pytest (sin BD ni modelo)
Dockerfile           # imagen de producción (dos etapas, usuario sin privilegios)
docker-compose.yml   # producción: backend + Ollama
```

## 🧪 Tests

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest
```

## 👥 Equipo

Desarrollado por el **equipo de [INICTEL-UNI](https://github.com/pdsiia-inictel-uni)** — Instituto
Nacional de Investigación y Capacitación de Telecomunicaciones, Universidad Nacional de Ingeniería.

## 📄 Licencia

Distribuido bajo la licencia [MIT](LICENSE).
