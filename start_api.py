#!/usr/bin/env python3
"""
Script de inicialização da API Oxossi
Configura o ambiente e inicia o servidor com todas as dependências.
"""

import asyncio
import uvicorn
import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_logging(level=logging.INFO):
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduz verbosidade de algumas bibliotecas
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)

def check_dependencies():
    """Verifica se todas as dependências estão instaladas."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'aiosqlite',
        'pydantic',
        'fitz',  # PyMuPDF
        'numpy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Dependências faltando:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstale as dependências com:")
        print("   pip install -r requirements_api.txt")
        return False
    
    print("✅ Todas as dependências estão instaladas")
    return True

def check_data_files():
    """Verifica se os arquivos de dados necessários existem."""
    data_dir = project_root / "data"
    required_files = [
        "date_config.json",
        "names.json", 
        "places.txt",
        "themes.json"
    ]
    
    missing_files = []
    
    for filename in required_files:
        file_path = data_dir / filename
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print("⚠️  Arquivos de dados faltando:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\nA API funcionará, mas alguns extractors podem falhar.")
        return False
    
    print("✅ Todos os arquivos de dados estão presentes")
    return True

async def initialize_database():
    """Inicializa o banco de dados."""
    try:
        from database import DatabaseManager
        
        print("🔧 Inicializando banco de dados...")
        db = DatabaseManager()
        await db.initialize()
        
        # Testa a conexão
        count = await db.get_document_count()
        print(f"✅ Banco inicializado com {count} documentos")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        return False

def create_sample_data_files():
    """Cria arquivos de dados de exemplo se não existirem."""
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    # date_config.json
    date_config_path = data_dir / "date_config.json"
    if not date_config_path.exists():
        date_config = {
            "century_map": {
                "xvi": 1500, "xvii": 1600, "xviii": 1700, "xix": 1800,
                "quinhentos": 1500, "seiscentos": 1600, "setecentos": 1700, "oitocentos": 1800
            },
            "part_map": {
                "primeira metade": [0, 50], "início": [0, 30], "começo": [0, 30],
                "segunda metade": [50, 100], "final": [70, 100], "fim": [70, 100],
                "meados": [40, 60]
            },
            "regex_patterns": {
                "year": "\\b(?P<year>1[5-8]\\d{2})\\b",
                "textual_phrase": "\\b(?P<part>primeira\\s+metade|segunda\\s+metade|in[íi]cio[s]?|come[çc]o|finais|final|fim|meados)?(?:\\s+(?:de|do|da|dos|das)\\s+)?(?P<century>s[ée]culo\\s+(?:xvi|xvii|xviii|xix)|quinhentos|seiscentos|setecentos|oitocentos)\\b"
            }
        }
        
        import json
        with open(date_config_path, 'w', encoding='utf-8') as f:
            json.dump(date_config, f, indent=2, ensure_ascii=False)
        print(f"📄 Criado: {date_config_path}")
    
    # names.json (versão simplificada)
    names_path = data_dir / "names.json"
    if not names_path.exists():
        names_config = {
            "first_names": [
                "António", "João", "Francisco", "Manuel", "José", "Pedro", "Luís", "Carlos",
                "Maria", "Ana", "Isabel", "Catarina", "Francisca", "Joana", "Margarida"
            ],
            "second_names": [
                "Silva", "Santos", "Pereira", "Costa", "Rodrigues", "Martins", "Jesus",
                "Sousa", "Fernandes", "Gonçalves", "Gomes", "Lopes", "Marques", "Alves"
            ],
            "prepositions": ["da", "das", "do", "dos", "de"]
        }
        
        with open(names_path, 'w', encoding='utf-8') as f:
            json.dump(names_config, f, indent=2, ensure_ascii=False)
        print(f"📄 Criado: {names_path}")
    
    # places.txt (versão simplificada)
    places_path = data_dir / "places.txt"
    if not places_path.exists():
        places_content = """# Arquivo de locais e capitanias
São Vicente,Capitania de São Vicente
Santos,Capitania de São Vicente
São Paulo de Piratininga,Capitania de São Vicente
Olinda,Capitania de Pernambuco
Recife,Capitania de Pernambuco
Salvador,Capitania da Bahia
Rio de Janeiro,Capitania do Rio de Janeiro
Vila Rica,Capitania de Minas Gerais"""
        
        with open(places_path, 'w', encoding='utf-8') as f:
            f.write(places_content)
        print(f"📄 Criado: {places_path}")
    
    # themes.json
    themes_path = data_dir / "themes.json"
    if not themes_path.exists():
        themes_config = {
            "Economia": ["comércio", "produção", "gado", "açúcar", "ouro", "preço", "negócio"],
            "Política": ["poder", "rei", "câmara", "lei", "governo", "capitão", "juiz"],
            "Religião": ["igreja", "padre", "fé", "missa", "santo", "deus", "oração"],
            "Geografia": ["vila", "cidade", "rio", "caminho", "serra", "mar", "terra"],
            "Social": ["família", "casamento", "escravidão", "senhor", "escravo", "filho"]
        }
        
        with open(themes_path, 'w', encoding='utf-8') as f:
            json.dump(themes_config, f, indent=2, ensure_ascii=False)
        print(f"📄 Criado: {themes_path}")

def print_startup_info():
    """Imprime informações de inicialização."""
    print("🚀 Oxossi API - Sistema de Análise de Documentos Históricos")
    print("=" * 60)
    print(f"📁 Diretório do projeto: {project_root}")
    print(f"🗄️  Banco de dados: {project_root / 'oxossi.db'}")
    print(f"📊 Diretório de dados: {project_root / 'data'}")
    print("")

async def main():
    """Função principal de inicialização."""
    print_startup_info()
    
    # Verifica dependências
    if not check_dependencies():
        sys.exit(1)
    
    # Cria arquivos de dados se necessário
    create_sample_data_files()
    
    # Verifica arquivos de dados
    check_data_files()
    
    # Inicializa banco de dados
    if not await initialize_database():
        sys.exit(1)
    
    print("\n🎯 Configurações do servidor:")
    print("   Host: 0.0.0.0")
    print("   Porta: 8000")
    print("   Modo: desenvolvimento (reload ativo)")
    print("   Documentação: http://localhost:8000/docs")
    print("   ReDoc: http://localhost:8000/redoc")
    print("")
    
    print("✅ Inicialização completa! Iniciando servidor...")
    print("=" * 60)

def run_server():
    """Inicia o servidor uvicorn."""
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True,
            reload_dirs=[str(project_root)]
        )
    except KeyboardInterrupt:
        print("\n\n👋 Servidor parado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configura logging
    setup_logging()
    
    # Executa inicialização assíncrona
    try:
        asyncio.run(main())
        
        # Inicia o servidor
        run_server()
        
    except KeyboardInterrupt:
        print("\n👋 Inicialização cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro na inicialização: {e}")
        sys.exit(1)
