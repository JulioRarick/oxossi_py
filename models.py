from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class DocumentResponse(BaseModel):
    """Resposta para informações de documento."""
    id: int
    filename: str
    upload_date: datetime
    file_size: int
    total_pages: int
    processing_status: str = "completed"
    message: Optional[str] = None

class SearchFilters(BaseModel):
    """Filtros para pesquisa de documentos."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    filename: Optional[str] = None
    captaincy: Optional[str] = None
    theme: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    
    @validator('year_from', 'year_to')
    def validate_years(cls, v):
        if v is not None and (v < 1400 or v > 2000):
            raise ValueError('Ano deve estar entre 1400 e 2000')
        return v

class SearchRequest(BaseModel):
    """Requisição de pesquisa."""
    query: str = Field(..., min_length=1, max_length=1000, description="Termo de busca")
    filters: Optional[SearchFilters] = None
    limit: int = Field(50, ge=1, le=1000, description="Número máximo de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginação")
    highlight: bool = Field(True, description="Destacar termos na busca")
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query não pode ser vazia')
        return v.strip()

class SearchResult(BaseModel):
    """Resultado individual de pesquisa."""
    document_id: int
    filename: str
    upload_date: datetime
    total_pages: int
    page_number: int
    word_count: int
    relevance_score: float
    content_snippet: str

class SearchResponse(BaseModel):
    """Resposta completa de pesquisa."""
    query: str
    total_results: int
    results: List[SearchResult]
    took_ms: int
    filters_applied: Optional[SearchFilters] = None

class DateResults(BaseModel):
    """Resultados do extractor de datas."""
    direct_numeric_years: List[int]
    calculated_textual_intervals: List[tuple]
    combined_representative_years: List[int]
    count: int
    mean: Optional[float]
    median: Optional[float]
    minimum: Optional[int]
    maximum: Optional[int]
    standard_deviation: Optional[float]
    full_range: Optional[str]
    dense_range_stddev: Optional[tuple]

class NamesResults(BaseModel):
    """Resultados do extractor de nomes."""
    potential_names_found: List[str]
    count: int

class PlacesResults(BaseModel):
    """Resultados do extractor de locais."""
    found_places_details: List[tuple]  # (place_name, frequency)
    top_captaincy: Optional[Union[str, List[str]]]
    all_captaincy_scores: Dict[str, int]

class ThemesResults(BaseModel):
    """Resultados do extractor de temas."""
    theme_counts: Dict[str, int]
    keyword_counts: Dict[str, int]
    top_theme: Optional[Union[str, List[str]]]
    theme_percentages: Dict[str, float]
    total_keywords_found: int

class ReferencesResults(BaseModel):
    """Resultados do extractor de referências."""
    formatted_references: List[str]
    count: int
    raw_anystyle_output: Optional[List[Dict[str, Any]]] = None

class ExtractorResult(BaseModel):
    """Resultado individual de um extractor."""
    results: Optional[Union[DateResults, NamesResults, PlacesResults, ThemesResults, ReferencesResults]]
    status: str
    message: str
    execution_time_ms: int
    created_at: datetime

class ExtractorResults(BaseModel):
    """Resultados completos de todos os extractors."""
    document_id: int
    filename: str
    dates: Optional[ExtractorResult] = None
    names: Optional[ExtractorResult] = None
    places: Optional[ExtractorResult] = None
    themes: Optional[ExtractorResult] = None
    references: Optional[ExtractorResult] = None
    last_updated: Optional[datetime] = None

class DocumentStats(BaseModel):
    """Estatísticas gerais da base de dados."""
    total_documents: int
    total_pages: int
    total_file_size: int
    documents_by_status: Dict[str, int]
    top_captaincies: List[Dict[str, Union[str, int]]]
    top_names: List[Dict[str, Union[str, int]]]
    documents_by_century: Dict[str, int]
    top_themes: List[Dict[str, Union[str, int]]]

class HealthResponse(BaseModel):
    """Resposta do health check."""
    status: str
    timestamp: datetime
    database_connected: bool
    total_documents: Optional[int] = None
    error: Optional[str] = None

class QuickSearchResponse(BaseModel):
    """Resposta da pesquisa rápida."""
    query: str
    suggestions: List[Dict[str, Any]]
    count: int

class UploadResponse(BaseModel):
    """Resposta do upload de documento."""
    success: bool
    document_id: Optional[int] = None
    filename: Optional[str] = None
    message: str
    processing_status: str = "uploaded"

class ErrorResponse(BaseModel):
    """Resposta de erro padrão."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BulkUploadRequest(BaseModel):
    """Requisição para upload em lote."""
    process_immediately: bool = Field(True, description="Processar extractors imediatamente")
    overwrite_duplicates: bool = Field(False, description="Sobrescrever arquivos duplicados")

