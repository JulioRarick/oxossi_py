# ox_extract_places.py

Este script Python é projetado para analisar um arquivo de texto (`.txt`) ou PDF (`.pdf`), identificar menções a locais (cidades, vilas, etc.) de um período específico (presumivelmente colonial, dado o nome "captaincy"), e determinar qual "capitania" (unidade administrativa histórica) é a mais associada ao texto, com base na frequência das menções aos locais pertencentes a cada capitania. A relação entre locais e capitanias é definida em um arquivo de dados separado.

## Dependências

O script utiliza as seguintes bibliotecas:

1.  **`re`**: Para operações com expressões regulares, usadas para encontrar nomes de locais no texto de forma eficiente e flexível. (Biblioteca padrão do Python)
2.  **`os`**: Para manipulação de caminhos de arquivos (verificar existência). (Biblioteca padrão do Python)
3.  **`argparse`**: Para processar argumentos passados pela linha de comando (caminho do arquivo de entrada e do arquivo de dados). (Biblioteca padrão do Python)
4.  **`collections.defaultdict`**: Para criar dicionários que atribuem um valor padrão a chaves inexistentes, útil para contar ocorrências. (Biblioteca padrão do Python)
5.  **`typing`**: Para adicionar dicas de tipo (type hints), melhorando a legibilidade e a manutenção do código. (Biblioteca padrão do Python)
6.  **`PyPDF2`**: (Opcional) Para extrair texto de arquivos PDF. Se não estiver instalada, o script exibirá um aviso e a funcionalidade de processar PDFs será desativada.
    * **Instalação:** Se necessário, instale via pip:
        ```bash
        pip install PyPDF2
        ```

## Estrutura do Código

O código é organizado em funções para tarefas específicas e um bloco principal para orquestrar a execução.

### Função: `extract_text_from_pdf`

* **Propósito:** Extrair o conteúdo textual de um arquivo PDF.
* **Parâmetros:**
    * `pdf_path` (str): O caminho para o arquivo PDF.
* **Retorno:**
    * Uma string contendo o texto extraído do PDF, com páginas separadas por nova linha (`\n`).
    * `None` se a biblioteca `PyPDF2` não estiver instalada ou se ocorrer um erro durante a leitura (arquivo não encontrado, corrompido, protegido, inválido).
* **Funcionamento:**
    1.  Verifica se `PyPDF2` foi importado com sucesso. Se não, imprime um erro e retorna `None`.
    2.  Tenta abrir o arquivo PDF em modo de leitura binária (`'rb'`).
    3.  Usa `PyPDF2.PdfReader` para ler o PDF.
    4.  Itera por todas as páginas, extraindo o texto de cada uma (`page.extract_text()`) e concatenando-o à variável `text`, adicionando uma nova linha após cada página.
    5.  Imprime mensagens de status.
    6.  Inclui tratamento de erros para `FileNotFoundError`, `PyPDF2.errors.PdfReadError` (com detalhes do erro) e outras exceções inesperadas. Retorna `None` em caso de erro.

### Função: `load_captaincy_data`

* **Propósito:** Carregar os dados de mapeamento entre locais e capitanias a partir de um arquivo de texto.
* **Parâmetros:**
    * `filepath` (str): O caminho para o arquivo de dados. Formato esperado: cada linha contém `Nome do Local,Nome da Capitania`.
* **Retorno:**
    * Um dicionário (`Dict[str, List[str]]`) onde as chaves são nomes de capitanias e os valores são listas de nomes de locais pertencentes a essa capitania.
    * Um dicionário vazio (`{}`) em caso de erro crítico na leitura ou processamento.
* **Funcionamento:**
    1.  Verifica se o arquivo de dados existe; lança `FileNotFoundError` se não existir.
    2.  Inicializa um `defaultdict(list)` para armazenar os dados e um `set` (`assigned_places`) para garantir que cada local seja atribuído a apenas uma capitania (a primeira encontrada no arquivo).
    3.  Abre e lê o arquivo linha por linha, ignorando linhas vazias ou que começam com `#` (comentários).
    4.  Para cada linha válida, divide-a na primeira vírgula (`line.split(',', 1)`).
    5.  Verifica se a divisão resultou em duas partes (local e capitania) e se ambas não estão vazias.
    6.  Se o local ainda não foi atribuído a nenhuma capitania (`place not in assigned_places`), adiciona o local à lista da capitania correspondente no `defaultdict` e adiciona o local ao `set` `assigned_places`.
    7.  Imprime avisos para linhas ignoradas devido a formato incorreto ou dados ausentes.
    8.  Imprime mensagens de status sobre o carregamento.
    9.  Inclui tratamento de erros para `IOError` e outras exceções.
    10. Converte o `defaultdict` para um `dict` normal antes de retornar. Imprime um aviso se nenhum dado válido foi carregado.

### Função: `search_colonial_places`

* **Propósito:** Analisar o texto fornecido para encontrar menções aos locais definidos nos dados das capitanias, contar essas menções e calcular uma pontuação para cada capitania.
* **Parâmetros:**
    * `text` (str): O texto extraído do arquivo de entrada.
    * `captaincy_data` (Dict[str, List[str]]): O dicionário retornado por `load_captaincy_data`.
