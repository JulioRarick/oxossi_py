import unittest
import os
import sys
import json
import fitz
from pathlib import Path
from unittest.mock import patch, mock_open

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.utils.pdf_utils import extract_text_from_pdf
    from oxossi.utils.data_utils import load_json_data, load_names_config, load_themes_config
    from oxossi.utils.output_utils import format_and_output_json
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos de utils: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    MODULES_FOUND = False
    def extract_text_from_pdf(pdf_path): raise ImportError("Module not found")
    def load_json_data(file_path): raise ImportError("Module not found")
    def load_names_config(file_path): raise ImportError("Module not found")
    def load_themes_config(file_path): raise ImportError("Module not found")
    def format_and_output_json(data, status, message, output_file): raise ImportError("Module not found")

TEST_PDF_UTIL_FILENAME = "temp_util_test_doc.pdf"
TEST_PDF_UTIL_TEXT = "Texto de teste para PDF."
TEST_JSON_UTIL_FILENAME = "temp_util_test_data.json"
TEST_JSON_UTIL_DATA = {"chave": "valor", "lista": [1, 2, 3]}
TEST_OUTPUT_FILENAME = "temp_util_output.json"

@unittest.skipIf(not MODULES_FOUND, "Módulos utilitários não encontrados, pulando testes de utils.")
class TestUtils(unittest.TestCase):

    def setUp(self):
        """Cria arquivos temporários antes de cada teste (se necessário)."""
        try:
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), TEST_PDF_UTIL_TEXT, fontsize=11)
            doc.save(TEST_PDF_UTIL_FILENAME)
            doc.close()
        except Exception:
            pass 

        try:
            with open(TEST_JSON_UTIL_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(TEST_JSON_UTIL_DATA, f, indent=4)
        except Exception:
            pass 

    def tearDown(self):
        """Remove arquivos temporários após cada teste."""
        if os.path.exists(TEST_PDF_UTIL_FILENAME):
            os.remove(TEST_PDF_UTIL_FILENAME)
        if os.path.exists(TEST_JSON_UTIL_FILENAME):
            os.remove(TEST_JSON_UTIL_FILENAME)
        if os.path.exists(TEST_OUTPUT_FILENAME):
            os.remove(TEST_OUTPUT_FILENAME)

    def test_pdf_util_extract_success(self):
        """Testa extração bem-sucedida de PDF."""
        text = extract_text_from_pdf(TEST_PDF_UTIL_FILENAME)
        self.assertIsNotNone(text)
        self.assertIn(TEST_PDF_UTIL_TEXT.strip(), text.strip())

    def test_pdf_util_file_not_found(self):
        """Testa extração de PDF inexistente."""
        text = extract_text_from_pdf("nao_existe.pdf")
        self.assertIsNone(text)

    def test_json_util_load_success(self):
        """Testa carregamento bem-sucedido de JSON."""
        data = load_json_data(TEST_JSON_UTIL_FILENAME)
        self.assertIsNotNone(data)
        self.assertEqual(data, TEST_JSON_UTIL_DATA)

    def test_json_util_file_not_found(self):
        """Testa carregamento de JSON inexistente."""
        data = load_json_data("nao_existe.json")
        self.assertIsNone(data)

    def test_json_util_invalid_json(self):
        """Testa carregamento de arquivo com JSON inválido."""
        invalid_json_file = "temp_invalid.json"
        with open(invalid_json_file, 'w') as f:
            f.write('{"chave": "valor",') 
        data = load_json_data(invalid_json_file)
        self.assertIsNone(data)
        os.remove(invalid_json_file)

    @patch('builtins.print') 
    def test_output_util_print_only(self, mock_print):
        """Testa a formatação e impressão no console."""
        test_data = {"resultado": "ok"}
        format_and_output_json(test_data, status="Teste", message="Funcionou")
       
        self.assertGreater(mock_print.call_count, 1)
        
        found = False
        
        expected_json_str = json.dumps({"status": "Teste", "message": "Funcionou", "results": test_data}, indent=4, ensure_ascii=False)
        for call in mock_print.call_args_list:
            args, kwargs = call
            if args and expected_json_str in args[0]:
                found = True
                break
        self.assertTrue(found, "String JSON formatada não encontrada na saída do print")

    @patch('builtins.print') 
    def test_output_util_save_to_file(self, mock_print):
        """Testa a formatação e salvamento em arquivo."""
        test_data = {"contagem": 5}
        format_and_output_json(test_data, status="OK", message="Salvo", output_file=TEST_OUTPUT_FILENAME)

        self.assertTrue(os.path.exists(TEST_OUTPUT_FILENAME))
        try:
            with open(TEST_OUTPUT_FILENAME, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data["status"], "OK")
            self.assertEqual(saved_data["message"], "Salvo")
            self.assertEqual(saved_data["results"], test_data)
        finally:
            if os.path.exists(TEST_OUTPUT_FILENAME):
                os.remove(TEST_OUTPUT_FILENAME) 
                
    @patch('builtins.print')
    @patch('json.dumps')
    
    def test_output_util_serialization_error(self, mock_json_dumps, mock_print):
        """Testa o tratamento de erro de serialização JSON."""
        mock_json_dumps.side_effect = TypeError("Não posso serializar isso")
        test_data = {"conjunto": {"a", "b"}} # Set não é serializável
        format_and_output_json(test_data, status="Erro", message="Dado inválido")

        found_error_msg = False
        for call in mock_print.call_args_list:
            args, kwargs = call
            if args and "Falha ao serializar resultados para JSON" in args[0]:
                found_error_msg = True
                break
        self.assertTrue(found_error_msg)

    @patch('builtins.print')
    @patch('builtins.open', mock_open()) 
    @patch('os.path.exists', return_value=True) 
    def test_output_util_save_io_error(self, mock_exists, mock_file_open, mock_print):
        """Testa o tratamento de erro ao salvar o arquivo."""
        mock_file_open.return_value.write.side_effect = IOError("Permissão negada")

        test_data = {"id": 1}
        format_and_output_json(test_data, status="Sucesso", message="...", output_file="arquivo_protegido.json")

        self.assertGreater(mock_print.call_count, 0)



if __name__ == '__main__':
    unittest.main(verbosity=2)
