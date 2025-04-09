import re
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, DefaultDict, Set

def load_captaincy_data(filepath: str) -> Dict[str, List[str]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Erro: Arquivo '{filepath}' não encontrado.")

    captaincy_data: DefaultDict[str, List[str]] = defaultdict(list)

    assigned_places: Set[str] = set()

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip() 
                if not line:
                    continue 

                parts = line.split(',', 1)
                if len(parts) == 2:
                    place, captaincy = map(str.strip, parts) 
                    if place and captaincy:
                        if place not in assigned_places:
                            captaincy_data[captaincy].append(place)
                            assigned_places.add(place)
                    else:
                        print(f"Advertência: linha {line_num} não compilada, sem localização ou capitania -> '{line}'")
                else:
                    print(f"Advertência: linha {line_num} não compilada, formato incorreto (formato: 'Local,Capitania') -> '{line}'")

    except IOError as e:
        print(f"I/O erro ao ler arquivo {filepath}: {e}")
        return {} 
    except Exception as e:
        print(f"Erro não especificado ao processar arquivo: {filepath}: {e}")
        return {} 

    if not captaincy_data:
         print(f"Advertência: formato inválido dos dados '{filepath}'. O objeto está vazio.")

    return dict(captaincy_data)

def search_colonial_places(text: str, captaincy_data: Dict[str, List[str]]) -> Dict:
    if not captaincy_data:
        print("Advertência: Objeto sem dados de capitanias. Sem lugares para pesquisa.")
        return {
            "found_places_details": [],
            "top_captaincy": None,
            "all_captaincy_scores": {}
        }

    captaincy_scores: Dict[str, int] = {cap: 0 for cap in captaincy_data}
    
    found_places_counts: DefaultDict[str, int] = defaultdict(int)

    place_to_captaincy: Dict[str, str] = {}
    all_places_canonical: Set[str] = set()
    
    lower_to_canonical_place: Dict[str, str] = {}

    for captaincy, places in captaincy_data.items():
        for place in places:
            if place not in place_to_captaincy:
                place_to_captaincy[place] = captaincy
                all_places_canonical.add(place)
                lower_to_canonical_place[place.lower()] = place


    if not all_places_canonical:
        print("Advertência: Sem local único nos dados.")
        return {
            "found_places_details": [],
            "top_captaincy": None,
            "all_captaincy_scores": captaincy_scores 
        }

    sorted_places = sorted(list(all_places_canonical), key=len, reverse=True)

    pattern_str = r'\b(' + '|'.join(re.escape(place) for place in sorted_places) + r')\b'

    try:
        regex_pattern = re.compile(pattern_str, re.IGNORECASE)

        for match in regex_pattern.finditer(text):
            matched_text = match.group(1) 

            canonical_place = lower_to_canonical_place.get(matched_text.lower())

            if canonical_place:
                found_places_counts[canonical_place] += 1

    except re.error as e:
        print(f"Regex error: {e}")
        
        print(f"Pattern (start): {pattern_str[:200]}...")
        return {
            "found_places_details": [],
            "top_captaincy": None,
            "all_captaincy_scores": captaincy_scores 
        }
    except Exception as e:
         print(f"Unexpected error during regex search: {e}")
         return {
            "found_places_details": [],
            "top_captaincy": None,
            "all_captaincy_scores": captaincy_scores
        }

    for place, count in found_places_counts.items():
        captaincy = place_to_captaincy.get(place)
        if captaincy:
            captaincy_scores[captaincy] += count

    top_captaincy: Optional[str] = None
    max_score = 0
    if captaincy_scores:
        positive_scores = {cap: score for cap, score in captaincy_scores.items() if score > 0}
        if positive_scores:
            top_captaincy = max(positive_scores, key=positive_scores.get)
            
            max_score = positive_scores[top_captaincy]
            tied_top_captaincies = [cap for cap, score in positive_scores.items() if score == max_score]
            top_captaincy = tied_top_captaincies 
            return {
                "found_places_details": [],
                "top_captaincy": top_captaincy,
                "all_captaincy_scores": captaincy_scores
            }

    found_places_details_list = list(found_places_counts.items())

    return {
        "found_places_details": found_places_details_list,
        "top_captaincy": top_captaincy,
        "all_captaincy_scores": dict(captaincy_scores)
    }

if __name__ == "__main__":
    data_filepath = os.getenv('PLACES_DATA_FILE_PATH')

    sample_text = """
    Document about exploration in the Captaincy of Pernambuco.
    Trips were made to Olinda, Recife and also Goiana.
    Later, expeditions reached the City of Bahia (Cidade da Bahia), the administrative center.
    They also visited Vila Rica in Minas Gerais and São Paulo de Piratininga.
    The mention of recife is important, as is olinda. Vila Rica too.
    """

    try:
        captaincy_place_map = load_captaincy_data(data_filepath)

        if captaincy_place_map:
            search_results = search_colonial_places(sample_text, captaincy_place_map)

            print("-" * 30)
            print("Search Results:")
            print("-" * 30)
            print(f"Top Captaincy (most mentions): {search_results['top_captaincy']}")
            print("\nDetails of Found Places:")
            if search_results['found_places_details']:
                sorted_details = sorted(search_results['found_places_details'], key=lambda item: item[0])

                for place, count in sorted_details:
                    print(f"- {place}: {count} time(s)")
            else:
                print("No known places were found in the text.")
            print("\nTotal Score per Captaincy:")

            sorted_scores = sorted(search_results['all_captaincy_scores'].items(), key=lambda item: item[1], reverse=True)
            any_score_found = False

            for captaincy, score in sorted_scores:
                 if score > 0:
                     print(f"- {captaincy}: {score}")
                     any_score_found = True

            if not any_score_found:
                print("No captaincies had a score greater than zero.")
            print("-" * 30)
        else:
            print("Search could not be performed because no data was loaded.")
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An overall error occurred: {e}")
