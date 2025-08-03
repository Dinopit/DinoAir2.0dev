#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calendar Event Models
Data models for calendar events and appointments with comprehensive
metadata support.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any
import uuid
import json
from enum import Enum


class EventType(Enum):
    """Event type enumeration"""
    APPOINTMENT = "appointment"
    MEETING = "meeting"
    TASK = "task"
    REMINDER = "reminder"
    OTHER = "other"


class EventStatus(Enum):
    """Event status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class RecurrencePattern(Enum):
    """Recurrence pattern enumeration"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class CalendarEvent:
    """Calendar event with comprehensive fields for appointments/scheduling"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: Optional[str] = None
    event_type: str = EventType.APPOINTMENT.value
    status: str = EventStatus.SCHEDULED.value
    
    # Date and time fields
    event_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    all_day: bool = False
    
    # Location and participants
    location: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    
    # Integration fields
    project_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    
    # Recurrence
    recurrence_pattern: str = RecurrencePattern.NONE.value
    recurrence_rule: Optional[str] = None  # For custom rules (RRULE format)
    
    # Reminders
    reminder_minutes_before: Optional[int] = None
    reminder_sent: bool = False
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type,
            'status': self.status,
            'event_date': (self.event_date.isoformat()
                           if self.event_date else None),
            'start_time': (self.start_time.isoformat()
                           if self.start_time else None),
            'end_time': (self.end_time.isoformat()
                         if self.end_time else None),
            'all_day': self.all_day,
            'location': self.location,
            'participants': (','.join(self.participants)
                             if self.participants else ''),
            'project_id': self.project_id,
            'chat_session_id': self.chat_session_id,
            'recurrence_pattern': self.recurrence_pattern,
            'recurrence_rule': self.recurrence_rule,
            'reminder_minutes_before': self.reminder_minutes_before,
            'reminder_sent': self.reminder_sent,
            'tags': ','.join(self.tags) if self.tags else '',
            'notes': self.notes,
            'color': self.color,
            'metadata': json.dumps(self.metadata) if self.metadata else None,
            'created_at': (self.created_at.isoformat()
                           if isinstance(self.created_at, datetime)
                           else self.created_at),
            'updated_at': (self.updated_at.isoformat()
                           if isinstance(self.updated_at, datetime)
                           else self.updated_at),
            'completed_at': (self.completed_at.isoformat()
                             if self.completed_at else None)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalendarEvent':
        """Create from dictionary"""
        # Parse dates and times
        event_date = data.get('event_date')
        if event_date and isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)
            
        start_time = data.get('start_time')
        if start_time and isinstance(start_time, str):
            start_time = time.fromisoformat(start_time)
            
        end_time = data.get('end_time')
        if end_time and isinstance(end_time, str):
            end_time = time.fromisoformat(end_time)
        
        # Parse timestamps
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        completed_at = data.get('completed_at')
        if completed_at and isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        
        # Parse lists
        participants = data.get('participants', '')
        if isinstance(participants, str) and participants:
            participants = [p.strip() for p in participants.split(',')]
        else:
            participants = []
            
        tags = data.get('tags', '')
        if isinstance(tags, str) and tags:
            tags = [tag.strip() for tag in tags.split(',')]
        else:
            tags = []
        
        # Parse metadata
        metadata = data.get('metadata')
        if metadata and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None
                
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            description=data.get('description'),
            event_type=data.get('event_type', EventType.APPOINTMENT.value),
            status=data.get('status', EventStatus.SCHEDULED.value),
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            all_day=data.get('all_day', False),
            location=data.get('location'),
            participants=participants,
            project_id=data.get('project_id'),
            chat_session_id=data.get('chat_session_id'),
            recurrence_pattern=data.get('recurrence_pattern',
                                        RecurrencePattern.NONE.value),
            recurrence_rule=data.get('recurrence_rule'),
            reminder_minutes_before=data.get('reminder_minutes_before'),
            reminder_sent=data.get('reminder_sent', False),
            tags=tags,
            notes=data.get('notes'),
            color=data.get('color'),
            metadata=metadata,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            completed_at=completed_at
        )
    
    def get_datetime(self) -> Optional[datetime]:
        """Get the combined datetime for the event"""
        if self.event_date and self.start_time:
            return datetime.combine(self.event_date, self.start_time)
        elif self.event_date:
            return datetime.combine(self.event_date, time(0, 0))
        return None
    
    def is_upcoming(self, buffer_minutes: int = 0) -> bool:
        """Check if the event is upcoming"""
        event_datetime = self.get_datetime()
        if event_datetime:
            now = datetime.now()
            buffer = timedelta(minutes=buffer_minutes)
            return event_datetime > now - buffer
        return False
    
    def get_duration_minutes(self) -> Optional[int]:
        """Get the duration of the event in minutes"""
        if self.start_time and self.end_time:
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            duration = end_dt - start_dt
            return int(duration.total_seconds() / 60)
        return None
    
    def __str__(self) -> str:
        """String representation"""
        date_str = (self.event_date.strftime("%Y-%m-%d")
                    if self.event_date else "No date")
        time_str = ""
        if self.all_day:
            time_str = "All day"
        elif self.start_time:
            time_str = self.start_time.strftime("%H:%M")
            if self.end_time:
                time_str += f" - {self.end_time.strftime('%H:%M')}"
        return f"CalendarEvent({self.title}, {date_str} {time_str})"