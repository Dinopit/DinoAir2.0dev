"""
Comprehensive Examples: Tool-Model Separation Demo

This module demonstrates how tools can function independently of AI models
and shows various usage patterns with the new abstraction layer.
"""

import asyncio
import time
import logging
import json

# Import our new abstraction components
from ..base_tool import ExecutionMode
from ..adapters import create_adapter, AdapterType, AdapterConfig
from ..integration.tool_bridge import get_tool_bridge, migrate_tool_config

# Import example tools
from ..pseudocode_tool_refactored import PseudocodeTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_standalone_mode():
    """
    Demo 1: Tool usage without AI models
    
    Shows how tools can operate completely independently of AI models
    using rule-based patterns and deterministic logic.
    """
    print("\n" + "="*60)
    print("DEMO 1: Standalone Mode (No AI Required)")
    print("="*60 + "\n")
    
    # Create tool instance
    tool = PseudocodeTool()
    
    # Example 1: Simple translation using patterns
    print("Example 1: Simple pattern-based translation")
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode="print 'Hello, World!'",
        target_language="python"
    )
    print("Input: print 'Hello, World!'")
    print(f"Output: {result['output']}")
    print(f"Success: {result['success']}")
    
    # Example 2: Loop translation
    print("\nExample 2: Loop structure translation")
    pseudocode = """
    for i from 1 to 10
        print i
    end
    """
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode=pseudocode,
        target_language="javascript"
    )
    print(f"Input:\n{pseudocode}")
    print(f"Output:\n{result['output']}")
    
    # Example 3: Conditional translation
    print("\nExample 3: Conditional structure")
    pseudocode = """
    if x > 5
        print "Large"
    else
        print "Small"
    end
    """
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode=pseudocode,
        target_language="java"
    )
    print(f"Input:\n{pseudocode}")
    print(f"Output:\n{result['output']}")
    
    # Performance metrics
    print("\nPerformance Metrics:")
    if 'metadata' in result and 'execution_time' in result['metadata']:
        print(f"- Execution time: {result['metadata']['execution_time']:.3f}s")
    print("- No AI model calls required")
    print("- Deterministic output guaranteed")


async def demo_ai_model_switching():
    """
    Demo 2: Tool usage with different AI models
    
    Shows how the same tool can work with different AI providers
    through the adapter pattern.
    """
    print("\n" + "="*60)
    print("DEMO 2: AI Model Switching via Adapters")
    print("="*60 + "\n")
    
    tool = PseudocodeTool()
    
    # Example 1: Using OpenAI adapter
    print("Example 1: Using OpenAI Adapter")
    try:
        openai_config = AdapterConfig(
            adapter_type=AdapterType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="demo-key",  # Would use real key in production
            extra_params={
                "temperature": 0.2,
                "max_tokens": 1000
            }
        )
        openai_adapter = create_adapter(AdapterType.OPENAI, openai_config)
        
        result = await tool.execute(
            mode=ExecutionMode.AI_GUIDED,
            model=openai_adapter,
            pseudocode="create function to calculate fibonacci",
            target_language="python"
        )
        print("Model: OpenAI GPT-3.5")
        print(f"Result: {result['output'][:100]}...")
    except Exception as e:
        print(f"OpenAI demo skipped (no API key): {e}")
    
    # Example 2: Using Anthropic adapter
    print("\nExample 2: Using Anthropic Adapter")
    try:
        anthropic_config = AdapterConfig(
            adapter_type=AdapterType.ANTHROPIC,
            model_name="claude-3-sonnet",
            api_key="demo-key",  # Would use real key in production
            extra_params={
                "temperature": 0.1,
                "max_tokens": 1500
            }
        )
        anthropic_adapter = create_adapter(
            AdapterType.ANTHROPIC, 
            anthropic_config
        )
        
        result = await tool.execute(
            mode=ExecutionMode.AI_GUIDED,
            model=anthropic_adapter,
            pseudocode="create function to calculate fibonacci",
            target_language="javascript"
        )
        print("Model: Anthropic Claude")
        print(f"Result: {result['output'][:100]}...")
    except Exception as e:
        print(f"Anthropic demo skipped (no API key): {e}")
    
    # Example 3: Using Ollama (local) adapter
    print("\nExample 3: Using Ollama Local Adapter")
    try:
        ollama_config = AdapterConfig(
            adapter_type=AdapterType.OLLAMA,
            model_name="codellama:7b",
            api_base="http://localhost:11434",
            timeout=120
        )
        ollama_adapter = create_adapter(AdapterType.OLLAMA, ollama_config)
        await ollama_adapter.initialize()
        
        result = await tool.execute(
            mode=ExecutionMode.AI_GUIDED,
            model=ollama_adapter,
            pseudocode="create function to sort array",
            target_language="python"
        )
        print("Model: Ollama CodeLlama (Local)")
        print(f"Result: {result['output'][:100]}...")
    except Exception as e:
        print(f"Ollama demo skipped (not running): {e}")
    
    print("\nKey Benefits:")
    print("- Same tool works with any AI provider")
    print("- Easy to switch between models")
    print("- Consistent interface across providers")
    print("- No vendor lock-in")


