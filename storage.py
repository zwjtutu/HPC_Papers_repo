"""
论文存储模块
使用SQLite数据库存储已处理的论文，避免重复发送
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PaperStorage:
    """论文存储管理器"""
    
    def __init__(self, db_path: str, max_storage_size: int = 0):
        """
        初始化存储管理器
        
        Args:
            db_path: SQLite数据库路径
            max_storage_size: 最大存储数量，0表示无限制
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_storage_size = max_storage_size
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                arxiv_id TEXT UNIQUE,
                title TEXT,
                authors TEXT,
                summary TEXT,
                published TEXT,
                link TEXT,
                pdf_link TEXT,
                categories TEXT,
                relevance_score REAL,
                relevance_reason TEXT,
                created_at TEXT,
                sent_at TEXT,
                last_accessed TEXT
            )
        """)
        
        # 如果表已存在但没有last_accessed字段，添加该字段
        cursor.execute("PRAGMA table_info(papers)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'last_accessed' not in columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN last_accessed TEXT")
            logger.info("已添加 last_accessed 字段到数据库表")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_arxiv_id ON papers(arxiv_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_published ON papers(published)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_accessed ON papers(last_accessed)
        """)
        
        conn.commit()
        conn.close()
    
    def paper_exists(self, arxiv_id: str) -> bool:
        """
        检查论文是否已存在，并更新访问时间（LRU）
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            是否存在
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        exists = cursor.fetchone() is not None
        
        # 如果存在，更新最后访问时间（LRU逻辑）
        if exists:
            cursor.execute("""
                UPDATE papers 
                SET last_accessed = ? 
                WHERE arxiv_id = ?
            """, (datetime.now().isoformat(), arxiv_id))
            conn.commit()
        
        conn.close()
        return exists
    
    def add_paper(self, paper: Dict, sent: bool = False):
        """
        添加论文到数据库，如果超过上限则删除最久未访问的论文（LRU）
        
        Args:
            paper: 论文字典
            sent: 是否已发送
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否需要执行LRU清理（在插入前检查，避免超过上限）
        if self.max_storage_size > 0:
            # 先检查论文是否已存在
            cursor.execute("SELECT 1 FROM papers WHERE arxiv_id = ?", (paper.get('arxiv_id'),))
            paper_exists = cursor.fetchone() is not None
            
            # 如果论文不存在，需要检查存储上限
            if not paper_exists:
                self._enforce_lru_limit(conn, cursor)
        
        try:
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT OR REPLACE INTO papers 
                (id, arxiv_id, title, authors, summary, published, link, pdf_link,
                 categories, relevance_score, relevance_reason, created_at, sent_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.get('id'),
                paper.get('arxiv_id'),
                paper.get('title'),
                ', '.join(paper.get('authors', [])),
                paper.get('summary'),
                paper.get('published'),
                paper.get('link'),
                paper.get('pdf_link'),
                ', '.join(paper.get('categories', [])),
                paper.get('relevance_score'),
                paper.get('relevance_reason'),
                now,
                now if sent else None,
                now  # 新添加的论文，访问时间设为当前时间
            ))
            
            conn.commit()
        except sqlite3.IntegrityError:
            # 如果已存在，更新发送状态和访问时间
            now = datetime.now().isoformat()
            if sent:
                cursor.execute("""
                    UPDATE papers 
                    SET sent_at = ?, relevance_score = ?, relevance_reason = ?, last_accessed = ?
                    WHERE arxiv_id = ?
                """, (
                    now,
                    paper.get('relevance_score'),
                    paper.get('relevance_reason'),
                    now,
                    paper.get('arxiv_id')
                ))
            else:
                # 即使未发送，也更新访问时间
                cursor.execute("""
                    UPDATE papers 
                    SET relevance_score = ?, relevance_reason = ?, last_accessed = ?
                    WHERE arxiv_id = ?
                """, (
                    paper.get('relevance_score'),
                    paper.get('relevance_reason'),
                    now,
                    paper.get('arxiv_id')
                ))
            conn.commit()
        finally:
            conn.close()
    
    def _enforce_lru_limit(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor):
        """
        执行LRU清理：如果超过存储上限，删除最久未访问的论文
        
        Args:
            conn: 数据库连接
            cursor: 数据库游标
        """
        # 获取当前论文数量
        cursor.execute("SELECT COUNT(*) FROM papers")
        current_count = cursor.fetchone()[0]
        
        if current_count >= self.max_storage_size:
            # 计算需要删除的数量
            delete_count = current_count - self.max_storage_size + 1
            
            # 查找最久未访问的论文（按last_accessed排序，NULL值优先）
            cursor.execute("""
                SELECT arxiv_id, title 
                FROM papers 
                ORDER BY 
                    CASE WHEN last_accessed IS NULL THEN 0 ELSE 1 END,
                    last_accessed ASC,
                    created_at ASC
                LIMIT ?
            """, (delete_count,))
            
            papers_to_delete = cursor.fetchall()
            
            if papers_to_delete:
                arxiv_ids = [row[0] for row in papers_to_delete]
                placeholders = ','.join(['?'] * len(arxiv_ids))
                cursor.execute(f"DELETE FROM papers WHERE arxiv_id IN ({placeholders})", arxiv_ids)
                
                deleted_titles = [row[1] for row in papers_to_delete]
                logger.info(f"LRU清理: 删除了 {len(papers_to_delete)} 篇最久未访问的论文")
                logger.debug(f"删除的论文: {', '.join(deleted_titles[:5])}{'...' if len(deleted_titles) > 5 else ''}")
    
    def add_papers(self, papers: List[Dict], sent: bool = False):
        """
        批量添加论文
        
        Args:
            papers: 论文列表
            sent: 是否已发送
        """
        for paper in papers:
            self.add_paper(paper, sent)
    
    def filter_new_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        过滤出新的论文（数据库中不存在的）
        
        Args:
            papers: 论文列表
            
        Returns:
            新的论文列表
        """
        new_papers = []
        for paper in papers:
            if not self.paper_exists(paper.get('arxiv_id')):
                new_papers.append(paper)
        
        logger.info(f"过滤后: {len(new_papers)}/{len(papers)} 篇新论文")
        return new_papers
    
    def get_recent_papers(self, days: int = 7) -> List[Dict]:
        """
        获取最近几天的论文，并更新访问时间（LRU）
        
        Args:
            days: 天数
            
        Returns:
            论文列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM papers 
            WHERE published >= ?
            ORDER BY published DESC
        """, (cutoff_date,))
        
        rows = cursor.fetchall()
        papers = [self._row_to_dict(row) for row in rows]
        
        # 更新访问时间（LRU逻辑）
        if papers:
            now = datetime.now().isoformat()
            arxiv_ids = [row['arxiv_id'] for row in rows]
            placeholders = ','.join(['?'] * len(arxiv_ids))
            cursor.execute(f"""
                UPDATE papers 
                SET last_accessed = ? 
                WHERE arxiv_id IN ({placeholders})
            """, [now] + arxiv_ids)
            conn.commit()
        
        conn.close()
        return papers
    
    def get_storage_stats(self) -> Dict:
        """
        获取存储统计信息
        
        Returns:
            包含总数、已发送数、未发送数等信息的字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM papers")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM papers WHERE sent_at IS NOT NULL")
        sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM papers WHERE last_accessed IS NULL")
        never_accessed = cursor.fetchone()[0]
        
        # 获取最久未访问的论文
        cursor.execute("""
            SELECT arxiv_id, title, last_accessed, created_at
            FROM papers 
            ORDER BY 
                CASE WHEN last_accessed IS NULL THEN 0 ELSE 1 END,
                last_accessed ASC,
                created_at ASC
            LIMIT 5
        """)
        oldest_papers = cursor.fetchall()
        
        conn.close()
        
        return {
            'total': total,
            'sent': sent,
            'unsent': total - sent,
            'never_accessed': never_accessed,
            'max_storage_size': self.max_storage_size,
            'oldest_papers': [
                {
                    'arxiv_id': row[0],
                    'title': row[1],
                    'last_accessed': row[2],
                    'created_at': row[3]
                }
                for row in oldest_papers
            ]
        }
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """将数据库行转换为字典"""
        return {
            'id': row['id'],
            'arxiv_id': row['arxiv_id'],
            'title': row['title'],
            'authors': row['authors'].split(', ') if row['authors'] else [],
            'summary': row['summary'],
            'published': row['published'],
            'link': row['link'],
            'pdf_link': row['pdf_link'],
            'categories': row['categories'].split(', ') if row['categories'] else [],
            'relevance_score': row['relevance_score'],
            'relevance_reason': row['relevance_reason']
        }