* **Retorno:**
    * Um dicionário (`Dict`) contendo os resultados da análise:
        * `"found_places_details"` (List[Tuple[str, int]]): Lista de tuplas, onde cada tupla contém o nome canônico de um local encontrado e sua contagem no texto, ordenada alfabeticamente pelo nome do local.
        * `"top_captaincy"` (Optional[Union[str, List[str]]]): O nome da capitania com a maior pontuação. Se houver empate, retorna uma lista ordenada dos nomes das capitanias empatadas. Retorna `None` se nenhuma pontuação for maior que zero.
        * `"all_captaincy_scores"` (Dict[str, int]): Um dicionário mapeando cada nome de capitania para sua pontuação total (soma das contagens dos locais pertencentes a ela).
* **Funcionamento:**
    1.  **Inicialização:** Define um template para os resultados e verifica se o texto ou os dados da capitania estão vazios; retorna o template vazio se estiverem. Inicializa dicionários para pontuações (`captaincy_scores`) e contagens de locais (`found_places_counts`).
    2.  **Construção de Lookups:** Cria estruturas de dados para facilitar a busca:
        * `place_to_captaincy`: Mapeia cada nome de local único de volta para sua capitania.
        * `all_places_canonical`: Um conjunto (`set`) com todos os nomes de locais únicos (forma canônica como aparecem no arquivo de dados).
        * `lower_to_canonical_place`: Mapeia a versão em minúsculas de cada nome de local para sua forma canônica (para busca case-insensitive).
    3.  **Criação do Padrão Regex:**
        * Obtém a lista de todos os locais únicos.
        * **Importante:** Ordena a lista de locais pelo comprimento em ordem decrescente (`key=len, reverse=True`). Isso garante que nomes mais longos (ex: "São Vicente") sejam encontrados antes de possíveis substrings (ex: "Vicente") que também possam estar na lista.
        * Escapa caracteres especiais de regex em cada nome de local (`re.escape`).
        * Constrói uma única string de padrão regex usando `|` (OU) para combinar qualquer um dos locais. Usa `\b` (word boundary - limite de palavra) no início e no fim para evitar correspondências parciais dentro de outras palavras (ex: encontrar "Salvador" mas não "Salvadoro").
        * Compila o padrão regex com a flag `re.IGNORECASE` para busca insensível a maiúsculas/minúsculas.
    4.  **Busca no Texto:** Usa `regex_pattern.finditer(text)` para encontrar todas as ocorrências dos locais no texto.
    5.  **Contagem de Locais:** Para cada correspondência encontrada (`match`):
        * Obtém o texto exato correspondido (`match.group(1)`).
        * Converte para minúsculas e usa `lower_to_canonical_place` para obter o nome canônico do local.
        * Incrementa a contagem para esse local canônico em `found_places_counts`.
    6.  **Cálculo das Pontuações das Capitanias:** Itera sobre os locais encontrados e suas contagens (`found_places_counts`). Para cada local, encontra sua capitania usando `place_to_captaincy` e adiciona a contagem do local à pontuação total da capitania em `captaincy_scores`.
    7.  **Determinação da(s) Capitania(s) Principal(is):**
        * Filtra as pontuações para considerar apenas aquelas maiores que zero.
        * Encontra a pontuação máxima entre elas.
        * Identifica todas as capitanias que atingiram essa pontuação máxima.
        * Define `top_captaincy` como o nome único se não houver empate, ou uma lista ordenada dos nomes se houver empate. Se nenhuma capitania pontuou, `top_captaincy` permanece `None`.
    8.  **Formatação Final:** Cria a lista `found_places_details` a partir de `found_places_counts` e ordena alfabeticamente pelo nome do local.
    9.  **Retorno:** Retorna o dicionário `results_template` preenchido com os dados encontrados. Inclui tratamento para `re.error` e outras exceções durante a busca.

### Bloco Principal (`if __name__ == "__main__":`)

* **Propósito:** Ponto de entrada do script. Controla o fluxo geral: parseia argumentos, carrega dados, lê o arquivo de entrada, chama a análise e imprime os resultados de forma organizada.
* **Funcionamento:**
    1.  **Configuração do `argparse`:** Define dois argumentos posicionais obrigatórios:
        * `input_file`: Caminho para o arquivo `.txt` ou `.pdf` a ser analisado.
        * `data_file`: Caminho para o arquivo de dados (`Place Name,Captaincy Name`). Usa `RawTextHelpFormatter` para preservar a formatação da ajuda no terminal.
    2.  **Parseamento dos Argumentos:** Lê os caminhos fornecidos pelo usuário na linha de comando.
    3.  **Carregamento dos Dados das Capitanias:** Chama `load_captaincy_data`. Se ocorrer `FileNotFoundError` ou outra exceção, ou se os dados carregados estiverem vazios, imprime um erro e encerra o script (`exit(1)`).
    4.  **Leitura do Arquivo de Entrada:**
        * Verifica se o `input_file` existe. Encerra se não existir.
        * Verifica a extensão do arquivo:
            * Se `.pdf`, chama `extract_text_from_pdf`. Encerra se a extração falhar.
            * Se `.txt`, abre e lê o arquivo diretamente. Encerra se houver erro na leitura.
            * Se for outro tipo, imprime erro e encerra.
    5.  **Execução da Análise:** Se o texto (`file_text`) foi carregado com sucesso, chama `search_colonial_places`.
    6.  **Impressão dos Resultados:**
        * Imprime a(s) capitania(s) com maior pontuação (`top_captaincy`).
        * Imprime os detalhes de contagem para cada local encontrado (`found_places_details`).
        * Imprime as pontuações totais para todas as capitanias que tiveram pontuação maior que zero, ordenadas da maior para a menor pontuação.
        * Inclui mensagens indicativas caso nenhum local ou pontuação seja encontrado.
    7.  Se o texto não pôde ser carregado, imprime uma mensagem informativa.

