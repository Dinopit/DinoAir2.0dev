"""
Unit tests for the prompts module
"""

import pytest
from pseudocode_translator.prompts import (
    PromptStyle, PromptTemplate, PromptLibrary, PromptEngineer,
    create_prompt, optimize_instruction, extract_code
)


class TestPromptStyle:
    """Test the PromptStyle enum"""
    
    def test_prompt_style_values(self):
        """Test that all prompt styles have correct values"""
        assert PromptStyle.DIRECT.value == "direct"
        assert PromptStyle.CHAIN_OF_THOUGHT.value == "cot"
        assert PromptStyle.FEW_SHOT.value == "few_shot"
        assert PromptStyle.CONTEXTUAL.value == "contextual"
    
    def test_prompt_style_members(self):
        """Test that we have exactly 4 prompt styles"""
        assert len(PromptStyle) == 4


class TestPromptTemplate:
    """Test the PromptTemplate dataclass"""
    
    def test_template_creation(self):
        """Test creating a prompt template"""
        template = PromptTemplate(
            name="test_template",
            template="Hello {name}, welcome to {place}!",
            style=PromptStyle.DIRECT,
            description="A test template"
        )
        
        assert template.name == "test_template"
        assert template.style == PromptStyle.DIRECT
        assert template.description == "A test template"
    
    def test_template_formatting(self):
        """Test formatting a template with arguments"""
        template = PromptTemplate(
            name="greeting",
            template="Hello {name}, you have {count} messages.",
            style=PromptStyle.DIRECT,
            description="Greeting template"
        )
        
        result = template.format(name="Alice", count=5)
        assert result == "Hello Alice, you have 5 messages."
    
    def test_template_partial_formatting(self):
        """Test template with missing arguments raises KeyError"""
        template = PromptTemplate(
            name="test",
            template="{arg1} and {arg2}",
            style=PromptStyle.DIRECT,
            description="Test"
        )
        
        with pytest.raises(KeyError):
            template.format(arg1="only one")


