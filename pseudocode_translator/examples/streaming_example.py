#!/usr/bin/env python3
"""
Streaming Translation Example

This example demonstrates how to use the streaming API for real-time
translation with progress tracking and partial results.
"""

import sys
import time
from typing import Optional
from pseudocode_translator import SimpleTranslator
from pseudocode_translator.streaming import StreamChunk


def print_progress_bar(progress: float, width: int = 50):
    """Display a progress bar in the terminal"""
    filled = int(width * progress / 100)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\rProgress: [{bar}] {progress:.1f}%", end='', flush=True)


def example_1_basic_streaming():
    """Example 1: Basic streaming translation"""
    print("\n=== Example 1: Basic Streaming ===")
    
    translator = SimpleTranslator(enable_streaming=True)
    
    pseudocode = """
    FUNCTION fibonacci(n)
        IF n <= 1 THEN
            RETURN n
        ELSE
            RETURN fibonacci(n-1) + fibonacci(n-2)
        END IF
    END FUNCTION
    
    FUNCTION print_fibonacci_sequence(count)
        FOR i FROM 0 TO count
            PRINT "F(" + i + ") = " + fibonacci(i)
        END FOR
    END FUNCTION
    """
    
    print("Translating pseudocode...")
    result = []
    
    for chunk in translator.translate_stream(pseudocode, target_language="python"):
        # Append content
        result.append(chunk.content)
        
        # Show progress if available
        if chunk.metadata.get('progress'):
            print_progress_bar(chunk.metadata['progress'])
        
        # Optional: show partial results
        if chunk.metadata.get('partial_complete'):
            print(f"\n\nPartial result:\n{chunk.content}")
    
    print("\n\nFinal translation:")
    print("".join(result))


def example_2_streaming_with_callbacks():
    """Example 2: Streaming with event callbacks"""
    print("\n=== Example 2: Streaming with Callbacks ===")
    
    translator = SimpleTranslator(enable_streaming=True)
    
    # Track translation state
    state = {
        'tokens_used': 0,
        'chunks_received': 0,
        'start_time': None,
        'functions_found': []
    }
    
    def on_chunk(chunk: StreamChunk):
        """Handle each streaming chunk"""
        state['chunks_received'] += 1
        
        # Track tokens
        if 'tokens_used' in chunk.metadata:
            state['tokens_used'] = chunk.metadata['tokens_used']
        
        # Track functions being generated
        if 'function_name' in chunk.metadata:
            state['functions_found'].append(chunk.metadata['function_name'])
        
        # Calculate speed
        if state['start_time']:
            elapsed = time.time() - state['start_time']
            speed = state['chunks_received'] / elapsed
            print(f"\rChunks: {state['chunks_received']} | "
                  f"Tokens: {state['tokens_used']} | "
                  f"Speed: {speed:.1f} chunks/s", end='', flush=True)
    
    pseudocode = """
    CREATE a BankAccount class with:
        - balance attribute (initially 0)
        - account_number attribute
        
        METHOD deposit(amount)
            IF amount > 0 THEN
                balance = balance + amount
                RETURN True
            ELSE
                RETURN False
            END IF
        END METHOD
        
        METHOD withdraw(amount)
            IF amount > 0 AND amount <= balance THEN
                balance = balance - amount
                RETURN True
            ELSE
                RETURN False
            END IF
        END METHOD
        
        METHOD get_balance()
            RETURN balance
        END METHOD
    END CLASS
    """
    
    print("Starting streaming translation...")
    state['start_time'] = time.time()
    
    result = []
    for chunk in translator.translate_stream(pseudocode):
        result.append(chunk.content)
        on_chunk(chunk)
    
    elapsed = time.time() - state['start_time']
    print(f"\n\nTranslation completed in {elapsed:.2f} seconds")
    print(f"Functions found: {', '.join(state['functions_found'])}")
    print("\nGenerated code:")
    print("".join(result))


