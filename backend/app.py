import os
from flask import Flask, request
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain.tools import BaseTool
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from typing import Type
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent


## ─── Credenciales ────────────────────────────────────────────────────────────
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "TU_LANGCHAIN_API_KEY"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "orientagov-agent"
os.environ["OPENAI_API_KEY"] = "TU_OPENAI_API_KEY"

ES_URL      = "http://TU_IP_ES:9200"
ES_USER     = "elastic"
ES_PASSWORD = "TU_ES_PASSWORD"
ES_INDEX    = "rag_tupa_lc"

DB_URI = os.environ.get(
    "DB_URI",
    "postgresql://postgres:TU_PASSWORD_DB@TU_IP_DB:5432/postgres?sslmode=disable"
)

## ─── HERRAMIENTA 1: Identificar entidad ─────────────────────────────────────
 
class IdentificarEntidadInput(BaseModel):
    consulta: str = Field(
        description="Consulta o situación del usuario para identificar qué entidad del Estado corresponde"
    )
 
class IdentificarEntidadTool(BaseTool):
    name: str = "identificar_entidad"
    description: str = (
        "Identifica qué entidad del Estado peruano (SBS, SUNAT o SUNARP) "
        "es la responsable del trámite según la consulta del usuario. "
        "Úsala cuando el usuario no mencione una entidad específica."
    )
    args_schema: Type[BaseModel] = IdentificarEntidadInput
 
    def _run(self, consulta: str) -> str:
        entidades = {
            "SBS": [
                "seguro", "AFP", "banco", "financiera", "pensión", "fondo de pensiones",
                "caja municipal", "cooperativa de ahorro", "empresa de seguros",
                "superintendencia de banca", "agencia bancaria", "microfinanciera"
            ],
            "SUNAT": [
                "impuesto", "RUC", "tributo", "factura", "boleta", "declaración",
                "renta", "IGV", "aduana", "exportación", "importación",
                "contribuyente", "ficha ruc", "deuda tributaria"
            ],
            "SUNARP": [
                "registro", "propiedad", "inmueble", "terreno", "escritura",
                "hipoteca", "empresa", "sociedad", "constitución de empresa",
                "partida registral", "notarial", "persona jurídica", "acto inscribible"
            ]
        }
 
        consulta_lower = consulta.lower()
        puntajes = {}
        for entidad, palabras_clave in entidades.items():
            puntajes[entidad] = sum(1 for palabra in palabras_clave if palabra in consulta_lower)
 
        mejor = max(puntajes, key=puntajes.get)
 
        if puntajes[mejor] == 0:
            return (
                "No pude identificar la entidad con certeza. "
                "Las entidades disponibles son:\n"
                "- SBS: trámites bancarios, seguros y AFP\n"
                "- SUNAT: trámites tributarios y aduaneros\n"
                "- SUNARP: registro de propiedades y empresas\n"
                "¿Puedes dar más detalles sobre tu trámite?"
            )
 
        return (
            f"Según tu consulta, la entidad correspondiente es: {mejor}\n\n"
            f"- SBS (bancario/seguros/AFP): {puntajes['SBS']} coincidencias\n"
            f"- SUNAT (tributario/aduanero): {puntajes['SUNAT']} coincidencias\n"
            f"- SUNARP (registros/propiedades): {puntajes['SUNARP']} coincidencias\n\n"
            f"Procede a buscar el trámite específico en {mejor}."
        )
 
    async def _arun(self, consulta: str) -> str:
        raise NotImplementedError("Usar _run en su lugar")
 
 
## ─── HERRAMIENTA 2: Buscar trámite ──────────────────────────────────────────
 
class BuscarTramiteInput(BaseModel):
    nombre_tramite: str = Field(
        description="Descripción completa del trámite incluyendo la entidad. Ejemplo: 'inscripción SAC SUNARP', 'obtener RUC SUNAT', 'cierre oficina seguros SBS'"
    )
 
class BuscarTramiteTool(BaseTool):
    name: str = "buscar_tramite"
    description: str = (
        "Busca en los documentos TUPA oficiales el procedimiento administrativo "
        "adecuado según la situación del usuario. Cubre trámites de SBS, SUNAT y SUNARP. "
        "IMPORTANTE: siempre incluye la entidad en el parámetro nombre_tramite."
    )
    args_schema: Type[BaseModel] = BuscarTramiteInput
 
    def _run(self, nombre_tramite: str) -> str:
        try:
            nombre_lower = nombre_tramite.lower()
            entidad_filtro = None
 
            if any(p in nombre_lower for p in ["sbs", "seguro", "banco", "financiera", "afp", "pension"]):
                entidad_filtro = "SBS"
            elif any(p in nombre_lower for p in ["sunat", "impuesto", "ruc", "tributo", "igv", "renta", "aduana"]):
                entidad_filtro = "SUNAT"
            elif any(p in nombre_lower for p in ["sunarp", "registro", "propiedad", "inmueble", "sociedad"]):
                entidad_filtro = "SUNARP"
 
            vector_store = _get_vector_store()
 
            if entidad_filtro:
                docs = vector_store.similarity_search(
                    nombre_tramite,
                    k=10,
                    filter=[{"term": {"metadata.entidad.keyword": entidad_filtro}}]
                )
            else:
                docs = vector_store.similarity_search(nombre_tramite, k=10)
 
            if not docs:
                return "No encontré información sobre ese trámite en los documentos TUPA."
 
            resultado = ""
            for doc in docs:
                entidad = doc.metadata.get("entidad", "Entidad desconocida")
                resultado += f"\n[{entidad}]\n{doc.page_content}\n---"
            return resultado
 
        except Exception as e:
            return f"Error en búsqueda: {str(e)}"
 
    async def _arun(self, nombre_tramite: str) -> str:
        raise NotImplementedError("Usar _run en su lugar")
 
 
