# ox_extract_names.py

Este script Python foi projetado para extrair potenciais nomes completos de pessoas a partir de arquivos de texto (`.txt`) ou PDF (`.pdf`). Ele utiliza listas pré-definidas de primeiros nomes, sobrenomes e preposições (como "da", "de", "do") para identificar sequências de palavras que provavelmente formam um nome.

## Dependências

O script utiliza as seguintes bibliotecas:

1.  **`json`**: Para ler e processar o arquivo `names.json` que contém as listas de nomes e preposições. (Biblioteca padrão do Python)
2.  **`os`**: Para manipulação de caminhos de arquivos (encontrar o diretório do script, juntar caminhos). (Biblioteca padrão do Python)
3.  **`argparse`**: Para processar argumentos passados pela linha de comando (neste caso, o caminho do arquivo de entrada). (Biblioteca padrão do Python)
4.  **`PyPDF2`**: Para extrair texto de arquivos PDF. Esta é uma dependência externa e precisa ser instalada.
    * **Instalação:** Se não estiver instalada, o script exibirá uma mensagem de erro e terminará. Instale-a usando o pip:
        ```bash
        pip install PyPDF2
        ```

## Estrutura do Código

O código é dividido em várias funções e um bloco principal de execução.

### Função: `load_names_from_json`

* **Propósito:** Carregar as listas de primeiros nomes, sobrenomes e preposições de um arquivo JSON especificado.
* **Parâmetros:**
    * `file_path` (str): O caminho para o arquivo JSON (`names.json`).
* **Retorno:** Uma tupla contendo três conjuntos (`set`):
    1.  `first_names`: Conjunto de primeiros nomes (capitalizados).
    2.  `second_names`: Conjunto de sobrenomes (capitalizados).
    3.  `prepositions`: Conjunto de preposições (em minúsculas).
* **Funcionamento:**
    1.  Tenta abrir e ler o arquivo JSON no caminho especificado.
    2.  Usa `json.load` para converter o conteúdo JSON em um dicionário Python.
    3.  Extrai as listas associadas às chaves `"first_names"`, `"second_names"` e `"prepositions"`. Se uma chave não existir, usa uma lista vazia como padrão (exceto para preposições, que tem um padrão definido).
    4.  Converte todos os nomes (primeiros e segundos) para o formato capitalizado (primeira letra maiúscula, resto minúsculo) e armazena-os em conjuntos (`set`) para busca eficiente.
    5.  Armazena as preposições (em minúsculas) em um conjunto.
    6.  Imprime mensagens de status sobre o carregamento.
    7.  Inclui tratamento de erros para `FileNotFoundError` (arquivo não encontrado), `json.JSONDecodeError` (JSON inválido) e outras exceções inesperadas. Em caso de erro, retorna conjuntos vazios.

### Função: `extract_text_from_pdf`

* **Propósito:** Extrair todo o texto contido em um arquivo PDF.
* **Parâmetros:**
    * `pdf_path` (str): O caminho para o arquivo PDF.
* **Retorno:**
    * Uma string contendo todo o texto extraído do PDF.
    * `None` se ocorrer um erro durante a leitura (arquivo não encontrado, corrompido, protegido por senha, etc.).
* **Funcionamento:**
    1.  Tenta abrir o arquivo PDF em modo de leitura binária (`'rb'`).
    2.  Usa `PyPDF2.PdfReader` para criar um objeto leitor de PDF.
    3.  Itera por todas as páginas do PDF.
    4.  Para cada página, chama `page.extract_text()` para obter o texto. Se a extração falhar para uma página, adiciona uma string vazia para evitar erros.
    5.  Concatena o texto de todas as páginas.
    6.  Imprime mensagens de status sobre a leitura e extração.
    7.  Inclui tratamento de erros para `FileNotFoundError`, `PyPDF2.errors.PdfReadError` (erros específicos do PyPDF2) e outras exceções. Retorna `None` em caso de erro.

### Função: `extract_potential_names`

* **Propósito:** Analisar um texto e identificar sequências de palavras que correspondem a potenciais nomes completos, com base nas listas fornecidas.
* **Parâmetros:**
    * `text` (str): O texto a ser analisado.
    * `first_names` (set): Conjunto de primeiros nomes válidos.
    * `second_names` (set): Conjunto de sobrenomes válidos.
    * `prepositions` (set): Conjunto de preposições válidas (usadas entre nomes/sobrenomes).
