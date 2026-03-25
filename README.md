# 🇵🇪 OrientaGov — Asistente de Trámites del Estado Peruano

OrientaGov es un asistente virtual inteligente que ayuda a los ciudadanos peruanos a consultar trámites administrativos del Estado de forma rápida y conversacional, en base a documentos oficiales de entidades como la **SBS**, **SUNAT** y **SUNARP**, respondiendo preguntas sobre requisitos, plazos y costos.

> 🎓 Demo desarrollado para el curso de IA Generativa — Universidad Ricardo Palma 2026

---

## 🏗️ Arquitectura

```
Usuario
  │
  ▼
Frontend (Next.js) ──► API Route /api/agent
  │
  ▼
Backend (Flask + LangGraph) ──► Agente ReAct
  │                                    │
  ▼                                    ▼
PostgreSQL                    Herramientas:
(Memoria conversacional)      - identificar_entidad
                              - buscar_tramite (RAG)
                              - resumir_tramite (RAG)
                              - explicar_tipos_empresa
                                    │
                                    ▼
                            Elasticsearch
                            (Vector Store)
                            índice: rag_tupa_lc
                                    │
                                    ▼
                            OpenAI Embeddings
                            text-embedding-3-small
```

### Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, NextAuth |
| Backend | Python, Flask, LangChain, LangGraph |
| Agente | LangGraph ReAct Agent, GPT-4o-mini |
| RAG | LangChain + ElasticsearchStore + OpenAI Embeddings |
| Vector Store | Elasticsearch |
| Memoria | PostgreSQL + LangGraph PostgresSaver |
| Autenticación | Google OAuth (NextAuth.js) |
| Despliegue | Google Cloud Run (backend y frontend) / Vercel (frontend) |

---

## 📁 Estructura del repositorio

```
orientagov/
├── backend/
│   ├── app.py              # API Flask con agente LangGraph
│   ├── requirements.txt    # Dependencias Python
│   └── Dockerfile          # Imagen para Cloud Run
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx          # Interfaz de chat
│   │       ├── layout.tsx        # Layout con header/footer
│   │       ├── globals.css       # Estilos globales
│   │       ├── AuthProvider.tsx  # Proveedor de sesión
│   │       └── api/
│   │           ├── agent/
│   │           │   └── route.ts  # Proxy al backend
│   │           └── auth/
│   │               └── route.ts  # NextAuth handler
│   ├── public/
│   │   └── logos/          # Logos de SBS, SUNAT, SUNARP
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.ts
├── notebook/
│   └── indexacion_tupa.py  # Script de indexación de documentos
└── README.md
```

---

## ⚙️ Instalación y configuración

### Requisitos previos

- Python 3.10+
- Node.js 20+
- Cuenta de Google Cloud Platform
- Cuenta de OpenAI (API Key)
- Elasticsearch desplegado (VM en GCP)
- PostgreSQL desplegado (VM en GCP)

### Variables de entorno

#### Backend (`backend/app.py`)
```python
OPENAI_API_KEY      = "sk-..."           # API Key de OpenAI
LANGCHAIN_API_KEY   = "lsv2_..."         # API Key de LangSmith (trazabilidad)
ES_URL              = "http://IP:9200"   # URL de Elasticsearch
ES_USER             = "elastic"
ES_PASSWORD         = "..."              # Password de Elasticsearch
ES_INDEX            = "rag_tupa_lc"      # Nombre del índice
DB_URI              = "postgresql://postgres:PASSWORD@IP:5432/postgres?sslmode=disable"
```

#### Frontend (Vercel o Cloud Run)
```
GOOGLE_CLIENT_ID        = "..."    # Client ID de Google OAuth
GOOGLE_CLIENT_SECRET    = "..."    # Client Secret de Google OAuth
NEXTAUTH_SECRET         = "..."    # Secret para NextAuth
NEXTAUTH_URL            = "https://tu-dominio.vercel.app"
```

---

## 📊 Indexación de documentos

Antes de correr el backend, debes indexar los documentos TUPA en Elasticsearch usando el notebook de Google Colab.

### Documentos requeridos
- **SBS**: PDFs individuales por procedimiento (carpeta `/TUPA/SBS/`)
- **SUNAT**: Archivos Excel `.xls` por procedimiento (carpeta `/TUPA/SUNAT/`)
- **SUNARP**: Un solo PDF con todas las tablas (carpeta `/TUPA/SUNARP/`)

