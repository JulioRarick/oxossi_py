import unittest
import os
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.themes import analyze_text_themes
    from oxossi.utils.data_utils import load_themes_config
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    MODULES_FOUND = False
    def analyze_text_themes(text, theme_groups): raise ImportError("Module not found")
    def load_themes_config(file_path): raise ImportError("Module not found")

TEST_THEMES_CONFIG_FILENAME = "temp_test_themes_config.json"
TEST_THEMES_CONFIG_DATA = {
  "Economia": ["gado", "comércio", "açúcar", "preço"],
  "Política": ["poder", "rei", "câmara", "lei"],
  "Geografia": ["vila", "rio", "caminho"]
}

@unittest.skipIf(not MODULES_FOUND, "Módulos principais ou utilitários não encontrados, pulando testes de temas.")
class TestThemeExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Cria arquivo de configuração de temas temporário e carrega os dados."""
        try:
            with open(TEST_THEMES_CONFIG_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(TEST_THEMES_CONFIG_DATA, f, indent=4)
            print(f"\nArquivo de Configuração de Temas de teste '{TEST_THEMES_CONFIG_FILENAME}' criado.")
            cls.theme_groups = load_themes_config(TEST_THEMES_CONFIG_FILENAME)
            if not cls.theme_groups:
                 raise unittest.SkipTest("Não foi possível carregar a configuração de temas de teste.")
        except Exception as e:
            print(f"Falha ao criar/carregar Config de Temas de teste: {e}")
            raise unittest.SkipTest(f"Não foi possível criar/carregar Config de Temas de teste: {e}")

    @classmethod
    def tearDownClass(cls):
        """Remove o arquivo de configuração temporário."""
        if os.path.exists(TEST_THEMES_CONFIG_FILENAME):
            os.remove(TEST_THEMES_CONFIG_FILENAME)
            print(f"Arquivo de Configuração de Temas de teste '{TEST_THEMES_CONFIG_FILENAME}' removido.")

    def test_analyze_simple_counts(self):
        """Testa a contagem básica de palavras-chave."""
        text = "O comércio de gado e açúcar floresceu. O poder do rei aumentou na câmara."
        
        results = analyze_text_themes(text, self.theme_groups)

        self.assertEqual(results["theme_counts"]["Economia"], 3) 
        self.assertEqual(results["theme_counts"]["Política"], 3) 
        self.assertEqual(results["theme_counts"]["Geografia"], 0)
        self.assertEqual(results["keyword_counts"]["comércio"], 1)
        self.assertEqual(results["keyword_counts"]["gado"], 1)
        self.assertEqual(results["keyword_counts"]["açúcar"], 1)
        self.assertEqual(results["keyword_counts"]["poder"], 1)
        self.assertEqual(results["keyword_counts"]["rei"], 1)
        self.assertEqual(results["keyword_counts"]["câmara"], 1)
        self.assertNotIn("preço", results["keyword_counts"])

        self.assertEqual(results["total_keywords_found"], 6)

    def test_analyze_case_insensitivity(self):
        """Testa se a contagem ignora maiúsculas/minúsculas."""
        text = "O Gado era importante para o Comércio. A Lei e o Poder."
        
        results = analyze_text_themes(text, self.theme_groups)

        self.assertEqual(results["theme_counts"]["Economia"], 2) 
        self.assertEqual(results["theme_counts"]["Política"], 2)
        self.assertEqual(results["keyword_counts"]["gado"], 1)
        self.assertEqual(results["keyword_counts"]["comércio"], 1)
        self.assertEqual(results["keyword_counts"]["lei"], 1)
        self.assertEqual(results["keyword_counts"]["poder"], 1)
        self.assertEqual(results["total_keywords_found"], 4)

    def test_analyze_percentages_and_top_theme(self):
        """Testa o cálculo de percentuais e a identificação do tema principal."""
        text = "Muito comércio, muito gado. Pouco poder."
        
        results = analyze_text_themes(text, self.theme_groups)

        self.assertEqual(results["theme_counts"]["Economia"], 2)
        self.assertEqual(results["theme_counts"]["Política"], 1)
        self.assertEqual(results["total_keywords_found"], 3)
        self.assertAlmostEqual(results["theme_percentages"]["Economia"], 66.67, places=2)
        self.assertAlmostEqual(results["theme_percentages"]["Política"], 33.33, places=2)
        self.assertAlmostEqual(results["theme_percentages"]["Geografia"], 0.0, places=2)
        self.assertEqual(results["top_theme"], "Economia")

    def test_analyze_top_theme_tie(self):
        """Testa o caso de empate no tema principal."""
        text = "Comércio e poder. Gado e rei."
        
        results = analyze_text_themes(text, self.theme_groups)

        self.assertEqual(results["theme_counts"]["Economia"], 2)
        self.assertEqual(results["theme_counts"]["Política"], 2)
        self.assertEqual(results["total_keywords_found"], 4)
        self.assertCountEqual(results["top_theme"], ["Economia", "Política"])
        self.assertAlmostEqual(results["theme_percentages"]["Economia"], 50.0, places=2)
        self.assertAlmostEqual(results["theme_percentages"]["Política"], 50.0, places=2)

    def test_analyze_no_matches(self):
        """Testa quando nenhuma palavra-chave é encontrada."""
        text = "Texto completamente diferente sem termos relevantes."
        results = analyze_text_themes(text, self.theme_groups)

        self.assertEqual(results["theme_counts"]["Economia"], 0)
        self.assertEqual(results["theme_counts"]["Política"], 0)
        self.assertEqual(results["theme_counts"]["Geografia"], 0)
        self.assertEqual(results["keyword_counts"], {})
        self.assertEqual(results["total_keywords_found"], 0)
        self.assertIsNone(results["top_theme"])
        self.assertEqual(results["theme_percentages"]["Economia"], 0.0)

    def test_analyze_empty_text(self):
        """Testa com texto de entrada vazio."""
        text = ""
        results = analyze_text_themes(text, self.theme_groups)
        self.assertEqual(results["total_keywords_found"], 0)
        self.assertIsNone(results["top_theme"])

    def test_analyze_empty_themes(self):
        """Testa com configuração de temas vazia."""
        text = "Comércio e poder."
        results = analyze_text_themes(text, {})
        self.assertEqual(results["total_keywords_found"], 0)
        self.assertIsNone(results["top_theme"])
        self.assertEqual(results["theme_counts"], {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