## Arquivo de Dados (`data_file`)

Este arquivo é **fundamental** e seu caminho deve ser passado como o segundo argumento ao executar o script.

* **Formato:** Arquivo de texto simples (`.txt`, `.csv`, etc.).
* **Conteúdo:** Cada linha deve conter o nome de um local e o nome da capitania à qual ele pertence, separados por **uma única vírgula**.
    ```
    Nome do Local,Nome da Capitania
    ```
* **Regras:**
    * Linhas que começam com `#` são ignoradas (comentários).
    * Linhas em branco são ignoradas.
    * Espaços em branco antes/depois do nome do local e da capitania são removidos (`strip`).
    * **Importante:** Um mesmo nome de local só será associado à *primeira* capitania listada para ele no arquivo. Ocorrências subsequentes do mesmo local com outras capitanias serão ignoradas.
* **Exemplo (`capitanias.txt`):**
    ```
    # Arquivo de dados de locais e capitanias
    São Vicente,Capitania de São Vicente
    Santos,Capitania de São Vicente
    São Paulo de Piratininga,Capitania de São Vicente
    Olinda,Capitania de Pernambuco
    Recife,Capitania de Pernambuco
    Igarassu,Capitania de Pernambuco
    Salvador,Capitania da Bahia
    Porto Seguro,Capitania de Porto Seguro
    Ilhéus,Capitania de Ilhéus
    Vila Velha,Capitania do Espírito Santo # Exemplo de comentário no final da linha
    ```

## Como Usar

1.  Certifique-se de ter o Python instalado.
2.  (Opcional, para PDFs) Instale `PyPDF2`: `pip install PyPDF2`.
3.  Crie o arquivo de dados (ex: `capitanias.txt`) com o mapeamento local-capitania no formato especificado.
4.  Execute o script a partir do terminal, fornecendo o caminho para o arquivo de entrada e o caminho para o arquivo de dados:

    ```bash
    python seu_script.py /caminho/para/documento.pdf /caminho/para/capitanias.txt
    ```
    ou
    ```bash
    python seu_script.py /caminho/para/documento.txt /caminho/para/dados_capitanias.csv 
    ```

5.  O script imprimirá mensagens de progresso e, ao final, os resultados da análise: a capitania principal, a contagem de cada local encontrado e a pontuação final de cada capitania.

## Fluxo de Execução (Resumo)

1.  Script inicia e parseia argumentos (arquivo de entrada, arquivo de dados).
2.  Carrega o mapeamento local -> capitania do arquivo de dados.
3.  Extrai texto do arquivo de entrada (PDF ou TXT).
4.  Se ambos foram carregados com sucesso:
    * Constrói um padrão regex otimizado com todos os locais conhecidos.
    * Busca todas as ocorrências desses locais no texto (case-insensitive, palavras inteiras).
    * Conta quantas vezes cada local foi mencionado.
    * Soma as contagens dos locais para calcular a pontuação de cada capitania.
    * Determina a(s) capitania(s) com maior pontuação.
5.  Imprime os resultados formatados no console.
6.  Encerra (com código de erro `1` se ocorrerem falhas críticas).

## Pontos Importantes/Considerações

* **Qualidade dos Dados:** A precisão da análise depende diretamente da completude e correção do arquivo de dados (`data_file`).
* **Regra de Atribuição Única:** Lembre-se que cada local só é atribuído à primeira capitania listada para ele no arquivo de dados.
* **Regex e Desempenho:** A busca usa uma única expressão regular compilada, o que é geralmente eficiente. A ordenação por tamanho decrescente dos locais no padrão evita problemas com nomes que são substrings de outros.
* **Limitações do PDF:** A extração de texto de PDFs pode ser imperfeita, especialmente para PDFs baseados em imagem (scans) ou com layouts complexos.
* **Tratamento de Empates:** O script identifica e lista todas as capitanias em caso de empate na pontuação máxima.
* **Saída de Erro:** O script usa `exit(1)` para sinalizar erros críticos (falha ao ler arquivos essenciais), o que pode ser útil em pipelines de processamento automatizado.