class BulkUploadResponse(BaseModel):
    """Resposta do upload em lote."""
    total_files: int
    successful_uploads: int
    failed_uploads: int
    uploaded_documents: List[DocumentResponse]
    errors: List[str]

class ReprocessRequest(BaseModel):
    """Requisição para reprocessamento."""
    extractors: Optional[List[str]] = Field(None, description="Extractors específicos para executar")
    force: bool = Field(False, description="Forçar reprocessamento mesmo se já processado")

class AdvancedSearchRequest(BaseModel):
    """Requisição de pesquisa avançada."""
    text_query: Optional[str] = None
    date_range: Optional[Dict[str, int]] = None  # {"from": 1600, "to": 1700}
    captaincies: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    names: Optional[List[str]] = None
    places: Optional[List[str]] = None
    combine_with: str = Field("AND", description="Como combinar filtros: AND ou OR")
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)
    
    @validator('combine_with')
    def validate_combine_with(cls, v):
        if v.upper() not in ['AND', 'OR']:
            raise ValueError('combine_with deve ser AND ou OR')
        return v.upper()

class AdvancedSearchResponse(BaseModel):
    """Resposta da pesquisa avançada."""
    request: AdvancedSearchRequest
    total_results: int
    results: List[Dict[str, Any]]
    took_ms: int
    aggregations: Optional[Dict[str, Any]] = None

class ExportRequest(BaseModel):
    """Requisição para exportação de dados."""
    format: str = Field("json", description="Formato de exportação: json, csv, xlsx")
    include_content: bool = Field(False, description="Incluir texto completo")
    include_extractors: bool = Field(True, description="Incluir resultados dos extractors")
    document_ids: Optional[List[int]] = None
    filters: Optional[SearchFilters] = None
    
    @validator('format')
    def validate_format(cls, v):
        if v.lower() not in ['json', 'csv', 'xlsx']:
            raise ValueError('Formato deve ser json, csv ou xlsx')
        return v.lower()

class BatchProcessRequest(BaseModel):
    """Requisição para processamento em lote."""
    document_ids: List[int]
    extractors: List[str]
    priority: str = Field("normal", description="Prioridade: low, normal, high")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v.lower() not in ['low', 'normal', 'high']:
            raise ValueError('Prioridade deve ser low, normal ou high')
        return v.lower()

class BatchProcessResponse(BaseModel):
    """Resposta do processamento em lote."""
    batch_id: str
    total_documents: int
    status: str
    estimated_completion: Optional[datetime] = None

class SuggestionResponse(BaseModel):
    """Resposta para sugestões de pesquisa."""
    suggestions: List[str]
    query: str
    categories: Dict[str, List[str]]  # {"names": [...], "places": [...], etc}

class ValidationResponse(BaseModel):
    """Resposta de validação de dados."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

# Modelos para MongoDB/PDFs
class PDFUrlInfo(BaseModel):
    """Informações de um PDF encontrado no MongoDB."""
    id: str
    url: str
    title: str
    description: str = ""
    scraped_at: Optional[datetime]
    file_size: Optional[int]
    content_type: Optional[str]
    source_url: Optional[str]
    metadata: Dict[str, Any] = {}

class PDFUrlFilters(BaseModel):
    """Filtros para busca de PDFs no MongoDB."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    min_file_size: Optional[int] = None
    source: Optional[str] = None
    domain: Optional[str] = None

class PDFUrlRequest(BaseModel):
    """Requisição para buscar URLs de PDFs."""
    limit: int = Field(100, ge=1, le=1000, description="Número máximo de resultados")
    offset: int = Field(0, ge=0, description="Offset para paginação")
    filters: Optional[PDFUrlFilters] = None

class PDFUrlResponse(BaseModel):
    """Resposta com URLs de PDFs encontrados."""
    pdfs: List[PDFUrlInfo]
    total_count: int
    limit: int
    offset: int
    has_more: bool

class PDFSearchRequest(BaseModel):
    """Requisição para busca textual de PDFs."""
    search_text: str = Field(..., min_length=1, max_length=500, description="Texto para buscar")
    limit: int = Field(50, ge=1, le=200, description="Número máximo de resultados")

class PDFStatistics(BaseModel):
    """Estatísticas sobre PDFs no MongoDB."""
    total_pdfs: int
    pdfs_by_domain: List[Dict[str, Any]]
    pdfs_by_month: List[Dict[str, Any]]
    file_size_stats: Dict[str, Any]

class DownloadPDFRequest(BaseModel):
    """Requisição para download e indexação de PDF do MongoDB."""
    pdf_id: str = Field(..., description="ID do PDF no MongoDB")
    auto_process: bool = Field(True, description="Executar extractors automaticamente")

class DownloadPDFResponse(BaseModel):
    """Resposta do download e indexação de PDF."""
    success: bool
    pdf_info: Optional[PDFUrlInfo] = None
    document_id: Optional[int] = None
    message: str
    processing_status: str = "downloaded"