## ─── HERRAMIENTA 3: Resumir trámite ─────────────────────────────────────────
 
class ResumirTramiteInput(BaseModel):
    nombre_tramite: str = Field(
        description="Nombre completo del trámite incluyendo la entidad. Ejemplo: 'inscripción SAC SUNARP', 'RUC SUNAT'"
    )
 
class ResumirTramiteTool(BaseTool):
    name: str = "resumir_tramite"
    description: str = (
        "Genera un resumen estructurado de un trámite del TUPA "
        "con requisitos, plazo y costo. "
        "IMPORTANTE: siempre incluye la entidad en el parámetro nombre_tramite."
    )
    args_schema: Type[BaseModel] = ResumirTramiteInput
 
    def _run(self, nombre_tramite: str) -> str:
        try:
            nombre_lower = nombre_tramite.lower()
            entidad_filtro = None
 
            if any(p in nombre_lower for p in ["sbs", "seguro", "banco", "financiera", "afp", "pension"]):
                entidad_filtro = "SBS"
            elif any(p in nombre_lower for p in ["sunat", "impuesto", "ruc", "tributo", "igv", "renta", "aduana"]):
                entidad_filtro = "SUNAT"
            elif any(p in nombre_lower for p in ["sunarp", "registro", "propiedad", "inmueble", "sociedad"]):
                entidad_filtro = "SUNARP"
 
            vector_store = _get_vector_store()
 
            if entidad_filtro:
                docs = vector_store.similarity_search(
                    nombre_tramite,
                    k=10,
                    filter=[{"term": {"metadata.entidad.keyword": entidad_filtro}}]
                )
            else:
                docs = vector_store.similarity_search(nombre_tramite, k=10)
 
            if not docs:
                return "No encontré información sobre ese trámite en los documentos TUPA."
 
            contexto = "\n---\n".join([doc.page_content for doc in docs])
            entidades = list(set(d.metadata.get("entidad", "?") for d in docs))
            return (
                f"Entidad(es) encontrada(s): {', '.join(entidades)}\n\n"
                f"Contexto del trámite '{nombre_tramite}':\n\n{contexto}\n\n"
                f"INSTRUCCIÓN IMPORTANTE: Resume ÚNICAMENTE con la información del contexto anterior. "
                f"NO uses conocimiento externo ni supongas datos. "
                f"Si el contexto dice 'Gratuito', escribe 'Gratuito'. "
                f"Si el contexto dice '15 días calendarios', escribe exactamente eso. "
                f"Si algún dato no aparece en el contexto, di 'No especificado en el documento'."
            )
 
        except Exception as e:
            return f"Error en resumen: {str(e)}"
 
    async def _arun(self, nombre_tramite: str) -> str:
        raise NotImplementedError("Usar _run en su lugar")
 
 
## ─── HERRAMIENTA 4: Explicar tipos de empresa ───────────────────────────────
 
class ExplicarTiposEmpresaInput(BaseModel):
    consulta: str = Field(
        description="Consulta del usuario sobre tipos de empresa para inscribir en SUNARP"
    )
 
