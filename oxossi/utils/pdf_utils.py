import fitz  
import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
log = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    if not isinstance(pdf_path, str) or not pdf_path:
        log.error("Caminho do PDF inválido fornecido.")
        return None
    if not os.path.exists(pdf_path):
        log.error(f"Arquivo PDF não encontrado em '{pdf_path}'")
        return None

    full_text = ""
    try:
        log.info(f"Abrindo PDF: {pdf_path}")
        with fitz.open(pdf_path) as doc:
            num_pages = len(doc)
            log.info(f"Lendo {num_pages} páginas...")
            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                page_text = page.get_text("text")
                if page_text:
                    full_text += page_text + "\n" 
            log.info(f"Texto extraído com sucesso do PDF ({len(full_text)} caracteres).")
        return full_text
    except fitz.FitzError as e:
        log.error(f"Erro do PyMuPDF ao ler o arquivo PDF '{pdf_path}': {e}", exc_info=True)
        return None
    except Exception as e:
        log.error(f"Erro inesperado ao ler o PDF '{pdf_path}': {e}", exc_info=True)
        return None

if __name__ == '__main__':
    test_pdf = "../../pdfs/Holanda, movimentos da população sao paulo.pdf" 
    if os.path.exists(test_pdf):
        text = extract_text_from_pdf(test_pdf)
        if text:
            print("\n--- Exemplo de Texto Extraído (primeiros 500 caracteres) ---")
            print(text[:500])
            print("...")
        else:
            print(f"Falha ao extrair texto de {test_pdf}")
    else:
        print(f"Arquivo de teste não encontrado: {test_pdf}")

