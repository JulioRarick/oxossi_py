import json
import os
import argparse
import logging
from typing import Optional, List, Set, Dict, Any

try:
    from oxossi.utils.pdf_utils import extract_text_from_pdf
    from oxossi.utils.data_utils import load_names_config
    from oxossi.utils.output_utils import format_and_output_json
except ImportError:
    print("Erro: Não foi possível importar módulos de 'oxossi.utils'.")
    print("Certifique-se de que o projeto está estruturado corretamente e/ou execute usando 'python -m oxossi.extractors.names ...'")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
log = logging.getLogger(__name__)

def extract_potential_names(
    text: str,
    first_names: Set[str],
    second_names: Set[str],
    prepositions: Set[str]
) -> List[str]:
    if not text:
        log.warning("Texto de entrada está vazio para extração de nomes.")
        return []
    if not first_names and not second_names:
        log.warning("Conjuntos de nomes próprios e/ou sobrenomes estão vazios. Extração de nomes pode ser ineficaz.")
    
    text_normalized = ' '.join(text.split())
    words = text_normalized.split(' ')
    found_names: List[str] = []
    current_name_parts: List[str] = []

    log.info(f"Analisando texto com {len(words)} palavras...")

    for i, word in enumerate(words):
        cleaned_word = word.strip('.,;!?()[]{}":\'')

        if not cleaned_word:
            if current_name_parts:
                if current_name_parts[-1].lower() not in prepositions and len(current_name_parts) >= 2:
                    found_names.append(" ".join(current_name_parts))
                current_name_parts = []
            continue

        capitalized_word = cleaned_word.capitalize()
        lower_word = cleaned_word.lower()

        is_first = capitalized_word in first_names
        is_second = capitalized_word in second_names
        is_prep = lower_word in prepositions

        if not current_name_parts:
            if is_first:
                current_name_parts.append(capitalized_word)
        else:
            last_part_was_prep = current_name_parts[-1].lower() in prepositions

            if is_first and not last_part_was_prep:
                current_name_parts.append(capitalized_word)
            elif is_prep and not last_part_was_prep:
                current_name_parts.append(lower_word)
            elif is_second and not last_part_was_prep:
                current_name_parts.append(capitalized_word)
            elif is_second and last_part_was_prep:
                 current_name_parts.append(capitalized_word)
            else:
                
                if not last_part_was_prep and len(current_name_parts) >= 2: 
                    found_names.append(" ".join(current_name_parts))
                current_name_parts = []
                
                if is_first:
                    current_name_parts.append(capitalized_word)

    if current_name_parts:
        if current_name_parts[-1].lower() not in prepositions and len(current_name_parts) >= 2:
            found_names.append(" ".join(current_name_parts))

    log.info(f"Extração concluída. Encontrados {len(found_names)} nomes potenciais.")

    seen = set()
    unique_names = [name for name in found_names if not (name in seen or seen.add(name))]

    return unique_names

def main():
    parser = argparse.ArgumentParser(
        description="Extrai nomes potenciais de um arquivo de texto ou PDF e gera saída JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_file",
        help="Caminho para o arquivo de entrada (.txt ou .pdf)."
    )
    parser.add_argument(
        "--names-config", "-n",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "names.json"),
        help="Caminho para o arquivo JSON de configuração de nomes."
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Caminho opcional para salvar a saída JSON."
    )
    args = parser.parse_args()

    log.info(f"Iniciando extração de nomes para: {args.input_file}")
    log.info(f"Usando arquivo de nomes: {args.names_config}")
    if args.output:
        log.info(f"Saída JSON será salva em: {args.output}")

    first_names, second_names, prepositions = load_names_config(args.names_config)
    if not first_names and not second_names:
        
        format_and_output_json(
            None, status="Erro",
            message=f"Falha ao carregar nomes de '{args.names_config}' ou listas estão vazias.",
            output_file=args.output
        )
        
        sys.exit(1)

    file_text: Optional[str] = None
    input_path = args.input_file
    if not os.path.exists(input_path):
        error_msg = f"Erro: Arquivo de entrada não encontrado em '{input_path}'"
        log.error(error_msg)
        format_and_output_json(None, status="Erro", message=error_msg, output_file=args.output)
        sys.exit(1)
    elif input_path.lower().endswith(".pdf"):
        file_text = extract_text_from_pdf(input_path)
        if file_text is None:
            error_msg = f"Falha ao extrair texto do PDF '{input_path}'."
            
            format_and_output_json(None, status="Erro", message=error_msg, output_file=args.output)
            sys.exit(1)
    elif input_path.lower().endswith(".txt"):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                file_text = f.read()
            log.info(f"Texto lido com sucesso de '{input_path}'")
        except Exception as e:
            error_msg = f"Erro ao ler arquivo de texto '{input_path}': {e}"
            log.error(error_msg, exc_info=True)
            format_and_output_json(None, status="Erro", message=error_msg, output_file=args.output)
            sys.exit(1)
    else:
        error_msg = f"Erro: Tipo de arquivo de entrada não suportado para '{input_path}'. Forneça .txt ou .pdf."
        log.error(error_msg)
        format_and_output_json(None, status="Erro", message=error_msg, output_file=args.output)
        sys.exit(1)

    potential_names = extract_potential_names(file_text, first_names, second_names, prepositions)

    results_data = {"potential_names_found": potential_names, "count": len(potential_names)}
    status = "Sucesso" if potential_names else "Aviso"
    message = f"{len(potential_names)} nome(s) potencial(is) encontrado(s)." if potential_names else "Nenhum nome potencial encontrado com os critérios definidos."

    format_and_output_json(results_data, status=status, message=message, output_file=args.output)

    log.info("Processo concluído.")

if __name__ == "__main__":
    import sys
    main()
