"""
Prompt templates and engineering for the Pseudocode Translator

This module contains carefully crafted prompts to guide the LLM in generating
high-quality Python code from English instructions.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class PromptStyle(Enum):
    """Different prompting styles for various use cases"""
    DIRECT = "direct"  # Simple instruction to code
    CHAIN_OF_THOUGHT = "cot"  # Step-by-step reasoning
    FEW_SHOT = "few_shot"  # With examples
    CONTEXTUAL = "contextual"  # With surrounding code context


@dataclass
class PromptTemplate:
    """Base class for prompt templates"""
    name: str
    template: str
    style: PromptStyle
    description: str
    
    def format(self, **kwargs) -> str:
        """Format the template with provided arguments"""
        return self.template.format(**kwargs)


class PromptLibrary:
    """Collection of prompt templates for different scenarios"""
    
    # System prompt for the model
    SYSTEM_PROMPT = """You are an expert Python programmer. Your task is to convert English instructions into clean, efficient, and correct Python code.

Guidelines:
1. Write clear, readable code following PEP 8 conventions
2. Use descriptive variable and function names
3. Add comments only for complex logic
4. Handle edge cases and potential errors
5. Import only necessary modules at the top of the code
6. Use type hints when appropriate
7. Prefer built-in functions and Pythonic idioms
8. Ensure the code is safe and doesn't perform harmful operations"""

    # Basic instruction to code prompt
    BASIC_INSTRUCTION = PromptTemplate(
        name="basic_instruction",
        style=PromptStyle.DIRECT,
        description="Simple instruction to Python code conversion",
        template="""Convert this instruction to Python code:

Instruction: {instruction}

Python code:
```python
"""
    )
    
    # Instruction with context
    CONTEXTUAL_INSTRUCTION = PromptTemplate(
        name="contextual_instruction",
        style=PromptStyle.CONTEXTUAL,
        description="Instruction with surrounding code context",
        template="""Convert this instruction to Python code that fits with the existing context:

Existing code context:
```python
{context}
```

Instruction: {instruction}

Generate Python code that integrates with the above context:
```python
"""
    )
    
    # Chain of thought prompt for complex instructions
    CHAIN_OF_THOUGHT = PromptTemplate(
        name="chain_of_thought",
        style=PromptStyle.CHAIN_OF_THOUGHT,
        description="Step-by-step reasoning for complex instructions",
        template="""Let's think step by step about converting this instruction to Python code.

Instruction: {instruction}

First, let me break down what needs to be done:
1. Identify the main task
2. Determine required inputs and outputs
3. Plan the algorithm
4. Consider edge cases
5. Write the code

Now, here's the Python implementation:
```python
"""
    )
    
    # Few-shot prompt with examples
    FEW_SHOT = PromptTemplate(
        name="few_shot",
        style=PromptStyle.FEW_SHOT,
        description="Instruction with examples for better guidance",
        template="""Here are some examples of converting instructions to Python code:

Example 1:
Instruction: Create a function that calculates the factorial of a number
Code:
```python
def factorial(n):
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

Example 2:
Instruction: Read a CSV file and return the data as a list of dictionaries
Code:
```python
import csv

def read_csv_to_dict(filename):
    data = []
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(dict(row))
    return data
```

Now convert this instruction:
Instruction: {instruction}

Python code:
```python
"""
    )
    
    # Code refinement prompt
    CODE_REFINEMENT = PromptTemplate(
        name="code_refinement",
        style=PromptStyle.DIRECT,
        description="Fix or improve existing code",
        template="""The following Python code needs to be fixed or improved:

Original code:
```python
{code}
```

Issue/Error: {error}

Please provide the corrected code:
```python
"""
    )
    
    # Code completion prompt
    CODE_COMPLETION = PromptTemplate(
        name="code_completion",
        style=PromptStyle.CONTEXTUAL,
        description="Complete partially written code",
        template="""Complete the following Python code:

```python
{partial_code}
```

The code should: {instruction}

Completed code:
```python
"""
    )
    
    # Variable and function naming prompt
    NAMING_SUGGESTION = PromptTemplate(
        name="naming_suggestion",
        style=PromptStyle.DIRECT,
        description="Suggest better names for variables and functions",
        template="""Suggest better Python names for the following:

Current code:
```python
{code}
```

Provide the same code with improved variable and function names following Python conventions:
```python
"""
    )


