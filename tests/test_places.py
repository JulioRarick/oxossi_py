import unittest
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.places import load_place_captaincy_data, search_colonial_places
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    MODULES_FOUND = False
    def load_place_captaincy_data(filepath): raise ImportError("Module not found")
    def search_colonial_places(text, captaincy_data): raise ImportError("Module not found")

TEST_PLACES_DATA_FILENAME = "temp_test_places_data.txt"
TEST_PLACES_DATA_CONTENT = """# Comentário
São Vicente,Capitania de São Vicente
Santos,Capitania de São Vicente
São Paulo de Piratininga,Capitania de São Vicente
Olinda,Capitania de Pernambuco
Recife,Capitania de Pernambuco
Salvador,Capitania da Bahia
São Vicente,Capitania da Bahia # Teste de atribuição única (deve ser ignorado)

Linha Inválida
Outra Linha Inválida,
,Capitania Vazia
Lugar Vazio,"""

@unittest.skipIf(not MODULES_FOUND, "Módulos principais ou utilitários não encontrados, pulando testes de locais.")
class TestPlaceExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Cria arquivo de dados de locais temporário."""
        try:
            with open(TEST_PLACES_DATA_FILENAME, 'w', encoding='utf-8') as f:
                f.write(TEST_PLACES_DATA_CONTENT)
            print(f"\nArquivo de Dados de Locais de teste '{TEST_PLACES_DATA_FILENAME}' criado.")
        except Exception as e:
            print(f"Falha ao criar arquivo de dados de locais de teste: {e}")
            raise unittest.SkipTest(f"Não foi possível criar arquivo de dados de locais: {e}")

    @classmethod
    def tearDownClass(cls):
        """Remove o arquivo de dados temporário."""
        if os.path.exists(TEST_PLACES_DATA_FILENAME):
            os.remove(TEST_PLACES_DATA_FILENAME)
            print(f"Arquivo de Dados de Locais de teste '{TEST_PLACES_DATA_FILENAME}' removido.")

    def test_load_data_success(self):
        """Testa o carregamento bem-sucedido dos dados."""
        data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        
        self.assertIsNotNone(data)
        self.assertIn("Capitania de São Vicente", data)
        self.assertIn("Capitania de Pernambuco", data)
        self.assertIn("Capitania da Bahia", data)
        self.assertNotIn("Capitania Vazia", data)
        self.assertCountEqual(data["Capitania de São Vicente"], ["São Vicente", "Santos", "São Paulo de Piratininga"])
        self.assertCountEqual(data["Capitania de Pernambuco"], ["Olinda", "Recife"])
        self.assertCountEqual(data["Capitania da Bahia"], ["Salvador"]) 

    def test_load_data_file_not_found(self):
        """Testa o carregamento com arquivo inexistente."""
        data = load_place_captaincy_data("arquivo_inexistente.txt")
        self.assertIsNone(data) 

    def test_load_data_empty_file(self):
        """Testa o carregamento de um arquivo vazio."""
        empty_file = "temp_empty_places.txt"
        open(empty_file, 'w').close()
        data = load_place_captaincy_data(empty_file)
        self.assertIsNotNone(data) 
        self.assertEqual(data, {})
        os.remove(empty_file)

    def test_search_simple_case(self):
        """Testa a busca básica de locais."""
        text = "Viajou de Santos para Olinda, passando por Salvador."
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertCountEqual(results["found_places_details"], [("Olinda", 1), ("Salvador", 1), ("Santos", 1)])
        self.assertCountEqual(results["top_captaincy"], ["Capitania da Bahia", "Capitania de Pernambuco", "Capitania de São Vicente"])
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Vicente"], 1)
        self.assertEqual(results["all_captaincy_scores"]["Capitania de Pernambuco"], 1)
        self.assertEqual(results["all_captaincy_scores"]["Capitania da Bahia"], 1)

    def test_search_case_insensitive(self):
        """Testa a busca ignorando maiúsculas/minúsculas."""
        text = "Em olinda e recife, diferente de sAlVaDoR."
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertCountEqual(results["found_places_details"], [("Olinda", 1), ("Recife", 1), ("Salvador", 1)])
        self.assertEqual(results["top_captaincy"], "Capitania de Pernambuco")
        self.assertEqual(results["all_captaincy_scores"]["Capitania de Pernambuco"], 2)
        self.assertEqual(results["all_captaincy_scores"]["Capitania da Bahia"], 1)
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Vicente"], 0)

    def test_search_multiple_occurrences(self):
        """Testa a contagem correta de múltiplas ocorrências."""
        text = "São Vicente era importante. Salvador também. Recife e Olinda. Depois voltou para São Vicente."
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertCountEqual(results["found_places_details"], [("Olinda", 1), ("Recife", 1), ("Salvador", 1), ("São Vicente", 2)])
        self.assertCountEqual(results["top_captaincy"], ["Capitania de Pernambuco", "Capitania de São Vicente"])
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Vicente"], 2)
        self.assertEqual(results["all_captaincy_scores"]["Capitania de Pernambuco"], 2)
        self.assertEqual(results["all_captaincy_scores"]["Capitania da Bahia"], 1)

    def test_search_word_boundaries(self):
        """Testa se a busca respeita limites de palavras."""
        text = "Visitou Olinda, mas não Olindana. Viu Recife e Recifense."
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertCountEqual(results["found_places_details"], [("Olinda", 1), ("Recife", 1)])
        self.assertEqual(results["top_captaincy"], "Capitania de Pernambuco")
        self.assertEqual(results["all_captaincy_scores"]["Capitania de Pernambuco"], 2)

    def test_search_longer_name_priority(self):
        """Testa se nomes mais longos são encontrados corretamente (ex: São Paulo de Piratininga vs São Paulo)."""
        temp_data_content = TEST_PLACES_DATA_CONTENT + "\nSão Paulo,Capitania de São Paulo Teste"
        temp_file = "temp_places_priority.txt"
        
        with open(temp_file, 'w', encoding='utf-8') as f: f.write(temp_data_content)
        captaincy_data = load_place_captaincy_data(temp_file)

        text = "Foi para São Paulo de Piratininga, não apenas São Paulo."
        
        results = search_colonial_places(text, captaincy_data)
        self.assertCountEqual(results["found_places_details"], [("São Paulo", 1), ("São Paulo de Piratininga", 1)])
        self.assertCountEqual(results["top_captaincy"], ["Capitania de São Paulo Teste", "Capitania de São Vicente"])
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Vicente"], 1)
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Paulo Teste"], 1)
        os.remove(temp_file)


    def test_search_no_matches(self):
        """Testa a busca em texto sem locais conhecidos."""
        text = "Um documento sobre a Europa medieval."
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertEqual(results["found_places_details"], [])
        self.assertIsNone(results["top_captaincy"])
        self.assertEqual(results["all_captaincy_scores"]["Capitania de São Vicente"], 0) 

    def test_search_empty_text(self):
        """Testa a busca com texto vazio."""
        text = ""
        
        captaincy_data = load_place_captaincy_data(TEST_PLACES_DATA_FILENAME)
        results = search_colonial_places(text, captaincy_data)
        self.assertEqual(results["found_places_details"], [])
        self.assertIsNone(results["top_captaincy"])

    def test_search_empty_data(self):
        """Testa a busca com dados de capitania vazios."""
        text = "Viajou de Santos para Olinda."
        
        results = search_colonial_places(text, {})
        self.assertEqual(results["found_places_details"], [])
        self.assertIsNone(results["top_captaincy"])
        self.assertEqual(results["all_captaincy_scores"], {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
