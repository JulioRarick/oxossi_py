import asyncio
import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime

from .database import DatabaseManager
from .indexer import PDFIndexer
from .extractors_integration import ExtractorRunner

logger = logging.getLogger(__name__)

class BulkPDFProcessor:
    """
    Processador otimizado para grandes volumes de PDFs.
    Processa até 18.000 PDFs de forma eficiente com controle de recursos.
    """
    
    def __init__(self, 
                 pdf_directory: str,
                 db: DatabaseManager,
                 max_concurrent: int = 10,
                 batch_size: int = 50,
                 skip_existing: bool = True):
        self.pdf_directory = Path(pdf_directory)
        self.db = db
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self.skip_existing = skip_existing
        
        self.indexer = PDFIndexer()
        self.extractor_runner = ExtractorRunner()
        
        # Estatísticas de processamento
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': None,
            'current_batch': 0,
            'errors_detail': []
        }
        
        # Controle de progresso
        self.progress_file = self.pdf_directory / "processing_progress.json"
        self.error_log_file = self.pdf_directory / "processing_errors.log"
        
        logger.info(f"BulkPDFProcessor inicializado para diretório: {self.pdf_directory}")
    
    async def discover_pdfs(self) -> List[Path]:
        """Descobre todos os PDFs no diretório e subdiretórios."""
        logger.info("Descobrindo arquivos PDF...")
        
        pdf_files = []
        
        # Busca recursiva por PDFs
        for pdf_path in self.pdf_directory.rglob("*.pdf"):
            if pdf_path.is_file():
                pdf_files.append(pdf_path)
        
        # Também busca por PDFs com extensão maiúscula
        for pdf_path in self.pdf_directory.rglob("*.PDF"):
            if pdf_path.is_file():
                pdf_files.append(pdf_path)
        
        logger.info(f"Encontrados {len(pdf_files)} arquivos PDF")
        self.stats['total_files'] = len(pdf_files)
        
        return sorted(pdf_files)  # Ordena para processamento consistente
    
    async def filter_existing_documents(self, pdf_files: List[Path]) -> List[Path]:
        """Remove PDFs que já foram processados (baseado no nome do arquivo)."""
        if not self.skip_existing:
            return pdf_files
        
        logger.info("Verificando PDFs já processados...")
        
        # Busca documentos existentes no banco
        async with self.db.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT DISTINCT filename FROM documents
            """)
            existing_files = {row[0] for row in await cursor.fetchall()}
        
        # Filtra arquivos não processados
        filtered_files = []
        for pdf_path in pdf_files:
            filename = pdf_path.name
            if filename not in existing_files:
                filtered_files.append(pdf_path)
            else:
                self.stats['skipped'] += 1
        
        logger.info(f"Arquivos filtrados: {len(filtered_files)} novos, {self.stats['skipped']} já processados")
        
        return filtered_files
    
    async def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Processa um único PDF (indexação + extractors)."""
        start_time = time.time()
        
        try:
            # Valida se arquivo ainda existe e é legível
            if not pdf_path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
            
            file_size = pdf_path.stat().st_size
            if file_size == 0:
                raise ValueError("Arquivo PDF vazio")
            
            # Indexa o documento
            document_id = await self.indexer.index_document(
                str(pdf_path), 
                pdf_path.name, 
                self.db
            )
            
            # Executa extractors
            extractor_results = await self.extractor_runner.run_all_extractors(
                document_id, 
                str(pdf_path), 
                self.db
            )
            
            # Atualiza status final
            await self.db.update_processing_status(document_id, "completed")
            
            processing_time = time.time() - start_time
            
            return {
                'status': 'success',
                'document_id': document_id,
                'filename': pdf_path.name,
                'file_size': file_size,
                'processing_time': processing_time,
                'extractors': {
                    name: result.get('status', 'unknown') 
                    for name, result in extractor_results.items()
                }
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Erro ao processar {pdf_path.name}: {str(e)}"
            logger.error(error_msg)
            
            # Log detalhado do erro
            await self._log_error(pdf_path, str(e))
            
            return {
                'status': 'error',
                'filename': pdf_path.name,
                'error': str(e),
                'processing_time': processing_time
            }
    
    async def process_batch(self, pdf_batch: List[Path]) -> List[Dict[str, Any]]:
        """Processa um lote de PDFs em paralelo."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(pdf_path: Path):
            async with semaphore:
                return await self.process_single_pdf(pdf_path)
        
        # Executa batch em paralelo
        tasks = [process_with_semaphore(pdf_path) for pdf_path in pdf_batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        batch_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    'status': 'error',
                    'filename': pdf_batch[i].name,
                    'error': str(result),
                    'processing_time': 0
                }
                batch_results.append(error_result)
                await self._log_error(pdf_batch[i], str(result))
            else:
                batch_results.append(result)
        
        return batch_results
    
    async def process_all_pdfs(self, 
                              progress_callback: Optional[callable] = None,
                              save_progress_interval: int = 10) -> Dict[str, Any]:
        """
        Processa todos os PDFs do diretório em lotes.
        
        Args:
            progress_callback: Função chamada a cada batch processado
            save_progress_interval: Intervalo (em batches) para salvar progresso
            
        Returns:
            Relatório final do processamento
        """
        self.stats['start_time'] = time.time()
        
        try:
            # Descobre e filtra PDFs
            all_pdfs = await self.discover_pdfs()
            pdf_files = await self.filter_existing_documents(all_pdfs)
            
            if not pdf_files:
                logger.info("Nenhum PDF novo para processar")
                return self._generate_final_report()
            
            logger.info(f"Iniciando processamento de {len(pdf_files)} PDFs em lotes de {self.batch_size}")
            
            # Processa em lotes
            total_batches = (len(pdf_files) + self.batch_size - 1) // self.batch_size
            
            for batch_idx in range(0, len(pdf_files), self.batch_size):
                batch_end = min(batch_idx + self.batch_size, len(pdf_files))
                current_batch = pdf_files[batch_idx:batch_end]
                
                self.stats['current_batch'] = (batch_idx // self.batch_size) + 1
                
                logger.info(f"Processando lote {self.stats['current_batch']}/{total_batches} ({len(current_batch)} arquivos)")
                
                # Processa lote
                batch_results = await self.process_batch(current_batch)
                
                # Atualiza estatísticas
                for result in batch_results:
                    if result['status'] == 'success':
                        self.stats['processed'] += 1
                    else:
                        self.stats['errors'] += 1
                        self.stats['errors_detail'].append({
                            'filename': result['filename'],
                            'error': result['error'],
                            'batch': self.stats['current_batch']
                        })
                
                # Callback de progresso
                if progress_callback:
                    await progress_callback(self.stats.copy())
                
                # Salva progresso periodicamente
                if self.stats['current_batch'] % save_progress_interval == 0:
                    await self._save_progress()
                
                # Log de progresso
                processed_total = self.stats['processed'] + self.stats['errors']
                percentage = (processed_total / len(pdf_files)) * 100
                
                logger.info(f"Progresso: {processed_total}/{len(pdf_files)} ({percentage:.1f}%) - "
                          f"Sucessos: {self.stats['processed']}, Erros: {self.stats['errors']}")
                
                # Pequena pausa entre lotes para não sobrecarregar
                await asyncio.sleep(0.1)
            
            # Salva progresso final
            await self._save_progress()
            
            logger.info("Processamento em lote concluído!")
            
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Erro no processamento em lote: {e}")
            await self._save_progress()
            raise
    
    async def _log_error(self, pdf_path: Path, error: str):
        """Log detalhado de erros."""
        try:
            timestamp = datetime.now().isoformat()
            error_entry = f"[{timestamp}] {pdf_path.name}: {error}\n"
            
            async with aiofiles.open(self.error_log_file, 'a', encoding='utf-8') as f:
                await f.write(error_entry)
        except Exception as log_error:
            logger.error(f"Erro ao salvar log de erro: {log_error}")
    
    async def _save_progress(self):
        """Salva progresso atual em arquivo JSON."""
        try:
            progress_data = {
                'stats': self.stats.copy(),
                'last_updated': datetime.now().isoformat(),
                'pdf_directory': str(self.pdf_directory)
            }
            
            # Remove tempo de início para serialização JSON
            if 'start_time' in progress_data['stats']:
                progress_data['stats']['elapsed_time'] = time.time() - self.stats['start_time']
                progress_data['stats']['start_time'] = datetime.fromtimestamp(self.stats['start_time']).isoformat()
            
            async with aiofiles.open(self.progress_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(progress_data, indent=2, ensure_ascii=False))
                
        except Exception as e:
            logger.error(f"Erro ao salvar progresso: {e}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Gera relatório final do processamento."""
        total_processed = self.stats['processed'] + self.stats['errors']
        elapsed_time = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        
        return {
            'summary': {
                'total_files_found': self.stats['total_files'],
                'total_processed': total_processed,
                'successful': self.stats['processed'],
                'errors': self.stats['errors'],
                'skipped': self.stats['skipped'],
                'success_rate': (self.stats['processed'] / total_processed * 100) if total_processed > 0 else 0
            },
            'performance': {
                'elapsed_time_seconds': elapsed_time,
                'elapsed_time_formatted': self._format_duration(elapsed_time),
                'average_time_per_file': elapsed_time / total_processed if total_processed > 0 else 0,
                'files_per_minute': (total_processed / elapsed_time * 60) if elapsed_time > 0 else 0
            },
            'errors': {
                'count': self.stats['errors'],
                'details': self.stats['errors_detail'][-10:],  # Últimos 10 erros
                'error_log_file': str(self.error_log_file)
            },
            'files': {
                'pdf_directory': str(self.pdf_directory),
                'progress_file': str(self.progress_file)
            }
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Formata duração em formato legível."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

# Função de conveniência para uso em scripts
async def process_pdf_directory(pdf_directory: str, 
                               max_concurrent: int = 10,
                               batch_size: int = 50,
                               skip_existing: bool = True) -> Dict[str, Any]:
    """
    Função de conveniência para processar um diretório de PDFs.
    
    Args:
        pdf_directory: Caminho para o diretório com PDFs
        max_concurrent: Número máximo de PDFs processados em paralelo
        batch_size: Tamanho dos lotes de processamento
        skip_existing: Se deve pular arquivos já processados
        
    Returns:
        Relatório final do processamento
    """
    
    # Inicializa banco de dados
    db = DatabaseManager()
    await db.initialize()
    
    # Cria processador
    processor = BulkPDFProcessor(
        pdf_directory=pdf_directory,
        db=db,
        max_concurrent=max_concurrent,
        batch_size=batch_size,
        skip_existing=skip_existing
    )
    
    # Função de callback para mostrar progresso
    async def progress_callback(stats):
        processed = stats['processed'] + stats['errors']
        total = stats['total_files'] - stats['skipped']
        if total > 0:
            percentage = (processed / total) * 100
            print(f"Progresso: {processed}/{total} ({percentage:.1f}%) - "
                  f"Lote {stats['current_batch']} - "
                  f"Sucessos: {stats['processed']}, Erros: {stats['errors']}")
    
    # Executa processamento
    return await processor.process_all_pdfs(progress_callback=progress_callback)

# Script para execução standalone
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python bulk_processor.py <diretório_pdfs> [max_concurrent] [batch_size]")
        print("Exemplo: python bulk_processor.py /caminho/para/pdfs 10 50")
        sys.exit(1)
    
    pdf_dir = sys.argv[1]
    max_concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    
    async def main():
        print(f"Iniciando processamento em lote de: {pdf_dir}")
        print(f"Configuração: {max_concurrent} concurrent, lotes de {batch_size}")
        
        try:
            report = await process_pdf_directory(
                pdf_directory=pdf_dir,
                max_concurrent=max_concurrent,
                batch_size=batch_size,
                skip_existing=True
            )
            
            print("\n" + "="*60)
            print("RELATÓRIO FINAL")
            print("="*60)
            print(f"Total de arquivos: {report['summary']['total_files_found']}")
            print(f"Processados: {report['summary']['total_processed']}")
            print(f"Sucessos: {report['summary']['successful']}")
            print(f"Erros: {report['summary']['errors']}")
            print(f"Pulados: {report['summary']['skipped']}")
            print(f"Taxa de sucesso: {report['summary']['success_rate']:.1f}%")
            print(f"Tempo total: {report['performance']['elapsed_time_formatted']}")
            print(f"Arquivos/minuto: {report['performance']['files_per_minute']:.1f}")
            
            if report['summary']['errors'] > 0:
                print(f"\nLog de erros salvo em: {report['errors']['error_log_file']}")
            
        except Exception as e:
            print(f"Erro no processamento: {e}")
            sys.exit(1)
    
    asyncio.run(main())