async def demo_migration_process():
    """
    Demo 3: Migration from old to new system
    
    Shows how to progressively migrate legacy tools to the new
    abstraction-based architecture.
    """
    print("\n" + "="*60)
    print("DEMO 3: Legacy Tool Migration")
    print("="*60 + "\n")
    
    # Get the tool bridge
    bridge = get_tool_bridge()
    
    # Simulate a legacy tool
    class LegacyTranslator:
        """Example legacy tool without proper abstraction"""
        def translate(self, text, language):
            # Simple mock translation
            return f"// Translated to {language}\n{text}"
        
        def validate_input(self, text):
            return len(text) > 0
    
    # Step 1: Register legacy tool
    print("Step 1: Register legacy tool")
    legacy_tool = LegacyTranslator()
    bridge.register_legacy_tool('legacy_translator', legacy_tool)
    print("✓ Legacy tool registered")
    
    # Step 2: Wrap for new system
    print("\nStep 2: Create wrapper for new system")
    wrapped_tool = bridge.wrap_legacy_tool(
        legacy_tool,
        'wrapped_translator',
        description='Legacy translator wrapped for new system',
        version='1.0.0'
    )
    print("✓ Legacy tool wrapped")
    
    # Step 3: Use wrapped tool with new system
    print("\nStep 3: Use wrapped tool with new executor")
    # The wrapped tool uses the legacy interface internally
    result = await wrapped_tool.execute(
        text="Hello World",
        language="python"
    )
    print(f"Result: {result['output']}")
    
    # Step 4: Create compatibility layer
    print("\nStep 4: Create backward compatibility layer")
    from ..pseudocode_tool_refactored import PseudocodeTool as NewTool
    new_tool = NewTool()
    
    compat_tool = bridge.create_compatibility_layer(
        new_tool,
        {
            'translate': 'execute',
            'translate_sync': 'execute',
            'validate_input': 'validate_config'
        }
    )
    print("✓ Compatibility layer created")
    
    # Use new tool with old interface
    print("\nUsing new tool with legacy interface:")
    result = compat_tool.translate(
        pseudocode="print hello",
        target_language="python"
    )
    print(f"Result: {result['output']}")
    
    # Migrate configuration
    print("\nStep 5: Migrate configuration format")
    old_config = {
        'name': 'translator',
        'ai': {
            'provider': 'openai',
            'model': 'gpt-4',
            'temperature': 0.5
        },
        'timeout': 30
    }
    
    new_config = migrate_tool_config(old_config)
    print(f"Old config: {json.dumps(old_config, indent=2)}")
    print(f"New config: {json.dumps(new_config, indent=2)}")
    
    print("\nMigration Benefits:")
    print("- Gradual transition possible")
    print("- No breaking changes")
    print("- Both systems can coexist")
    print("- Easy rollback if needed")


