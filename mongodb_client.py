import motor.motor_asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class MongoDBClient:
    """
    Cliente para interação com MongoDB.
    Focado na coleção scraped_items para buscar URLs de PDFs.
    """
    
    def __init__(self, connection_string: str = None, database_name: str = "oxossi_scraped"):
        self.connection_string = connection_string or os.getenv(
            'MONGODB_CONNECTION_STRING', 
            'mongodb://localhost:27017'
        )
        self.database_name = database_name
        self.client = None
        self.db = None
        
    async def connect(self):
        """Conecta ao MongoDB."""
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Testa a conexão
            await self.client.admin.command('ping')
            logger.info(f"Conectado ao MongoDB: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Desconecta do MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Desconectado do MongoDB")
    
    async def get_pdf_urls(self, limit: int = 100, offset: int = 0, 
                          filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Busca URLs de PDFs na coleção scraped_items.
        
        Args:
            limit: Número máximo de resultados
            offset: Offset para paginação
            filters: Filtros adicionais para a consulta
            
        Returns:
            Dict com PDFs encontrados e metadados
        """
        try:
            collection = self.db.scraped_items
            
            # Constrói query MongoDB
            query = self._build_pdf_query(filters)
            
            # Projeção para retornar apenas campos relevantes
            projection = {
                'url': 1,
                'title': 1,
                'description': 1,
                'scraped_at': 1,
                'file_size': 1,
                'content_type': 1,
                'source_url': 1,
                'metadata': 1,
                '_id': 1
            }
            
            # Executa consulta com paginação
            cursor = collection.find(query, projection)
            cursor = cursor.skip(offset).limit(limit)
            
            # Ordena por data de scraping (mais recentes primeiro)
            cursor = cursor.sort('scraped_at', -1)
            
            # Busca documentos
            documents = await cursor.to_list(length=limit)
            
            # Conta total de documentos
            total_count = await collection.count_documents(query)
            
            # Formata resultados
            pdf_urls = []
            for doc in documents:
                pdf_info = {
                    'id': str(doc['_id']),
                    'url': doc.get('url'),
                    'title': doc.get('title', 'Sem título'),
                    'description': doc.get('description', ''),
                    'scraped_at': doc.get('scraped_at'),
                    'file_size': doc.get('file_size'),
                    'content_type': doc.get('content_type'),
                    'source_url': doc.get('source_url'),
                    'metadata': doc.get('metadata', {})
                }
                pdf_urls.append(pdf_info)
            
            return {
                'pdfs': pdf_urls,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(pdf_urls)) < total_count
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar PDFs no MongoDB: {e}")
            raise
    
    def _build_pdf_query(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Constrói query MongoDB para buscar PDFs."""
        query = {}
        
        # Filtro base: apenas URLs que terminam com .pdf ou têm content_type de PDF
        pdf_conditions = [
            {'url': {'$regex': r'\.pdf$', '$options': 'i'}},
            {'content_type': {'$regex': r'application/pdf', '$options': 'i'}},
            {'content_type': {'$regex': r'pdf', '$options': 'i'}}
        ]
        query['$or'] = pdf_conditions
        
        if filters:
            # Filtro por data
            if 'date_from' in filters or 'date_to' in filters:
                date_filter = {}
                if 'date_from' in filters:
                    date_filter['$gte'] = filters['date_from']
                if 'date_to' in filters:
                    date_filter['$lte'] = filters['date_to']
                query['scraped_at'] = date_filter
            
            # Filtro por título
            if 'title' in filters:
                query['title'] = {'$regex': filters['title'], '$options': 'i'}
            
            # Filtro por descrição
            if 'description' in filters:
                query['description'] = {'$regex': filters['description'], '$options': 'i'}
            
            # Filtro por tamanho mínimo do arquivo
            if 'min_file_size' in filters:
                query['file_size'] = {'$gte': filters['min_file_size']}
            
            # Filtro por fonte
            if 'source' in filters:
                query['source_url'] = {'$regex': filters['source'], '$options': 'i'}
            
            # Filtro por domínio
            if 'domain' in filters:
                query['url'] = {'$regex': f"https?://{filters['domain']}", '$options': 'i'}
        
        return query
    
    async def get_pdf_by_id(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """Busca um PDF específico por ID."""
        try:
            from bson import ObjectId
            
            collection = self.db.scraped_items
            
            doc = await collection.find_one({'_id': ObjectId(pdf_id)})
            
            if doc:
                return {
                    'id': str(doc['_id']),
                    'url': doc.get('url'),
                    'title': doc.get('title'),
                    'description': doc.get('description'),
                    'scraped_at': doc.get('scraped_at'),
                    'file_size': doc.get('file_size'),
                    'content_type': doc.get('content_type'),
                    'source_url': doc.get('source_url'),
                    'metadata': doc.get('metadata', {})
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar PDF por ID: {e}")
            return None
    
    async def get_pdf_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas sobre os PDFs na coleção."""
        try:
            collection = self.db.scraped_items
            
            # Query base para PDFs
            pdf_query = self._build_pdf_query()
            
            # Total de PDFs
            total_pdfs = await collection.count_documents(pdf_query)
            
            # PDFs por domínio (top 10)
            domain_pipeline = [
                {'$match': pdf_query},
                {
                    '$addFields': {
                        'domain': {
                            '$arrayElemAt': [
                                {'$split': [
                                    {'$arrayElemAt': [{'$split': ['$url', '://']}, 1]},
                                    '/'
                                ]}, 0
                            ]
                        }
                    }
                },
                {'$group': {'_id': '$domain', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]
            
            domains_cursor = collection.aggregate(domain_pipeline)
            domains = await domains_cursor.to_list(length=10)
            
            # PDFs por mês (últimos 12 meses)
            monthly_pipeline = [
                {'$match': pdf_query},
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$scraped_at'},
                            'month': {'$month': '$scraped_at'}
                        },
                        'count': {'$sum': 1}
                    }
                },
                {'$sort': {'_id.year': -1, '_id.month': -1}},
                {'$limit': 12}
            ]
            
            monthly_cursor = collection.aggregate(monthly_pipeline)
            monthly_data = await monthly_cursor.to_list(length=12)
            
            # Tamanho total dos arquivos
            size_pipeline = [
                {'$match': pdf_query},
                {'$match': {'file_size': {'$exists': True, '$ne': None}}},
                {
                    '$group': {
                        '_id': None,
                        'total_size': {'$sum': '$file_size'},
                        'avg_size': {'$avg': '$file_size'},
                        'max_size': {'$max': '$file_size'},
                        'min_size': {'$min': '$file_size'}
                    }
                }
            ]
            
            size_cursor = collection.aggregate(size_pipeline)
            size_stats = await size_cursor.to_list(length=1)
            
            return {
                'total_pdfs': total_pdfs,
                'pdfs_by_domain': [
                    {'domain': item['_id'], 'count': item['count']} 
                    for item in domains
                ],
                'pdfs_by_month': [
                    {
                        'year': item['_id']['year'],
                        'month': item['_id']['month'], 
                        'count': item['count']
                    }
                    for item in monthly_data
                ],
                'file_size_stats': size_stats[0] if size_stats else {
                    'total_size': 0, 'avg_size': 0, 'max_size': 0, 'min_size': 0
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas: {e}")
            return {}
    
    async def search_pdfs_by_text(self, search_text: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Busca PDFs por texto no título ou descrição.
        
        Args:
            search_text: Texto para buscar
            limit: Número máximo de resultados
            
        Returns:
            Lista de PDFs que correspondem à busca
        """
        try:
            collection = self.db.scraped_items
            
            # Query combinada: PDFs + busca textual
            base_query = self._build_pdf_query()
            
            text_query = {
                '$or': [
                    {'title': {'$regex': search_text, '$options': 'i'}},
                    {'description': {'$regex': search_text, '$options': 'i'}},
                    {'metadata.keywords': {'$regex': search_text, '$options': 'i'}}
                ]
            }
            
            combined_query = {'$and': [base_query, text_query]}
            
            # Executa busca
            cursor = collection.find(combined_query, {
                'url': 1, 'title': 1, 'description': 1, 'scraped_at': 1,
                'file_size': 1, 'source_url': 1, '_id': 1
            })
            
            cursor = cursor.sort('scraped_at', -1).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            return [
                {
                    'id': str(doc['_id']),
                    'url': doc.get('url'),
                    'title': doc.get('title', 'Sem título'),
                    'description': doc.get('description', ''),
                    'scraped_at': doc.get('scraped_at'),
                    'file_size': doc.get('file_size'),
                    'source_url': doc.get('source_url')
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Erro na busca textual: {e}")
            return []

# Dependência para injeção nas rotas
_mongo_client = None

async def get_mongo_client() -> MongoDBClient:
    """Retorna instância do cliente MongoDB (singleton)."""
    global _mongo_client
    
    if _mongo_client is None:
        _mongo_client = MongoDBClient()
        await _mongo_client.connect()
    
    return _mongo_client

async def close_mongo_connection():
    """Fecha conexão MongoDB."""
    global _mongo_client
    
    if _mongo_client:
        await _mongo_client.disconnect()
        _mongo_client = None