def example_3_streaming_large_file():
    """Example 3: Stream translation of large pseudocode"""
    print("\n=== Example 3: Streaming Large File ===")
    
    translator = SimpleTranslator(
        enable_streaming=True,
        chunk_size=500  # Smaller chunks for more frequent updates
    )
    
    # Large pseudocode example
    pseudocode = """
    # Comprehensive Task Management System
    
    CREATE a Task class with:
        - id: unique identifier
        - title: task title
        - description: detailed description
        - status: "pending", "in_progress", "completed"
        - priority: 1-5 (5 being highest)
        - created_at: creation timestamp
        - updated_at: last update timestamp
        - assigned_to: user assignment
        - due_date: optional due date
        - tags: list of tags
        
        METHOD __init__(title, description, priority=3)
            SET id TO generate_unique_id()
            SET self.title TO title
            SET self.description TO description
            SET self.priority TO priority
            SET self.status TO "pending"
            SET self.created_at TO current_timestamp()
            SET self.updated_at TO current_timestamp()
            SET self.assigned_to TO None
            SET self.due_date TO None
            SET self.tags TO empty list
        END METHOD
        
        METHOD update_status(new_status)
            IF new_status IN ["pending", "in_progress", "completed"] THEN
                SET self.status TO new_status
                SET self.updated_at TO current_timestamp()
                RETURN True
            ELSE
                RETURN False
            END IF
        END METHOD
        
        METHOD assign_to(user)
            SET self.assigned_to TO user
            SET self.updated_at TO current_timestamp()
        END METHOD
        
        METHOD add_tag(tag)
            IF tag NOT IN self.tags THEN
                APPEND tag TO self.tags
                SET self.updated_at TO current_timestamp()
            END IF
        END METHOD
        
        METHOD is_overdue()
            IF self.due_date IS NOT None THEN
                RETURN current_date() > self.due_date
            ELSE
                RETURN False
            END IF
        END METHOD
    END CLASS
    
    CREATE a TaskManager class with:
        - tasks: dictionary of tasks by id
        - users: list of users
        
        METHOD __init__()
            SET self.tasks TO empty dictionary
            SET self.users TO empty list
        END METHOD
        
        METHOD create_task(title, description, priority=3)
            SET task TO new Task(title, description, priority)
            SET self.tasks[task.id] TO task
            RETURN task
        END METHOD
        
        METHOD get_task(task_id)
            RETURN self.tasks.get(task_id)
        END METHOD
        
        METHOD update_task(task_id, **updates)
            IF task_id IN self.tasks THEN
                SET task TO self.tasks[task_id]
                FOR key, value IN updates
                    IF hasattr(task, key) THEN
                        SET task.key TO value
                    END IF
                END FOR
                SET task.updated_at TO current_timestamp()
                RETURN True
            ELSE
                RETURN False
            END IF
        END METHOD
        
        METHOD delete_task(task_id)
            IF task_id IN self.tasks THEN
                DELETE self.tasks[task_id]
                RETURN True
            ELSE
                RETURN False
            END IF
        END METHOD
        
        METHOD get_tasks_by_status(status)
            SET result TO empty list
            FOR task IN self.tasks.values()
                IF task.status == status THEN
                    APPEND task TO result
                END IF
            END FOR
            RETURN result
        END METHOD
        
        METHOD get_tasks_by_user(user)
            SET result TO empty list
            FOR task IN self.tasks.values()
                IF task.assigned_to == user THEN
                    APPEND task TO result
                END IF
            END FOR
            RETURN result
        END METHOD
        
        METHOD get_high_priority_tasks()
            SET result TO empty list
            FOR task IN self.tasks.values()
                IF task.priority >= 4 THEN
                    APPEND task TO result
                END IF
            END FOR
            SORT result BY priority DESCENDING
            RETURN result
        END METHOD
        
        METHOD get_overdue_tasks()
            SET result TO empty list
            FOR task IN self.tasks.values()
                IF task.is_overdue() THEN
                    APPEND task TO result
                END IF
            END FOR
            RETURN result
        END METHOD
        
        METHOD generate_report()
            SET report TO empty dictionary
            SET report["total_tasks"] TO length of self.tasks
            SET report["by_status"] TO empty dictionary
            
            FOR status IN ["pending", "in_progress", "completed"]
                SET report["by_status"][status] TO length of get_tasks_by_status(status)
            END FOR
            
            SET report["high_priority"] TO length of get_high_priority_tasks()
            SET report["overdue"] TO length of get_overdue_tasks()
            
            RETURN report
        END METHOD
    END CLASS
    """
    
    print("Streaming translation of large pseudocode file...")
    print("This demonstrates handling of complex, multi-class translations\n")
    
    # Track streaming metrics
    metrics = {
        'start_time': time.time(),
        'first_chunk_time': None,
        'chunks': 0,
        'characters': 0
    }
    
    result = []
    
    for chunk in translator.translate_stream(pseudocode, target_language="python"):
        if metrics['first_chunk_time'] is None:
            metrics['first_chunk_time'] = time.time()
            ttfb = metrics['first_chunk_time'] - metrics['start_time']
            print(f"Time to first byte: {ttfb:.2f}s\n")
        
        result.append(chunk.content)
        metrics['chunks'] += 1
        metrics['characters'] += len(chunk.content)
        
        # Show streaming progress
        if chunk.metadata.get('progress'):
            elapsed = time.time() - metrics['start_time']
            rate = metrics['characters'] / elapsed if elapsed > 0 else 0
            print(f"\rProgress: {chunk.metadata['progress']:.1f}% | "
                  f"Chunks: {metrics['chunks']} | "
                  f"Rate: {rate:.0f} chars/s", end='', flush=True)
    
    total_time = time.time() - metrics['start_time']
    final_code = "".join(result)
    
    print(f"\n\nStreaming completed!")
    print(f"Total time: {total_time:.2f}s")
    print(f"Total chunks: {metrics['chunks']}")
    print(f"Generated {len(final_code)} characters of code")
    print(f"Average chunk size: {len(final_code) / metrics['chunks']:.0f} characters")
    
    # Show first few lines of generated code
    lines = final_code.split('\n')
    print(f"\nFirst 10 lines of generated code:")
    for i, line in enumerate(lines[:10]):
        print(f"{i+1:3d} | {line}")
    print(f"... ({len(lines)} total lines)")


