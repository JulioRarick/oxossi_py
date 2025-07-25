import os
import logging
import asyncio
from typing import List, Tuple, Optional
import time
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from .database import DatabaseManager

logger = logging.getLogger(__name__)

class PDFIndexer:
    """
    Indexador otimizado para documentos PDF.
    Extrai texto página por página e armazena no banco com FTS.
    """
    
    def __init__(self):
        if not fitz:
            logger.error("PyMuPDF não encontrado. Instale com: pip install PyMuPDF")
            raise ImportError("PyMuPDF é necessário para o indexador")
    
    async def index_document(self, pdf_path: str, original_filename: str, 
                           db: DatabaseManager) -> int:
        """
        Indexa um documento PDF completo.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            original_filename: Nome original do arquivo
            db: Instância do DatabaseManager
            
        Returns:
            ID do documento criado no banco
        """
        start_time = time.time()
        
        try:
            logger.info(f"Iniciando indexação de {original_filename}")
            
            # Extrai informações e texto do PDF
            pdf_info = await self._extract_pdf_info(pdf_path)
            pages_content = await self._extract_pages_content(pdf_path)
            
            if not pages_content:
                raise ValueError("Não foi possível extrair texto do PDF")
            
            # Insere documento no banco
            document_id = await db.insert_document(
                filename=original_filename,
                file_size=pdf_info['file_size'],
                total_pages=pdf_info['total_pages'],
                file_path=None  # Por enquanto não armazenamos o arquivo
            )
            
            # Insere conteúdo das páginas
            await db.insert_document_content(document_id, pages_content)
            
            # Atualiza status
            await db.update_processing_status(document_id, "indexed")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Documento {original_filename} indexado em {elapsed_time:.2f}s")
            
            return document_id
            
        except Exception as e:
            logger.error(f"Erro na indexação de {original_filename}: {e}")
            raise
    
    async def _extract_pdf_info(self, pdf_path: str) -> dict:
        """Extrai informações básicas do PDF."""
        try:
            # Executa em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_extract_pdf_info, pdf_path)
            
        except Exception as e:
            logger.error(f"Erro ao extrair informações do PDF: {e}")
            raise
    
    def _sync_extract_pdf_info(self, pdf_path: str) -> dict:
        """Versão síncrona da extração de informações do PDF."""
        try:
            with fitz.open(pdf_path) as doc:
                file_size = os.path.getsize(pdf_path)
                total_pages = len(doc)
                
                # Metadados do PDF
                metadata = doc.metadata
                
                return {
                    'file_size': file_size,
                    'total_pages': total_pages,
                    'metadata': metadata
                }
                
        except Exception as e:
            logger.error(f"Erro ao abrir PDF {pdf_path}: {e}")
            raise
    
    async def _extract_pages_content(self, pdf_path: str) -> List[Tuple[int, str]]:
        """Extrai texto de todas as páginas do PDF."""
        try:
            # Executa em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_extract_pages_content, pdf_path)
            
        except Exception as e:
            logger.error(f"Erro ao extrair páginas do PDF: {e}")
            raise
    
    def _sync_extract_pages_content(self, pdf_path: str) -> List[Tuple[int, str]]:
        """Versão síncrona da extração de conteúdo das páginas."""
        pages_content = []
        
        try:
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                logger.info(f"Extraindo texto de {total_pages} páginas...")
                
                for page_num in range(total_pages):
                    try:
                        page = doc.load_page(page_num)
                        
                        # Extrai texto da página
                        text = page.get_text("text")
                        
                        # Limpa e normaliza o texto
                        cleaned_text = self._clean_text(text)
                        
                        if cleaned_text:  # Só adiciona se há texto
                            pages_content.append((page_num + 1, cleaned_text))
                        else:
                            # Adiciona página vazia para manter sequência
                            pages_content.append((page_num + 1, ""))
                            logger.warning(f"Página {page_num + 1} sem texto extraível")
                    
                    except Exception as e:
                        logger.warning(f"Erro ao extrair página {page_num + 1}: {e}")
                        pages_content.append((page_num + 1, ""))
                
                logger.info(f"Texto extraído de {len(pages_content)} páginas")
                return pages_content
                
        except Exception as e:
            logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """
        Limpa e normaliza o texto extraído.
        Remove caracteres desnecessários e padroniza espaçamento.
        """
        if not text:
            return ""
        
        # Remove caracteres de controle
        cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Normaliza espaços e quebras de linha
        cleaned = ' '.join(cleaned.split())
        
        # Remove linhas muito curtas (possível ruído)
        lines = cleaned.split('\n')
        filtered_lines = [line.strip() for line in lines if len(line.strip()) > 2]
        
        return '\n'.join(filtered_lines) if filtered_lines else cleaned
    
    async def reindex_document(self, document_id: int, pdf_path: str, 
                              db: DatabaseManager) -> bool:
        """Reindexa um documento existente."""
        try:
            logger.info(f"Reindexando documento {document_id}")
            
            # Remove conteúdo anterior do FTS
            async with db.get_connection() as conn:
                await conn.execute("DELETE FROM documents_fts WHERE document_id = ?", (document_id,))
                await conn.execute("DELETE FROM documents_content WHERE document_id = ?", (document_id,))
                await conn.commit()
            
            # Extrai novo conteúdo
            pages_content = await self._extract_pages_content(pdf_path)
            
            if not pages_content:
                raise ValueError("Não foi possível extrair texto do PDF")
            
            # Insere novo conteúdo
            await db.insert_document_content(document_id, pages_content)
            
            # Atualiza informações do documento
            pdf_info = await self._extract_pdf_info(pdf_path)
            async with db.get_connection() as conn:
                await conn.execute("""
                    UPDATE documents 
                    SET total_pages = ?, file_size = ?, updated_at = CURRENT_TIMESTAMP,
                        processing_status = 'reindexed'
                    WHERE id = ?
                """, (pdf_info['total_pages'], pdf_info['file_size'], document_id))
                await conn.commit()
            
            logger.info(f"Documento {document_id} reindexado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao reindexar documento {document_id}: {e}")
            return False
    
    async def index_multiple_documents(self, pdf_files: List[Tuple[str, str]], 
                                     db: DatabaseManager, 
                                     progress_callback=None) -> List[int]:
        """
        Indexa múltiplos documentos em lote.
        
        Args:
            pdf_files: Lista de tuplas (caminho_pdf, nome_original)
            db: DatabaseManager
            progress_callback: Callback opcional para progresso
            
        Returns:
            Lista de IDs dos documentos criados
        """
        document_ids = []
        total_files = len(pdf_files)
        
        logger.info(f"Iniciando indexação em lote de {total_files} documentos")
        
        for i, (pdf_path, original_filename) in enumerate(pdf_files):
            try:
                document_id = await self.index_document(pdf_path, original_filename, db)
                document_ids.append(document_id)
                
                if progress_callback:
                    progress = (i + 1) / total_files * 100
                    await progress_callback(progress, f"Indexado: {original_filename}")
                
            except Exception as e:
                logger.error(f"Erro ao indexar {original_filename}: {e}")
                if progress_callback:
                    await progress_callback(None, f"Erro: {original_filename} - {str(e)}")
        
        logger.info(f"Indexação em lote concluída: {len(document_ids)}/{total_files} sucessos")
        return document_ids
    
    def validate_pdf(self, pdf_path: str) -> dict:
        """
        Valida se um arquivo PDF pode ser processado.
        
        Returns:
            Dict com informações de validação
        """
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        try:
            # Verifica se arquivo existe
            if not os.path.exists(pdf_path):
                validation_result['errors'].append("Arquivo não encontrado")
                return validation_result
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(pdf_path)
            if file_size == 0:
                validation_result['errors'].append("Arquivo vazio")
                return validation_result
            
            if file_size > 100 * 1024 * 1024:  # 100MB
                validation_result['warnings'].append("Arquivo muito grande (>100MB)")
            
            # Tenta abrir com PyMuPDF
            try:
                with fitz.open(pdf_path) as doc:
                    total_pages = len(doc)
                    
                    if total_pages == 0:
                        validation_result['errors'].append("PDF sem páginas")
                        return validation_result
                    
                    if total_pages > 1000:
                        validation_result['warnings'].append(f"PDF com muitas páginas ({total_pages})")
                    
                    # Testa extração de texto em algumas páginas
                    text_pages = 0
                    sample_pages = min(5, total_pages)
                    
                    for i in range(sample_pages):
                        page = doc.load_page(i)
                        text = page.get_text("text")
                        if text.strip():
                            text_pages += 1
                    
                    if text_pages == 0:
                        validation_result['warnings'].append("Nenhum texto extraível encontrado nas primeiras páginas")
                    
                    # Informações do documento
                    validation_result['info'] = {
                        'total_pages': total_pages,
                        'file_size': file_size,
                        'text_pages_sample': text_pages,
                        'metadata': doc.metadata
                    }
                    
                    validation_result['is_valid'] = True
                    
            except Exception as e:
                validation_result['errors'].append(f"Erro ao abrir PDF: {str(e)}")
                
        except Exception as e:
            validation_result['errors'].append(f"Erro na validação: {str(e)}")
        
        return validation_result
    
    async def extract_sample_text(self, pdf_path: str, max_pages: int = 3) -> str:
        """Extrai texto de uma amostra de páginas para preview."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._sync_extract_sample_text, pdf_path, max_pages
            )
        except Exception as e:
            logger.error(f"Erro ao extrair amostra de texto: {e}")
            return ""
    
    def _sync_extract_sample_text(self, pdf_path: str, max_pages: int) -> str:
        """Versão síncrona da extração de amostra."""
        try:
            with fitz.open(pdf_path) as doc:
                sample_text = []
                pages_to_check = min(max_pages, len(doc))
                
                for i in range(pages_to_check):
                    page = doc.load_page(i)
                    text = page.get_text("text")
                    cleaned = self._clean_text(text)
                    
                    if cleaned:
                        # Pega apenas os primeiros 500 caracteres por página
                        sample_text.append(f"[Página {i+1}]\n{cleaned[:500]}...")
                
                return "\n\n".join(sample_text)
                
        except Exception as e:
            logger.error(f"Erro ao extrair amostra: {e}")
            return ""
    
    async def get_indexing_stats(self, db: DatabaseManager) -> dict:
        """Retorna estatísticas de indexação."""
        try:
            async with db.get_connection() as conn:
                conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
                
                # Documentos por status
                cursor = await conn.execute("""
                    SELECT processing_status, COUNT(*) as count
                    FROM documents
                    GROUP BY processing_status
                """)
                status_counts = await cursor.fetchall()
                
                # Páginas indexadas
                cursor = await conn.execute("SELECT SUM(total_pages) FROM documents")
                total_pages = (await cursor.fetchone())['SUM(total_pages)'] or 0
                
                # Tamanho total indexado
                cursor = await conn.execute("SELECT SUM(file_size) FROM documents")
                total_size = (await cursor.fetchone())['SUM(file_size)'] or 0
                
                # Documentos indexados por dia (últimos 7 dias)
                cursor = await conn.execute("""
                    SELECT DATE(upload_date) as date, COUNT(*) as count
                    FROM documents
                    WHERE upload_date >= datetime('now', '-7 days')
                    GROUP BY DATE(upload_date)
                    ORDER BY date DESC
                """)
                daily_counts = await cursor.fetchall()
                
                return {
                    'status_counts': {row['processing_status']: row['count'] for row in status_counts},
                    'total_pages_indexed': total_pages,
                    'total_size_bytes': total_size,
                    'daily_indexing': daily_counts
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de indexação: {e}")
            return {}
    
    def optimize_extraction_settings(self, pdf_path: str) -> dict:
        """
        Analisa um PDF e sugere configurações otimizadas para extração.
        """
        settings = {
            'text_extraction_mode': 'text',  # 'text', 'dict', 'rawdict'
            'preserve_layout': False,
            'extract_images': False,
            'ocr_required': False
        }
        
        try:
            with fitz.open(pdf_path) as doc:
                # Analisa primeira página como amostra
                if len(doc) > 0:
                    page = doc.load_page(0)
                    
                    # Verifica se há texto extraível
                    text = page.get_text("text")
                    if len(text.strip()) < 50:  # Pouco texto
                        settings['ocr_required'] = True
                        settings['extract_images'] = True
                    
                    # Verifica layout complexo
                    blocks = page.get_text("dict")["blocks"]
                    if len(blocks) > 10:  # Muitos blocos = layout complexo
                        settings['preserve_layout'] = True
                        settings['text_extraction_mode'] = 'dict'
                
        except Exception as e:
            logger.warning(f"Erro ao analisar PDF para otimização: {e}")
        
        return settings
