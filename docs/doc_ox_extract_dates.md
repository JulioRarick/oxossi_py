# ox_extract_dates

## Descrição

Este script Python foi projetado para extrair texto de um arquivo PDF, identificar referências a datas (anos numéricos específicos e descrições textuais de séculos ou partes de séculos em português), e realizar uma análise estatística básica sobre as datas encontradas.

## Funcionalidades

* Extrai texto de arquivos PDF usando a biblioteca `PyMuPDF` (`fitz`).
* Identifica anos numéricos no formato `YYYY` (limitado ao intervalo 1500-1899 por padrão).
* Identifica frases textuais que descrevem datas, como:
    * Séculos (ex: "século xvi", "século xviii", "quinhentos", "setecentos").
    * Partes de séculos (ex: "primeira metade", "início", "fim", "meados").
* Converte as descrições textuais em intervalos de anos (ex: "início do século xvi" -> (1500, 1530)).
* Calcula um ano representativo (ponto médio) para cada intervalo textual encontrado.
* Combina os anos numéricos diretos com os anos representativos dos intervalos textuais.
* Calcula estatísticas sobre o conjunto combinado de anos:
    * Contagem total
    * Média
    * Mediana
    * Mínimo
    * Máximo
    * Desvio Padrão
* Determina intervalos de datas:
    * Intervalo completo (mínimo - máximo)
    * Intervalo denso (média ± desvio padrão)

## Dependências

* **re**: Módulo de expressões regulares do Python (padrão).
* **numpy**: Para cálculos numéricos e estatísticos.
* **PyMuPDF (fitz)**: Para extração de texto de PDFs.
* **sys**: Para acesso a argumentos de linha de comando (padrão).
* **os**: Para interações com o sistema operacional, como verificar a existência de arquivos e obter variáveis de ambiente (padrão).

