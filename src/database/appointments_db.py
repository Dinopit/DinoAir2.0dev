#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Appointments Database Manager
Manages all calendar event database operations with resilient handling.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any

from ..models.calendar_event import CalendarEvent
from ..utils.logger import Logger


class AppointmentsDatabase:
    """Manages appointments/calendar events database operations"""
    
    def __init__(self, db_manager):
        """Initialize with database manager reference"""
        self.db_manager = db_manager
        self.logger = Logger()
        
    def _get_connection(self):
        """Get database connection"""
        return self.db_manager.get_appointments_connection()
        
    def create_event(self, event: CalendarEvent) -> Dict[str, Any]:
        """Create a new calendar event"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                event_dict = event.to_dict()
                
                cursor.execute('''
                    INSERT INTO calendar_events 
                    (id, title, description, event_type, status, event_date,
                     start_time, end_time, all_day, location, participants,
                     project_id, chat_session_id, recurrence_pattern,
                     recurrence_rule, reminder_minutes_before, reminder_sent,
                     tags, notes, color, metadata, created_at, updated_at,
                     completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_dict['id'],
                    event_dict['title'],
                    event_dict['description'],
                    event_dict['event_type'],
                    event_dict['status'],
                    event_dict['event_date'],
                    event_dict['start_time'],
                    event_dict['end_time'],
                    event_dict['all_day'],
                    event_dict['location'],
                    event_dict['participants'],
                    event_dict['project_id'],
                    event_dict['chat_session_id'],
                    event_dict['recurrence_pattern'],
                    event_dict['recurrence_rule'],
                    event_dict['reminder_minutes_before'],
                    event_dict['reminder_sent'],
                    event_dict['tags'],
                    event_dict['notes'],
                    event_dict['color'],
                    event_dict['metadata'],
                    event_dict['created_at'],
                    event_dict['updated_at'],
                    event_dict['completed_at']
                ))
                
                # Create reminder if specified
                if event.reminder_minutes_before and event.event_date:
                    self._create_reminder(cursor, event)
                
                conn.commit()
                
                self.logger.info(f"Created calendar event: {event.id}")
                return {"success": True, "id": event.id}
                
        except Exception as e:
            self.logger.error(f"Failed to create event: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_event(self, event_id: str, 
                     updates: Dict[str, Any]) -> bool:
        """Update an existing calendar event"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                params = []
                
                # Allowed fields for update
                allowed_fields = [
                    'title', 'description', 'event_type', 'status',
                    'event_date', 'start_time', 'end_time', 'all_day',
                    'location', 'participants', 'project_id',
                    'chat_session_id', 'recurrence_pattern',
                    'recurrence_rule', 'reminder_minutes_before',
                    'reminder_sent', 'tags', 'notes', 'color', 'metadata',
                    'completed_at'
                ]
                
                for key, value in updates.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = ?")
                        # Handle special formatting for certain fields
                        if key == 'participants' and isinstance(value, list):
                            value = ','.join(value)
                        elif key == 'tags' and isinstance(value, list):
                            value = ','.join(value)
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                # Always update the timestamp
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(event_id)
                
                query = f"""UPDATE calendar_events 
                           SET {', '.join(set_clauses)} 
                           WHERE id = ?"""
                cursor.execute(query, params)
                
                # Update reminder if reminder time changed
                if 'reminder_minutes_before' in updates:
                    self._update_reminder(cursor, event_id, 
                                          updates['reminder_minutes_before'])
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to update event: {str(e)}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event and all its related data"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete reminders first (foreign key constraint)
                cursor.execute('''DELETE FROM event_reminders 
                                 WHERE event_id = ?''', (event_id,))
                
                # Delete attachments
                cursor.execute('''DELETE FROM event_attachments 
                                 WHERE event_id = ?''', (event_id,))
                
                # Delete event
                cursor.execute('''DELETE FROM calendar_events 
                                 WHERE id = ?''', (event_id,))
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to delete event: {str(e)}")
            return False
    
    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get a specific calendar event"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calendar_events WHERE id = ?
                ''', (event_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return self._row_to_event(row)
                
        except Exception as e:
            self.logger.error(f"Failed to get event: {str(e)}")
            return None
    
    def get_events_for_date_range(self, start_date: date, 
                                  end_date: date) -> List[CalendarEvent]:
        """Get all events within a date range"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calendar_events 
                    WHERE event_date >= ? AND event_date <= ?
                    ORDER BY event_date, start_time
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get events for date range: {str(e)}")
            return []
    
    def get_events_for_date(self, target_date: date) -> List[CalendarEvent]:
        """Get all events for a specific date"""
        return self.get_events_for_date_range(target_date, target_date)
    
    def search_events(self, query: str) -> List[CalendarEvent]:
        """Search events by title, description, location, or notes"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT * FROM calendar_events 
                    WHERE title LIKE ? OR description LIKE ? 
                    OR location LIKE ? OR notes LIKE ?
                    ORDER BY event_date DESC, start_time DESC
                    LIMIT 100
                ''', (search_pattern, search_pattern, 
                      search_pattern, search_pattern))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to search events: {str(e)}")
            return []
    
    def get_upcoming_reminders(self) -> List[Dict[str, Any]]:
        """Get all upcoming reminders that need to be sent"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT r.*, e.title, e.description, e.event_date, 
                           e.start_time, e.location
                    FROM event_reminders r
                    JOIN calendar_events e ON r.event_id = e.id
                    WHERE r.sent = 0 AND r.reminder_time <= datetime('now')
                    ORDER BY r.reminder_time
                ''')
                
                reminders = []
                for row in cursor.fetchall():
                    reminder = {
                        'id': row[0],
                        'event_id': row[1],
                        'reminder_time': row[2],
                        'sent': bool(row[3]),
                        'sent_at': row[4],
                        'event_title': row[5],
                        'event_description': row[6],
                        'event_date': row[7],
                        'start_time': row[8],
                        'location': row[9]
                    }
                    reminders.append(reminder)
                
                return reminders
                
        except Exception as e:
            self.logger.error(f"Failed to get upcoming reminders: {str(e)}")
            return []
    
    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark a reminder as sent"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE event_reminders 
                    SET sent = 1, sent_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (reminder_id,))
                
                # Also update the event's reminder_sent flag
                cursor.execute('''
                    UPDATE calendar_events 
                    SET reminder_sent = 1 
                    WHERE id = (SELECT event_id FROM event_reminders 
                               WHERE id = ?)
                ''', (reminder_id,))
                
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to mark reminder sent: {str(e)}")
            return False
    
    def get_events_by_status(self, status: str,
                             limit: int = 100) -> List[CalendarEvent]:
        """Get events by status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calendar_events 
                    WHERE status = ?
                    ORDER BY event_date DESC, start_time DESC
                    LIMIT ?
                ''', (status, limit))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get events by status: {str(e)}")
            return []
    
    def get_events_by_project(self, project_id: str) -> List[CalendarEvent]:
        """Get all events for a specific project"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM calendar_events 
                    WHERE project_id = ?
                    ORDER BY event_date DESC, start_time DESC
                ''', (project_id,))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Failed to get events by project: {str(e)}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get calendar event statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total events
                cursor.execute('SELECT COUNT(*) FROM calendar_events')
                stats['total_events'] = cursor.fetchone()[0]
                
                # Events by status
                cursor.execute('''
                    SELECT status, COUNT(*) 
                    FROM calendar_events 
                    GROUP BY status
                ''')
                stats['events_by_status'] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }
                
                # Events by type
                cursor.execute('''
                    SELECT event_type, COUNT(*) 
                    FROM calendar_events 
                    GROUP BY event_type
                ''')
                stats['events_by_type'] = {
                    row[0]: row[1] for row in cursor.fetchall()
                }
                
                # Upcoming events (next 7 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM calendar_events 
                    WHERE event_date >= date('now') 
                    AND event_date <= date('now', '+7 days')
                    AND status = 'scheduled'
                ''')
                stats['upcoming_events_week'] = cursor.fetchone()[0]
                
                # Events with reminders
                cursor.execute('''
                    SELECT COUNT(*) FROM calendar_events 
                    WHERE reminder_minutes_before IS NOT NULL
                ''')
                stats['events_with_reminders'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {str(e)}")
            return {}
    
    def _create_reminder(self, cursor, event: CalendarEvent):
        """Create a reminder for an event"""
        if not event.event_date or not event.reminder_minutes_before:
            return
            
        # Calculate reminder time
        event_datetime = event.get_datetime()
        if event_datetime:
            reminder_time = (event_datetime -
                             timedelta(minutes=event.reminder_minutes_before))
            
            import uuid
            cursor.execute('''
                INSERT INTO event_reminders 
                (id, event_id, reminder_time, sent, sent_at)
                VALUES (?, ?, ?, 0, NULL)
            ''', (str(uuid.uuid4()), event.id, 
                  reminder_time.isoformat()))
    
    def _update_reminder(self, cursor, event_id: str,
                         reminder_minutes: Optional[int]):
        """Update or create reminder for an event"""
        # Delete existing reminder
        cursor.execute('DELETE FROM event_reminders WHERE event_id = ?',
                       (event_id,))
        
        # Create new reminder if needed
        if reminder_minutes:
            cursor.execute('''
                SELECT event_date, start_time FROM calendar_events 
                WHERE id = ?
            ''', (event_id,))
            
            row = cursor.fetchone()
            if row and row[0]:
                event_date = date.fromisoformat(row[0])
                start_time = (time.fromisoformat(row[1])
                              if row[1] else time(0, 0))
                event_datetime = datetime.combine(event_date, start_time)
                reminder_time = (event_datetime -
                                 timedelta(minutes=reminder_minutes))
                
                import uuid
                cursor.execute('''
                    INSERT INTO event_reminders 
                    (id, event_id, reminder_time, sent, sent_at)
                    VALUES (?, ?, ?, 0, NULL)
                ''', (str(uuid.uuid4()), event_id, 
                      reminder_time.isoformat()))
    
    def _row_to_event(self, row) -> CalendarEvent:
        """Convert database row to CalendarEvent object"""
        return CalendarEvent.from_dict({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'event_type': row[3],
            'status': row[4],
            'event_date': row[5],
            'start_time': row[6],
            'end_time': row[7],
            'all_day': bool(row[8]),
            'location': row[9],
            'participants': row[10],
            'project_id': row[11],
            'chat_session_id': row[12],
            'recurrence_pattern': row[13],
            'recurrence_rule': row[14],
            'reminder_minutes_before': row[15],
            'reminder_sent': bool(row[16]),
            'tags': row[17],
            'notes': row[18],
            'color': row[19],
            'metadata': row[20],
            'created_at': row[21],
            'updated_at': row[22],
            'completed_at': row[23]
        })