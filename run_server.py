import os
import sys
import subprocess
from pathlib import Path

def main():
    """Executa o servidor FastAPI do Oxossi."""
    
    project_root = Path(__file__).resolve().parent
    main_py_path = project_root / "main.py"
    
    if not main_py_path.exists():
        print("Erro: main.py não encontrado no diretório atual")
        sys.exit(1)
    
    try:
        import fastapi
        import uvicorn
    except ImportError as e:
        print(f"Erro: Dependências não encontradas: {e}")
        print("Execute: pip install -r requirements.txt")
        sys.exit(1)
    
    os.environ.setdefault("PYTHONPATH", str(project_root))
    
    print("🚀 Iniciando servidor Oxossi API...")
    print(f"📁 Diretório do projeto: {project_root}")
    print("🌐 Servidor será executado em: http://localhost:8000")
    print("📖 Documentação da API: http://localhost:8000/docs")
    print("⚡ Para parar o servidor: Ctrl+C")
    print("-" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload",
            "--reload-dir", str(project_root)
        ], cwd=project_root, check=True)
    
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar servidor: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()