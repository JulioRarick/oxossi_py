import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import shutil
from typing import Optional
import logging

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.dates import extract_and_analyze_dates, _load_date_config
    from oxossi.extractors.names import extract_potential_names
    from oxossi.extractors.places import search_colonial_places, load_place_captaincy_data
    from oxossi.extractors.themes import analyze_text_themes
    from oxossi.extractors.references import extract_references_with_anystyle
    from oxossi.utils.pdf_utils import extract_text_from_pdf
    from oxossi.utils.data_utils import load_names_config, load_themes_config
except ImportError as e:
    logging.error(f"Erro ao importar módulos do Oxossi: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Oxossi API",
    description="API para análise de documentos históricos coloniais brasileiros",
    version="1.0.0"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_DIR = project_root / "data"
DATE_CONFIG_PATH = CONFIG_DIR / "date_config.json"
NAMES_CONFIG_PATH = CONFIG_DIR / "names.json"
THEMES_CONFIG_PATH = CONFIG_DIR / "themes.json"
PLACES_CONFIG_PATH = CONFIG_DIR / "places.txt"

date_config = None
names_config = None
themes_config = None
places_config = None

@app.on_event("startup")
async def startup_event():
    """Carrega as configurações na inicialização do servidor."""
    global date_config, names_config, themes_config, places_config
    
    try:
        if DATE_CONFIG_PATH.exists():
            date_config = _load_date_config(str(DATE_CONFIG_PATH))
            logger.info("Configuração de datas carregada com sucesso")
        else:
            logger.warning(f"Arquivo de configuração de datas não encontrado: {DATE_CONFIG_PATH}")
        
        if NAMES_CONFIG_PATH.exists():
            first_names, second_names, prepositions = load_names_config(str(NAMES_CONFIG_PATH))
            names_config = {
                "first_names": first_names,
                "second_names": second_names,
                "prepositions": prepositions
            }
            logger.info("Configuração de nomes carregada com sucesso")
        else:
            logger.warning(f"Arquivo de configuração de nomes não encontrado: {NAMES_CONFIG_PATH}")
        
        if THEMES_CONFIG_PATH.exists():
            themes_config = load_themes_config(str(THEMES_CONFIG_PATH))
            logger.info("Configuração de temas carregada com sucesso")
        else:
            logger.warning(f"Arquivo de configuração de temas não encontrado: {THEMES_CONFIG_PATH}")
        
        if PLACES_CONFIG_PATH.exists():
            places_config = load_place_captaincy_data(str(PLACES_CONFIG_PATH))
            logger.info("Configuração de lugares carregada com sucesso")
        else:
            logger.warning(f"Arquivo de configuração de lugares não encontrado: {PLACES_CONFIG_PATH}")
            
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")

@app.get("/")
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "Oxossi API - Análise de Documentos Históricos Coloniais",
        "version": "1.0.0",
        "endpoints": {
            "extract_dates": "/extract/dates",
            "extract_names": "/extract/names", 
            "extract_places": "/extract/places",
            "extract_themes": "/extract/themes",
            "extract_references": "/extract/references",
            "extract_all": "/extract/all"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint para verificação de saúde da API."""
    config_status = {
        "date_config": date_config is not None,
        "names_config": names_config is not None,
        "themes_config": themes_config is not None,
        "places_config": places_config is not None
    }
    
    return {
        "status": "healthy",
        "configurations_loaded": config_status
    }

async def process_uploaded_file(file: UploadFile) -> str:
    """Processa arquivo enviado e extrai texto."""
    if not file.filename.lower().endswith(('.pdf', '.txt')):
        raise HTTPException(
            status_code=400, 
            detail="Formato de arquivo não suportado. Use PDF ou TXT."
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        if file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(tmp_path)
            if not text:
                raise HTTPException(
                    status_code=400,
                    detail="Falha ao extrair texto do PDF"
                )
        else:  # .txt
            with open(tmp_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        return text
    
    finally:
        # Remove arquivo temporário
        os.unlink(tmp_path)

@app.post("/extract/dates")
async def extract_dates(file: UploadFile = File(...)):
    """Extrai e analisa datas do documento."""
    if not date_config:
        raise HTTPException(
            status_code=500,
            detail="Configuração de datas não carregada"
        )
    
    try:
        text = await process_uploaded_file(file)
        results = extract_and_analyze_dates(text, date_config)
        
        return {
            "status": "success",
            "message": f"{results.get('count', 0)} datas analisadas",
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na extração de datas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/names")
async def extract_names(file: UploadFile = File(...)):
    """Extrai nomes potenciais do documento."""
    if not names_config:
        raise HTTPException(
            status_code=500,
            detail="Configuração de nomes não carregada"
        )
    
    try:
        text = await process_uploaded_file(file)
        results = extract_potential_names(
            text,
            names_config["first_names"],
            names_config["second_names"],
            names_config["prepositions"]
        )
        
        return {
            "status": "success",
            "message": f"{len(results)} nomes encontrados",
            "results": {
                "potential_names_found": results,
                "count": len(results)
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na extração de nomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/places")
async def extract_places(file: UploadFile = File(...)):
    """Extrai e analisa lugares mencionados no documento."""
    if not places_config:
        raise HTTPException(
            status_code=500,
            detail="Configuração de lugares não carregada"
        )
    
    try:
        text = await process_uploaded_file(file)
        results = search_colonial_places(text, places_config)
        
        return {
            "status": "success",
            "message": "Análise de lugares concluída",
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na extração de lugares: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/themes")
async def extract_themes(file: UploadFile = File(...)):
    """Analisa temas do documento."""
    if not themes_config:
        raise HTTPException(
            status_code=500,
            detail="Configuração de temas não carregada"
        )
    
    try:
        text = await process_uploaded_file(file)
        results = analyze_text_themes(text, themes_config)
        
        return {
            "status": "success",
            "message": "Análise de temas concluída",
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na análise de temas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/references")
async def extract_references(file: UploadFile = File(...)):
    """Extrai referências bibliográficas do documento PDF."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Extração de referências disponível apenas para arquivos PDF"
        )
    
    try:
        # Salva arquivo temporário para o anystyle
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            references_raw = extract_references_with_anystyle(tmp_path)
            
            if references_raw is None:
                return {
                    "status": "error",
                    "message": "Falha ao extrair referências",
                    "results": None
                }
            
            # Formata referências (implementação simplificada)
            formatted_refs = []
            for ref in references_raw:
                if ref.get("author") and ref.get("title"):
                    author = ref["author"][0].get("family", "Autor") if ref["author"] else "Autor"
                    title = ref["title"][0][:50] + "..." if ref["title"] else "Título"
                    year = ref.get("date", [""])[0][:4] if ref.get("date") else "Ano"
                    formatted_refs.append(f"{author} ({year}) {title}")
            
            return {
                "status": "success",
                "message": f"{len(formatted_refs)} referências encontradas",
                "results": {
                    "formatted_references": formatted_refs,
                    "count": len(formatted_refs),
                    "raw_anystyle_output": references_raw
                }
            }
        
        finally:
            os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"Erro na extração de referências: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/all")
