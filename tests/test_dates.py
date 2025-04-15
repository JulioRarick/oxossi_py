import unittest
import os
import numpy as np
import fitz 
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.dates import extract_and_analyze_dates, _load_date_config
    from oxossi.utils.pdf_utils import extract_text_from_pdf
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    
    MODULES_FOUND = False
    
    def extract_text_from_pdf(pdf_path): raise ImportError("Module not found")
    def extract_and_analyze_dates(text, config): raise ImportError("Module not found")
    def _load_date_config(config_path): raise ImportError("Module not found")


TEST_PDF_FILENAME = "temp_test_dates_document.pdf"
TEST_PDF_TEXT_PAGE1 = "Texto da página 1 com o ano 1750 e início do século XVII."
TEST_PDF_TEXT_PAGE2 = "Continuação na página 2 sobre meados do século XVIII e o ano 1810."
TEST_CONFIG_FILENAME = "temp_test_date_config.json"
TEST_CONFIG_DATA = {
  "century_map": { "xvi": 1500, "xvii": 1600, "xviii": 1700, "xix": 1800, "seiscentos": 1600, "setecentos": 1700, "oitocentos": 1800 },
  "part_map": { "primeira metade": [0, 50], "início": [0, 30], "segunda metade": [50, 100], "final": [70, 100], "meados": [40, 60] },
  "regex_patterns": {
    "year": "\\b(?P<year>1[5-8]\\d{2})\\b",
    "textual_phrase": "\\b(?P<part>primeira\\s+metade|segunda\\s+metade|in[íi]cio[s]?|come[çc]o|finais|final|fim|meados)?(?:\\s+(?:de|do|da|dos|das)\\s+)?(?P<century>s[ée]culo\\s+(?:xvi|xvii|xviii|xix)|quinhentos|seiscentos|setecentos|oitocentos)\\b"
  }
}

