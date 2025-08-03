#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chat History Database Manager
Manages all chat history database operations with resilient handling.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models.chat_session import ChatSession, ChatMessage, ChatSchedule
from ..utils.logger import Logger


class ChatHistoryDatabase:
    """Manages chat history database operations"""
    
    def __init__(self, db_manager):
        """Initialize with database manager reference"""
        self.db_manager = db_manager
        self.logger = Logger()
        
    def _get_connection(self):
        """Get database connection"""
        return self.db_manager.get_chat_history_connection()
        
    def create_session(self, session: ChatSession) -> Dict[str, Any]:
        """Create a new chat session"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                session_dict = session.to_dict()
                
                cursor.execute('''
                    INSERT INTO chat_sessions 
                    (id, title, created_at, updated_at, project_id, 
                     task_id, tags, summary, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_dict['id'],
                    session_dict['title'],
                    session_dict['created_at'],
                    session_dict['updated_at'],
                    session_dict['project_id'],
                    session_dict['task_id'],
                    session_dict['tags'],
                    session_dict['summary'],
                    session_dict['status']
                ))
                conn.commit()
                
                self.logger.info(f"Created chat session: {session.id}")
                return {"success": True, "id": session.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create session: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing chat session"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                for key, value in updates.items():
                    if key in ['title', 'project_id', 'task_id', 'tags', 'summary', 'status']:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return {"success": False, "error": "No valid fields to update"}
                
                # Always update the timestamp
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(session_id)
                
                query = f"UPDATE chat_sessions SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                return {"success": True}
                
        except Exception as e:
            self.logger.error(f"Failed to update session: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_message(self, session_id: str, message: ChatMessage) -> Dict[str, Any]:
        """Add a message to a session"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                msg_dict = message.to_dict()
                
                cursor.execute('''
                    INSERT INTO chat_messages 
                    (id, session_id, message, is_user, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    msg_dict['id'],
                    session_id,
                    msg_dict['message'],
                    msg_dict['is_user'],
                    msg_dict['timestamp'],
                    msg_dict['metadata']
                ))
                
                # Update session timestamp
                cursor.execute('''
                    UPDATE chat_sessions 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (session_id,))
                
                conn.commit()
                return {"success": True}
                
        except Exception as e:
            self.logger.error(f"Failed to add message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a specific chat session with all messages"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get session
                cursor.execute('''
                    SELECT * FROM chat_sessions WHERE id = ?
                ''', (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                session = self._row_to_session(row)
                
                # Load messages
                session.messages = self.get_session_messages(session_id)
                
                return session
                
        except Exception as e:
            self.logger.error(f"Failed to get session: {str(e)}")
            return None
    
    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Get all messages for a session"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM chat_messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp ASC
                ''', (session_id,))
                
                messages = []
                for row in cursor.fetchall():
                    msg = self._row_to_message(row)
                    messages.append(msg)
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Failed to get messages: {str(e)}")
            return []
    
    def get_recent_sessions(
        self, 
        limit: int = 50,
        filter_date: Optional[datetime] = None,
        filter_project: Optional[str] = None,
        filter_task: Optional[str] = None,
        filter_status: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[ChatSession]:
        """Get recent chat sessions with optional filters"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM chat_sessions WHERE 1=1'
                params = []
                
                if filter_date:
                    query += ' AND DATE(created_at) = DATE(?)'
                    params.append(filter_date.isoformat())
                
                if filter_project:
                    query += ' AND project_id = ?'
                    params.append(filter_project)
                    
                if filter_task:
                    query += ' AND task_id = ?'
                    params.append(filter_task)
                    
                if filter_status:
                    query += ' AND status = ?'
                    params.append(filter_status)
                    
                if search_query:
                    query += ' AND (title LIKE ? OR summary LIKE ?)'
                    search_pattern = f'%{search_query}%'
                    params.extend([search_pattern, search_pattern])
                
                query += ' ORDER BY updated_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                
                sessions = []
                for row in cursor.fetchall():
                    session = self._row_to_session(row)
                    sessions.append(session)
                
                return sessions
                
        except Exception as e:
            self.logger.error(f"Failed to get recent sessions: {str(e)}")
            return []
    
    def search_messages(self, search_query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search through all chat messages"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT m.*, s.title as session_title 
                    FROM chat_messages m
                    JOIN chat_sessions s ON m.session_id = s.id
                    WHERE m.message LIKE ?
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                ''', (f'%{search_query}%', limit))
                
                results = []
                for row in cursor.fetchall():
                    result = {
                        'message': self._row_to_message(row),
                        'session_title': row[-1]  # Last column is session_title
                    }
                    results.append(result)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to search messages: {str(e)}")
            return []
    
    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a chat session and all its messages"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete messages first (foreign key constraint)
                cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
                
                # Delete schedules
                cursor.execute('DELETE FROM chat_schedules WHERE session_id = ?', (session_id,))
                
                # Delete session
                cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
                
                conn.commit()
                return {"success": True}
                
        except Exception as e:
            self.logger.error(f"Failed to delete session: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def archive_session(self, session_id: str) -> Dict[str, Any]:
        """Archive a chat session"""
        return self.update_session(session_id, {"status": "archived"})
    
    def clean_old_sessions(self, retention_days: int = 90) -> Dict[str, Any]:
        """Clean old chat sessions based on retention policy"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                # Get count of sessions to be deleted
                cursor.execute('''
                    SELECT COUNT(*) FROM chat_sessions 
                    WHERE created_at < ? AND status = 'archived'
                ''', (cutoff_date.isoformat(),))
                
                count = cursor.fetchone()[0]
                
                if count > 0:
                    # Delete old archived sessions and their messages
                    cursor.execute('''
                        DELETE FROM chat_messages 
                        WHERE session_id IN (
                            SELECT id FROM chat_sessions 
                            WHERE created_at < ? AND status = 'archived'
                        )
                    ''', (cutoff_date.isoformat(),))
                    
                    cursor.execute('''
                        DELETE FROM chat_sessions 
                        WHERE created_at < ? AND status = 'archived'
                    ''', (cutoff_date.isoformat(),))
                    
                    conn.commit()
                
                return {"success": True, "deleted_count": count}
                
        except Exception as e:
            self.logger.error(f"Failed to clean old sessions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get chat session statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total sessions
                cursor.execute('SELECT COUNT(*) FROM chat_sessions')
                stats['total_sessions'] = cursor.fetchone()[0]
                
                # Active sessions
                cursor.execute('SELECT COUNT(*) FROM chat_sessions WHERE status = "active"')
                stats['active_sessions'] = cursor.fetchone()[0]
                
                # Total messages
                cursor.execute('SELECT COUNT(*) FROM chat_messages')
                stats['total_messages'] = cursor.fetchone()[0]
                
                # Sessions by date
                cursor.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count 
                    FROM chat_sessions 
                    WHERE created_at > datetime('now', '-7 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''')
                
                stats['sessions_by_date'] = [
                    {'date': row[0], 'count': row[1]} 
                    for row in cursor.fetchall()
                ]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def _row_to_session(self, row) -> ChatSession:
        """Convert database row to ChatSession object"""
        return ChatSession.from_dict({
            'id': row[0],
            'title': row[1],
            'created_at': row[2],
            'updated_at': row[3],
            'project_id': row[4],
            'task_id': row[5],
            'tags': row[6],
            'summary': row[7],
            'status': row[8]
        })
    
    def _row_to_message(self, row) -> ChatMessage:
        """Convert database row to ChatMessage object"""
        return ChatMessage.from_dict({
            'id': row[0],
            'session_id': row[1],
            'message': row[2],
            'is_user': bool(row[3]),
            'timestamp': row[4],
            'metadata': row[5]
        })
    
    # Schedule management methods
    def create_schedule(self, schedule: ChatSchedule) -> Dict[str, Any]:
        """Create a new chat schedule"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                schedule_dict = schedule.to_dict()
                
                cursor.execute('''
                    INSERT INTO chat_schedules 
                    (id, session_id, cron_expression, next_run, last_run, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    schedule_dict['id'],
                    schedule_dict['session_id'],
                    schedule_dict['cron_expression'],
                    schedule_dict['next_run'],
                    schedule_dict['last_run'],
                    schedule_dict['is_active']
                ))
                conn.commit()
                
                return {"success": True, "id": schedule.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create schedule: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_active_schedules(self) -> List[ChatSchedule]:
        """Get all active schedules that need to run"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM chat_schedules 
                    WHERE is_active = 1 AND 
                    (next_run IS NULL OR next_run <= datetime('now'))
                ''')
                
                schedules = []
                for row in cursor.fetchall():
                    schedule = ChatSchedule(
                        id=row[0],
                        session_id=row[1],
                        cron_expression=row[2],
                        next_run=datetime.fromisoformat(row[3]) if row[3] else None,
                        last_run=datetime.fromisoformat(row[4]) if row[4] else None,
                        is_active=bool(row[5])
                    )
                    schedules.append(schedule)
                
                return schedules
                
        except Exception as e:
            self.logger.error(f"Failed to get active schedules: {str(e)}")
            return []