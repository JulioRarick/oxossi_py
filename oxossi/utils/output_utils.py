import json
import logging
import os
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
log = logging.getLogger(__name__)

def format_and_output_json(
    data: Optional[Dict[str, Any]],
    status: str = "Sucesso",
    message: str = "Operação concluída.",
    output_file: Optional[str] = None
) -> None:
    output_structure = {
        "status": status,
        "message": message,
        "results": data 
    }

    try:
        json_output_string = json.dumps(output_structure, indent=4, ensure_ascii=False)

        print("\n--- Saída JSON ---")
        print(json_output_string)
        print("------------------")

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_output_string)
                log.info(f"Saída JSON salva com sucesso em '{output_file}'")
            except IOError as e:
                log.error(f"Erro ao salvar saída JSON em '{output_file}': {e}", exc_info=True)
            except Exception as e:
                log.error(f"Erro inesperado ao salvar JSON em '{output_file}': {e}", exc_info=True)

    except TypeError as e:
        log.error(f"Erro de tipo ao serializar para JSON: {e}. Verifique os tipos de dados em 'results'.", exc_info=True)
        
        print("\n--- Saída JSON (Erro de Serialização) ---")
        print(f'{{"status": "Erro", "message": "Falha ao serializar resultados para JSON: {e}", "results": null}}')
        print("----------------------------------------")
    except Exception as e:
        log.error(f"Erro inesperado ao formatar ou imprimir JSON: {e}", exc_info=True)
        print("\n--- Erro na Saída JSON ---")
        print(f'{{"status": "Erro", "message": "Falha inesperada ao gerar saída JSON: {e}", "results": null}}')
        print("--------------------------")


if __name__ == '__main__':
    print("--- Exemplo 1: Sucesso ---")
    results_success = {"contagem": 10, "itens": ["a", "b"]}
    format_and_output_json(results_success, status="Sucesso", message="Itens processados.")

    print("\n--- Exemplo 2: Sucesso com Arquivo ---")
    output_path = "temp_output.json"
    format_and_output_json(results_success, output_file=output_path)
    if os.path.exists(output_path):
        print(f"Verifique o arquivo '{output_path}'")
        os.remove(output_path) 

    print("\n--- Exemplo 3: Aviso (sem dados) ---")
    format_and_output_json(None, status="Aviso", message="Nenhum item encontrado.")

    print("\n--- Exemplo 4: Erro (sem dados) ---")
    format_and_output_json(None, status="Erro", message="Falha ao ler arquivo de entrada.")

    print("\n--- Exemplo 5: Erro de Serialização ---")
    
    results_error = {"conjunto": {"a", "b"}}
    format_and_output_json(results_error)

