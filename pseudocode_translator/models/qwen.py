"""
Qwen model implementation for the Pseudocode Translator

This module provides a Qwen 7B model implementation using llama-cpp-python.
The model is optimized for code generation and instruction following.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError(
        "llama-cpp-python is required for Qwen model support. "
        "Install with: pip install llama-cpp-python"
    )

from ..prompts import PromptEngineer, PromptLibrary
from .base import BaseModel, ModelMetadata, ModelCapabilities, ModelFormat
from .registry import register_model


logger = logging.getLogger(__name__)


@register_model(name="qwen", aliases=["qwen-7b", "qwen-7b-chat"])
class QwenModel(BaseModel):
    """
    Qwen 7B Chat model implementation
    
    This model uses the GGUF format and is optimized for code generation
    from natural language instructions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Qwen model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        super().__init__(config)
        self.prompt_engineer = PromptEngineer()
        
        # Set default configuration values
        self.config.setdefault('n_ctx', 2048)
        self.config.setdefault('n_batch', 512)
        self.config.setdefault('n_threads', 4)
        self.config.setdefault('n_gpu_layers', 0)
        self.config.setdefault('temperature', 0.3)
        self.config.setdefault('top_p', 0.9)
        self.config.setdefault('top_k', 40)
        self.config.setdefault('repeat_penalty', 1.1)
        self.config.setdefault('max_tokens', 1024)
        self.config.setdefault('seed', -1)
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        return ModelMetadata(
            name="qwen",
            display_name="Qwen 7B Chat",
            description=(
                "Qwen 7B is a large language model developed by Alibaba "
                "Cloud. This is the chat variant optimized for instruction "
                "following and code generation."
            ),
            version="7B-Chat-Q4_K_M",
            author="Alibaba Cloud",
            license="Tongyi Qianwen License Agreement",
            homepage="https://github.com/QwenLM/Qwen",
            download_url="https://huggingface.co/Qwen/Qwen-7B-Chat-GGUF",
            format=ModelFormat.GGUF,
            filename_pattern="qwen-7b-*.gguf",
            tags=["code-generation", "instruction-following", "chat"],
            examples=[
                {
                    "instruction": "create a function to calculate factorial",
                    "output": (
                        "def factorial(n):\n"
                        "    if n <= 1:\n"
                        "        return 1\n"
                        "    return n * factorial(n - 1)"
                    )
                },
                {
                    "instruction": "sort a list of numbers in ascending order",
                    "output": "numbers.sort()  # or sorted(numbers)"
                }
            ],
            citation=(
                "@article{qwen,\n"
                "  title={Qwen Technical Report},\n"
                "  author={Jinze Bai and Shuai Bai and Yunfei Chu and "
                "Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan "
                "and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui "
                "and Luo Ji and Mei Li "
                "and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu "
                "and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men "
                "and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan "
                "and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang "
                "and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu "
                "and An Yang and Hao Yang and Jian Yang and Shusheng Yang "
                "and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan "
                "and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang "
                "and Zhenru Zhang and Chang Zhou and Jingren Zhou "
                "and Xiaohuan Zhou and Tianhang Zhu},\n"
                "  journal={arXiv preprint arXiv:2309.16609},\n"
                "  year={2023}\n"
                "}"
            )
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Get model capabilities"""
        return ModelCapabilities(
            supported_languages=["python", "javascript", "java", "c++", "go"],
            max_context_length=self.config['n_ctx'],
            supports_code_completion=True,
            supports_translation=True,
            supports_refinement=True,
            supports_streaming=False,  # llama-cpp no streaming support yet
            min_memory_gb=4.0,  # Q4_K_M quantization
            recommended_memory_gb=8.0,
            supports_gpu=True,
            requires_gpu=False,
            model_size_gb=4.5,  # Approximate size of Q4_K_M
            quantization_bits=4,
            is_instruction_tuned=True,
            tokens_per_second_cpu=10.0,  # Approximate
            tokens_per_second_gpu=50.0,  # Approximate with GPU
        )
    
    def initialize(self, model_path: Path, **kwargs) -> None:
        """
        Initialize/load the Qwen model
        
        Args:
            model_path: Path to the GGUF model file
            **kwargs: Additional initialization parameters
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If model loading fails
        """
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Please download the Qwen 7B GGUF model from:\n"
                f"{self.metadata.download_url}"
            )
        
        logger.info(f"Loading Qwen model from: {model_path}")
        
        try:
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self.config['n_ctx'],
                n_batch=self.config['n_batch'],
                n_threads=self.config['n_threads'],
                n_gpu_layers=self.config['n_gpu_layers'],
                verbose=kwargs.get('verbose', False),
                seed=self.config['seed'],
            )
            self._initialized = True
            logger.info("Qwen model loaded successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Qwen model: {str(e)}")
    
    def generate(self,
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.3,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 stop_sequences: Optional[List[str]] = None,
                 **kwargs) -> str:
        """
        Generate text from a prompt using Qwen
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            stop_sequences: List of sequences to stop generation
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        if not self._initialized:
            raise RuntimeError(
                "Model not initialized. Call initialize() first."
            )
        
        # Use provided parameters or fall back to config
        generation_params = {
            'max_tokens': max_tokens or self.config['max_tokens'],
            'temperature': temperature or self.config['temperature'],
            'top_p': top_p or self.config['top_p'],
            'top_k': top_k or self.config['top_k'],
            'repeat_penalty': kwargs.get('repeat_penalty', 
                                         self.config['repeat_penalty']),
            'stop': stop_sequences or ["```", "\n\n\n", "Instruction:"],
        }
        
        try:
            response = self._model(prompt, **generation_params)
            return response['choices'][0]['text']
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate text: {str(e)}")
    
    def translate_instruction(self,
                              instruction: str,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """
        Translate an English instruction to Python code
        
        Args:
            instruction: Natural language instruction
            context: Optional context (e.g., surrounding code)
            
        Returns:
            Generated Python code
        """
        # Extract code context if provided
        code_context = context.get('code', '') if context else ''
        
        # Select best prompting style
        prompt_style = self.prompt_engineer.select_best_style(
            instruction, code_context
        )
        
        # Create prompt
        prompt = self.prompt_engineer.create_prompt(
            instruction=instruction,
            style=prompt_style,
            context=code_context
        )
        
        # Add system prompt
        full_prompt = f"{PromptLibrary.SYSTEM_PROMPT}\n\n{prompt}"
        
        # Generate code
        logger.debug(f"Translating: {instruction[:50]}...")
        generated_text = self.generate(full_prompt)
        
        # Extract code from response
        code = self.prompt_engineer.extract_code_from_response(generated_text)
        
        # Validate and clean code
        return self._validate_and_clean_code(code)
    
    def refine_code(self,
                    code: str,
                    error_context: str,
                    max_attempts: int = 1) -> str:
        """
        Attempt to fix code based on error feedback
        
        Args:
            code: Code that needs fixing
            error_context: Error message or context
            max_attempts: Maximum refinement attempts
            
        Returns:
            Refined code
        """
        # Create refinement prompt
        prompt = self.prompt_engineer.create_refinement_prompt(
            code, error_context
        )
        full_prompt = f"{PromptLibrary.SYSTEM_PROMPT}\n\n{prompt}"
        
        # Generate with lower temperature for refinement
        generated_text = self.generate(
            full_prompt,
            temperature=self.config['temperature'] * 0.8
        )
        
        # Extract and validate refined code
        refined_code = self.prompt_engineer.extract_code_from_response(
            generated_text
        )
        return self._validate_and_clean_code(refined_code)
    
    def _validate_and_clean_code(self, code: str) -> str:
        """
        Validate and clean generated code
        
        Args:
            code: Generated code to validate
            
        Returns:
            Cleaned and validated code
        """
        if not code or not code.strip():
            return ""
        
        # Remove any remaining markdown artifacts
        code = code.replace("```python", "").replace("```", "")
        
        # Basic syntax validation
        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            logger.warning(f"Generated code has syntax error: {e}")
            # Try to fix common issues
            code = self._attempt_syntax_fix(code)
        
        return code.strip()
    
    def _attempt_syntax_fix(self, code: str) -> str:
        """
        Attempt to fix common syntax issues in generated code
        
        Args:
            code: Code with potential syntax errors
            
        Returns:
            Potentially fixed code
        """
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix incomplete function/class definitions
            if (line.strip() and
                    line.strip().endswith(':') and
                    i + 1 < len(lines) and
                    not lines[i + 1].strip()):
                fixed_lines.append(line)
                fixed_lines.append("    pass  # TODO: Implement")
                continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def validate_config(self) -> List[str]:
        """
        Validate Qwen-specific configuration
        
        Returns:
            List of validation issues
        """
        issues = super().validate_config()
        
        # Check context size
        if self.config['n_ctx'] < 512:
            issues.append(
                f"Context size too small: {self.config['n_ctx']}. "
                f"Minimum recommended is 512"
            )
        
        # Check batch size
        if self.config['n_batch'] > self.config['n_ctx']:
            issues.append(
                f"Batch size ({self.config['n_batch']}) cannot exceed "
                f"context size ({self.config['n_ctx']})"
            )
        
        # Check GPU layers
        if self.config['n_gpu_layers'] < 0:
            issues.append("n_gpu_layers must be >= 0")
        
        return issues