async def extract_all(file: UploadFile = File(...)):
    """Executa todas as análises disponíveis no documento."""
    try:
        text = await process_uploaded_file(file)
        results = {}
        
        # Análise de datas
        if date_config:
            try:
                results["dates"] = extract_and_analyze_dates(text, date_config)
            except Exception as e:
                results["dates"] = {"error": str(e)}
        
        # Análise de nomes
        if names_config:
            try:
                names = extract_potential_names(
                    text,
                    names_config["first_names"],
                    names_config["second_names"],
                    names_config["prepositions"]
                )
                results["names"] = {
                    "potential_names_found": names,
                    "count": len(names)
                }
            except Exception as e:
                results["names"] = {"error": str(e)}
        
        # Análise de lugares
        if places_config:
            try:
                results["places"] = search_colonial_places(text, places_config)
            except Exception as e:
                results["places"] = {"error": str(e)}
        
        # Análise de temas
        if themes_config:
            try:
                results["themes"] = analyze_text_themes(text, themes_config)
            except Exception as e:
                results["themes"] = {"error": str(e)}
        
        # Análise de referências (apenas para PDFs)
        if file.filename.lower().endswith('.pdf'):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    file.file.seek(0)  # Reset file pointer
                    shutil.copyfileobj(file.file, tmp_file)
                    tmp_path = tmp_file.name
                
                try:
                    references_raw = extract_references_with_anystyle(tmp_path)
                    if references_raw:
                        formatted_refs = []
                        for ref in references_raw:
                            if ref.get("author") and ref.get("title"):
                                author = ref["author"][0].get("family", "Autor") if ref["author"] else "Autor"
                                title = ref["title"][0][:50] + "..." if ref["title"] else "Título"
                                year = ref.get("date", [""])[0][:4] if ref.get("date") else "Ano"
                                formatted_refs.append(f"{author} ({year}) {title}")
                        
                        results["references"] = {
                            "formatted_references": formatted_refs,
                            "count": len(formatted_refs)
                        }
                finally:
                    os.unlink(tmp_path)
            except Exception as e:
                results["references"] = {"error": str(e)}
        
        return {
            "status": "success",
            "message": "Análise completa realizada",
            "results": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na análise completa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)