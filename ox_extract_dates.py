import re
import numpy as np
import json 
import fitz  
import sys   
import os  

century_map = {
    "xvi": 1500,
    "xvii": 1600, 
    "xviii": 1700, 
    "xix": 1800,
    "quinhentos": 1500, 
    "seiscentos": 1600, 
    "setecentos": 1700, 
    "oitocentos": 1800,
}

part_map = {
    "primeira metade": (0, 50),
    "início": (0, 30),
    "começo": (0, 30),
    "segunda metade": (50, 100),
    "final": (70, 100), 
    "fim": (70, 100),
    "meados": (40, 60), 
}

regex_year = r'\b(?P<year>1[5-8]\d{2})\b'

regex_textual_phrase = r"""
    \b
    (?P<part>primeira\s+metade|segunda\s+metade|in[íi]cio[s]?|come[çc]o|finais|final|fim|meados)?
    (?:\s+(?:de|do|da|dos|das)\s+)?
    (?P<century>s[ée]culo\s+(?:xvi|xvii|xviii|xix)|quinhentos|seiscentos|setecentos|oitocentos)
    \b
"""

combined_regex = f"({regex_year})|({regex_textual_phrase})"

def calculate_interval_from_match(match_dict):
    century_str = match_dict.get('century')
    part_str = match_dict.get('part') 

    if not century_str:
        return None 

    century_norm = re.sub(r's[ée]culo\s+', '', century_str.lower())
    base_year = century_map.get(century_norm)

    if base_year is None:
        print(f"Warning: Unrecognized century normalization: {century_norm}")
        return None 

    if not part_str:
        return (base_year, base_year + 100)
    else:
        part_norm = part_str.lower()
        part_norm = part_norm.replace('í', 'i').replace('ç', 'c').replace('finais', 'final')
        relative_interval = part_map.get(part_norm)

        if relative_interval:
            return (base_year + relative_interval[0], base_year + relative_interval[1])
        else:
            print(f"Warning: Unrecognized part phrase: {part_str}")
            return (base_year, base_year + 100) 


def extract_and_analyze_dates(text):
    if not isinstance(text, str):
        print("Error: Input must be a string.")
        return None

    numeric_years_found = []
    textual_intervals_found = []

    for match in re.finditer(combined_regex, text, flags=re.IGNORECASE | re.VERBOSE):
        if match.group(1): 
            numeric_years_found.append(int(match.group('year')))
        elif match.group(2): 
            interval = calculate_interval_from_match(match.groupdict())
            if interval:
                textual_intervals_found.append(interval)

    representative_years_from_intervals = []

    for start, end in textual_intervals_found:
        representative_years_from_intervals.append((start + end) // 2)

    combined_years = sorted(list(set(numeric_years_found + representative_years_from_intervals)))

    results = {
        'direct_numeric_years': sorted(list(set(numeric_years_found))),
        'calculated_textual_intervals': sorted(list(set(textual_intervals_found))), 
        'combined_representative_years': combined_years,
        'count': len(combined_years),
        'mean': None, 'median': None, 'minimum': None, 'maximum': None,
        'standard_deviation': None, 'full_range': None, 'dense_range_stddev': None
    }

    if not combined_years:
        return results 

    results['mean'] = np.mean(combined_years)
    results['median'] = np.median(combined_years)
    results['minimum'] = min(combined_years)
    results['maximum'] = max(combined_years)

    results['standard_deviation'] = np.std(combined_years) if len(combined_years) > 1 else 0.0

    results['full_range'] = f"{results['minimum']} - {results['maximum']}"

    if results['standard_deviation'] is not None and results['mean'] is not None:
        mean_val = results['mean']
        std_dev_val = results['standard_deviation']
        results['dense_range_stddev'] = (round(mean_val - std_dev_val), round(mean_val + std_dev_val))

    return results

sample_text_pt = """
Ocorreu em 1780 e depois no início do século XVI (1545).
Mais tarde, em 1786 e 1754, e também na segunda metade do século XVIII.
O evento principal foi no final dos seiscentos. Algo aconteceu em meados do século XVII.
Documento de 1650.
"""

dating_data = extract_and_analyze_dates(sample_text_pt)

def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Erro: Arquivo PDF não encontrado em '{pdf_path}'")
        return None
    try:
        with fitz.open(pdf_path) as doc:
            full_text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                full_text += page.get_text() 
            return full_text
    except Exception as e:
        print(f"Erro ao ler o arquivo PDF '{pdf_path}': {e}")
        return None

if __name__ == "__main__":
    pdf_file_path = os.getenv("PDF_FILE_PATH") 
    
    if len(sys.argv) > 1:
        pdf_file_path = sys.argv[1]
    else:
        print("Caso prefira use: python ox_extract_dates.py <caminho_para_o_pdf>")
        if pdf_file_path == "seu_arquivo.pdf": 
            sys.exit(1) 

    print(f"Processando o arquivo PDF: {pdf_file_path}")

    extracted_text = extract_text_from_pdf(pdf_file_path)

    if extracted_text:
        print(f"Texto extraído com sucesso ({len(extracted_text)} caracteres). Analisando datas...")

        dating_data = extract_and_analyze_dates(extracted_text)

        if dating_data:
            output_json = dating_data
            if dating_data.get('count', 0) > 0:
                 output_json['status'] = 'Sucesso: Datas analisadas.'
            else:
                 output_json['status'] = f"Aviso: {dating_data.get('message', 'Nenhuma data relevante encontrada.')}"

        else:
            print("Erro inesperado durante a análise das datas.")
            output_json = {'status': 'Erro', 'message': 'Falha na análise das datas.'}
    else:
        print("Não foi possível extrair texto do PDF para análise.")
        output_json = {'status': 'Erro', 'message': 'Falha ao extrair texto do PDF.'}

    json_output_string = json.dumps(output_json, indent=4, ensure_ascii=False)
  
    print("\n--- Saída JSON ---")
    print(json_output_string)
    print("------------------")