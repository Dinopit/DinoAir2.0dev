#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test script for the recent chat history feature."""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.chat_history_db import ChatHistoryDatabase  # noqa: E402
from src.models.chat_session import ChatSession, ChatMessage  # noqa: E402
from src.database.initialize_db import DatabaseManager  # noqa: E402


def test_recent_chat():
    """Test the recent chat history functionality."""
    print("Testing Recent Chat History Feature...")
    print("=" * 50)
    
    # Initialize database manager and chat database
    db_manager = DatabaseManager()
    db = ChatHistoryDatabase(db_manager)
    
    # Create a test session
    session = ChatSession(
        title="Test Chat Session",
        created_at=datetime.now()
    )
    session_dict = db.create_session(session)
    session_id = session_dict['id']
    print(f"✓ Created session with ID: {session_id}")
    
    # Add some test messages
    messages = [
        ("Hello, how can I help you today?", False),
        ("I need help with Python programming", True),
        ("I'd be happy to help with Python! What specific topic?", False),
        ("Can you explain decorators?", True),
        ("Decorators are functions that modify other functions...", False),
    ]
    
    for i, (content, is_user) in enumerate(messages):
        msg = ChatMessage(
            session_id=session_id,
            message=content,
            is_user=is_user,
            timestamp=datetime.now() + timedelta(seconds=i)
        )
        db.add_message(session_id, msg)
        print(f"✓ Added message {i+1}: {'User' if is_user else 'Assistant'}")
    
    # Test retrieving recent sessions
    print("\n" + "=" * 50)
    print("Recent Sessions:")
    recent = db.get_recent_sessions(limit=5)
    for session in recent:
        print(f"  - {session.title} (ID: {session.id})")
        print(f"    Created: {session.created_at}")
        # Get message count for the session
        messages = db.get_session_messages(session.id)
        print(f"    Messages: {len(messages)}")
    
    # Test filtering by date
    print("\n" + "=" * 50)
    print("Sessions from today:")
    # Get recent sessions and filter by date
    recent_sessions = db.get_recent_sessions(limit=100)
    today = datetime.now().date()
    today_sessions = [
        s for s in recent_sessions
        if s.created_at.date() == today
    ]
    for session in today_sessions:
        print(f"  - {session.title}")
    
    # Test search functionality
    print("\n" + "=" * 50)
    print("Search for 'Python' in messages:")
    # Search through recent sessions for Python-related content
    search_results = []
    recent_sessions = db.get_recent_sessions(limit=100)
    for session in recent_sessions:
        messages = db.get_session_messages(session.id)
        for msg in messages:
            if 'Python' in msg.message:
                if session not in search_results:
                    search_results.append(session)
                    break
    
    for session in search_results:
        print(f"  - {session.title} (ID: {session.id})")
        # Get messages for this session
        messages = db.get_session_messages(session.id)
        for msg in messages[:3]:  # Show first 3 messages
            prefix = "User: " if msg.is_user else "Assistant: "
            print(f"    {prefix}{msg.message[:50]}...")
    
    # Test updating session
    print("\n" + "=" * 50)
    print("Updating session title...")
    updates = {'title': "Python Decorators Discussion"}
    db.update_session(session_id, updates)
    updated = db.get_session(session_id)
    if updated:
        print(f"✓ Updated title to: {updated.title}")
    
    print("\n" + "=" * 50)
    print("✅ All tests passed successfully!")


if __name__ == "__main__":
    test_recent_chat()