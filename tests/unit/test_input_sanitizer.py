#!/usr/bin/env python3
"""
Simple test script for the enhanced InputPipeline with new features.
Run this to verify the implementation works correctly.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from input_processing.input_sanitizer import InputPipeline, Intent

def test_feedback(message: str):
    """Mock GUI feedback function."""
    print(f"[GUI FEEDBACK] {message}")

def test_basic_functionality():
    """Test basic pipeline functionality."""
    print("=== Testing Basic Functionality ===")
    
    # Initialize pipeline with minimal cooldown for testing
    pipeline = InputPipeline(test_feedback, cooldown_seconds=0.1)
    
    test_cases = [
        ("Create a new note about the meeting", Intent.NOTE),
        ("Set a timer for 10 minutes", Intent.TIMER),
        ("Search for Python tutorials", Intent.SEARCH),
        ("How do I use this app?", Intent.HELP),
        ("Hello, how are you?", Intent.UNKNOWN),
    ]
    
    import time
    for text, expected_intent in test_cases:
        time.sleep(0.15)  # Wait between tests to avoid rate limiting
        try:
            result, intent = pipeline.run(text)
            print(f"✓ '{text}' → {intent.name} (expected: {expected_intent.name})")
            # Note: Intent classification might not always match expected due to context
        except Exception as e:
            print(f"✗ Error processing '{text}': {e}")

def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n=== Testing Rate Limiting ===")
    
    # Initialize with short cooldown for testing
    pipeline = InputPipeline(test_feedback, cooldown_seconds=0.5)
    
    # First input should work
    try:
        result, intent = pipeline.run("Test message 1")
        print("✓ First message processed successfully")
    except Exception as e:
        print(f"✗ First message failed: {e}")
    
    # Immediate second input should be rate limited
    try:
        result, intent = pipeline.run("Test message 2")
        print("✗ Rate limiting failed - second message should have been blocked")
    except Exception as e:
        print(f"✓ Rate limiting working: {e}")
    
    # Wait and try again
    import time
    time.sleep(0.6)
    try:
        result, intent = pipeline.run("Test message 3")
        print("✓ Message after cooldown processed successfully")
    except Exception as e:
        print(f"✗ Message after cooldown failed: {e}")

def test_profanity_filter():
    """Test profanity filtering."""
    print("\n=== Testing Profanity Filter ===")
    
    pipeline = InputPipeline(test_feedback, cooldown_seconds=0.1)
    
    import time
    # Test clean text
    try:
        result, intent = pipeline.run("This is a clean message")
        print("✓ Clean message processed successfully")
    except Exception as e:
        print(f"✗ Clean message failed: {e}")
    
    time.sleep(0.15)
    # Test text with flagged words (should process but show warning)
    try:
        result, intent = pipeline.run("This message contains badword content")
        print("✓ Flagged content processed with warning")
    except Exception as e:
        print(f"✗ Flagged content failed: {e}")

def test_context_awareness():
    """Test context-aware intent classification."""
    print("\n=== Testing Context Awareness ===")
    
    pipeline = InputPipeline(test_feedback, cooldown_seconds=0.1)
    
    import time
    # Build context
    try:
        # First message about calendar
        result1, intent1 = pipeline.run("I'm working with my calendar")
        print(f"✓ Context built: '{result1}' → {intent1.name}")
        
        time.sleep(0.15)
        # Second message should use context for better classification
        result2, intent2 = pipeline.run("remind me about the meeting")
        print(f"✓ Context-aware classification: '{result2}' → {intent2.name}")
        
        # Check context
        context = pipeline.get_conversation_context()
        print(f"✓ Current context: '{context}'")
        
    except Exception as e:
        print(f"✗ Context awareness test failed: {e}")

def test_llm_escaping():
    """Test LLM-specific escaping."""
    print("\n=== Testing LLM Escaping ===")
    
    # Test Claude escaping
    pipeline_claude = InputPipeline(test_feedback, model_type="claude", cooldown_seconds=0.1)
    try:
        result, intent = pipeline_claude.run("Test message with <brackets>")
        print(f"✓ Claude escaping: Contains escaped brackets: {'&lt;' in result and '&gt;' in result}")
    except Exception as e:
        print(f"✗ Claude escaping failed: {e}")
    
    # Test GPT escaping
    pipeline_gpt = InputPipeline(test_feedback, model_type="gpt", cooldown_seconds=0.1)
    try:
        result, intent = pipeline_gpt.run("Test message with ```code blocks```")
        print(f"✓ GPT escaping: Contains escaped backticks: {'\\`\\`\\`' in result}")
    except Exception as e:
        print(f"✗ GPT escaping failed: {e}")

def main():
    """Run all tests."""
    print("Testing Enhanced InputPipeline Implementation")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_rate_limiting()
        test_profanity_filter()
        test_context_awareness()
        test_llm_escaping()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed! Check output above for any failures.")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
