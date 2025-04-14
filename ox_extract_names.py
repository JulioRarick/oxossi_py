import json
import os
import argparse 
try:
    import PyPDF2 
except ImportError:
    print("Error: PyPDF2 library not found. Please install it using: pip install PyPDF2")
    exit(1) 

def load_names_from_json(file_path: str) -> tuple[set[str], set[str], set[str]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            first_names = set(name.capitalize() for name in data.get("first_names", []))
            second_names = set(name.capitalize() for name in data.get("second_names", []))
        
            prepositions = set(data.get("prepositions", ["da", "das", "do", "dos", "de"]))

            print(f"Successfully loaded {len(first_names)} first names, {len(second_names)} second names, and {len(prepositions)} prepositions from {file_path}")
            return first_names, second_names, prepositions
    except FileNotFoundError:
        print(f"Error: Names file not found at '{file_path}'")
        return set(), set(), set()
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file '{file_path}'")
        return set(), set(), set()
    except Exception as e:
        print(f"Unexpected error loading names from '{file_path}': {e}")
        return set(), set(), set()

def extract_text_from_pdf(pdf_path: str) -> str | None:
    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            print(f"Reading PDF: {pdf_path} ({num_pages} pages)")
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text += page.extract_text() or "" 
        print("Successfully extracted text from PDF.")
        return text
    except FileNotFoundError:
        print(f"Error: PDF file not found at '{pdf_path}'")
        return None
    except PyPDF2.errors.PdfReadError:
        print(f"Error: Could not read PDF file '{pdf_path}'. It might be corrupted or password-protected.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading PDF '{pdf_path}': {e}")
        return None

def extract_potential_names(
    text: str,
    first_names: set[str],
    second_names: set[str],
    prepositions: set[str]
) -> list[str]:
    if not text:
        print("Warning: Input text is empty.")
        return []
    if not first_names and not second_names:
        print("Warning: Name sets are empty. Check 'names.json' or its loading process.")
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

    parser = argparse.ArgumentParser(description="Extract potential names from a text or PDF file.")
    parser.add_argument("input_file", help="Path to the input file (.txt or .pdf)")
    args = parser.parse_args()

    input_path = args.input_file
    file_text = None

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
    elif input_path.lower().endswith(".pdf"):
        file_text = extract_text_from_pdf(input_path)
    elif input_path.lower().endswith(".txt"):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                file_text = f.read()
            print(f"Successfully read text from '{input_path}'")
        except Exception as e:
            print(f"Error reading text file '{input_path}': {e}")
    else:
        print(f"Error: Unsupported file type for '{input_path}'. Please provide a .txt or .pdf file.")

    if file_text and (FIRST_NAMES or SECOND_NAMES):
        print("\n--- Analysis ---")
        potential_names = extract_potential_names(file_text, FIRST_NAMES, SECOND_NAMES, PREPOSITIONS)

        if potential_names:
            print("\nPotenciais Nomes encontrados:")
            for name in potential_names:
                print(f"- {name}")
        else:
            print("\nNo potential names found matching the criteria.")

    elif not file_text:
        print("\nCould not extract text from the input file. Cannot perform name extraction.")
    else: 
        print("\nName extraction not performed because the name lists (first/second names) are empty.")
        print(f"Please check the '{NAMES_FILE_PATH}' file and ensure it's correctly formatted and populated.")