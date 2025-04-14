import re
import os
import argparse 
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, DefaultDict, Set, Union # Added Union

try:
    import PyPDF2
except ImportError:
    print("Warning: PyPDF2 library not found. PDF processing will not be available.")
    print("Please install it using: pip install PyPDF2")
    PyPDF2 = None 

def extract_text_from_pdf(pdf_path: str) -> str | None:
    if PyPDF2 is None:
        print("Error: Cannot process PDF. PyPDF2 library is not installed.")
        return None

    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file: 
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            print(f"Reading PDF: {pdf_path} ({num_pages} pages)")
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                extracted = page.extract_text()
                if extracted: 
                    text += extracted + "\n" 
        print("Successfully extracted text from PDF.")
        return text
    except FileNotFoundError:
        print(f"Error: PDF file not found at '{pdf_path}'")
        return None
    except PyPDF2.errors.PdfReadError as e:
        print(f"Error: Could not read PDF file '{pdf_path}'. It might be corrupted, password-protected, or an invalid PDF. Details: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading PDF '{pdf_path}': {e}")
        return None

def load_captaincy_data(filepath: str) -> Dict[str, List[str]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Error: Captaincy data file '{filepath}' not found.")

    captaincy_data: DefaultDict[str, List[str]] = defaultdict(list)
    assigned_places: Set[str] = set() 

    try:
        print(f"Loading captaincy data from: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'): 
                    continue

                parts = line.split(',', 1) 
                if len(parts) == 2:
                    place, captaincy = map(str.strip, parts)
                    if place and captaincy:
                        if place not in assigned_places:
                            captaincy_data[captaincy].append(place)
                            assigned_places.add(place)
                    else:
                        print(f"Warning: Skipped line {line_num} due to missing place or captaincy: '{line}'")
                else:
                    print(f"Warning: Skipped line {line_num} due to incorrect format (Expected 'Place,Captaincy'): '{line}'")
        print(f"Successfully loaded data for {len(captaincy_data)} captaincies and {len(assigned_places)} unique places.")

    except IOError as e:
        print(f"I/O error reading file {filepath}: {e}")
        return {} 
    except Exception as e:
        print(f"Unexpected error processing file {filepath}: {e}")
        return {} 

    if not captaincy_data:
         print(f"Warning: No valid captaincy data loaded from '{filepath}'. Resulting dictionary is empty.")

    return dict(captaincy_data) 

def search_colonial_places(text: str, captaincy_data: Dict[str, List[str]]) -> Dict[str, Union[List[Tuple[str, int]], Optional[List[str]], Dict[str, int]]]:
    results_template = {
        "found_places_details": [],
        "top_captaincy": None,
        "all_captaincy_scores": {}
    }

    if not text:
        print("Warning: Input text is empty. Cannot perform search.")
        return results_template
    if not captaincy_data:
        print("Warning: Captaincy data is empty. Cannot perform search.")
        return results_template

    captaincy_scores: Dict[str, int] = {cap: 0 for cap in captaincy_data}
    found_places_counts: DefaultDict[str, int] = defaultdict(int)

    place_to_captaincy: Dict[str, str] = {}
    all_places_canonical: Set[str] = set()
    lower_to_canonical_place: Dict[str, str] = {}

    print("Building place lookup tables...")
    for captaincy, places in captaincy_data.items():
        for place in places:
            if place not in place_to_captaincy:
                place_to_captaincy[place] = captaincy
                all_places_canonical.add(place)
                lower_to_canonical_place[place.lower()] = place

    if not all_places_canonical:
        print("Warning: No unique places found in the provided captaincy data.")
        results_template["all_captaincy_scores"] = captaincy_scores 
        return results_template

    sorted_places = sorted(list(all_places_canonical), key=len, reverse=True)
    
    pattern_str = r'\b(' + '|'.join(re.escape(place) for place in sorted_places) + r')\b'
    print(f"Created regex pattern with {len(sorted_places)} places.")

    try:
        regex_pattern = re.compile(pattern_str, re.IGNORECASE)

        print("Searching text for places...")

        for match in regex_pattern.finditer(text):
            matched_text = match.group(1) # The actual matched place name

            canonical_place = lower_to_canonical_place.get(matched_text.lower())

            if canonical_place:
                found_places_counts[canonical_place] += 1

    except re.error as e:
        print(f"Regex error during pattern compilation or search: {e}")

        results_template["all_captaincy_scores"] = captaincy_scores
        return results_template
    except Exception as e:
         print(f"Unexpected error during regex search: {e}")
         results_template["all_captaincy_scores"] = captaincy_scores
         return results_template

    if not found_places_counts:
        print("No known places found in the text.")
        results_template["all_captaincy_scores"] = captaincy_scores
        return results_template

    print("Calculating captaincy scores...")
    for place, count in found_places_counts.items():
        captaincy = place_to_captaincy.get(place)
        if captaincy:
            captaincy_scores[captaincy] += count

    top_captaincy: Optional[Union[str, List[str]]] = None 
    max_score = 0
    if captaincy_scores:
        positive_scores = {cap: score for cap, score in captaincy_scores.items() if score > 0}
        if positive_scores:
            max_score = max(positive_scores.values())
            tied_top_captaincies = [cap for cap, score in positive_scores.items() if score == max_score]

            if len(tied_top_captaincies) == 1:
                top_captaincy = tied_top_captaincies[0] 
            else:
                top_captaincy = sorted(tied_top_captaincies) 

    found_places_details_list = sorted(list(found_places_counts.items())) 

    return {
        "found_places_details": found_places_details_list,
        "top_captaincy": top_captaincy,
        "all_captaincy_scores": dict(captaincy_scores) 
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze text or PDF file for mentions of colonial places and determine the top captaincy.",
        formatter_class=argparse.RawTextHelpFormatter 
        )
    parser.add_argument(
        "input_file",
        help="Path to the input file (.txt or .pdf) to analyze."
        )
    parser.add_argument(
        "data_file",
        help="Path to the data file containing places and their captaincies.\nFormat: Each line should be 'Place Name,Captaincy Name'"
        )
    args = parser.parse_args()

    input_path = args.input_file
    data_filepath = args.data_file
    file_text = None

    captaincy_place_map = {}
    try:
        captaincy_place_map = load_captaincy_data(data_filepath)
    except FileNotFoundError as e:
        print(e)
        exit(1) 
    except Exception as e:
        print(f"Failed to load or process captaincy data: {e}")
        exit(1) 

    if not captaincy_place_map:
        print("Exiting: Captaincy data could not be loaded or is empty.")
        exit(1)

    print(f"\nProcessing input file: {input_path}")
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        exit(1) 

    if input_path.lower().endswith(".pdf"):
        file_text = extract_text_from_pdf(input_path)
        if file_text is None:
            print("Exiting: Failed to extract text from PDF.")
            exit(1) 
    elif input_path.lower().endswith(".txt"):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                file_text = f.read()
            print(f"Successfully read text from '{input_path}'")
        except Exception as e:
            print(f"Error reading text file '{input_path}': {e}")
            exit(1) 
    else:
        print(f"Error: Unsupported input file type for '{input_path}'. Please provide a .txt or .pdf file.")
        exit(1) 

    if file_text:
        print("\n--- Resultado Pesquisa ---")
        search_results = search_colonial_places(file_text, captaincy_place_map)

        top_result = search_results['top_captaincy']
        if top_result:
            if isinstance(top_result, list):
                 print(f"Ordem dos resultados encontrados: {', '.join(top_result)}")
            else: 
                 print(f"Top 1 Capitania: {top_result}")
        else:
            print("Top 1 Capitania: Sem registro.")

        print("\nDetalhes dos resultados encontrados:")
        if search_results['found_places_details']:
            for place, count in search_results['found_places_details']:
                print(f"- {place}: {count} vez(es)")
        else:
            print("No known places were found in the text.")

        print("\nTotal do Score por Capitania (Score > 0):")
        sorted_scores = sorted(
            search_results['all_captaincy_scores'].items(),
            key=lambda item: item[1], 
            reverse=True
            )
        any_score_found = False
        for captaincy, score in sorted_scores:
             if score > 0:
                 print(f"- {captaincy}: {score}")
                 any_score_found = True

        if not any_score_found:
            print("No captaincies had a score greater than zero.")

        print("-" * 30)
    else:
        print("\nAnalysis could not be performed as no text was loaded from the input file.")

