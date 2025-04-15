import unittest
import os
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from oxossi.extractors.names import extract_potential_names
    from oxossi.utils.data_utils import load_names_config 
    MODULES_FOUND = True
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique a estrutura do projeto e o PYTHONPATH.")
    MODULES_FOUND = False
    def extract_potential_names(text, first_names, second_names, prepositions): raise ImportError("Module not found")
    def load_names_config(file_path): raise ImportError("Module not found")

TEST_NAMES_CONFIG_FILENAME = "temp_test_names_config.json"
TEST_NAMES_CONFIG_DATA = {
  "first_names": ["Maria", "João", "Ana", "Pedro", "Paula", "António", "José", "Carlos"],
  "second_names": ["Silva", "Santos", "Pereira", "Costa", "Albuquerque", "Machado", "Andrade"],
  "prepositions": ["da", "das", "do", "dos", "de"]
}

@unittest.skipIf(not MODULES_FOUND, "Módulos principais ou utilitários não encontrados, pulando testes de nomes.")
class TestExtractPotentialNames(unittest.TestCase):
    """
    Classe de testes para a função extract_potential_names.
    """
    @classmethod
    def setUpClass(cls):
        """Cria arquivo de configuração de nomes temporário e carrega os dados."""
        try:
            with open(TEST_NAMES_CONFIG_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(TEST_NAMES_CONFIG_DATA, f, indent=4)
            print(f"\nArquivo de Configuração de Nomes de teste '{TEST_NAMES_CONFIG_FILENAME}' criado.")
            cls.FIRST_NAMES, cls.SECOND_NAMES, cls.PREPOSITIONS = load_names_config(TEST_NAMES_CONFIG_FILENAME)
            
            if not cls.FIRST_NAMES and not cls.SECOND_NAMES:
                 raise unittest.SkipTest("Não foi possível carregar a configuração de nomes de teste.")
             
        except Exception as e:
            print(f"Falha ao criar/carregar Config de Nomes de teste: {e}")
            raise unittest.SkipTest(f"Não foi possível criar/carregar Config de Nomes de teste: {e}")

    @classmethod
    def tearDownClass(cls):
        """Remove o arquivo de configuração temporário."""
        if os.path.exists(TEST_NAMES_CONFIG_FILENAME):
            os.remove(TEST_NAMES_CONFIG_FILENAME)
            print(f"Arquivo de Configuração de Nomes de teste '{TEST_NAMES_CONFIG_FILENAME}' removido.")

    def test_nome_simples(self):
        """Testa a extração de um nome simples (Primeiro + Último)."""
        text = "O João Silva foi à loja."
        
        expected = ["João Silva"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_multiplos_nomes(self):
        """Testa a extração de múltiplos nomes no mesmo texto."""
        text = "Maria Santos encontrou Pedro Pereira."
        
        expected = ["Maria Santos", "Pedro Pereira"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertCountEqual(result, expected)
        
    def test_nome_com_preposicao(self):
        """Testa a extração de nomes contendo preposições."""
        text = "A Ana da Costa chegou."
        expected = ["Ana da Costa"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_com_multiplas_preposicoes_e_nomes(self):
        """Testa nomes com múltiplas preposições e nomes."""
        text = "Chegou João Pedro da Silva Costa."

        expected = ["João Pedro da Silva"] 
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

        text2 = "Carlos de Andrade foi visto."
        
        expected2 = ["Carlos de Andrade"]
        result2 = extract_potential_names(text2, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result2, expected2)


    def test_nome_composto_primeiro(self):
        """Testa nomes onde o primeiro nome é composto (ex: Ana Paula)."""
        text = "Ana Paula Machado estava lá."
        expected = ["Ana Paula Machado"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_sem_nomes_no_texto(self):
        """Testa um texto que não contém nomes reconhecidos."""
        text = "O cão correu pelo parque."
        
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_texto_vazio(self):
        """Testa a função com uma string de texto vazia."""
        text = ""
        
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_terminado_em_preposicao_invalido(self):
        """Testa se nomes terminados em preposição são ignorados."""
        text = "O António de foi visto."
        
        expected = [] 
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_apenas_primeiro_nome(self):
        """Testa se um primeiro nome isolado é extraído (a lógica atual permite isso)."""
        text = "Pedro estava sozinho."
        
        expected = ["Pedro"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_apenas_segundo_nome_ignorado(self):
        """Testa se um segundo nome isolado é ignorado (pois não começa com nome próprio)."""
        text = "O Silva chegou."
        
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_no_inicio_texto(self):
        """Testa um nome que aparece no início do texto."""
        text = "José Santos foi o primeiro."
        
        expected = ["José Santos"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_no_fim_texto(self):
        """Testa um nome que aparece no final do texto."""
        text = "O último a sair foi Pedro Silva"
        
        expected = ["Pedro Silva"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_com_pontuacao_adjacente(self):
        """Testa o comportamento com pontuação adjacente."""
        text = "Vi a Maria Santos, ela estava bem. E o João Pereira? Também."

        expected = ["Maria Santos", "João Pereira"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertCountEqual(result, expected)

    def test_case_sensitivity_nomes(self):
        """Testa a sensibilidade a maiúsculas/minúsculas nos nomes."""
        text = "O joão silva estava lá, mas a ANA PEREIRA não."
        
        expected = ["Ana Pereira"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_case_sensitivity_preposicoes(self):
        """Testa a sensibilidade a maiúsculas/minúsculas nas preposições."""
        text = "Chegou Ana Da Costa."
        
        expected = ["Ana"]
        result = extract_potential_names(text, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result, expected)

        text_correto = "Chegou Ana da Costa."
        
        expected_correto = ["Ana da Costa"]
        result_correto = extract_potential_names(text_correto, self.FIRST_NAMES, self.SECOND_NAMES, self.PREPOSITIONS)
        self.assertEqual(result_correto, expected_correto)

if __name__ == '__main__':
    unittest.main(verbosity=2)