class PromptEngineer:
    """
    Handles prompt engineering and optimization for better code generation
    """
    
    def __init__(self):
        self.library = PromptLibrary()
        self.cache: Dict[str, str] = {}
    
    def create_prompt(self, 
                     instruction: str, 
                     style: PromptStyle = PromptStyle.DIRECT,
                     context: Optional[str] = None,
                     examples: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Create an optimized prompt based on the instruction and style
        
        Args:
            instruction: The English instruction to convert
            style: The prompting style to use
            context: Optional code context
            examples: Optional examples for few-shot prompting
            
        Returns:
            Formatted prompt string
        """
        # Clean and normalize the instruction
        instruction = self._normalize_instruction(instruction)
        
        # Select appropriate template
        if style == PromptStyle.DIRECT:
            template = self.library.BASIC_INSTRUCTION
            return template.format(instruction=instruction)
        
        elif style == PromptStyle.CONTEXTUAL:
            if not context:
                # Fall back to direct style if no context
                return self.create_prompt(instruction, PromptStyle.DIRECT)
            template = self.library.CONTEXTUAL_INSTRUCTION
            return template.format(instruction=instruction, context=context)
        
        elif style == PromptStyle.CHAIN_OF_THOUGHT:
            template = self.library.CHAIN_OF_THOUGHT
            return template.format(instruction=instruction)
        
        elif style == PromptStyle.FEW_SHOT:
            template = self.library.FEW_SHOT
            return template.format(instruction=instruction)
        
        else:
            # Default to direct style
            template = self.library.BASIC_INSTRUCTION
            return template.format(instruction=instruction)
    
    def create_refinement_prompt(self, code: str, error: str) -> str:
        """Create a prompt for code refinement/fixing"""
        template = self.library.CODE_REFINEMENT
        return template.format(code=code, error=error)
    
    def create_completion_prompt(self, partial_code: str, instruction: str) -> str:
        """Create a prompt for code completion"""
        template = self.library.CODE_COMPLETION
        return template.format(partial_code=partial_code, instruction=instruction)
    
    def optimize_instruction(self, instruction: str) -> str:
        """
        Optimize an instruction for better code generation
        
        Args:
            instruction: Raw English instruction
            
        Returns:
            Optimized instruction
        """
        # Add clarifying keywords if missing
        optimizations = {
            r"^make\s+": "Create a function that ",
            r"^get\s+": "Create a function to get ",
            r"^calculate\s+": "Create a function to calculate ",
            r"^find\s+": "Create a function to find ",
            r"^check\s+": "Create a function to check ",
        }
        
        import re
        optimized = instruction
        
        for pattern, replacement in optimizations.items():
            if re.match(pattern, instruction.lower()):
                optimized = re.sub(pattern, replacement, instruction, flags=re.IGNORECASE)
                break
        
        # Add common clarifications
        if "list" in optimized.lower() and "return" not in optimized.lower():
            optimized += " and return the result as a list"
        
        if "file" in optimized.lower() and "handle" not in optimized.lower():
            optimized += " with proper error handling"
        
        return optimized
    
    def _normalize_instruction(self, instruction: str) -> str:
        """Normalize and clean instruction text"""
        # Remove extra whitespace
        instruction = " ".join(instruction.split())
        
        # Ensure proper ending
        if instruction and not instruction[-1] in '.!?':
            instruction += '.'
        
        # Capitalize first letter
        if instruction:
            instruction = instruction[0].upper() + instruction[1:]
        
        return instruction
    
    def select_best_style(self, instruction: str, context: Optional[str] = None) -> PromptStyle:
        """
        Automatically select the best prompting style based on instruction complexity
        
        Args:
            instruction: The instruction to analyze
            context: Optional code context
            
        Returns:
            Best PromptStyle for the instruction
        """
        instruction_lower = instruction.lower()
        
        # Check instruction complexity indicators
        complex_indicators = [
            "algorithm", "complex", "multiple", "system", "class",
            "integrate", "optimize", "efficient", "handle errors"
        ]
        
        simple_indicators = [
            "print", "return", "add", "subtract", "simple", "basic"
        ]
        
        # Count indicators
        complex_count = sum(1 for indicator in complex_indicators if indicator in instruction_lower)
        simple_count = sum(1 for indicator in simple_indicators if indicator in instruction_lower)
        
        # Determine style
        if context and len(context.strip()) > 50:
            return PromptStyle.CONTEXTUAL
        elif complex_count >= 2:
            return PromptStyle.CHAIN_OF_THOUGHT
        elif complex_count == 1 and simple_count == 0:
            return PromptStyle.FEW_SHOT
        else:
            return PromptStyle.DIRECT
    
    def extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from model response
        
        Args:
            response: Raw model response
            
        Returns:
            Extracted Python code
        """
        import re
        
        # Look for code blocks
        code_block_pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            # Return the first code block
            return matches[0].strip()
        
        # Try to find code without markers
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Simple heuristics to identify code
            if any([
                line.strip().startswith('def '),
                line.strip().startswith('class '),
                line.strip().startswith('import '),
                line.strip().startswith('from '),
                re.match(r'^\s*\w+\s*=', line),  # Variable assignment
                re.match(r'^\s*if\s+.*:', line),  # If statement
                re.match(r'^\s*for\s+.*:', line),  # For loop
                re.match(r'^\s*while\s+.*:', line),  # While loop
            ]):
                in_code = True
            
            if in_code:
                # Stop at obvious non-code markers
                if line.strip() and not any([
                    line[0].isspace(),  # Indented line
                    line.strip()[0] in '#@',  # Comment or decorator
                    ':' in line,  # Likely part of code structure
                    '=' in line,  # Assignment
                    '(' in line,  # Function call
                    line.strip() in ['', 'pass', 'continue', 'break']
                ]):
                    break
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip()


# Convenience functions
def create_prompt(instruction: str, **kwargs) -> str:
    """Create a prompt using the default engineer"""
    engineer = PromptEngineer()
    return engineer.create_prompt(instruction, **kwargs)


def optimize_instruction(instruction: str) -> str:
    """Optimize an instruction using the default engineer"""
    engineer = PromptEngineer()
    return engineer.optimize_instruction(instruction)


def extract_code(response: str) -> str:
    """Extract code from a model response"""
    engineer = PromptEngineer()
    return engineer.extract_code_from_response(response)