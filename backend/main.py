import os
import time
import uuid
import logging
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


# ── Configuración por variables de entorno ──────────────────────
# En Kubernetes, estas se inyectan vía ConfigMap (no se necesita .env)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
LOG_LEVEL = os.getenv("LOG_LEVEL", "debug").upper()


# ── Logging estructurado a stdout (compatible con K8s) ──────────
# En contenedores, SIEMPRE se loguea a stdout/stderr.
# Promtail/Fluentd los recolecta automáticamente desde ahí.
# Escribir a archivos es un antipatrón en Kubernetes porque el
# filesystem del contenedor es efímero.

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    if logger.hasHandlers():
        logger.handlers.clear()
    handler = logging.StreamHandler()  # siempre stdout
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger

logger_tecnico = setup_logger("tecnico")
logger_auditoria = setup_logger("auditoria")


# ── Aplicación con prefijo /api ─────────────────────────────────
# El prefijo es necesario para que el Ingress de Kubernetes enrute:
#   / → frontend
#   /api → backend
app = FastAPI(
    title="API REST Calculadora",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS configurado por ambiente ───────────────────────────────
if ENVIRONMENT == "dev":
    origins = ["*"]
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS if o.strip() != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelo de datos ─────────────────────────────────────────────
class Operacion(BaseModel):
    a: float
    b: float


# ── Funciones auxiliares de logging ─────────────────────────────
def generar_log_tecnico(
    request_id: str, method: str, path: str,
    status_code: int, latency: float,
    message: str = "OK", level: str = "INFO",
):
    log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": "calculadora-api",
        "environment": ENVIRONMENT,
        "request_id": request_id,
        "method": method,
        "path": path,
        "status": status_code,
        "latency_ms": round(latency * 1000, 2),
        "message": message,
    }
    if level == "ERROR":
        logger_tecnico.error(json.dumps(log))
    else:
        logger_tecnico.info(json.dumps(log))


def generar_log_auditoria(
    request_id: str, action: str, actor_id: str,
    entity: str, entity_id: str, changes: dict,
):
    log = {
        "table": "audit_events",
        "action": action,
        "actor_id": actor_id,
        "entity": entity,
        "entity_id": entity_id,
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
    }
    logger_auditoria.info(json.dumps(log))


def get_actor_id(request: Request) -> str:
    """Extrae el actor del header X-User-ID o usa 'anonymous'."""
    return request.headers.get("X-User-ID", "anonymous")


# ── Health check (requerido por etapas 1, 10, 11, 13) ──────────
@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """
    Endpoint de salud. Kubernetes lo usa como liveness y readiness probe.
    Accesible como /api/health desde el Ingress.
    """
    return {"status": "ok", "environment": ENVIRONMENT}


# ── GET endpoints ───────────────────────────────────────────────
@app.get("/sumar", status_code=status.HTTP_200_OK)
def sumar(a: float, b: float, request: Request):
    """Suma dos números. Ejemplo: /api/sumar?a=2&b=3"""
    start = time.time()
    rid = str(uuid.uuid4())
    resultado = a + b
    latency = time.time() - start

    generar_log_tecnico(rid, "GET", "/sumar", 200, latency)
    generar_log_auditoria(
        rid, "CALCULAR_SUMA", get_actor_id(request),
        "Operacion", rid, {"a": a, "b": b, "res": resultado},
    )
    return {"resultado": resultado}


@app.get("/restar", status_code=status.HTTP_200_OK)
def restar(a: float, b: float, request: Request):
    """Resta dos números. Ejemplo: /api/restar?a=10&b=4"""
    start = time.time()
    rid = str(uuid.uuid4())
    resultado = a - b
    latency = time.time() - start

    generar_log_tecnico(rid, "GET", "/restar", 200, latency)
    generar_log_auditoria(
        rid, "CALCULAR_RESTA", get_actor_id(request),
        "Operacion", rid, {"a": a, "b": b, "res": resultado},
    )
    return {"resultado": resultado}


# ── POST endpoints ──────────────────────────────────────────────
@app.post("/multiplicar", status_code=status.HTTP_201_CREATED)
def multiplicar(datos: Operacion, request: Request):
    """Multiplica dos números enviados en el cuerpo JSON."""
    start = time.time()
    rid = str(uuid.uuid4())
    resultado = datos.a * datos.b
    latency = time.time() - start

    generar_log_tecnico(rid, "POST", "/multiplicar", 201, latency)
    generar_log_auditoria(
        rid, "CALCULAR_MULT", get_actor_id(request),
        "Operacion", rid, {"a": datos.a, "b": datos.b, "res": resultado},
    )
    return {"resultado": resultado}


@app.post("/dividir", status_code=status.HTTP_200_OK)
def dividir(datos: Operacion, request: Request):
    """Divide dos números, validando la división entre cero."""
    start = time.time()
    rid = str(uuid.uuid4())

    if datos.b == 0:
        latency = time.time() - start
        generar_log_tecnico(
            rid, "POST", "/dividir", 400, latency,
            "Intento de division por cero", level="ERROR",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede dividir entre cero",
        )

    resultado = datos.a / datos.b
    latency = time.time() - start

    generar_log_tecnico(rid, "POST", "/dividir", 200, latency)
    generar_log_auditoria(
        rid, "CALCULAR_DIV", get_actor_id(request),
        "Operacion", rid, {"a": datos.a, "b": datos.b, "res": resultado},
    )
    return {"resultado": resultado}
