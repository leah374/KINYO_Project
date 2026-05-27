"""
History Database Manager
SQLite database for storing generation history
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryDatabase:
    """Manages generation history in SQLite database"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent / "database" / "kinuyo_history.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS script_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                brief TEXT NOT NULL,
                objective TEXT,
                duration INTEGER,
                result TEXT NOT NULL,
                metadata TEXT,
                file_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storyboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                script_id INTEGER,
                source_file TEXT,
                result TEXT NOT NULL,
                shots_count INTEGER,
                metadata TEXT,
                file_path TEXT,
                FOREIGN KEY (script_id) REFERENCES script_history(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                storyboard_id INTEGER,
                source_file TEXT,
                result TEXT NOT NULL,
                clips_count INTEGER,
                duration_seconds REAL,
                file_size_mb REAL,
                metadata TEXT,
                file_path TEXT,
                FOREIGN KEY (storyboard_id) REFERENCES storyboard_history(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS full_pipeline_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                brief TEXT NOT NULL,
                script_id INTEGER,
                storyboard_id INTEGER,
                video_id INTEGER,
                total_duration_seconds REAL,
                metadata TEXT,
                FOREIGN KEY (script_id) REFERENCES script_history(id),
                FOREIGN KEY (storyboard_id) REFERENCES storyboard_history(id),
                FOREIGN KEY (video_id) REFERENCES video_history(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_script_generation(
        self,
        brief: str,
        result: Dict[str, Any],
        objective: Optional[str] = None,
        duration: Optional[int] = None,
        metadata: Optional[Dict] = None,
        file_path: Optional[str] = None
    ) -> int:
        """Save script generation to history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO script_history 
            (timestamp, brief, objective, duration, result, metadata, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            brief,
            objective,
            duration,
            json.dumps(result, ensure_ascii=False),
            json.dumps(metadata or {}, ensure_ascii=False),
            file_path
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def save_storyboard_generation(
        self,
        result: Dict[str, Any],
        script_id: Optional[int] = None,
        source_file: Optional[str] = None,
        metadata: Optional[Dict] = None,
        file_path: Optional[str] = None
    ) -> int:
        """Save storyboard generation to history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        shots_count = len(result.get("storyboard", []))
        
        cursor.execute('''
            INSERT INTO storyboard_history 
            (timestamp, script_id, source_file, result, shots_count, metadata, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            script_id,
            source_file,
            json.dumps(result, ensure_ascii=False),
            shots_count,
            json.dumps(metadata or {}, ensure_ascii=False),
            file_path
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def save_video_generation(
        self,
        result: Dict[str, Any],
        storyboard_id: Optional[int] = None,
        source_file: Optional[str] = None,
        metadata: Optional[Dict] = None,
        file_path: Optional[str] = None
    ) -> int:
        """Save video generation to history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        clips_count = result.get("job_count", 0)
        
        cursor.execute('''
            INSERT INTO video_history 
            (timestamp, storyboard_id, source_file, result, clips_count, duration_seconds, file_size_mb, metadata, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            storyboard_id,
            source_file,
            json.dumps(result, ensure_ascii=False),
            clips_count,
            metadata.get("duration_seconds") if metadata else None,
            metadata.get("file_size_mb") if metadata else None,
            json.dumps(metadata or {}, ensure_ascii=False),
            file_path
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def save_full_pipeline(
        self,
        brief: str,
        script_id: int,
        storyboard_id: int,
        video_id: int,
        total_duration: float,
        metadata: Optional[Dict] = None
    ) -> int:
        """Save full pipeline run to history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO full_pipeline_history 
            (timestamp, brief, script_id, storyboard_id, video_id, total_duration_seconds, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            brief,
            script_id,
            storyboard_id,
            video_id,
            total_duration,
            json.dumps(metadata or {}, ensure_ascii=False)
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_script_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get script generation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM script_history
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_storyboard_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get storyboard generation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM storyboard_history
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_video_history(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get video generation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM video_history
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_history(
        self,
        limit: int = 50,
        offset: int = 0,
        history_type: Optional[str] = None
    ) -> List[Dict]:
        """Get all history with optional filtering"""
        results = []
        
        if history_type is None or history_type == "script":
            for row in self.get_script_history(limit, offset):
                row["type"] = "script"
                results.append(row)
        
        if history_type is None or history_type == "storyboard":
            for row in self.get_storyboard_history(limit, offset):
                row["type"] = "storyboard"
                results.append(row)
        
        if history_type is None or history_type == "video":
            for row in self.get_video_history(limit, offset):
                row["type"] = "video"
                results.append(row)
        
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]
    
    def delete_record(self, history_type: str, record_id: int) -> bool:
        """Delete a history record"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        table_map = {
            "script": "script_history",
            "storyboard": "storyboard_history",
            "video": "video_history"
        }
        
        table_name = table_map.get(history_type)
        if not table_name:
            conn.close()
            return False
        
        cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (record_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def search_history(self, query: str, history_type: Optional[str] = None) -> List[Dict]:
        """Search history by query"""
        all_history = self.get_all_history(limit=1000, history_type=history_type)
        
        results = []
        query_lower = query.lower()
        
        for record in all_history:
            if query_lower in record.get("brief", "").lower():
                results.append(record)
            elif query_lower in record.get("source_file", "").lower():
                results.append(record)
        
        return results
    
    def get_record_by_id(self, history_type: str, record_id: int) -> Optional[Dict]:
        """Get a specific record by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        table_map = {
            "script": "script_history",
            "storyboard": "storyboard_history",
            "video": "video_history"
        }
        
        table_name = table_map.get(history_type)
        if not table_name:
            conn.close()
            return None
        
        cursor.execute(f'SELECT * FROM {table_name} WHERE id = ?', (record_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM script_history')
        stats["script_count"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM storyboard_history')
        stats["storyboard_count"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM video_history')
        stats["video_count"] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM full_pipeline_history')
        stats["full_pipeline_count"] = cursor.fetchone()[0]
        
        conn.close()
        return stats
