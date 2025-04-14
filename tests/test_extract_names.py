import unittest
from ox_extract_names import extract_potential_names

class TestExtractPotentialNames(unittest.TestCase):
    """
    Classe de testes para a função extract_potential_names.
    """
    PREPOSITIONS = {"da", "das", "do", "dos", "de"}
    FIRST_NAMES_SAMPLE = {"Maria", "João", "Ana", "Pedro", "Paula", "António", "José"}
    SECOND_NAMES_SAMPLE = {"Silva", "Santos", "Pereira", "Costa", "Albuquerque", "Machado"}

    def test_nome_simples(self):
        """Testa a extração de um nome simples (Primeiro + Último)."""
        text = "O João Silva foi à loja."
        expected = ["João Silva"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_multiplos_nomes(self):
        """Testa a extração de múltiplos nomes no mesmo texto."""
        text = "Maria Santos encontrou Pedro Pereira."
        expected = ["Maria Santos", "Pedro Pereira"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertCountEqual(result, expected) 

    def test_nome_com_preposicao(self):
        """Testa a extração de nomes contendo preposições."""
        text = "A Ana da Costa chegou."
        expected = ["Ana da Costa"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_com_multiplas_preposicoes(self):
        """Testa nomes com múltiplas preposições e nomes."""
        text = "Chegou João Pedro da Silva e Costa."
    
        second_names_extended = self.SECOND_NAMES_SAMPLE | {"Costa"}
        expected = ["João Pedro da Silva"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, second_names_extended, self.PREPOSITIONS)
        self.assertEqual(result, expected)
 

    def test_nome_composto_primeiro(self):
        """Testa nomes onde o primeiro nome é composto (ex: Ana Paula)."""
        text = "Ana Paula Machado estava lá."
        expected = ["Ana Paula Machado"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_sem_nomes_no_texto(self):
        """Testa um texto que não contém nomes reconhecidos."""
        text = "O cão correu pelo parque."
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_texto_vazio(self):
        """Testa a função com uma string de texto vazia."""
        text = ""
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_terminado_em_preposicao_invalido(self):
        """Testa se nomes terminados em preposição são ignorados."""
        text = "O António de foi visto."
        expected = [] 
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_apenas_primeiro_nome(self):
        """Testa se um primeiro nome isolado é extraído."""
        text = "Pedro estava sozinho."
        expected = ["Pedro"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_apenas_segundo_nome_ignorado(self):
        """Testa se um segundo nome isolado é ignorado (pois não começa com nome próprio)."""
        text = "O Silva chegou."
        expected = []
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_no_inicio_texto(self):
        """Testa um nome que aparece no início do texto."""
        text = "José Santos foi o primeiro."
        expected = ["José Santos"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_no_fim_texto(self):
        """Testa um nome que aparece no final do texto."""
        text = "O último a sair foi Pedro Silva"
        expected = ["Pedro Silva"]
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

    def test_nome_com_pontuacao_adjacente(self):
        """Testa o comportamento com pontuação (baseado no split() simples)."""
        text = "Vi a Maria Santos, ela estava bem."
        expected = ["Maria Santos"] 
        result_actual_split = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        
        self.assertEqual(result_actual_split, [])

        text_sem_virgula = "Vi a Maria Santos . Ela estava bem."
        expected_sem_virgula = ["Maria Santos"]
        result_sem_virgula = extract_potential_names(text_sem_virgula, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result_sem_virgula, expected_sem_virgula)


    def test_case_sensitivity(self):
        """Testa a sensibilidade a maiúsculas/minúsculas."""
        text = "O joão silva estava lá." 
        expected = [] 
        result = extract_potential_names(text, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result, expected)

        text_correto = "O João Silva estava lá."
        expected_correto = ["João Silva"]
        result_correto = extract_potential_names(text_correto, self.FIRST_NAMES_SAMPLE, self.SECOND_NAMES_SAMPLE, self.PREPOSITIONS)
        self.assertEqual(result_correto, expected_correto)


if __name__ == '__main__':
    unittest.main(verbosity=2) 