async def demo_execution_modes():
    """
    Demo 4: All execution modes
    
    Shows complete examples for each execution mode with
    performance comparisons.
    """
    print("\n" + "="*60)
    print("DEMO 4: Execution Modes Comparison")
    print("="*60 + "\n")
    
    tool = PseudocodeTool()
    pseudocode = """
    function calculate_average(numbers)
        sum = 0
        for each num in numbers
            sum = sum + num
        end
        return sum / length(numbers)
    end
    """
    
    results = {}
    
    # Mode 1: STANDALONE
    print("Mode 1: STANDALONE (No AI)")
    start = time.time()
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode=pseudocode,
        target_language="python"
    )
    results['standalone'] = {
        'time': time.time() - start,
        'output': result['output'],
        'success': result['success']
    }
    print(f"Time: {results['standalone']['time']:.3f}s")
    print(f"Output preview: {result['output'][:80]}...")
    
    # Mode 2: AI_ASSISTED (if available)
    print("\nMode 2: AI_ASSISTED (AI helps with complex parts)")
    # Mock AI adapter for demo
    mock_adapter = None  # Would use real adapter
    if mock_adapter:
        try:
            start = time.time()
            result = await tool.execute(
                mode=ExecutionMode.AI_ASSISTED,
                model=mock_adapter,
                pseudocode=pseudocode,
                target_language="javascript"
            )
            results['ai_assisted'] = {
                'time': time.time() - start,
                'output': result['output'],
                'success': result['success']
            }
            print(f"Time: {results['ai_assisted']['time']:.3f}s")
            print(f"Output preview: {result['output'][:80]}...")
        except Exception as e:
            print(f"AI_ASSISTED skipped (no model): {e}")
    else:
        print("AI_ASSISTED skipped (no model configured)")
    
    # Mode 3: AI_GUIDED (if available)
    print("\nMode 3: AI_GUIDED (AI drives translation)")
    if mock_adapter:
        try:
            start = time.time()
            result = await tool.execute(
                mode=ExecutionMode.AI_GUIDED,
                model=mock_adapter,
                pseudocode=pseudocode,
                target_language="java"
            )
            results['ai_guided'] = {
                'time': time.time() - start,
                'output': result['output'],
                'success': result['success']
            }
            print(f"Time: {results['ai_guided']['time']:.3f}s")
            print(f"Output preview: {result['output'][:80]}...")
        except Exception as e:
            print(f"AI_GUIDED skipped (no model): {e}")
    else:
        print("AI_GUIDED skipped (no model configured)")
    
    # Mode 4: HYBRID
    print("\nMode 4: HYBRID (Best of both)")
    start = time.time()
    result = await tool.execute(
        mode=ExecutionMode.HYBRID,
        model=None,
        pseudocode=pseudocode,
        target_language="go"
    )
    results['hybrid'] = {
        'time': time.time() - start,
        'output': result['output'],
        'success': result['success']
    }
    print(f"Time: {results['hybrid']['time']:.3f}s")
    print(f"Output preview: {result['output'][:80]}...")
    
    # Performance comparison
    print("\n" + "-"*40)
    print("Performance Comparison:")
    print("-"*40)
    print(f"{'Mode':<15} {'Time (s)':<10} {'Success':<10}")
    print("-"*40)
    for mode, data in results.items():
        print(f"{mode:<15} {data['time']:<10.3f} {str(data['success']):<10}")
    
    print("\nMode Selection Guidelines:")
    print("- STANDALONE: Fast, deterministic, no AI costs")
    print("- AI_ASSISTED: Balance of speed and quality")
    print("- AI_GUIDED: Best quality, requires AI")
    print("- HYBRID: Adaptive based on complexity")


async def demo_error_handling():
    """
    Demo 5: Error handling and recovery
    
    Shows how the system handles errors gracefully without
    depending on AI models for recovery.
    """
    print("\n" + "="*60)
    print("DEMO 5: Error Handling & Recovery")
    print("="*60 + "\n")
    
    tool = PseudocodeTool()
    
    # Example 1: Invalid input handling
    print("Example 1: Invalid input (empty pseudocode)")
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode="",
        target_language="python"
    )
    print(f"Success: {result['success']}")
    print(f"Errors: {result['errors']}")
    
    # Example 2: Unsupported language
    print("\nExample 2: Unsupported target language")
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode="print hello",
        target_language="cobol"  # Not supported
    )
    print(f"Success: {result['success']}")
    print(f"Errors: {result['errors']}")
    print(f"Warnings: {result['warnings']}")
    
    # Example 3: Complex syntax fallback
    print("\nExample 3: Complex syntax with fallback")
    complex_code = """
    parallel for i in range(workers)
        async process(data[i])
    end
    """
    result = await tool.execute(
        mode=ExecutionMode.STANDALONE,
        pseudocode=complex_code,
        target_language="python"
    )
    print(f"Input: {complex_code.strip()}")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    print(f"Warnings: {result['warnings']}")
    
    # Example 4: Error recovery strategies
    print("\nExample 4: Error recovery without AI")
    
    # Simulate a failing operation
    async def failing_operation():
        raise ValueError("Simulated error")
    
    # Try with retry strategy
    print("- Retry strategy:")
    try:
        # Simulate error and recovery
        await failing_operation()
    except Exception as e:
        # Simulate recovery
        recovered = {"recovered": True, "strategy": "retry", "error": str(e)}
        print(f"  Recovered: {recovered}")
    
    # Try with fallback strategy
    print("- Fallback strategy:")
    
    async def fallback_operation():
        return {"output": "Fallback result", "success": True}
    
    # For fallback, we'll catch the error and use fallback
    try:
        result = await failing_operation()
    except Exception:
        result = await fallback_operation()
    print(f"  Recovered: {result}")
    
    print("\nError Handling Benefits:")
    print("- Graceful degradation")
    print("- No AI dependency for recovery")
    print("- Clear error messages")
    print("- Multiple recovery strategies")