def example_4_error_handling_in_streams():
    """Example 4: Handling errors during streaming"""
    print("\n=== Example 4: Error Handling in Streams ===")
    
    translator = SimpleTranslator(enable_streaming=True)
    
    # Pseudocode with potential issues
    pseudocode = """
    FUNCTION divide_numbers(a, b)
        # This might cause division by zero
        RETURN a / b
    END FUNCTION
    
    FUNCTION risky_operation(data)
        IF data is None THEN
            RAISE ValueError("Data cannot be None")
        END IF
        
        # Undefined variable reference
        RETURN process_data(data) + undefined_variable
    END FUNCTION
    """
    
    print("Streaming translation with error detection...")
    
    result = []
    errors = []
    warnings = []
    
    try:
        for chunk in translator.translate_stream(pseudocode):
            result.append(chunk.content)
            
            # Check for errors in metadata
            if 'error' in chunk.metadata:
                errors.append(chunk.metadata['error'])
                print(f"\n⚠️  Error detected: {chunk.metadata['error']}")
            
            if 'warning' in chunk.metadata:
                warnings.append(chunk.metadata['warning'])
                print(f"\n⚡ Warning: {chunk.metadata['warning']}")
            
            # Show progress
            if chunk.metadata.get('progress'):
                print(f"\rProgress: {chunk.metadata['progress']:.1f}%", end='', flush=True)
        
    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        print("Partial result generated before error:")
        print("".join(result))
        return
    
    print("\n\nTranslation completed with issues:")
    print(f"- Errors: {len(errors)}")
    print(f"- Warnings: {len(warnings)}")
    
    print("\nGenerated code with inline warnings:")
    print("".join(result))


def example_5_interactive_streaming():
    """Example 5: Interactive streaming with user control"""
    print("\n=== Example 5: Interactive Streaming ===")
    print("This example shows how to pause/resume streaming\n")
    
    translator = SimpleTranslator(enable_streaming=True)
    
    pseudocode = """
    CREATE an InteractiveCalculator class with:
        - history: list of calculations
        - memory: stored value
        
        METHOD calculate(expression)
            TRY
                SET result TO evaluate(expression)
                APPEND (expression, result) TO history
                RETURN result
            CATCH Exception as e
                RETURN "Error: " + str(e)
            END TRY
        END METHOD
        
        METHOD store_memory(value)
            SET memory TO value
        END METHOD
        
        METHOD recall_memory()
            RETURN memory
        END METHOD
        
        METHOD clear_history()
            SET history TO empty list
        END METHOD
        
        METHOD show_history()
            FOR entry IN history
                PRINT entry[0] + " = " + entry[1]
            END FOR
        END METHOD
    END CLASS
    """
    
    print("Starting interactive streaming...")
    print("(In a real application, you could pause/resume with keyboard input)\n")
    
    result = []
    paused = False
    chunk_count = 0
    
    for chunk in translator.translate_stream(pseudocode):
        chunk_count += 1
        
        # Simulate pausing after every 5 chunks
        if chunk_count % 5 == 0 and not paused:
            print(f"\n[Simulated pause after chunk {chunk_count}]")
            time.sleep(1)  # Simulate pause
            print("[Resuming...]\n")
        
        result.append(chunk.content)
        
        # Show what's being generated
        if chunk.content.strip():
            print(f"Chunk {chunk_count}: {repr(chunk.content[:50])}...")


def main():
    """Run all streaming examples"""
    print("Pseudocode Translator - Streaming Examples")
    print("=" * 50)
    
    examples = [
        example_1_basic_streaming,
        example_2_streaming_with_callbacks,
        example_3_streaming_large_file,
        example_4_error_handling_in_streams,
        example_5_interactive_streaming
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "-" * 50)
            input("\nPress Enter to continue to next example...")
        except KeyboardInterrupt:
            print("\n\nExample interrupted by user")
            break
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
    
    print("\nAll streaming examples completed!")
    print("\nKey takeaways:")
    print("- Streaming provides real-time feedback during translation")
    print("- Progress tracking helps with user experience")
    print("- Metadata in chunks provides valuable information")
    print("- Error handling is important for robust applications")
    print("- Interactive controls can enhance user engagement")


if __name__ == "__main__":
    main()