class ExplicarTiposEmpresaTool(BaseTool):
    name: str = "explicar_tipos_empresa"
    description: str = (
        "Explica los diferentes tipos de empresa que se pueden inscribir en SUNARP "
        "para ayudar al usuario a decidir cuál es la más adecuada para su situación. "
        "Úsala cuando el usuario quiera inscribir una empresa pero no sepa qué tipo elegir."
    )
    args_schema: Type[BaseModel] = ExplicarTiposEmpresaInput
 
    def _run(self, consulta: str) -> str:
        return """
Los principales tipos de empresa que puedes inscribir en SUNARP son:
 
1. **SAC - Sociedad Anónima Cerrada**
   - Ideal para: pequeñas y medianas empresas, negocios familiares o entre socios conocidos.
   - Socios: mínimo 2, máximo 20.
   - Las acciones NO se pueden vender libremente sin aprobación de los socios.
   - Es el tipo más común para emprendedores en Perú.
 
2. **SA - Sociedad Anónima**
   - Ideal para: empresas grandes que buscan crecer o atraer inversión.
   - Socios: mínimo 2, sin límite máximo.
   - Las acciones SÍ se pueden transferir libremente.
   - Puede cotizar en bolsa de valores.
 
3. **SRL - Sociedad de Responsabilidad Limitada**
   - Ideal para: negocios pequeños entre pocos socios de confianza.
   - Socios: mínimo 2, máximo 20.
   - No tiene acciones sino "participaciones".
   - Estructura más simple que la SAC.
 
4. **EIRL - Empresa Individual de Responsabilidad Limitada**
   - Ideal para: emprendedores que quieren trabajar solos con responsabilidad limitada.
   - Titular: solo 1 persona natural.
   - El patrimonio personal está separado del patrimonio de la empresa.
 
5. **Asociación**
   - Ideal para: organizaciones sin fines de lucro, clubes, ONG.
   - No reparte utilidades entre sus miembros.
 
6. **Cooperativa**
   - Ideal para: grupos de personas con un objetivo económico común.
   - Funciona bajo principios de solidaridad y ayuda mutua.
 
¿Cuál de estos tipos se adapta mejor a lo que necesitas?
"""
 
    async def _arun(self, consulta: str) -> str:
        raise NotImplementedError("Usar _run en su lugar")
 
 
## ─── Helper vector store ─────────────────────────────────────────────────────
 
def _get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return ElasticsearchStore(
        es_url=ES_URL,
        es_user=ES_USER,
        es_password=ES_PASSWORD,
        index_name=ES_INDEX,
        embedding=embeddings
    )
 
 
## ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(__name__)
 
@app.route('/agent', methods=['GET'])
def main():
    id_usuario = request.args.get('idagente')
    msg = request.args.get('msg')
 
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = ElasticsearchStore(
        es_url=ES_URL,
        es_user=ES_USER,
        es_password=ES_PASSWORD,
        index_name=ES_INDEX,
        embedding=embeddings
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 15})
 
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
 
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",
             """
             Eres OrientaGov, un asistente inteligente especializado en trámites
             administrativos del Estado peruano.
 
             Puedes ayudar con trámites de:
             - SBS: bancarios, seguros y AFP
             - SUNAT: tributarios y aduaneros
             - SUNARP: registro de propiedades y empresas
 
             Herramientas disponibles:
             - identificar_entidad: úsala cuando el usuario NO mencione una entidad específica.
             - buscar_tramite: busca el procedimiento en los documentos TUPA oficiales.
             - resumir_tramite: genera un resumen con requisitos, plazo y costo.
             - explicar_tipos_empresa: explica los tipos de empresa para inscribir en SUNARP.
 
             Instrucciones:
             - Si el usuario NO menciona entidad → usa identificar_entidad primero.
             - Si el usuario SÍ menciona entidad → ve directo a buscar_tramite.
             - Si el usuario pide detalles o resumen → usa resumir_tramite.
             - Indica siempre de qué entidad proviene la información.
             - Responde ÚNICAMENTE con información de los documentos recuperados.
             - NO uses conocimiento externo ni inventes datos.
             - Si un dato no está en el documento, di "No especificado en el documento".
             - Si el documento indica aprobación automática (X), el plazo es "Aprobación automática".
             - Si un plazo no aparece en el contexto, di "Aprobación automática o no especificado".
             - Sé claro, preciso y profesional.
             - Responde siempre en español.
 
             Instrucciones para búsquedas:
             - Cuando uses buscar_tramite o resumir_tramite, SIEMPRE incluye la entidad
               identificada en la consulta. Por ejemplo: si el usuario dijo "SAC" pero
               previamente identificamos SUNARP, busca "inscripción SAC SUNARP".
               Si dice "quiero mi RUC", busca "inscripción RUC SUNAT".
               Nunca busques solo con lo que dijo el usuario en el último mensaje.
 
             Instrucciones para trámites que requieren más detalle:
             - Si el usuario quiere inscribir una empresa en SUNARP pero NO especifica
               el tipo → usa explicar_tipos_empresa primero para orientarlo.
             - Solo usa buscar_tramite cuando el usuario ya haya indicado el tipo de empresa.
             - Si el usuario quiere hacer un trámite tributario en SUNAT y no especifica
               el tipo de contribuyente (persona natural o jurídica), pregúntale antes de buscar.
             """),
            ("human", "{messages}"),
        ]
    )
 
    with ConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs,
    ) as pool:
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
 
        config = {"configurable": {"thread_id": id_usuario}}
 
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
 
        toolkit = [
            IdentificarEntidadTool(),
            ExplicarTiposEmpresaTool(),
            BuscarTramiteTool(),
            ResumirTramiteTool()
        ]
 
        agent_executor = create_react_agent(model, toolkit, checkpointer=checkpointer, prompt=prompt)
 
        response = agent_executor.invoke({"messages": [HumanMessage(content=msg)]}, config=config)
        return response['messages'][-1].content
 
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)