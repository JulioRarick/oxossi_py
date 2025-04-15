import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock 
import subprocess

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.references import extract_references_with_anystyle, _format_reference
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    MODULES_FOUND = False
    def extract_references_with_anystyle(pdf_path): raise ImportError("Module not found")
    def _format_reference(item): raise ImportError("Module not found")

TEST_PDF_FILENAME_REFS = "temp_test_refs_document.pdf" 
MOCK_ANYSTYLE_OUTPUT_VALID = """
[
  {"type": "article-journal", "title": ["An Example Title"], "author": [{"family": "Silva", "given": "João A."}], "date": ["2023"], "container-title": ["Journal of Examples"]},
  {"type": "book", "title": ["Another Book"], "author": [{"family": "Santos", "given": "Maria B."}], "date": ["2022"], "publisher": ["Publisher X"]},
  {"author": [{"family": "Costa"}], "date": ["2021"]},
  {"title": ["Only Title"], "date": ["2020"]},
  {}
]
"""
MOCK_ANYSTYLE_OUTPUT_INVALID_JSON = """
[
  {"type": "article", "title": ["Good"], "author": [{"family": "Ok"}]},
  {"invalid json...
]
"""
MOCK_ANYSTYLE_OUTPUT_NOT_LIST = '{"message": "Not a list output"}'

@unittest.skipIf(not MODULES_FOUND, "Módulos principais ou utilitários não encontrados, pulando testes de referências.")
class TestReferenceExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Cria um arquivo PDF vazio apenas para testar a verificação de existência."""
        try:
            with open(TEST_PDF_FILENAME_REFS, 'w') as f:
                f.write("")
            print(f"\nArquivo PDF de teste (vazio) '{TEST_PDF_FILENAME_REFS}' criado.")
        except Exception as e:
             print(f"Falha ao criar PDF de teste (vazio): {e}")
             pass

    @classmethod
    def tearDownClass(cls):
        """Remove o arquivo PDF vazio."""
        if os.path.exists(TEST_PDF_FILENAME_REFS):
            os.remove(TEST_PDF_FILENAME_REFS)
            print(f"Arquivo PDF de teste (vazio) '{TEST_PDF_FILENAME_REFS}' removido.")

    def test_format_reference_full(self):
        """Testa a formatação de uma referência completa."""
        item = {"author": [{"family": "Silva", "given": "João A."}], "date": ["2023"], "title": ["An Example Title"]}
        expected = "Silva,J. (2023) An Example Title..." 
        self.assertEqual(_format_reference(item), expected)

    def test_format_reference_no_given_name(self):
        """Testa formatação quando falta o 'given' name."""
        item = {"author": [{"family": "Costa"}], "date": ["2021"], "title": ["Some Work"]}
        expected = "Costa. (2021) Some Work..."
        self.assertEqual(_format_reference(item), expected)

    def test_format_reference_no_date(self):
        """Testa formatação quando falta a data."""
        item = {"author": [{"family": "Santos", "given": "Maria"}], "title": ["A Title"]}
        expected = "Santos,M. (-) A Title..."
        self.assertEqual(_format_reference(item), expected)

    def test_format_reference_no_title(self):
        """Testa formatação quando falta o título."""
        item = {"author": [{"family": "Pereira", "given": "Carlos"}], "date": ["2020"]}
        expected = "Pereira,C. (2020) -" 
        self.assertEqual(_format_reference(item), expected)

    def test_format_reference_no_author(self):
        """Testa que retorna None se não houver autor."""
        item = {"title": ["Only Title"], "date": ["2019"]}
        self.assertIsNone(_format_reference(item))

    def test_format_reference_empty_or_invalid(self):
        """Testa com dados de entrada inválidos ou vazios."""
        self.assertIsNone(_format_reference({}))
        self.assertIsNone(_format_reference({"author": [], "title": [], "date": []}))
        self.assertIsNone(_format_reference({"author": [{"given": "Ana"}]}))

    @patch('subprocess.run') 
    def test_extract_success(self, mock_subprocess_run):
        """Testa extração bem-sucedida simulando a saída do anystyle."""
        mock_result = MagicMock()
        mock_result.stdout = MOCK_ANYSTYLE_OUTPUT_VALID
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        references = extract_references_with_anystyle(TEST_PDF_FILENAME_REFS)

        mock_subprocess_run.assert_called_once_with(
            ["anystyle", "find", TEST_PDF_FILENAME_REFS],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        self.assertIsNotNone(references)
        self.assertIsInstance(references, list)
        self.assertEqual(len(references), 5)
        self.assertEqual(references[0]['title'], ["An Example Title"])

    @patch('subprocess.run')
    def test_extract_anystyle_not_found(self, mock_subprocess_run):
        """Testa o que acontece se o comando 'anystyle' não for encontrado."""
        mock_subprocess_run.side_effect = FileNotFoundError("Comando 'anystyle' não encontrado")

        references = extract_references_with_anystyle(TEST_PDF_FILENAME_REFS)
        self.assertIsNone(references)
        mock_subprocess_run.assert_called_once() 

    @patch('subprocess.run')
    def test_extract_anystyle_error(self, mock_subprocess_run):
        """Testa o que acontece se o anystyle retornar um erro."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["anystyle", "find", "..."], stderr="Algum erro do anystyle"
        )

        references = extract_references_with_anystyle(TEST_PDF_FILENAME_REFS)
        self.assertIsNone(references)
        mock_subprocess_run.assert_called_once()

    @patch('subprocess.run')
    def test_extract_invalid_json_output(self, mock_subprocess_run):
        """Testa o que acontece se a saída do anystyle não for JSON válido."""
        mock_result = MagicMock()
        mock_result.stdout = MOCK_ANYSTYLE_OUTPUT_INVALID_JSON
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        references = extract_references_with_anystyle(TEST_PDF_FILENAME_REFS)
        self.assertIsNone(references)
        mock_subprocess_run.assert_called_once()

    @patch('subprocess.run')
    def test_extract_json_output_not_list(self, mock_subprocess_run):
        """Testa o que acontece se a saída JSON não for uma lista."""
        mock_result = MagicMock()
        mock_result.stdout = MOCK_ANYSTYLE_OUTPUT_NOT_LIST
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        references = extract_references_with_anystyle(TEST_PDF_FILENAME_REFS)
        self.assertIsNone(references)
        mock_subprocess_run.assert_called_once()

    def test_extract_pdf_not_found(self):
        """Testa a extração quando o arquivo PDF não existe (sem mock)."""
        references = extract_references_with_anystyle("pdf_que_nao_existe.pdf")
        self.assertIsNone(references)


if __name__ == '__main__':
    unittest.main(verbosity=2)