### Pasos de indexación
1. Abre `notebook/indexacion_tupa.py` en Google Colab
2. Instala las dependencias:
```bash
pip install langchain langchain-openai langchain-elasticsearch langchain-community langchain-text-splitters pdfplumber pypdf openpyxl xlrd elasticsearch
```
3. Configura las credenciales (OpenAI y Elasticsearch)
4. Ajusta las rutas de los documentos
5. Ejecuta todas las celdas — el índice `rag_tupa_lc` se creará en Elasticsearch

---

## 🚀 Despliegue

### Backend en Google Cloud Run

```bash
cd backend

# Build de la imagen
gcloud builds submit --tag gcr.io/TU_PROYECTO/agentupa:v1

# Deploy
gcloud run deploy apicloudia \
  --image gcr.io/TU_PROYECTO/agentupa:v1 \
  --platform managed \
  --region us-west4 \
  --allow-unauthenticated \
  --memory 2Gi
```

### Frontend en Vercel

1. Sube el repositorio a GitHub
2. Ve a [vercel.com](https://vercel.com) → New Project
3. Selecciona el repositorio y la carpeta `frontend/`
4. Agrega las variables de entorno
5. Clic en Deploy

### Frontend en Google Cloud Run (alternativo)

```bash
cd frontend

# Build
gcloud builds submit --tag gcr.io/TU_PROYECTO/apicloudiafr:v1

# Deploy
gcloud run deploy apicloudiafr \
  --image gcr.io/TU_PROYECTO/apicloudiafr:v1 \
  --platform managed \
  --region us-west4 \
  --allow-unauthenticated \
  --port 8080

# Variables de entorno
gcloud run services update apicloudiafr \
  --region us-west4 \
  --update-env-vars="GOOGLE_CLIENT_ID=...,GOOGLE_CLIENT_SECRET=...,NEXTAUTH_SECRET=..."

gcloud run services update apicloudiafr \
  --region us-west4 \
  --update-env-vars="NEXTAUTH_URL=https://tu-url.run.app"
```

---

## 🧪 Cómo probar

### Probar el backend directamente
```bash
# Prueba básica
curl "https://TU_BACKEND_URL/agent?idagente=test_001&msg=Hola"

# Prueba SBS
curl "https://TU_BACKEND_URL/agent?idagente=test_002&msg=quiero+cerrar+una+oficina+de+seguros+ante+la+SBS"

# Prueba SUNAT
curl "https://TU_BACKEND_URL/agent?idagente=test_003&msg=como+obtengo+mi+RUC+en+SUNAT"

# Prueba SUNARP
curl "https://TU_BACKEND_URL/agent?idagente=test_004&msg=quiero+inscribir+una+empresa+en+SUNARP"
```

### Probar el frontend
1. Abre la URL del frontend en el navegador
2. Inicia sesión con Google
3. Escribe una consulta en el chat
4. Verifica que el agente responde correctamente

### Casos de prueba recomendados

| Consulta | Comportamiento esperado |
|---|---|
| "Hola" | Mensaje de bienvenida + pregunta en qué puede ayudar |
| "quiero hacer un trámite sobre impuestos" | Identifica SUNAT automáticamente |
| "quiero inscribir una empresa" | Pregunta el tipo de empresa (SAC, SA, SRL, EIRL...) |
| "cerrar oficina de seguros SBS" | Muestra requisitos, plazo (15 días calendarios) y costo (Gratuito) |
| "obtener RUC SUNAT" | Muestra requisitos y costo (Gratuito) |

---

## 🤖 Herramientas del agente

| Herramienta | Descripción |
|---|---|
| `identificar_entidad` | Detecta si el trámite corresponde a SBS, SUNAT o SUNARP usando palabras clave |
| `buscar_tramite` | Búsqueda semántica RAG en Elasticsearch para encontrar el procedimiento TUPA |
| `resumir_tramite` | Genera resumen estructurado con requisitos, plazo y costo del trámite |
| `explicar_tipos_empresa` | Explica los tipos de empresa inscribibles en SUNARP (SAC, SA, SRL, EIRL, etc.) |

---

## 👩‍💻 Autora

Desarrollado por **Kimberley Ojeda**  
Curso de IA Generativa — Universidad Ricardo Palma 2026
