"""
Local Transformer Model Implementation for the Pseudocode Translator

This module provides a HuggingFace Transformers-based model implementation
for local code generation using models like CodeGen, StarCoder, etc.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import torch

from .base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult,
    validate_instruction
)
from .model_factory import register_model, ModelPriority

logger = logging.getLogger(__name__)

# Try to import transformers
try:
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer,
        GenerationConfig, StoppingCriteria, StoppingCriteriaList
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    AutoModelForCausalLM = None
    AutoTokenizer = None
    GenerationConfig = None
    StoppingCriteria = None
    StoppingCriteriaList = None


class CodeStoppingCriteria:
    """Custom stopping criteria for code generation"""
    
    def __init__(self, tokenizer, stop_tokens):
        self.tokenizer = tokenizer
        self.stop_tokens = stop_tokens
    
    def __call__(self, input_ids, scores, **kwargs):
        # Check if any stop token is generated
        for stop_token in self.stop_tokens:
            if input_ids[0][-1] == stop_token:
                return True
        return False


@register_model(
    name="local-transformer",
    aliases=["huggingface", "hf", "transformer", "codegen", "starcoder"],
    priority=ModelPriority.MEDIUM
)
class LocalTransformerModel(BaseTranslationModel):
    """
    Local transformer model using HuggingFace Transformers
    
    Supports various code generation models like CodeGen, StarCoder,
    CodeT5, etc. for offline code generation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize local transformer model
        
        Args:
            config: Model configuration dictionary
        """
        super().__init__(config)
        
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers package is required. "
                "Install with: pip install transformers torch"
            )
        
        # Set default configuration
        self.config.setdefault('model_name', 'Salesforce/codegen-350M-mono')
        self.config.setdefault(
            'device', 'cuda' if torch.cuda.is_available() else 'cpu'
        )
        self.config.setdefault(
            'torch_dtype',
            'float16' if torch.cuda.is_available() else 'float32'
        )
        self.config.setdefault('temperature', 0.3)
        self.config.setdefault('top_p', 0.9)
        self.config.setdefault('top_k', 40)
        self.config.setdefault('max_length', 2048)
        self.config.setdefault('do_sample', True)
        self.config.setdefault('num_return_sequences', 1)
        self.config.setdefault('load_in_8bit', False)
        self.config.setdefault('trust_remote_code', False)
        
        self._model = None
        self._tokenizer = None
        
        # Language mapping for model selection
        self.language_suffixes = {
            OutputLanguage.PYTHON: "-python",
            OutputLanguage.JAVASCRIPT: "-javascript",
            OutputLanguage.JAVA: "-java",
            OutputLanguage.CPP: "-cpp",
            OutputLanguage.GO: "-go",
            OutputLanguage.RUST: "-rust",
            OutputLanguage.PHP: "-php",
            OutputLanguage.RUBY: "-ruby",
            OutputLanguage.SQL: "-sql",
            OutputLanguage.BASH: "-shell"
        }
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        return ModelMetadata(
            name="local-transformer",
            version=self.config['model_name'].split('/')[-1],
            supported_languages=list(OutputLanguage),
            description=(
                "Local transformer model using HuggingFace Transformers. "
                "Supports various code generation models for offline use."
            ),
            author="HuggingFace/Community",
            license="Various (model-dependent)",
            model_type="transformer",
            size_gb=self._estimate_model_size(),
            requires_gpu=self.config['device'] == 'cuda',
            supports_streaming=True,
            max_context_length=self.config['max_length']
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Get model capabilities"""
        return ModelCapabilities(
            translate_instruction=True,
            validate_input=True,
            get_capabilities=True,
            supports_refinement=True,
            supports_batch_processing=True,
            supports_context_aware=True,
            supports_code_completion=True,
            supports_error_correction=False,
            tokens_per_second=self._estimate_speed(),
            max_batch_size=4,
            optimal_temperature=0.3,
            min_memory_gb=2.0,
            recommended_memory_gb=8.0
        )
    
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """
        Initialize the transformer model
        
        Args:
            model_path: Optional local path to model
            **kwargs: Additional initialization parameters
        """
        model_name_or_path = (str(model_path) if model_path
                              else self.config['model_name'])
        logger.info(f"Loading transformer model: {model_name_or_path}")
        
        try:
            # Determine torch dtype
            torch_dtype = getattr(torch, self.config['torch_dtype'])
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name_or_path,
                trust_remote_code=self.config['trust_remote_code']
            )
            
            # Set padding token if not present
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Load model
            load_kwargs = {
                'torch_dtype': torch_dtype,
                'device_map': ('auto' if self.config['device'] == 'cuda'
                               else None),
                'trust_remote_code': self.config['trust_remote_code']
            }
            
            if self.config['load_in_8bit']:
                load_kwargs['load_in_8bit'] = True
            
            self._model = AutoModelForCausalLM.from_pretrained(
                model_name_or_path,
                **load_kwargs
            )
            
            # Move to device if not using device_map
            if (self.config['device'] != 'cuda' or
                    not load_kwargs.get('device_map')):
                self._model = self._model.to(self.config['device'])
            
            # Set to eval mode
            self._model.eval()
            
            self._initialized = True
            logger.info("Transformer model loaded successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load transformer model: {str(e)}")
    
    def translate(self,
                  instruction: str,
                  config: Optional[TranslationConfig] = None,
                  context: Optional[Dict[str, Any]] = None
                  ) -> TranslationResult:
        """
        Translate instruction using local transformer
        
        Args:
            instruction: Natural language instruction
            config: Translation configuration
            context: Optional context
            
        Returns:
            TranslationResult with generated code
        """
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        # Use default config if not provided
        if config is None:
            config = TranslationConfig()
        
        try:
            # Build prompt
            prompt = self._build_prompt(instruction, config, context)
            
            # Tokenize
            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.config['max_length']
            ).to(self._model.device)
            
            # Generate
            with torch.no_grad():
                generation_config = GenerationConfig(
                    temperature=config.temperature,
                    top_p=config.top_p,
                    top_k=config.top_k,
                    max_new_tokens=config.max_tokens,
                    do_sample=self.config['do_sample'],
                    num_return_sequences=self.config['num_return_sequences'],
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id
                )
                
                # Add stopping criteria if stop sequences provided
                stopping_criteria = None
                if config.stop_sequences:
                    stop_tokens = [
                        self._tokenizer.encode(
                            seq, add_special_tokens=False
                        )[0]
                        for seq in config.stop_sequences
                    ]
                    stopping_criteria = StoppingCriteriaList([
                        CodeStoppingCriteria(self._tokenizer, stop_tokens)
                    ])
                
                outputs = self._model.generate(
                    **inputs,
                    generation_config=generation_config,
                    stopping_criteria=stopping_criteria
                )
            
            # Decode
            generated_text = self._tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )
            
            # Extract code
            code = self._extract_code(generated_text, config.target_language)
            
            return TranslationResult(
                success=True,
                code=code,
                language=config.target_language,
                confidence=0.8,  # Fixed confidence for local models
                metadata={
                    'model': self.config['model_name'],
                    'device': self.config['device'],
                    'prompt_length': len(prompt),
                    'generated_length': len(code)
                }
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return TranslationResult(
                success=False,
                code=None,
                language=config.target_language,
                errors=[f"Translation error: {str(e)}"]
            )
    
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """Validate input instruction"""
        # Basic validation
        is_valid, error = validate_instruction(
            instruction, max_length=1000
        )
        
        if not is_valid:
            return is_valid, error
        
        # Check tokenization length
        if self._tokenizer:
            tokens = self._tokenizer.encode(instruction)
            if len(tokens) > self.config['max_length'] * 0.8:
                return False, "Instruction too long for model context"
        
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get detailed model capabilities"""
        return {
            "model_name": self.config['model_name'],
            "device": self.config['device'],
            "supported_languages": [lang.value for lang in OutputLanguage],
            "features": {
                "local": True,
                "gpu_enabled": self.config['device'] == 'cuda',
                "8bit_quantization": self.config['load_in_8bit'],
                "max_context": self.config['max_length']
            },
            "performance": {
                "estimated_tokens_per_second": self._estimate_speed(),
                "memory_usage_gb": self._estimate_memory_usage()
            }
        }
    
    def _build_prompt(self,
                      instruction: str,
                      config: TranslationConfig,
                      context: Optional[Dict[str, Any]]) -> str:
        """Build prompt for the model"""
        # Language-specific prompt
        lang_instruction = (
            f"Generate {config.target_language.value} code for: "
            f"{instruction}"
        )
        
        # Add context if provided
        if context and context.get('code'):
            prompt = (
                f"Given the following context:\n"
                f"```\n{context['code']}\n```\n\n"
                f"{lang_instruction}\n\n"
                f"Code:"
            )
        else:
            prompt = f"{lang_instruction}\n\nCode:"
        
        return prompt
    
    def _extract_code(self, text: str, language: OutputLanguage) -> str:
        """Extract code from generated text"""
        # Remove any markdown formatting
        if "```" in text:
            # Extract from code block
            lines = text.split('\n')
            in_code = False
            code_lines = []
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    code_lines.append(line)
            
            if code_lines:
                return '\n'.join(code_lines)
        
        # Clean up the text
        text = text.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            "Here's the code:",
            "Here is the code:",
            "Code:",
            "```",
            f"```{language.value}"
        ]
        
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        return text
    
    def _estimate_model_size(self) -> float:
        """Estimate model size in GB"""
        model_name = self.config['model_name'].lower()
        
        # Common model sizes
        if "350m" in model_name:
            return 0.7
        elif "1b" in model_name or "1.5b" in model_name:
            return 3.0
        elif "2b" in model_name or "2.7b" in model_name:
            return 5.5
        elif "6b" in model_name or "7b" in model_name:
            return 13.0
        elif "13b" in model_name:
            return 26.0
        else:
            return 2.0  # Default estimate
    
    def _estimate_speed(self) -> float:
        """Estimate tokens per second"""
        if self.config['device'] == 'cuda':
            return 30.0  # GPU estimate
        else:
            return 5.0   # CPU estimate
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in GB"""
        base_size = self._estimate_model_size()
        if self.config['load_in_8bit']:
            return base_size * 0.5
        elif self.config['torch_dtype'] == 'float16':
            return base_size
        else:
            return base_size * 2