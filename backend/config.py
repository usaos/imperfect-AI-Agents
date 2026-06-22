import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 数据库路径
    DB_PATH = os.getenv("DB_PATH", "imperfect.db")
    FAISS_PATH = os.getenv("FAISS_PATH", "scars.faiss")
    
    # Embedding 模型
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM = 384  # 对应 all-MiniLM-L6-v2 维度
    
    # API 鉴权
    API_KEY = os.getenv("API_KEY", "")  # 为空则不开启鉴权
    
    # 默认配置
    DEFAULT_CREDIT_SCORE = int(os.getenv("INIT_CREDIT_SCORE", 600))
    DEFAULT_FRESHNESS_LEVEL = "active"
    DEFAULT_DATA_QUALITY = "complete"

config = Config()
