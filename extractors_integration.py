import asyncio
import logging
import tempfile
import json
import time
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Importa os extractors existentes
try:
    from oxossi.extractors.dates import extract_and_analyze_dates, _load_date_config
    from oxossi.extractors.names import extract_potential_names
    from oxossi.extractors.places import search_colonial_places, load_place_captaincy_data
    from oxossi.extractors.themes import analyze_text_themes
    from oxossi.extractors.references import extract_references_with_anystyle
    from oxossi.utils.pdf_utils import extract_text_from_pdf
    from oxossi.utils.data_utils import load_names_config, load_themes_config
except ImportError as e:
    logging.error(f"Erro ao importar extractors: {e}")
    raise

from .database import DatabaseManager

logger = logging.getLogger(__name__)

class ExtractorRunner:
    """
    Executor integrado para todos os extractors do Oxossi.
    Executa os extractors de forma assíncrona e armazena resultados no banco.
    """
    
    def __init__(self, data_dir: str = None):
        # Define diretório de dados
        if data_dir is None:
            current_dir = Path(__file__).parent
            self.data_dir = current_dir.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        # Caminhos para arquivos de configuração
        self.config_paths = {
            'dates': self.data_dir / "date_config.json",
            'names': self.data_dir / "names.json",
            'places': self.data_dir / "places.txt",
            'themes': self.data_dir / "themes.json"
        }
        
        # Cache para configurações carregadas
        self._config_cache = {}
        
        logger.info(f"ExtractorRunner inicializado com data_dir: {self.data_dir}")
    
    async def run_all_extractors(self, document_id: int, pdf_path: str, 
                                db: DatabaseManager) -> Dict[str, Any]:
        """
        Executa todos os extractors para um documento.
        
        Args:
            document_id: ID do documento no banco
            pdf_path: Caminho para o arquivo PDF
            db: Instância do DatabaseManager
            
        Returns:
            Dict com resultados de todos os extractors
        """
        logger.info(f"Iniciando execução de todos os extractors para documento {document_id}")
        
        try:
            # Atualiza status
            await db.update_processing_status(document_id, "processing_extractors")
            
            # Extrai texto do PDF uma vez para todos os extractors
            text_content = await self._extract_text_async(pdf_path)
            if not text_content:
                raise ValueError("Não foi possível extrair texto do PDF")
            
            # Lista de extractors para executar
            extractors = ['dates', 'names', 'places', 'themes', 'references']
            
            # Executa extractors em paralelo (mas com limite para não sobrecarregar)
            semaphore = asyncio.Semaphore(3)  # Máximo 3 extractors simultâneos
            tasks = []
            
            for extractor_name in extractors:
                task = self._run_single_extractor_with_semaphore(
                    semaphore, extractor_name, document_id, pdf_path, text_content, db
                )
                tasks.append(task)
            
            # Aguarda conclusão de todos
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processa resultados
            all_results = {}
            successful = 0
            
            for i, result in enumerate(results):
                extractor_name = extractors[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Erro no extractor {extractor_name}: {result}")
                    all_results[extractor_name] = {
                        'status': 'error',
                        'message': str(result),
                        'results': None
                    }
                else:
                    all_results[extractor_name] = result
                    if result.get('status') == 'success':
                        successful += 1
            
            # Atualiza status final
            if successful == len(extractors):
                await db.update_processing_status(document_id, "completed")
            elif successful > 0:
                await db.update_processing_status(document_id, "partially_completed")
            else:
                await db.update_processing_status(document_id, "failed")
            
            logger.info(f"Extractors concluídos para documento {document_id}: {successful}/{len(extractors)} sucessos")
            
            return all_results
            
        except Exception as e:
            logger.error(f"Erro na execução dos extractors para documento {document_id}: {e}")
            await db.update_processing_status(document_id, "failed")
            raise
    
    async def _run_single_extractor_with_semaphore(self, semaphore: asyncio.Semaphore,
                                                  extractor_name: str, document_id: int,
                                                  pdf_path: str, text_content: str,
                                                  db: DatabaseManager) -> Dict[str, Any]:
        """Executa um único extractor com controle de concorrência."""
        async with semaphore:
            return await self.run_single_extractor(
                extractor_name, document_id, pdf_path, text_content, db
            )
    
    async def run_single_extractor(self, extractor_name: str, document_id: int,
                                  pdf_path: str, text_content: str,
                                  db: DatabaseManager) -> Dict[str, Any]:
        """
        Executa um único extractor.
        
        Args:
            extractor_name: Nome do extractor ('dates', 'names', 'places', 'themes', 'references')
            document_id: ID do documento
            pdf_path: Caminho para o PDF
            text_content: Texto extraído do PDF
            db: DatabaseManager
            
        Returns:
            Dict com resultado do extractor
        """
        start_time = time.time()
        
        try:
            logger.info(f"Executando extractor '{extractor_name}' para documento {document_id}")
            
            # Executa o extractor específico
            if extractor_name == 'dates':
                result = await self._run_dates_extractor(text_content)
            elif extractor_name == 'names':
                result = await self._run_names_extractor(text_content)
            elif extractor_name == 'places':
                result = await self._run_places_extractor(text_content)
            elif extractor_name == 'themes':
                result = await self._run_themes_extractor(text_content)
            elif extractor_name == 'references':
                result = await self._run_references_extractor(pdf_path)
            else:
                raise ValueError(f"Extractor desconhecido: {extractor_name}")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Formata resultado
            formatted_result = {
                'status': 'success',
                'message': f'Extractor {extractor_name} executado com sucesso',
                'results': result,
                'execution_time_ms': execution_time_ms
            }
            
            # Armazena no banco
            await db.store_extractor_results(
                document_id, extractor_name, formatted_result, execution_time_ms
            )
            
            logger.info(f"Extractor '{extractor_name}' concluído em {execution_time_ms}ms")
            
            return formatted_result
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Erro no extractor '{extractor_name}': {e}")
            
            error_result = {
                'status': 'error',
                'message': f'Erro no extractor {extractor_name}: {str(e)}',
                'results': None,
                'execution_time_ms': execution_time_ms
            }
            
            try:
                await db.store_extractor_results(
                    document_id, extractor_name, error_result, execution_time_ms
                )
            except Exception as db_error:
                logger.error(f"Erro ao armazenar resultado de erro: {db_error}")
            
            return error_result
    
    async def _extract_text_async(self, pdf_path: str) -> str:
        """Extrai texto do PDF de forma assíncrona."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_text_from_pdf, pdf_path)
    
    async def _run_dates_extractor(self, text: str) -> Dict[str, Any]:
        """Executa o extractor de datas."""
        # Carrega configuração
        config = await self._load_config('dates')
        if not config:
            raise ValueError("Configuração de datas não encontrada")
        
        # Executa extractor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, extract_and_analyze_dates, text, config
        )
        
        return result
    
    async def _run_names_extractor(self, text: str) -> Dict[str, Any]:
        """Executa o extractor de nomes."""
        # Carrega configuração
        names_config = await self._load_config('names')
        if not names_config:
            raise ValueError("Configuração de nomes não encontrada")
        
        first_names, second_names, prepositions = names_config
        
        # Executa extractor
        loop = asyncio.get_event_loop()
        potential_names = await loop.run_in_executor(
            None, extract_potential_names, text, first_names, second_names, prepositions
        )
        
        return {
            'potential_names_found': potential_names,
            'count': len(potential_names)
        }
    
    async def _run_places_extractor(self, text: str) -> Dict[str, Any]:
        """Executa o extractor de locais."""
        # Carrega dados de locais/capitanias
        places_data = await self._load_config('places')
        if not places_data:
            raise ValueError("Dados de locais/capitanias não encontrados")
        
        # Executa extractor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, search_colonial_places, text, places_data
        )
        
        return result
    
    async def _run_themes_extractor(self, text: str) -> Dict[str, Any]:
        """Executa o extractor de temas."""
        # Carrega configuração de temas
        themes_config = await self._load_config('themes')
        if not themes_config:
            raise ValueError("Configuração de temas não encontrada")
        
        # Executa extractor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, analyze_text_themes, text, themes_config
        )
        
        return result
    
    async def _run_references_extractor(self, pdf_path: str) -> Dict[str, Any]:
        """Executa o extractor de referências."""
        # Executa extractor (que usa subprocess internamente)
        loop = asyncio.get_event_loop()
        references = await loop.run_in_executor(
            None, extract_references_with_anystyle, pdf_path
        )
        
        if references is None:
            return {
                'formatted_references': [],
                'count': 0
            }
        
        # Formata referências (assumindo que já vem formatadas)
        return {
            'formatted_references': references,
            'count': len(references)
        }
    
    async def _load_config(self, config_type: str) -> Any:
        """Carrega configuração específica com cache."""
        if config_type in self._config_cache:
            return self._config_cache[config_type]
        
        loop = asyncio.get_event_loop()
        
        try:
            if config_type == 'dates':
                config = await loop.run_in_executor(
                    None, _load_date_config, str(self.config_paths['dates'])
                )
            elif config_type == 'names':
                config = await loop.run_in_executor(
                    None, load_names_config, str(self.config_paths['names'])
                )
            elif config_type == 'places':
                config = await loop.run_in_executor(
                    None, load_place_captaincy_data, str(self.config_paths['places'])
                )
            elif config_type == 'themes':
                config = await loop.run_in_executor(
                    None, load_themes_config, str(self.config_paths['themes'])
                )
            else:
                raise ValueError(f"Tipo de configuração desconhecido: {config_type}")
            
            # Cache da configuração
            self._config_cache[config_type] = config
            return config
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuração '{config_type}': {e}")
            return None
    
    async def run_extractors_subset(self, document_id: int, pdf_path: str,
                                   extractors: List[str], db: DatabaseManager) -> Dict[str, Any]:
        """
        Executa apenas um subconjunto específico de extractors.
        
        Args:
            document_id: ID do documento
            pdf_path: Caminho para o PDF
            extractors: Lista de nomes dos extractors para executar
            db: DatabaseManager
            
        Returns:
            Dict com resultados dos extractors executados
        """
        logger.info(f"Executando extractors {extractors} para documento {document_id}")
        
        try:
            # Extrai texto se necessário
            text_content = None
            if any(ext in extractors for ext in ['dates', 'names', 'places', 'themes']):
                text_content = await self._extract_text_async(pdf_path)
            
            results = {}
            
            for extractor_name in extractors:
                try:
                    result = await self.run_single_extractor(
                        extractor_name, document_id, pdf_path, text_content, db
                    )
                    results[extractor_name] = result
                except Exception as e:
                    logger.error(f"Erro no extractor {extractor_name}: {e}")
                    results[extractor_name] = {
                        'status': 'error',
                        'message': str(e),
                        'results': None
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na execução dos extractors subset: {e}")
            raise
    
    def get_available_extractors(self) -> List[str]:
        """Retorna lista de extractors disponíveis."""
        return ['dates', 'names', 'places', 'themes', 'references']
    
    def validate_extractor_configs(self) -> Dict[str, bool]:
        """Valida se todas as configurações necessárias estão disponíveis."""
        validation_results = {}
        
        for config_type, config_path in self.config_paths.items():
            validation_results[config_type] = config_path.exists()
            
            if not validation_results[config_type]:
                logger.warning(f"Configuração não encontrada: {config_path}")
        
        return validation_results
    
    async def get_extractor_performance_stats(self, db: DatabaseManager) -> Dict[str, Any]:
        """Retorna estatísticas de performance dos extractors."""
        try:
            stats = {}
            
            async with db.get_connection() as conn:
                conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
                
                # Tempo médio de execução por extractor
                cursor = await conn.execute("""
                    SELECT 
                        extractor_type,
                        AVG(execution_time_ms) as avg_time_ms,
                        MIN(execution_time_ms) as min_time_ms,
                        MAX(execution_time_ms) as max_time_ms,
                        COUNT(*) as total_executions
                    FROM extractor_results
                    GROUP BY extractor_type
                """)
                
                performance_data = await cursor.fetchall()
                
                for row in performance_data:
                    stats[row['extractor_type']] = {
                        'avg_execution_time_ms': round(row['avg_time_ms'], 2),
                        'min_execution_time_ms': row['min_time_ms'],
                        'max_execution_time_ms': row['max_time_ms'],
                        'total_executions': row['total_executions']
                    }
                
                # Taxa de sucesso por extractor
                cursor = await conn.execute("""
                    SELECT 
                        extractor_type,
                        SUM(CASE WHEN JSON_EXTRACT(results, '$.status') = 'success' THEN 1 ELSE 0 END) as successes,
                        COUNT(*) as total
                    FROM extractor_results
                    GROUP BY extractor_type
                """)
                
                success_data = await cursor.fetchall()
                
                for row in success_data:
                    extractor_type = row['extractor_type']
                    if extractor_type in stats:
                        stats[extractor_type]['success_rate'] = round(
                            (row['successes'] / row['total']) * 100, 2
                        )
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de performance: {e}")
            return {}