async def demo_tool_orchestration():
    """
    Demo 6: Complex tool orchestration
    
    Shows how multiple tools can work together in workflows
    without requiring AI coordination.
    """
    print("\n" + "="*60)
    print("DEMO 6: Tool Orchestration")
    print("="*60 + "\n")
    
    # Create tools for orchestration demo
    translator = PseudocodeTool()
    
    # Define a workflow with simplified steps
    print("Creating multi-language translation workflow...")
    
    # Simulate workflow execution without full orchestration
    pseudocode_input = "print 'Hello from workflow'"
    languages = ['python', 'javascript', 'java']
    
    print(f"Translating to {len(languages)} languages in parallel...")
    
    # Execute workflow simulation
    start = time.time()
    
    # Simulate parallel execution
    tasks = []
    for lang in languages:
        task = translator.execute(
            mode=ExecutionMode.STANDALONE,
            pseudocode=pseudocode_input,
            target_language=lang
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    print(f"\nWorkflow completed in {elapsed:.3f}s")
    print("Results:")
    for lang, result in zip(languages, results):
        if result['success']:
            print(f"- {lang}: {result['output'][:50]}...")
        else:
            print(f"- {lang}: Failed - {result['errors']}")
    
    # Pipeline example
    print("\n" + "-"*40)
    print("Pipeline Execution Example:")
    print("-"*40)
    
    # Simplified pipeline execution
    print("Executing tool pipeline...")
    
    # Execute a series of tool operations
    pipeline_steps = [
        {
            "pseudocode": "for i from 1 to 5\n  print i\nend",
            "target_language": "python"
        },
        {
            "pseudocode": "if x > 0\n  return true\nelse\n  return false\nend",
            "target_language": "javascript"
        }
    ]
    
    results = []
    for step in pipeline_steps:
        result = await translator.execute(
            mode=ExecutionMode.STANDALONE,
            **step
        )
        results.append(result)
    
    for i, result in enumerate(results):
        print(f"Stage {i+1}: {result.get('success', False)}")
        if result.get('success'):
            print(f"Output: {result.get('output', 'N/A')}")
    
    print("\nOrchestration Benefits:")
    print("- Complex workflows without AI coordination")
    print("- Parallel execution support")
    print("- Pipeline processing")
    print("- Dependency management")


async def main():
    """Run all demonstrations"""
    print("\n" + "="*60)
    print("TOOL-MODEL SEPARATION DEMONSTRATION")
    print("Showing how tools work independently of AI models")
    print("="*60)
    
    demos = [
        ("Standalone Mode", demo_standalone_mode),
        ("AI Model Switching", demo_ai_model_switching),
        ("Migration Process", demo_migration_process),
        ("Execution Modes", demo_execution_modes),
        ("Error Handling", demo_error_handling),
        ("Tool Orchestration", demo_tool_orchestration)
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n[{i}/{len(demos)}] Running: {name}")
        try:
            await demo_func()
        except Exception as e:
            logger.error(f"Demo '{name}' failed: {e}")
            print(f"\n⚠️  Demo '{name}' encountered an error: {e}")
        
        if i < len(demos):
            print("\nPress Enter to continue to next demo...")
            # In real usage, would wait for input
            await asyncio.sleep(0.5)
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nKey Takeaways:")
    print("1. Tools can operate without AI models (STANDALONE mode)")
    print("2. Easy switching between AI providers via adapters")
    print("3. Smooth migration path from legacy systems")
    print("4. Multiple execution modes for different needs")
    print("5. Robust error handling without AI dependency")
    print("6. Complex orchestration capabilities")
    print("\nThe abstraction layer ensures clean separation between")
    print("tool logic and AI model implementations!")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())