@unittest.skipIf(not MODULES_FOUND, "Módulos principais ou utilitários não encontrados, pulando testes de datas.")
class TestDateExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Cria arquivos temporários de PDF e Configuração antes de todos os testes."""
        try:
            doc = fitz.open()
            page1 = doc.new_page(width=595, height=842)
            page1.insert_text((72, 72), TEST_PDF_TEXT_PAGE1, fontsize=11)
            page2 = doc.new_page(width=595, height=842)
            page2.insert_text((72, 72), TEST_PDF_TEXT_PAGE2, fontsize=11)
            doc.save(TEST_PDF_FILENAME)
            doc.close()
            print(f"\nArquivo PDF de teste '{TEST_PDF_FILENAME}' criado.")
        except Exception as e:
            print(f"Falha ao criar PDF de teste: {e}")
            raise unittest.SkipTest(f"Não foi possível criar PDF de teste: {e}")
        try:
            with open(TEST_CONFIG_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(TEST_CONFIG_DATA, f, indent=4)
            print(f"Arquivo de Configuração de teste '{TEST_CONFIG_FILENAME}' criado.")
            
            cls.date_config = _load_date_config(TEST_CONFIG_FILENAME)
            if not cls.date_config:
                 raise unittest.SkipTest("Não foi possível carregar a configuração de teste.")
        except Exception as e:
            print(f"Falha ao criar/carregar Config de teste: {e}")
            
            if os.path.exists(TEST_PDF_FILENAME): os.remove(TEST_PDF_FILENAME) 
            raise unittest.SkipTest(f"Não foi possível criar/carregar Config de teste: {e}")


    @classmethod
    def tearDownClass(cls):
        """Remove os arquivos temporários após todos os testes."""
        if os.path.exists(TEST_PDF_FILENAME):
            os.remove(TEST_PDF_FILENAME)
            print(f"Arquivo PDF de teste '{TEST_PDF_FILENAME}' removido.")
        if os.path.exists(TEST_CONFIG_FILENAME):
            os.remove(TEST_CONFIG_FILENAME)
            print(f"Arquivo de Configuração de teste '{TEST_CONFIG_FILENAME}' removido.")

    def test_pdf_extraction_success(self):
        """Testa a extração de texto de um PDF válido usando o utilitário."""
        
        extracted_text = extract_text_from_pdf(TEST_PDF_FILENAME)
        
        self.assertIsNotNone(extracted_text)
        self.assertIn(TEST_PDF_TEXT_PAGE1, extracted_text)
        self.assertIn(TEST_PDF_TEXT_PAGE2, extracted_text)
        expected_combined = TEST_PDF_TEXT_PAGE1 + "\n" + TEST_PDF_TEXT_PAGE2 + "\n"
        self.assertEqual(extracted_text.strip(), expected_combined.strip())

    def test_pdf_extraction_nonexistent_file(self):
        """Testa extração com caminho de PDF inexistente."""
        extracted_text = extract_text_from_pdf("arquivo_que_nao_existe.pdf")
        self.assertIsNone(extracted_text)

    def test_pdf_extraction_invalid_path(self):
        """Testa extração com caminho inválido (None ou vazio)."""
        self.assertIsNone(extract_text_from_pdf(None))
        self.assertIsNone(extract_text_from_pdf(""))

    def test_analysis_numeric_years_only(self):
        """Testa análise quando apenas anos numéricos estão presentes."""
        text = "Eventos em 1650, 1688 e 1720."
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertListEqual(result['direct_numeric_years'], [1650, 1688, 1720])
        self.assertListEqual(result['calculated_textual_intervals'], [])
        self.assertListEqual(result['combined_representative_years'], [1650, 1688, 1720])
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['minimum'], 1650)
        self.assertEqual(result['maximum'], 1720)
        self.assertAlmostEqual(result['mean'], (1650 + 1688 + 1720) / 3)
        self.assertEqual(result['median'], 1688)

    def test_analysis_textual_dates_only(self):
        """Testa análise quando apenas frases textuais estão presentes."""
        text = "Relatos do início do século XVII e de meados do século XVIII."
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertListEqual(result['direct_numeric_years'], [])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1630), (1740, 1760)])       
        self.assertListEqual(result['combined_representative_years'], [1615, 1750])
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['minimum'], 1615)
        self.assertEqual(result['maximum'], 1750)

    def test_analysis_mixed_dates(self):
        """Testa análise com mistura de anos numéricos e frases textuais."""
        text = "Aconteceu em 1710, durante a primeira metade do século XVIII, e novamente em 1795."
        
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertListEqual(result['direct_numeric_years'], [1710, 1795])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1700, 1750)])      
        self.assertListEqual(result['combined_representative_years'], [1710, 1725, 1795])
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['minimum'], 1710)
        self.assertEqual(result['maximum'], 1795)
        self.assertEqual(result['median'], 1725)

    def test_analysis_full_century(self):
        """Testa análise quando apenas o século é mencionado."""
        text = "Artefatos do século XVII."
        
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertListEqual(result['direct_numeric_years'], [])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1700)])
        self.assertListEqual(result['combined_representative_years'], [1650])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['minimum'], 1650)
        self.assertEqual(result['maximum'], 1650)
        self.assertEqual(result['mean'], 1650)
        self.assertEqual(result['median'], 1650)
        self.assertEqual(result['standard_deviation'], 0.0)

    def test_analysis_no_dates(self):
        """Testa comportamento da análise quando nenhuma data relevante é encontrada."""
        text = "Um texto descritivo sem referências cronológicas claras."
        
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertEqual(result['count'], 0)
        self.assertListEqual(result['direct_numeric_years'], [])
        self.assertListEqual(result['calculated_textual_intervals'], [])
        self.assertListEqual(result['combined_representative_years'], [])
        self.assertIsNone(result['minimum'])
        self.assertIsNone(result['maximum'])
        self.assertIsNone(result['mean'])
        self.assertIsNone(result['median'])
        self.assertIsNone(result['standard_deviation'])

    def test_analysis_duplicate_textual_phrases(self):
        """Testa se frases textuais duplicadas geram apenas um intervalo."""
        text = "No início do século XVII e novamente no início do século XVII."
        
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1630)]) 
        self.assertListEqual(result['combined_representative_years'], [1615])
        self.assertEqual(result['count'], 1)

    def test_analysis_case_insensitivity_and_accents(self):
        """Testa insensibilidade a maiúsculas/minúsculas e acentos comuns."""
        text = "SÉCULO XVI e inicio do seculo xviii. Ano 1777."
        
        result = extract_and_analyze_dates(text, self.date_config)
        self.assertListEqual(result['direct_numeric_years'], [1777])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1500, 1600), (1700, 1730)])
        self.assertListEqual(result['combined_representative_years'], [1550, 1715, 1777])
        self.assertEqual(result['count'], 3)

    def test_integration_pdf_to_analysis(self):
        """Testa o fluxo completo: extrair texto do PDF e analisá-lo."""
        extracted_text = extract_text_from_pdf(TEST_PDF_FILENAME)
        self.assertIsNotNone(extracted_text)

        result = extract_and_analyze_dates(extracted_text, self.date_config)

        self.assertListEqual(result['direct_numeric_years'], [1750, 1810])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1630), (1740, 1760)])
        self.assertListEqual(result['combined_representative_years'], [1615, 1750, 1810])
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['minimum'], 1615)
        self.assertEqual(result['maximum'], 1810)
        self.assertEqual(result['median'], 1750)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDateExtractor))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
