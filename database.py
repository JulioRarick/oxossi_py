import sqlite3
import aiosqlite
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import time
from datetime import datetime
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gerenciador de banco de dados otimizado para o Oxossi.
    Utiliza SQLite com FTS5 para pesquisa de texto completo ultra-rápida.
    """
    
    def __init__(self, db_path: str = "oxossi.db"):
        self.db_path = db_path
        self.connection = None
    
    async def initialize(self):
        """Inicializa o banco de dados e cria as tabelas necessárias."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Habilita WAL mode para melhor concorrência
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("PRAGMA synchronous=NORMAL")
                await db.execute("PRAGMA cache_size=10000")
                await db.execute("PRAGMA temp_store=memory")
                
                # Cria tabelas principais
                await self._create_tables(db)
                await db.commit()
                
            logger.info(f"Banco de dados inicializado: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do banco: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Cria todas as tabelas necessárias."""
        
        # Tabela de documentos
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_pages INTEGER,
                processing_status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela FTS5 para texto completo (otimizada)
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                document_id UNINDEXED,
                content,
                page_number UNINDEXED,
                tokenize = 'porter ascii',
                content='documents_content',
                content_rowid='rowid'
            )
        """)
        
        # Tabela auxiliar para conteúdo das páginas
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents_content (
                rowid INTEGER PRIMARY KEY,
                document_id INTEGER,
                page_number INTEGER,
                content TEXT,
                word_count INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Tabela para resultados dos extractors
        await db.execute("""
            CREATE TABLE IF NOT EXISTS extractor_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                extractor_type TEXT,
                results JSON,
                execution_time_ms INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Tabela para datas extraídas (indexada para pesquisas rápidas)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                year_numeric INTEGER,
                year_representative INTEGER,
                date_text TEXT,
                confidence REAL,
                page_number INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Tabela para nomes extraídos
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                name_full TEXT,
                name_normalized TEXT,
                name_type TEXT, -- 'person', 'place', etc.
                frequency INTEGER DEFAULT 1,
                confidence REAL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Tabela para locais e capitanias
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                place_name TEXT,
                captaincy TEXT,
                frequency INTEGER DEFAULT 1,
                confidence REAL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Tabela para temas
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                theme_name TEXT,
                keyword TEXT,
                frequency INTEGER,
                percentage REAL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
        """)
        
        # Índices para performance
        await self._create_indexes(db)
    
    async def _create_indexes(self, db: aiosqlite.Connection):
        """Cria índices otimizados para consultas rápidas."""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)",
            "CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date)",
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status)",
            
            "CREATE INDEX IF NOT EXISTS idx_content_document ON documents_content(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_content_page ON documents_content(page_number)",
            
            "CREATE INDEX IF NOT EXISTS idx_extractor_doc_type ON extractor_results(document_id, extractor_type)",
            "CREATE INDEX IF NOT EXISTS idx_extractor_created ON extractor_results(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_dates_doc ON document_dates(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_dates_year ON document_dates(year_numeric)",
            "CREATE INDEX IF NOT EXISTS idx_dates_representative ON document_dates(year_representative)",
            
            "CREATE INDEX IF NOT EXISTS idx_names_doc ON document_names(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_names_normalized ON document_names(name_normalized)",
            "CREATE INDEX IF NOT EXISTS idx_names_frequency ON document_names(frequency DESC)",
            
            "CREATE INDEX IF NOT EXISTS idx_places_doc ON document_places(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_places_captaincy ON document_places(captaincy)",
            "CREATE INDEX IF NOT EXISTS idx_places_name ON document_places(place_name)",
            
            "CREATE INDEX IF NOT EXISTS idx_themes_doc ON document_themes(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_themes_name ON document_themes(theme_name)",
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
    
    async def insert_document(self, filename: str, file_size: int, total_pages: int, 
                             file_path: str = None) -> int:
        """Insere um novo documento e retorna o ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO documents (filename, file_path, file_size, total_pages)
                    VALUES (?, ?, ?, ?)
                """, (filename, file_path, file_size, total_pages))
                
                document_id = cursor.lastrowid
                await db.commit()
                
                logger.info(f"Documento inserido: ID={document_id}, arquivo={filename}")
                return document_id
                
        except Exception as e:
            logger.error(f"Erro ao inserir documento: {e}")
            raise
    
    async def insert_document_content(self, document_id: int, pages_content: List[Tuple[int, str]]):
        """Insere o conteúdo das páginas e atualiza o índice FTS."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Insere conteúdo das páginas
                content_data = []
                fts_data = []
                
                for page_num, content in pages_content:
                    word_count = len(content.split())
                    content_data.append((document_id, page_num, content, word_count))
                    fts_data.append((document_id, content, page_num))
                
                await db.executemany("""
                    INSERT INTO documents_content (document_id, page_number, content, word_count)
                    VALUES (?, ?, ?, ?)
                """, content_data)
                
                # Atualiza índice FTS
                await db.executemany("""
                    INSERT INTO documents_fts (document_id, content, page_number)
                    VALUES (?, ?, ?)
                """, fts_data)
                
                await db.commit()
                logger.info(f"Conteúdo inserido para documento {document_id}: {len(pages_content)} páginas")
                
        except Exception as e:
            logger.error(f"Erro ao inserir conteúdo: {e}")
            raise
    
    async def search_documents(self, query: str, filters: Dict = None, 
                             limit: int = 50, offset: int = 0, 
                             highlight: bool = True) -> Dict[str, Any]:
        """
        Pesquisa otimizada usando FTS5.
        Retorna resultados com destacamento de termos e metadados.
        """
        start_time = time.time()
        
        try:
            # Prepara a query FTS
            fts_query = self._prepare_fts_query(query)
            
            # SQL base para pesquisa
            base_sql = """
                SELECT 
                    d.id,
                    d.filename,
                    d.upload_date,
                    d.total_pages,
                    dc.page_number,
                    dc.word_count,
                    fts.rank,
                    CASE WHEN ? THEN 
                        highlight(documents_fts, 1, '<mark>', '</mark>')
                    ELSE 
                        substr(dc.content, 1, 300) || '...'
                    END as content_snippet
                FROM documents_fts fts
                JOIN documents_content dc ON fts.rowid = dc.rowid
                JOIN documents d ON dc.document_id = d.id
                WHERE documents_fts MATCH ?
            """
            
            # Aplica filtros se fornecidos
            where_conditions = []
            params = [highlight, fts_query]
            
            if filters:
                if 'date_from' in filters:
                    where_conditions.append("d.upload_date >= ?")
                    params.append(filters['date_from'])
                
                if 'date_to' in filters:
                    where_conditions.append("d.upload_date <= ?")
                    params.append(filters['date_to'])
                
                if 'filename' in filters:
                    where_conditions.append("d.filename LIKE ?")
                    params.append(f"%{filters['filename']}%")
            
            if where_conditions:
                base_sql += " AND " + " AND ".join(where_conditions)
            
            # Ordena por relevância e adiciona paginação
            base_sql += """
                ORDER BY fts.rank DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Executa pesquisa principal
                cursor = await db.execute(base_sql, params)
                rows = await cursor.fetchall()
                
                # Conta total de resultados
                count_sql = """
                    SELECT COUNT(DISTINCT d.id)
                    FROM documents_fts fts
                    JOIN documents_content dc ON fts.rowid = dc.rowid
                    JOIN documents d ON dc.document_id = d.id
                    WHERE documents_fts MATCH ?
                """
                
                count_params = [fts_query]
                if where_conditions:
                    for i, condition in enumerate(where_conditions):
                        count_sql += f" AND {condition}"
                        count_params.append(params[2 + i])  # Skip highlight and query params
                
                cursor = await db.execute(count_sql, count_params)
                total_count = (await cursor.fetchone())[0]
                
                # Formata resultados
                results = []
                for row in rows:
                    results.append({
                        'document_id': row['id'],
                        'filename': row['filename'],
                        'upload_date': row['upload_date'],
                        'total_pages': row['total_pages'],
                        'page_number': row['page_number'],
                        'word_count': row['word_count'],
                        'relevance_score': row['rank'],
                        'content_snippet': row['content_snippet']
                    })
                
                took_ms = int((time.time() - start_time) * 1000)
                
                return {
                    'documents': results,
                    'total': total_count,
                    'took_ms': took_ms
                }
                
        except Exception as e:
            logger.error(f"Erro na pesquisa: {e}")
            raise
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepara a query para FTS5, tratando caracteres especiais."""
        # Remove caracteres especiais que podem quebrar o FTS
        special_chars = ['"', "'", "*", ":", "(", ")", "[", "]"]
        clean_query = query
        
        for char in special_chars:
            clean_query = clean_query.replace(char, " ")
        
        # Divide em termos e adiciona wildcards
        terms = [term.strip() for term in clean_query.split() if term.strip()]
        
        if not terms:
            return query  # Retorna original se não há termos válidos
        
        # Para queries simples, adiciona wildcard ao final
        if len(terms) == 1:
            return f'"{terms[0]}"*'
        
        # Para múltiplos termos, usa AND implícito
        return " ".join(f'"{term}"' for term in terms)
    
    async def quick_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Pesquisa rápida para autocompletar."""
        try:
            fts_query = self._prepare_fts_query(query)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT DISTINCT
                        d.id,
                        d.filename,
                        substr(dc.content, 1, 100) || '...' as snippet
                    FROM documents_fts fts
                    JOIN documents_content dc ON fts.rowid = dc.rowid
                    JOIN documents d ON dc.document_id = d.id
                    WHERE documents_fts MATCH ?
                    ORDER BY fts.rank DESC
                    LIMIT ?
                """, (fts_query, limit))
                
                rows = await cursor.fetchall()
                
                return [
                    {
                        'document_id': row['id'],
                        'filename': row['filename'],
                        'snippet': row['snippet']
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Erro na pesquisa rápida: {e}")
            return []
    
    async def store_extractor_results(self, document_id: int, extractor_type: str, 
                                    results: Dict[str, Any], execution_time_ms: int):
        """Armazena resultados de um extractor."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Remove resultados anteriores do mesmo tipo
                await db.execute("""
                    DELETE FROM extractor_results 
                    WHERE document_id = ? AND extractor_type = ?
                """, (document_id, extractor_type))
                
                # Insere novo resultado
                await db.execute("""
                    INSERT INTO extractor_results 
                    (document_id, extractor_type, results, execution_time_ms)
                    VALUES (?, ?, ?, ?)
                """, (document_id, extractor_type, json.dumps(results), execution_time_ms))
                
                # Armazena dados específicos em tabelas dedicadas
                await self._store_specialized_data(db, document_id, extractor_type, results)
                
                await db.commit()
                logger.info(f"Resultados do {extractor_type} armazenados para documento {document_id}")
                
        except Exception as e:
            logger.error(f"Erro ao armazenar resultados do extractor: {e}")
            raise
    
    async def _store_specialized_data(self, db: aiosqlite.Connection, 
                                    document_id: int, extractor_type: str, 
                                    results: Dict[str, Any]):
        """Armazena dados específicos em tabelas especializadas para consultas rápidas."""
        
        if extractor_type == 'dates' and results.get('results'):
            date_results = results['results']
            
            # Remove dados antigos
            await db.execute("DELETE FROM document_dates WHERE document_id = ?", (document_id,))
            
            # Insere anos numéricos
            for year in date_results.get('direct_numeric_years', []):
                await db.execute("""
                    INSERT INTO document_dates (document_id, year_numeric, year_representative, confidence)
                    VALUES (?, ?, ?, ?)
                """, (document_id, year, year, 1.0))
            
            # Insere anos representativos de intervalos
            for year in date_results.get('combined_representative_years', []):
                if year not in date_results.get('direct_numeric_years', []):
                    await db.execute("""
                        INSERT INTO document_dates (document_id, year_representative, confidence)
                        VALUES (?, ?, ?)
                    """, (document_id, year, 0.8))
        
        elif extractor_type == 'names' and results.get('results'):
            name_results = results['results']
            
            await db.execute("DELETE FROM document_names WHERE document_id = ?", (document_id,))
            
            for name in name_results.get('potential_names_found', []):
                normalized_name = name.lower().strip()
                await db.execute("""
                    INSERT INTO document_names (document_id, name_full, name_normalized, name_type, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, name, normalized_name, 'person', 0.9))
        
        elif extractor_type == 'places' and results.get('results'):
            place_results = results['results']
            
            await db.execute("DELETE FROM document_places WHERE document_id = ?", (document_id,))
            
            # Armazena locais encontrados
            for place_name, frequency in place_results.get('found_places_details', []):
                # Busca capitania nas pontuações
                captaincy = None
                for cap, places in place_results.get('all_captaincy_scores', {}).items():
                    if places > 0:  # Se a capitania teve pontuação
                        captaincy = cap
                        break
                
                await db.execute("""
                    INSERT INTO document_places (document_id, place_name, captaincy, frequency, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (document_id, place_name, captaincy, frequency, 0.9))
        
        elif extractor_type == 'themes' and results.get('results'):
            theme_results = results['results']
            
            await db.execute("DELETE FROM document_themes WHERE document_id = ?", (document_id,))
            
            # Armazena contagens de temas
            theme_counts = theme_results.get('theme_counts', {})
            theme_percentages = theme_results.get('theme_percentages', {})
            keyword_counts = theme_results.get('keyword_counts', {})
            
            for theme_name, count in theme_counts.items():
                if count > 0:
                    percentage = theme_percentages.get(theme_name, 0.0)
                    
                    # Insere tema principal
                    await db.execute("""
                        INSERT INTO document_themes (document_id, theme_name, frequency, percentage)
                        VALUES (?, ?, ?, ?)
                    """, (document_id, theme_name, count, percentage))
                    
                    # Insere palavras-chave específicas relacionadas ao tema
                    for keyword, kw_count in keyword_counts.items():
                        await db.execute("""
                            INSERT INTO document_themes (document_id, theme_name, keyword, frequency, percentage)
                            VALUES (?, ?, ?, ?, ?)
                        """, (document_id, theme_name, keyword, kw_count, 0.0))
    
    async def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Busca um documento por ID."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT id, filename, file_path, file_size, upload_date, 
                           total_pages, processing_status, created_at, updated_at
                    FROM documents WHERE id = ?
                """, (document_id,))
                
                row = await cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar documento: {e}")
            raise
    
    async def get_documents(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Lista documentos com paginação."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT id, filename, file_size, upload_date, total_pages, processing_status
                    FROM documents 
                    ORDER BY upload_date DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Erro ao listar documentos: {e}")
            raise
    
    async def get_document_count(self) -> int:
        """Retorna o total de documentos."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM documents")
                count = (await cursor.fetchone())[0]
                return count
                
        except Exception as e:
            logger.error(f"Erro ao contar documentos: {e}")
            return 0
    
    async def get_extractor_results(self, document_id: int) -> Dict[str, Any]:
        """Busca todos os resultados de extractors para um documento."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT extractor_type, results, created_at, execution_time_ms
                    FROM extractor_results 
                    WHERE document_id = ?
                    ORDER BY created_at DESC
                """, (document_id,))
                
                rows = await cursor.fetchall()
                
                results = {}
                latest_update = None
                
                for row in rows:
                    extractor_type = row['extractor_type']
                    extractor_results = json.loads(row['results'])
                    
                    results[extractor_type] = {
                        'results': extractor_results.get('results'),
                        'status': extractor_results.get('status'),
                        'message': extractor_results.get('message'),
                        'execution_time_ms': row['execution_time_ms'],
                        'created_at': row['created_at']
                    }
                    
                    if not latest_update or row['created_at'] > latest_update:
                        latest_update = row['created_at']
                
                results['last_updated'] = latest_update
                return results
                
        except Exception as e:
            logger.error(f"Erro ao buscar resultados dos extractors: {e}")
            return {}
    
    async def update_processing_status(self, document_id: int, status: str):
        """Atualiza o status de processamento de um documento."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE documents 
                    SET processing_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, document_id))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            raise
    
    async def delete_document(self, document_id: int) -> bool:
        """Remove um documento e todos os dados relacionados."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Verifica se documento existe
                cursor = await db.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
                if not await cursor.fetchone():
                    return False
                
                # Remove da tabela FTS primeiro
                await db.execute("DELETE FROM documents_fts WHERE document_id = ?", (document_id,))
                
                # Remove das tabelas relacionadas (CASCADE cuida do resto)
                await db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                
                await db.commit()
                logger.info(f"Documento {document_id} removido com sucesso")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao deletar documento: {e}")
            raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais da base de dados."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # Total de documentos
                cursor = await db.execute("SELECT COUNT(*) FROM documents")
                stats['total_documents'] = (await cursor.fetchone())[0]
                
                # Total de páginas
                cursor = await db.execute("SELECT SUM(total_pages) FROM documents")
                result = await cursor.fetchone()
                stats['total_pages'] = result[0] if result[0] else 0
                
                # Tamanho total dos arquivos
                cursor = await db.execute("SELECT SUM(file_size) FROM documents")
                result = await cursor.fetchone()
                stats['total_file_size'] = result[0] if result[0] else 0
                
                # Documentos por status
                cursor = await db.execute("""
                    SELECT processing_status, COUNT(*) 
                    FROM documents 
                    GROUP BY processing_status
                """)
                status_counts = await cursor.fetchall()
                stats['documents_by_status'] = {status: count for status, count in status_counts}
                
                # Top 10 capitanias mais mencionadas
                cursor = await db.execute("""
                    SELECT captaincy, COUNT(*) as mentions
                    FROM document_places 
                    WHERE captaincy IS NOT NULL
                    GROUP BY captaincy
                    ORDER BY mentions DESC
                    LIMIT 10
                """)
                captaincies = await cursor.fetchall()
                stats['top_captaincies'] = [{'name': cap, 'mentions': count} for cap, count in captaincies]
                
                # Top 10 nomes mais frequentes
                cursor = await db.execute("""
                    SELECT name_full, SUM(frequency) as total_freq
                    FROM document_names
                    GROUP BY name_normalized
                    ORDER BY total_freq DESC
                    LIMIT 10
                """)
                names = await cursor.fetchall()
                stats['top_names'] = [{'name': name, 'frequency': freq} for name, freq in names]
                
                # Distribuição por século
                cursor = await db.execute("""
                    SELECT 
                        CASE 
                            WHEN year_representative BETWEEN 1500 AND 1599 THEN '16'
                            WHEN year_representative BETWEEN 1600 AND 1699 THEN '17'
                            WHEN year_representative BETWEEN 1700 AND 1799 THEN '18'
                            WHEN year_representative BETWEEN 1800 AND 1899 THEN '19'
                            ELSE 'Outros'
                        END as century,
                        COUNT(*) as count
                    FROM document_dates
                    WHERE year_representative IS NOT NULL
                    GROUP BY century
                    ORDER BY century
                """)
                centuries = await cursor.fetchall()
                stats['documents_by_century'] = {f"Século {cent}": count for cent, count in centuries}
                
                # Temas mais frequentes
                cursor = await db.execute("""
                    SELECT theme_name, SUM(frequency) as total_freq
                    FROM document_themes
                    WHERE keyword IS NULL  -- Apenas temas principais
                    GROUP BY theme_name
                    ORDER BY total_freq DESC
                    LIMIT 10
                """)
                themes = await cursor.fetchall()
                stats['top_themes'] = [{'theme': theme, 'frequency': freq} for theme, freq in themes]
                
                return stats
                
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {}
    
    async def optimize_database(self):
        """Otimiza o banco de dados (vacuum, rebuild indexes, etc.)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                logger.info("Iniciando otimização do banco de dados...")
                
                # Atualiza estatísticas das tabelas
                await db.execute("ANALYZE")
                
                # Otimiza FTS
                await db.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
                
                # Vacuum incremental
                await db.execute("PRAGMA incremental_vacuum")
                
                await db.commit()
                logger.info("Otimização do banco concluída")
                
        except Exception as e:
            logger.error(f"Erro na otimização: {e}")
            raise

# Dependência para injeção nas rotas
async def get_db() -> DatabaseManager:
    """Retorna uma instância do gerenciador de banco."""
    return DatabaseManager()