* **Retorno:** Uma lista (`list`) de strings, onde cada string é um nome potencial encontrado.
* **Funcionamento:**
    1.  Verificações iniciais: Retorna uma lista vazia se o texto de entrada ou as listas de nomes estiverem vazios, imprimindo avisos.
    2.  Normalização: Remove espaços extras entre palavras no texto.
    3.  Divide o texto normalizado em uma lista de palavras.
    4.  Itera sobre cada `word` na lista de palavras:
        * Limpa a palavra de pontuações comuns nas bordas (`.,;!?()[]{}`).
        * Capitaliza a palavra limpa para comparação com as listas de nomes.
        * Verifica se a palavra capitalizada está em `first_names` ou `second_names`, ou se a palavra limpa em minúsculas está em `prepositions`.
        * Mantém uma lista `current_name_parts` para construir o nome atual.
        * **Lógica de construção do nome:**
            * Se uma palavra é um `first_name` e nenhum nome está sendo construído (`current_name_parts` está vazio), inicia um novo nome potencial.
            * Se um nome já está sendo construído, adiciona a palavra se ela for um `first_name`, `second_name` ou `preposition`. Preposições são adicionadas em minúsculas, nomes/sobrenomes capitalizados.
            * Se a palavra *não* é parte de um nome (não é nome, sobrenome ou preposição válida no contexto):
                * Verifica se `current_name_parts` contém um nome potencial válido (pelo menos 2 partes e não termina com preposição). Se sim, junta as partes com espaço e adiciona à lista `found_names`.
                * Limpa `current_name_parts` para começar a procurar um novo nome.
    5.  Após o loop, verifica uma última vez se `current_name_parts` contém um nome válido e o adiciona se necessário.
    6.  Retorna a lista `found_names`.

### Bloco Principal (`if __name__ == "__main__":`)

* **Propósito:** Ponto de entrada principal do script quando executado diretamente. Orquestra o fluxo de trabalho: carregar nomes, processar argumentos, ler arquivo, extrair nomes e exibir resultados.
* **Funcionamento:**
    1.  Determina o diretório onde o script está localizado (`script_dir`).
    2.  Constrói o caminho completo para o arquivo `names.json` (esperado na subpasta `data`).
    3.  Chama `load_names_from_json` para carregar os dados do JSON.
    4.  Configura o `argparse` para aceitar um argumento obrigatório: `input_file`, que é o caminho para o arquivo `.txt` ou `.pdf` a ser processado.
    5.  Obtém o caminho do arquivo de entrada dos argumentos da linha de comando.
    6.  Verifica se o arquivo de entrada existe.
    7.  Determina o tipo de arquivo (PDF ou TXT) pela extensão:
        * Se for `.pdf`, chama `extract_text_from_pdf` para obter o texto.
        * Se for `.txt`, abre e lê o conteúdo do arquivo diretamente.
        * Se for outro tipo, imprime um erro.
    8.  Inclui tratamento de erro ao ler o arquivo `.txt`.
    9.  Se o texto foi extraído com sucesso (`file_text` não é `None`) *e* as listas de nomes não estão vazias:
        * Chama `extract_potential_names` para encontrar os nomes.
        * Imprime os nomes potenciais encontrados ou uma mensagem informando que nenhum foi encontrado.
    10. Se o texto não pôde ser extraído, informa o usuário.
    11. Se as listas de nomes estavam vazias (problema ao carregar `names.json`), informa o usuário e sugere verificar o arquivo JSON.

## Arquivo `names.json`

Este arquivo é **crucial** para o funcionamento do script. Ele deve estar localizado em uma subpasta chamada `data` no mesmo diretório do script Python. Sua estrutura deve ser um objeto JSON com as seguintes chaves (opcionais, mas necessárias para encontrar nomes):

* `"first_names"`: Uma lista de strings contendo primeiros nomes comuns.
* `"second_names"`: Uma lista de strings contendo sobrenomes comuns.
* `"prepositions"`: Uma lista de strings contendo preposições que podem aparecer em nomes compostos (ex: "da", "de", "do", "dos"). Se omitida, um padrão `["da", "das", "do", "dos", "de"]` é usado.

**Exemplo de `data/names.json`:**

```json
{
  "first_names": [
    "Maria", "José", "Antônio", "João", "Ana", "Luiz", "Paulo", "Carlos", 
    "Pedro", "Lucas", "Mariana", "Fernanda", "Beatriz", "Ricardo", "Marcos" 
    // ... muitos outros
  ],
  "second_names": [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", 
    "Pereira", "Lima", "Gomes", "Ribeiro", "Martins", "Carvalho", "Almeida",
    "Costa", "Nunes", "Mendes", "Barbosa"
    // ... muitos outros
  ],
  "prepositions": [
    "da", "das", "do", "dos", "de" 
  ]
}