class TestPromptLibrary:
    """Test the PromptLibrary class"""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined"""
        assert hasattr(PromptLibrary, 'SYSTEM_PROMPT')
        assert isinstance(PromptLibrary.SYSTEM_PROMPT, str)
        assert len(PromptLibrary.SYSTEM_PROMPT) > 0
    
    def test_basic_instruction_template(self):
        """Test the basic instruction template"""
        template = PromptLibrary.BASIC_INSTRUCTION
        
        assert template.name == "basic_instruction"
        assert template.style == PromptStyle.DIRECT
        assert "{instruction}" in template.template
        
        # Test formatting
        result = template.format(instruction="Create a hello world function")
        assert "Create a hello world function" in result
        assert "```python" in result
    
    def test_contextual_instruction_template(self):
        """Test the contextual instruction template"""
        template = PromptLibrary.CONTEXTUAL_INSTRUCTION
        
        assert template.name == "contextual_instruction"
        assert template.style == PromptStyle.CONTEXTUAL
        assert "{context}" in template.template
        assert "{instruction}" in template.template
    
    def test_chain_of_thought_template(self):
        """Test the chain of thought template"""
        template = PromptLibrary.CHAIN_OF_THOUGHT
        
        assert template.name == "chain_of_thought"
        assert template.style == PromptStyle.CHAIN_OF_THOUGHT
        assert "step by step" in template.template.lower()
    
    def test_few_shot_template(self):
        """Test the few-shot template"""
        template = PromptLibrary.FEW_SHOT
        
        assert template.name == "few_shot"
        assert template.style == PromptStyle.FEW_SHOT
        assert "Example" in template.template
    
    def test_code_refinement_template(self):
        """Test the code refinement template"""
        template = PromptLibrary.CODE_REFINEMENT
        
        assert template.name == "code_refinement"
        assert "{code}" in template.template
        assert "{error}" in template.template
    
    def test_code_completion_template(self):
        """Test the code completion template"""
        template = PromptLibrary.CODE_COMPLETION
        
        assert template.name == "code_completion"
        assert "{partial_code}" in template.template
        assert "{instruction}" in template.template
    
    def test_naming_suggestion_template(self):
        """Test the naming suggestion template"""
        template = PromptLibrary.NAMING_SUGGESTION
        
        assert template.name == "naming_suggestion"
        assert "{code}" in template.template


class TestPromptEngineer:
    """Test the PromptEngineer class"""
    
    @pytest.fixture
    def engineer(self):
        """Create a PromptEngineer instance"""
        return PromptEngineer()
    
    def test_initialization(self, engineer):
        """Test PromptEngineer initialization"""
        assert engineer.library is not None
        assert isinstance(engineer.cache, dict)
    
    def test_create_prompt_direct_style(self, engineer):
        """Test creating a direct style prompt"""
        prompt = engineer.create_prompt(
            "Create a function to add two numbers",
            style=PromptStyle.DIRECT
        )
        
        assert "Create a function to add two numbers" in prompt
        assert "```python" in prompt
    
    def test_create_prompt_contextual_style(self, engineer):
        """Test creating a contextual style prompt"""
        context = "x = 10\ny = 20"
        prompt = engineer.create_prompt(
            "Create a function to add x and y",
            style=PromptStyle.CONTEXTUAL,
            context=context
        )
        
        assert "Create a function to add x and y" in prompt
        assert "x = 10" in prompt
        assert "y = 20" in prompt
    
    def test_create_prompt_contextual_fallback(self, engineer):
        """Test contextual prompt falls back to direct when no context"""
        prompt = engineer.create_prompt(
            "Create a function",
            style=PromptStyle.CONTEXTUAL,
            context=None
        )
        
        # Should fall back to direct style
        assert "Create a function" in prompt
        assert "context" not in prompt.lower()
    
    def test_create_prompt_chain_of_thought(self, engineer):
        """Test creating a chain of thought prompt"""
        prompt = engineer.create_prompt(
            "Create a complex sorting algorithm",
            style=PromptStyle.CHAIN_OF_THOUGHT
        )
        
        assert "Create a complex sorting algorithm" in prompt
        assert "step" in prompt.lower()
    
    def test_create_prompt_few_shot(self, engineer):
        """Test creating a few-shot prompt"""
        prompt = engineer.create_prompt(
            "Create a factorial function",
            style=PromptStyle.FEW_SHOT
        )
        
        assert "Create a factorial function" in prompt
        assert "Example" in prompt
    
    def test_create_refinement_prompt(self, engineer):
        """Test creating a code refinement prompt"""
        code = "def add(a, b)\n    return a + b"
        error = "SyntaxError: missing colon"
        
        prompt = engineer.create_refinement_prompt(code, error)
        
        assert code in prompt
        assert error in prompt
        assert "corrected code" in prompt.lower()
    
    def test_create_completion_prompt(self, engineer):
        """Test creating a code completion prompt"""
        partial = "def calculate_average(numbers):\n    # TODO"
        instruction = "complete the function to calculate average"
        
        prompt = engineer.create_completion_prompt(partial, instruction)
        
        assert partial in prompt
        assert instruction in prompt
    
    def test_optimize_instruction_function_creation(self, engineer):
        """Test instruction optimization for function creation"""
        # Test various function creation patterns
        tests = [
            ("make add function", "Create a function that add function"),
            ("get user data", "Create a function to get user data"),
            ("calculate total", "Create a function to calculate total"),
            ("find maximum", "Create a function to find maximum"),
            ("check validity", "Create a function to check validity")
        ]
        
        for input_inst, expected_start in tests:
            result = engineer.optimize_instruction(input_inst)
            assert result.startswith(expected_start)
    
    def test_optimize_instruction_list_handling(self, engineer):
        """Test instruction optimization for list operations"""
        instruction = "sort the list of numbers"
        result = engineer.optimize_instruction(instruction)
        
        assert "return" in result.lower()
        assert "list" in result.lower()
    
    def test_optimize_instruction_file_handling(self, engineer):
        """Test instruction optimization for file operations"""
        instruction = "read data from file"
        result = engineer.optimize_instruction(instruction)
        
        assert "error handling" in result.lower()
    
    def test_normalize_instruction(self, engineer):
        """Test instruction normalization"""
        # Test whitespace normalization
        instruction = "  Create   a    function  "
        normalized = engineer._normalize_instruction(instruction)
        assert normalized == "Create a function."
        
        # Test punctuation addition
        instruction = "Create a function"
        normalized = engineer._normalize_instruction(instruction)
        assert normalized.endswith(".")
        
        # Test capitalization
        instruction = "create a function."
        normalized = engineer._normalize_instruction(instruction)
        assert normalized[0].isupper()
    
    def test_select_best_style_simple(self, engineer):
        """Test style selection for simple instructions"""
        simple_instructions = [
            "print hello world",
            "return the sum",
            "add two numbers"
        ]
        
        for inst in simple_instructions:
            style = engineer.select_best_style(inst)
            assert style == PromptStyle.DIRECT
    
    def test_select_best_style_complex(self, engineer):
        """Test style selection for complex instructions"""
        complex_instruction = "Create a complex algorithm to optimize database queries"
        style = engineer.select_best_style(complex_instruction)
        assert style in [PromptStyle.CHAIN_OF_THOUGHT, PromptStyle.FEW_SHOT]
    
    def test_select_best_style_with_context(self, engineer):
        """Test style selection with context"""
        instruction = "Add a method to the class"
        context = "class Calculator:\n    def __init__(self):\n        pass"
        
        style = engineer.select_best_style(instruction, context)
        assert style == PromptStyle.CONTEXTUAL
    
    def test_extract_code_from_response_with_markers(self, engineer):
        """Test extracting code from response with markdown markers"""
        response = """Here's the solution:

```python
def add(a, b):
    return a + b
```

This function adds two numbers."""
        
        code = engineer.extract_code_from_response(response)
        assert code == "def add(a, b):\n    return a + b"
    
    def test_extract_code_from_response_without_markers(self, engineer):
        """Test extracting code from response without markers"""
        response = """Here's the solution:

def add(a, b):
    return a + b

This function adds two numbers."""
        
        code = engineer.extract_code_from_response(response)
        assert "def add(a, b):" in code
        assert "return a + b" in code
    
    def test_extract_code_from_response_multiple_blocks(self, engineer):
        """Test extracting code when multiple code blocks exist"""
        response = """First, import required modules:

```python
import math
```

Then create the function:

```python
def calculate_circle_area(radius):
    return math.pi * radius ** 2
```"""
        
        # Should extract the first code block
        code = engineer.extract_code_from_response(response)
        assert "import math" in code
    
    def test_extract_code_empty_response(self, engineer):
        """Test extracting code from empty response"""
        code = engineer.extract_code_from_response("")
        assert code == ""
    
    def test_extract_code_no_code_in_response(self, engineer):
        """Test extracting code when no code is present"""
        response = "This is just plain text without any code."
        code = engineer.extract_code_from_response(response)
        assert code == ""


class TestConvenienceFunctions:
    """Test the module-level convenience functions"""
    
    def test_create_prompt_function(self):
        """Test the create_prompt convenience function"""
        prompt = create_prompt("Create a hello world function")
        assert "Create a hello world function" in prompt
        assert isinstance(prompt, str)
    
    def test_optimize_instruction_function(self):
        """Test the optimize_instruction convenience function"""
        result = optimize_instruction("make calculator")
        assert result.startswith("Create a function")
    
    def test_extract_code_function(self):
        """Test the extract_code convenience function"""
        response = "```python\nprint('hello')\n```"
        code = extract_code(response)
        assert code == "print('hello')"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def engineer(self):
        return PromptEngineer()
    
    def test_empty_instruction(self, engineer):
        """Test handling of empty instruction"""
        prompt = engineer.create_prompt("")
        assert prompt  # Should still create some prompt
    
    def test_very_long_instruction(self, engineer):
        """Test handling of very long instruction"""
        long_instruction = "Create a function that " + " and ".join(
            [f"does task {i}" for i in range(100)]
        )
        prompt = engineer.create_prompt(long_instruction)
        assert len(prompt) > len(long_instruction)
    
    def test_special_characters_in_instruction(self, engineer):
        """Test handling of special characters"""
        instruction = "Create a function that handles $pecial ch@rs & symbols!"
        prompt = engineer.create_prompt(instruction)
        assert "$pecial ch@rs & symbols!" in prompt
    
    def test_unicode_in_instruction(self, engineer):
        """Test handling of Unicode characters"""
        instruction = "Create a function that prints 你好世界 and émojis 🌍"
        prompt = engineer.create_prompt(instruction)
        assert "你好世界" in prompt
        assert "🌍" in prompt
    
    def test_code_extraction_with_nested_backticks(self, engineer):
        """Test code extraction with nested backticks"""
        response = """```python
def print_code():
    code = '''
    def inner():
        return "nested"
    '''
    print(code)
```"""
        
        code = engineer.extract_code_from_response(response)
        assert "def print_code():" in code
        assert "def inner():" in code
    
    def test_malformed_code_blocks(self, engineer):
        """Test handling of malformed code blocks"""
        response = "```python\ndef func():\n    pass"  # Missing closing ```
        
        code = engineer.extract_code_from_response(response)
        # Should still try to extract what's there
        assert "def func():" in code


@pytest.mark.parametrize("instruction,expected_style", [
    ("print hello", PromptStyle.DIRECT),
    ("implement a complex sorting algorithm with multiple criteria", 
     PromptStyle.CHAIN_OF_THOUGHT),
    ("add method to class", PromptStyle.DIRECT),
])
def test_style_selection_parametrized(instruction, expected_style):
    """Parametrized test for style selection"""
    engineer = PromptEngineer()
    # For simple tests without context
    if "complex" in instruction:
        style = engineer.select_best_style(instruction)
        assert style in [PromptStyle.CHAIN_OF_THOUGHT, PromptStyle.FEW_SHOT]
    else:
        style = engineer.select_best_style(instruction)
        assert style == expected_style


if __name__ == "__main__":
    pytest.main([__file__, "-v"])