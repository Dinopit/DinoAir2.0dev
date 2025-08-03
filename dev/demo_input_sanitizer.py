#!/usr/bin/env python3
"""
CLI Demo for Enhanced InputPipeline
Demonstrates the new features: rate limiting, profanity filtering, context awareness, and LLM escaping.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from input_processing.input_sanitizer import InputPipeline, Intent

def demo_feedback(message: str):
    """Demo feedback function that prints with color."""
    print(f"🔔 {message}")

def main():
    """Interactive demo of the enhanced InputPipeline."""
    print("🚀 Enhanced InputPipeline Demo")
    print("=" * 40)
    print("Features: Rate Limiting, Profanity Filter, Context Awareness, LLM Escaping")
    print("Type 'quit' to exit, 'clear' to clear context, 'help' for commands")
    print()
    
    # Initialize pipeline with demo settings
    pipeline = InputPipeline(
        gui_feedback_hook=demo_feedback,
        model_type="claude",  # Try "claude", "gpt", or "default"
        cooldown_seconds=1.0   # 1 second between inputs
    )
    
    print("🎯 Model Type: claude (use 'model gpt' or 'model default' to change)")
    print("⏰ Rate Limit: 1.0 seconds between inputs")
    print()
    
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == 'quit':
                print("👋 Goodbye!")
                break
                
            if user_input.lower() == 'clear':
                pipeline.clear_context()
                continue
                
            if user_input.lower() == 'help':
                print("📋 Available commands:")
                print("  quit     - Exit the demo")
                print("  clear    - Clear conversation context")
                print("  model X  - Change model type (claude/gpt/default)")
                print("  context  - Show current context")
                print("  Try saying things like:")
                print("    'Create a note about the meeting'")
                print("    'Set a timer for 5 minutes'")
                print("    'Search for Python tutorials'")
                print("    'This contains badword content' (to test profanity filter)")
                continue
                
            if user_input.lower().startswith('model '):
                model_type = user_input[6:].strip()
                pipeline.update_model_type(model_type)
                continue
                
            if user_input.lower() == 'context':
                context = pipeline.get_conversation_context()
                print(f"📚 Current context: '{context}'" if context else "📚 No context yet")
                continue
            
            # Process input through pipeline
            sanitized_text, intent = pipeline.run(user_input)
            
            # Show results
            print(f"🧹 Sanitized: '{sanitized_text}'")
            print(f"🎯 Intent: {intent.name}")
            
            # Show context
            context = pipeline.get_conversation_context()
            if context:
                print(f"📚 Context: '{context[-50]}{'...' if len(context) > 50 else ''}'")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    main()
