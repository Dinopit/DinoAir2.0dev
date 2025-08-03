#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Appointments backend implementation
Tests the CalendarEvent model and AppointmentsDatabase functionality.
"""

import sys
from datetime import date, time, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.models.calendar_event import (  # noqa: E402
    CalendarEvent, EventType, EventStatus
)
from src.database.initialize_db import DatabaseManager  # noqa: E402
from src.database.appointments_db import AppointmentsDatabase  # noqa: E402


def test_calendar_event_model():
    """Test CalendarEvent dataclass functionality"""
    print("\n=== Testing CalendarEvent Model ===")
    
    # Create a test event
    event = CalendarEvent(
        title="Team Meeting",
        description="Weekly team sync meeting",
        event_type=EventType.MEETING.value,
        status=EventStatus.SCHEDULED.value,
        event_date=date.today() + timedelta(days=1),
        start_time=time(14, 0),
        end_time=time(15, 30),
        location="Conference Room A",
        participants=["john@example.com", "jane@example.com"],
        project_id="proj_123",
        reminder_minutes_before=15,
        tags=["weekly", "team", "important"],
        notes="Discuss Q4 goals"
    )
    
    print(f"Created event: {event}")
    print(f"Event ID: {event.id}")
    print(f"Event datetime: {event.get_datetime()}")
    print(f"Duration: {event.get_duration_minutes()} minutes")
    print(f"Is upcoming: {event.is_upcoming()}")
    
    # Test to_dict and from_dict
    event_dict = event.to_dict()
    print(f"\nEvent as dict keys: {list(event_dict.keys())}")
    
    # Recreate from dict
    event2 = CalendarEvent.from_dict(event_dict)
    print(f"Recreated event: {event2}")
    print(f"IDs match: {event.id == event2.id}")
    
    return event


def test_appointments_database(event: CalendarEvent):
    """Test AppointmentsDatabase functionality"""
    print("\n\n=== Testing AppointmentsDatabase ===")
    
    # Initialize database
    db_manager = DatabaseManager("test_user")
    db_manager.initialize_all_databases()
    
    # Create appointments database instance
    appointments_db = AppointmentsDatabase(db_manager)
    
    # Test create_event
    print("\n1. Testing create_event...")
    result = appointments_db.create_event(event)
    print(f"Create result: {result}")
    
    # Test get_event
    print("\n2. Testing get_event...")
    retrieved_event = appointments_db.get_event(event.id)
    if retrieved_event:
        print(f"Retrieved event: {retrieved_event}")
        print(f"Title matches: {retrieved_event.title == event.title}")
    else:
        print("Failed to retrieve event")
    
    # Test update_event
    print("\n3. Testing update_event...")
    updates = {
        "location": "Virtual - Zoom",
        "notes": "Updated: Discuss Q4 goals and budget",
        "reminder_minutes_before": 30
    }
    success = appointments_db.update_event(event.id, updates)
    print(f"Update success: {success}")
    
    # Verify update
    updated_event = appointments_db.get_event(event.id)
    if updated_event:
        print(f"Updated location: {updated_event.location}")
        print(f"Updated notes: {updated_event.notes}")
        print(f"Updated reminder: {updated_event.reminder_minutes_before} min")
    
    # Test get_events_for_date
    print("\n4. Testing get_events_for_date...")
    tomorrow_events = appointments_db.get_events_for_date(
        date.today() + timedelta(days=1)
    )
    print(f"Events for tomorrow: {len(tomorrow_events)}")
    
    # Test search_events
    print("\n5. Testing search_events...")
    search_results = appointments_db.search_events("team")
    print(f"Search results for 'team': {len(search_results)}")
    for result in search_results:
        print(f"  - {result.title}: {result.description}")
    
    # Test get_events_for_date_range
    print("\n6. Testing get_events_for_date_range...")
    start_date = date.today()
    end_date = date.today() + timedelta(days=7)
    week_events = appointments_db.get_events_for_date_range(
        start_date, end_date
    )
    print(f"Events for next 7 days: {len(week_events)}")
    
    # Test get_upcoming_reminders
    print("\n7. Testing get_upcoming_reminders...")
    reminders = appointments_db.get_upcoming_reminders()
    print(f"Upcoming reminders: {len(reminders)}")
    
    # Test get_event_statistics
    print("\n8. Testing get_event_statistics...")
    stats = appointments_db.get_event_statistics()
    print(f"Event statistics: {stats}")
    
    # Create another event for testing
    event2 = CalendarEvent(
        title="Doctor Appointment",
        description="Annual checkup",
        event_type=EventType.APPOINTMENT.value,
        event_date=date.today() + timedelta(days=3),
        start_time=time(10, 0),
        end_time=time(11, 0),
        location="Medical Center",
        reminder_minutes_before=60,
        tags=["health", "personal"]
    )
    appointments_db.create_event(event2)
    print(f"\nCreated second event: {event2.title}")
    
    # Test get_events_by_status
    print("\n9. Testing get_events_by_status...")
    scheduled_events = appointments_db.get_events_by_status(
        EventStatus.SCHEDULED.value
    )
    print(f"Scheduled events: {len(scheduled_events)}")
    
    # Test delete_event
    print("\n10. Testing delete_event...")
    delete_success = appointments_db.delete_event(event2.id)
    print(f"Delete success: {delete_success}")
    
    # Verify deletion
    deleted_event = appointments_db.get_event(event2.id)
    print(f"Event still exists: {deleted_event is not None}")
    
    return appointments_db


def test_edge_cases(appointments_db: AppointmentsDatabase):
    """Test edge cases and error handling"""
    print("\n\n=== Testing Edge Cases ===")
    
    # Test all-day event
    print("\n1. Testing all-day event...")
    all_day_event = CalendarEvent(
        title="Company Holiday",
        event_type=EventType.OTHER.value,
        event_date=date.today() + timedelta(days=14),
        all_day=True,
        tags=["holiday", "company"]
    )
    result = appointments_db.create_event(all_day_event)
    print(f"Created all-day event: {result}")
    
    # Test recurring event (with recurrence pattern)
    print("\n2. Testing recurring event...")
    recurring_event = CalendarEvent(
        title="Weekly Stand-up",
        event_type=EventType.MEETING.value,
        event_date=date.today() + timedelta(days=7),
        start_time=time(9, 0),
        end_time=time(9, 15),
        recurrence_pattern="weekly",
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        project_id="proj_456"
    )
    result = appointments_db.create_event(recurring_event)
    print(f"Created recurring event: {result}")
    
    # Test event with metadata
    print("\n3. Testing event with metadata...")
    metadata_event = CalendarEvent(
        title="Client Presentation",
        event_date=date.today() + timedelta(days=5),
        start_time=time(15, 0),
        end_time=time(16, 30),
        metadata={
            "client_id": "client_789",
            "presentation_url": "https://example.com/presentation",
            "attendee_count": 12
        },
        color="#FF5733"
    )
    result = appointments_db.create_event(metadata_event)
    print(f"Created event with metadata: {result}")
    
    # Retrieve and check metadata
    retrieved = appointments_db.get_event(metadata_event.id)
    if retrieved and retrieved.metadata:
        print(f"Metadata preserved: {retrieved.metadata}")
    
    # Test invalid event ID
    print("\n4. Testing invalid event ID...")
    invalid_event = appointments_db.get_event("invalid_id_12345")
    print(f"Invalid event result: {invalid_event}")
    
    # Test empty search
    print("\n5. Testing empty search...")
    empty_results = appointments_db.search_events("xyznotfound123")
    print(f"Empty search results: {len(empty_results)}")


def main():
    """Run all tests"""
    print("Starting Appointments Backend Tests")
    print("=" * 50)
    
    try:
        # Test the model
        event = test_calendar_event_model()
        
        # Test the database
        appointments_db = test_appointments_database(event)
        
        # Test edge cases
        test_edge_cases(appointments_db)
        
        print("\n\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()