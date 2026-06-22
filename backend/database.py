import sqlite3
import numpy as np
import os
import hashlib
from collections import deque
from config import config

# 优雅降级：尝试导入向量检索依赖，失败则使用关键词匹配
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    print("[init] Loading embedding model...")
    EMBEDDING_MODEL = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    VECTOR_SEARCH_AVAILABLE = True
    print("[init] Vector search enabled")
except ImportError as e:
    VECTOR_SEARCH_AVAILABLE = False
    print(f"[init] Vector search not available ({e}), using keyword matching fallback")

class ImperfectDB:
    def __init__(self):
        # 确保数据目录存在
        db_dir = os.path.dirname(config.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        self.conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
        
        if VECTOR_SEARCH_AVAILABLE:
            self._init_faiss()
            
        self.recent_hashes = deque(maxlen=200)  # 防刷屏去重队列

    def _init_db(self):
        """初始化数据表，对齐v3.1三元组数据结构"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS scars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT DEFAULT 'anonymous',
                credit_score INTEGER DEFAULT 600,
                source_platform TEXT DEFAULT 'api',
                task TEXT,
                pre_condition TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                failure_action TEXT DEFAULT 'Unknown',
                failure_error TEXT,
                failure_trace TEXT DEFAULT '',
                reflection_analysis TEXT,
                corrected_action TEXT,
                uncertainty_score REAL DEFAULT 0.5,
                valid_votes INTEGER DEFAULT 0,
                invalid_votes INTEGER DEFAULT 0,
                freshness_level TEXT DEFAULT 'active',
                data_quality TEXT DEFAULT 'complete',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def _init_faiss(self):
        """初始化向量索引，使用IndexIDMap绑定数据库主键，彻底解决映射错位"""
        if os.path.exists(config.FAISS_PATH):
            self.index = faiss.read_index(config.FAISS_PATH)
        else:
            # 内积相似度（归一化后等价余弦）+ ID映射
            base_index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
            self.index = faiss.IndexIDMap(base_index)

    def _get_embedding(self, text: str) -> np.ndarray:
        """生成向量嵌入（仅向量模式可用）"""
        embedding = EMBEDDING_MODEL.encode(text)
        faiss.normalize_L2(embedding.reshape(1, -1))
        return embedding.astype("float32")

    def is_duplicate(self, task: str, error: str) -> bool:
        """防死循环刷屏：MD5哈希去重"""
        text_hash = hashlib.md5(f"{task}{error}".encode()).hexdigest()
        if text_hash in self.recent_hashes:
            return True
        self.recent_hashes.append(text_hash)
        return False

    def add_scar(
        self, task, failure_action, failure_error, 
        reflection_analysis, corrected_action, uncertainty_score, 
        source_platform, pre_condition="", tags="", 
        agent_id="anonymous", failure_trace=""
    ):
        """新增疤痕，同步写入数据库和向量索引"""
        if self.is_duplicate(task, failure_error):
            return -1  # 重复数据拦截

        # 数据质量判断
        data_quality = "complete" if reflection_analysis and corrected_action else "incomplete"

        # 写入数据库
        cursor = self.conn.execute('''
            INSERT INTO scars (
                agent_id, credit_score, source_platform, task, pre_condition, tags,
                failure_action, failure_error, failure_trace,
                reflection_analysis, corrected_action, uncertainty_score,
                data_quality
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            agent_id, config.DEFAULT_CREDIT_SCORE, source_platform, task, pre_condition, tags,
            failure_action, failure_error, failure_trace,
            reflection_analysis, corrected_action, uncertainty_score,
            data_quality
        ))
        self.conn.commit()
        scar_id = cursor.lastrowid

        # 写入向量索引（仅向量模式可用）
        if VECTOR_SEARCH_AVAILABLE:
            embed_text = f"{task} {failure_error} {reflection_analysis} {corrected_action}"
            embedding = self._get_embedding(embed_text)
            self.index.add_with_ids(
                np.array([embedding], dtype="float32"),
                np.array([scar_id], dtype="int64")
            )
            faiss.write_index(self.index, config.FAISS_PATH)

        return scar_id

    def search_scars(self, query: str, limit: int = 5, min_quality: str = None):
        """搜索疤痕，向量模式用相似度，降级模式用关键词匹配"""
        if VECTOR_SEARCH_AVAILABLE and self.index.ntotal > 0:
            # 向量相似度搜索
            query_embedding = self._get_embedding(query)
            distances, indices = self.index.search(
                np.array([query_embedding], dtype="float32"), limit
            )

            results = []
            for dist, scar_id in zip(distances[0], indices[0]):
                if scar_id == -1:
                    continue
                row = self.conn.execute("SELECT * FROM scars WHERE id = ?", (int(scar_id),)).fetchone()
                if not row:
                    continue
                # 质量过滤
                if min_quality and row["data_quality"] != min_quality:
                    continue
                results.append({
                    "id": row["id"],
                    "task": row["task"],
                    "pre_condition": row["pre_condition"],
                    "tags": row["tags"],
                    "failure_error": row["failure_error"],
                    "failure_action": row["failure_action"],
                    "reflection_analysis": row["reflection_analysis"],
                    "corrected_action": row["corrected_action"],
                    "uncertainty_score": row["uncertainty_score"],
                    "freshness_level": row["freshness_level"],
                    "credit_score": row["credit_score"],
                    "similarity": round(float(dist), 4)
                })
            return results
        else:
            # 降级：关键词模糊匹配
            query_lower = query.lower()
            query = f"%{query}%"
            sql = """
                SELECT * FROM scars 
                WHERE task LIKE ? 
                   OR failure_error LIKE ? 
                   OR reflection_analysis LIKE ?
                   OR corrected_action LIKE ?
            """
            params = [query, query, query, query]
            
            if min_quality:
                sql += " AND data_quality = ?"
                params.append(min_quality)
            
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            
            rows = self.conn.execute(sql, params).fetchall()
            
            results = []
            for row in rows:
                # 简单计算关键词匹配相似度
                text = f"{row['task']} {row['failure_error']} {row['reflection_analysis']}".lower()
                match_count = sum(1 for word in query_lower.split() if word in text)
                similarity = round(match_count / max(len(query_lower.split()), 1), 4)
                
                results.append({
                    "id": row["id"],
                    "task": row["task"],
                    "pre_condition": row["pre_condition"],
                    "tags": row["tags"],
                    "failure_error": row["failure_error"],
                    "failure_action": row["failure_action"],
                    "reflection_analysis": row["reflection_analysis"],
                    "corrected_action": row["corrected_action"],
                    "uncertainty_score": row["uncertainty_score"],
                    "freshness_level": row["freshness_level"],
                    "credit_score": row["credit_score"],
                    "similarity": similarity
                })
            return results

    def get_stats(self):
        """获取全局统计数据"""
        total = self.conn.execute("SELECT COUNT(*) FROM scars").fetchone()[0]
        complete = self.conn.execute("SELECT COUNT(*) FROM scars WHERE data_quality = 'complete'").fetchone()[0]
        platforms = self.conn.execute(
            "SELECT source_platform, COUNT(*) as cnt FROM scars GROUP BY source_platform"
        ).fetchall()
        return {
            "total_scars": total,
            "complete_reflection": complete,
            "platform_distribution": {row["source_platform"]: row["cnt"] for row in platforms},
            "search_mode": "vector" if VECTOR_SEARCH_AVAILABLE else "keyword"
        }

    def export_dpo(self, tags: str = "", min_quality: str = "complete"):
        """导出DPO训练格式数据集"""
        query = "SELECT * FROM scars WHERE data_quality = ?"
        params = [min_quality]
        if tags:
            query += " AND tags LIKE ?"
            params.append(f"%{tags}%")
        
        rows = self.conn.execute(query, params).fetchall()
        dpo_list = []
        for row in rows:
            prompt = row["task"]
            if row["pre_condition"]:
                prompt += f"\n前置条件：{row['pre_condition']}"
            dpo_list.append({
                "prompt": prompt,
                "chosen": row["corrected_action"],
                "rejected": row["failure_action"]
            })
        return dpo_list

# 全局单例
db = ImperfectDB()
