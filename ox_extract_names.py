import json
import os
import argparse 
try:
    import PyPDF2 
except ImportError:
    print("Erro: Biblioteca PyPDF2 não encontrada. Por favor, instale usando: pip install PyPDF2")
    exit(1) 

def load_names_from_json(file_path: str) -> tuple[set[str], set[str], set[str]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            first_names = set(name.capitalize() for name in data.get("first_names", []))
            second_names = set(name.capitalize() for name in data.get("second_names", []))
        
            prepositions = set(data.get("prepositions", ["da", "das", "do", "dos", "de"]))

            print(f"Sucesso: Carregados {len(first_names)} nomes próprios, {len(second_names)} sobrenomes, e {len(prepositions)} preposições de {file_path}")
            return first_names, second_names, prepositions
    except FileNotFoundError:
        print(f"Erro: Arquivo de nomes não encontrado em '{file_path}'")
        return set(), set(), set()
    except json.JSONDecodeError:
        print(f"Erro: Formato JSON inválido no arquivo '{file_path}'")
        return set(), set(), set()
    except Exception as e:
        print(f"Erro inesperado ao carregar nomes de '{file_path}': {e}")
        return set(), set(), set()

def extract_text_from_pdf(pdf_path: str) -> str | None:
    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            print(f"Lendo PDF: {pdf_path} ({num_pages} páginas)")
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text += page.extract_text() or "" 
        print("Sucesso: Texto extraído do PDF.")
        return text
    except FileNotFoundError:
        print(f"Erro: Arquivo PDF não encontrado em '{pdf_path}'")
        return None
    except PyPDF2.errors.PdfReadError:
        print(f"Erro: Não foi possível ler o arquivo PDF '{pdf_path}'. Pode estar corrompido ou protegido por senha.")
        return None
    except Exception as e:
        print(f"Erro inesperado ao ler o PDF '{pdf_path}': {e}")
        return None

def extract_potential_names(
    text: str,
    first_names: set[str],
    second_names: set[str],
    prepositions: set[str]
) -> list[str]:
    if not text:
        print("Aviso: Texto de entrada está vazio.")
        return []
    if not first_names and not second_names:
        print("Aviso: Conjuntos de nomes estão vazios. Verifique 'names.json' ou o processo de carregamento.")
        return []

    text_normalized = ' '.join(text.split())
    words = text_normalized.split(' ')
    found_names = []
    current_name_parts = []
    potential_start = True 

    for word in words:
        cleaned_word = word.strip('.,;!?()[]{}')
        
        capitalized_word = cleaned_word.capitalize() if cleaned_word else ""

        if not capitalized_word:
             continue

        is_first = capitalized_word in first_names
        is_second = capitalized_word in second_names
        
        is_prep = cleaned_word.lower() in prepositions

        
        is_part_of_name = is_first or is_second or (is_prep and current_name_parts)

        if is_part_of_name:
            if is_first and not current_name_parts:
                current_name_parts.append(capitalized_word)
                potential_start = False 
            elif current_name_parts:
                 if is_prep or is_first or is_second:
                    current_name_parts.append(cleaned_word if is_prep else capitalized_word)

        else: 
            if current_name_parts:
                if current_name_parts[-1].lower() not in prepositions:
                    if len(current_name_parts) >= 2:
                        found_names.append(" ".join(current_name_parts))
                current_name_parts = []
            potential_start = True 

    if current_name_parts:
        if current_name_parts[-1].lower() not in prepositions and len(current_name_parts) >= 2:
            found_names.append(" ".join(current_name_parts))

    return found_names

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'
    NAMES_FILE_PATH = os.path.join(script_dir, "data", "names.json")

    FIRST_NAMES, SECOND_NAMES, PREPOSITIONS = load_names_from_json(NAMES_FILE_PATH)

    parser = argparse.ArgumentParser(description="Extrai nomes potenciais de um arquivo de texto ou PDF e gera saída JSON.")
    parser.add_argument("input_file", help="Caminho para o arquivo de entrada (.txt ou .pdf)")
    args = parser.parse_args() 

    input_path = args.input_file
    file_text = None 
    output_data = {} 

    if not os.path.exists(input_path):
        error_message = f"Erro: Arquivo de entrada não encontrado em '{input_path}'"
        print(error_message)
        output_data = {"status": "Erro", "message": error_message, "potential_names": []}
    elif input_path.lower().endswith(".pdf"):
        file_text = extract_text_from_pdf(input_path)
        if file_text is None:
             output_data = {"status": "Erro", "message": f"Falha ao extrair texto do PDF '{input_path}'.", "potential_names": []}
    elif input_path.lower().endswith(".txt"):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                file_text = f.read()
            print(f"Sucesso: Texto lido de '{input_path}'")
        except Exception as e:
            error_message = f"Erro ao ler arquivo de texto '{input_path}': {e}"
            print(error_message)
            output_data = {"status": "Erro", "message": error_message, "potential_names": []}
    else:
        error_message = f"Erro: Tipo de arquivo não suportado para '{input_path}'. Forneça um arquivo .txt ou .pdf."
        print(error_message)
        output_data = {"status": "Erro", "message": error_message, "potential_names": []}

    if file_text is not None and not output_data: 
        if FIRST_NAMES or SECOND_NAMES:
            print("\n--- Análise ---")
            potential_names = extract_potential_names(file_text, FIRST_NAMES, SECOND_NAMES, PREPOSITIONS)

            output_data["potential_names"] = potential_names
            if potential_names:
                print(f"Sucesso: {len(potential_names)} nome(s) potencial(is) encontrado(s).")
                output_data["status"] = "Sucesso"
                output_data["message"] = f"{len(potential_names)} nome(s) potencial(is) encontrado(s)."
            else:
                print("Aviso: Nenhum nome potencial encontrado com os critérios definidos.")
                output_data["status"] = "Aviso"
                output_data["message"] = "Nenhum nome potencial encontrado."
        else:
             error_message = f"Extração não realizada: listas de nomes vazias. Verifique '{NAMES_FILE_PATH}'."
             print(f"\n{error_message}")
             output_data = {"status": "Erro", "message": error_message, "potential_names": []}

    print("\n--- Saída JSON ---")

    json_output_string = json.dumps(output_data, indent=4, ensure_ascii=False)
    print(json_output_string)
    print("------------------")
