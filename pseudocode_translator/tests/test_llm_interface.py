"""
Unit tests for the llm_interface module
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path
import json
import hashlib
from pseudocode_translator.llm_interface import (
    LLMInterface, TranslationCache, create_llm_interface
)


class TestTranslationCache:
    """Test the TranslationCache class"""
    
    def test_initialization(self):
        """Test cache initialization"""
        cache = TranslationCache(max_size=100, ttl_seconds=3600)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert len(cache._cache) == 0
    
    def test_put_and_get(self):
        """Test putting and getting items from cache"""
        cache = TranslationCache()
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Non-existent key
        assert cache.get("key2") is None
    
    def test_cache_expiration(self):
        """Test cache TTL expiration"""
        cache = TranslationCache(ttl_seconds=0)  # Immediate expiration
        
        cache.put("key1", "value1")
        # Should expire immediately
        assert cache.get("key1") is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = TranslationCache(max_size=2)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_clear_cache(self):
        """Test clearing the cache"""
        cache = TranslationCache()
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        cache.clear()
        assert len(cache._cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_thread_safety(self):
        """Test thread safety of cache operations"""
        cache = TranslationCache()
        
        # Basic thread safety test - mainly checking no exceptions
        import threading
        
        def add_items():
            for i in range(10):
                cache.put(f"key{i}", f"value{i}")
        
        threads = [threading.Thread(target=add_items) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have some items (exact count may vary due to overwrites)
        assert len(cache._cache) > 0


class TestLLMInterface:
    """Test the LLMInterface class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock LLM configuration"""
        config = Mock()
        config.model_type = "qwen-7b"
        config.model_name = "qwen-7b-q4_k_m.gguf"
        config.models_dir = "./models"
        config.n_ctx = 2048
        config.n_batch = 512
        config.n_threads = 4
        config.n_gpu_layers = 0
        config.max_tokens = 1024
        config.temperature = 0.7
        config.top_p = 0.95
        config.top_k = 40
        config.repeat_penalty = 1.1
        config.cache_enabled = True
        config.cache_ttl_hours = 24
        config.validation_level = "normal"
        
        # Mock methods
        config.validate.return_value = []
        config.get_model_path.return_value = Path("./models/qwen-7b/model.gguf")
        
        return config
    
    @pytest.fixture
    def llm_interface(self, mock_config):
        """Create an LLMInterface instance with mocked config"""
        with patch('pseudocode_translator.llm_interface.Llama'):
            interface = LLMInterface(mock_config)
            return interface
    
    def test_initialization(self, llm_interface, mock_config):
        """Test LLM interface initialization"""
        assert llm_interface.config == mock_config
        assert llm_interface.model is None
        assert llm_interface._initialized is False
        assert isinstance(llm_interface.cache, TranslationCache)
    
    @patch('pseudocode_translator.llm_interface.Llama')
    def test_initialize_model_success(self, mock_llama, llm_interface):
        """Test successful model initialization"""
        # Mock the model file exists
        llm_interface.config.get_model_path.return_value.exists.return_value = True
        
        # Initialize model
        llm_interface.initialize_model()
        
        assert llm_interface._initialized is True
        assert llm_interface.model is not None
        mock_llama.assert_called_once()
    
    def test_initialize_model_file_not_found(self, llm_interface):
        """Test model initialization when file doesn't exist"""
        # Mock the model file doesn't exist
        llm_interface.config.get_model_path.return_value.exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            llm_interface.initialize_model()
    
    @patch('pseudocode_translator.llm_interface.Llama')
    def test_initialize_model_load_failure(self, mock_llama, llm_interface):
        """Test model initialization failure"""
        llm_interface.config.get_model_path.return_value.exists.return_value = True
        mock_llama.side_effect = Exception("Failed to load model")
        
        with pytest.raises(RuntimeError, match="Failed to load model"):
            llm_interface.initialize_model()
    
    @patch('pseudocode_translator.llm_interface.Llama')
    def test_translate_simple(self, mock_llama, llm_interface):
        """Test simple translation"""
        # Setup
        llm_interface.config.get_model_path.return_value.exists.return_value = True
        mock_model = Mock()
        mock_llama.return_value = mock_model
        
        # Mock model response
        mock_model.return_value = {
            'choices': [{
                'text': '```python\ndef hello():\n    print("Hello, World!")\n```'
            }]
        }
        
        # Initialize and translate
        llm_interface.initialize_model()
        result = llm_interface.translate("Create a hello world function")
        
        assert result == 'def hello():\n    print("Hello, World!")'
        mock_model.assert_called_once()
    
    def test_translate_with_cache_hit(self, llm_interface):
        """Test translation with cache hit"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        
        # Pre-populate cache
        instruction = "Create a function"
        cached_code = "def my_function(): pass"
        cache_key = llm_interface._create_cache_key(instruction, None)
        llm_interface.cache.put(cache_key, cached_code)
        
        # Translate - should hit cache
        result = llm_interface.translate(instruction)
        
        assert result == cached_code
        # Model should not be called due to cache hit
        llm_interface.model.assert_not_called()
    
    def test_translate_with_context(self, llm_interface):
        """Test translation with context"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{
                'text': 'def add(): return x + y'
            }]
        }
        
        context = {'code': 'x = 10\ny = 20'}
        result = llm_interface.translate("Create add function", context)
        
        assert "def add()" in result
        # Check that context was used in prompt
        call_args = llm_interface.model.call_args[0][0]
        assert "x = 10" in call_args
        assert "y = 20" in call_args
    
    def test_translate_not_initialized(self, llm_interface):
        """Test translation triggers initialization if needed"""
        # Setup
        llm_interface.config.get_model_path.return_value.exists.return_value = True
        
        with patch('pseudocode_translator.llm_interface.Llama') as mock_llama:
            mock_model = Mock()
            mock_llama.return_value = mock_model
            mock_model.return_value = {
                'choices': [{'text': 'def test(): pass'}]
            }
            
            # Should initialize and then translate
            result = llm_interface.translate("Create test function")
            
            assert llm_interface._initialized is True
            assert "def test()" in result
    
    def test_batch_translate(self, llm_interface):
        """Test batch translation"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        
        responses = [
            {'choices': [{'text': 'def func1(): pass'}]},
            {'choices': [{'text': 'def func2(): pass'}]},
            {'choices': [{'text': 'invalid syntax'}]}  # One failure
        ]
        llm_interface.model.side_effect = responses
        
        instructions = [
            "Create func1",
            "Create func2",
            "Create func3"
        ]
        
        results = llm_interface.batch_translate(instructions)
        
        assert len(results) == 3
        assert "def func1()" in results[0]
        assert "def func2()" in results[1]
        assert "# Error:" in results[2] or results[2] == "invalid syntax"
    
    def test_refine_code(self, llm_interface):
        """Test code refinement"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{
                'text': '```python\ndef add(a, b):\n    return a + b\n```'
            }]
        }
        
        broken_code = "def add(a, b)\n    return a + b"
        error = "SyntaxError: missing colon"
        
        result = llm_interface.refine_code(broken_code, error)
        
        assert "def add(a, b):" in result
        assert "return a + b" in result
    
    def test_refine_code_failure(self, llm_interface):
        """Test code refinement failure returns original"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.side_effect = Exception("Model error")
        
        original_code = "def test(): pass"
        result = llm_interface.refine_code(original_code, "Some error")
        
        # Should return original code on failure
        assert result == original_code
    
    def test_shutdown(self, llm_interface):
        """Test interface shutdown"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.cache.put("key", "value")
        
        # Shutdown
        llm_interface.shutdown()
        
        assert llm_interface.model is None
        assert llm_interface._initialized is False
        assert len(llm_interface.cache._cache) == 0
    
    def test_get_model_info_not_initialized(self, llm_interface):
        """Test getting model info when not initialized"""
        llm_interface.config.get_model_path.return_value.exists.return_value = True
        
        info = llm_interface.get_model_info()
        
        assert info["status"] == "not_initialized"
        assert info["exists"] is True
    
    def test_get_model_info_initialized(self, llm_interface):
        """Test getting model info when initialized"""
        llm_interface._initialized = True
        llm_interface.cache._cache = {"k1": ("v1", 0), "k2": ("v2", 0)}
        
        info = llm_interface.get_model_info()
        
        assert info["status"] == "initialized"
        assert info["model_type"] == "qwen-7b"
        assert info["cache_size"] == 2
    
    def test_create_cache_key(self, llm_interface):
        """Test cache key creation"""
        instruction = "Create a function"
        context = {"code": "x = 1"}
        
        key1 = llm_interface._create_cache_key(instruction, context)
        key2 = llm_interface._create_cache_key(instruction, context)
        key3 = llm_interface._create_cache_key(instruction, None)
        
        # Same inputs should produce same key
        assert key1 == key2
        # Different inputs should produce different keys
        assert key1 != key3
        # Should be a valid hash
        assert len(key1) == 64  # SHA256 hex length
    
    def test_validate_and_clean_code(self, llm_interface):
        """Test code validation and cleaning"""
        # Valid code
        code = "def test():\n    return 42"
        result = llm_interface._validate_and_clean_code(code)
        assert result == code.strip()
        
        # Code with markdown
        code_with_markdown = "```python\ndef test():\n    return 42\n```"
        result = llm_interface._validate_and_clean_code(code_with_markdown)
        assert "```" not in result
        assert "def test():" in result
        
        # Invalid syntax - should attempt fix
        invalid_code = "def test():\n"
        result = llm_interface._validate_and_clean_code(invalid_code)
        assert "pass" in result  # Should add pass
        
        # Empty code
        result = llm_interface._validate_and_clean_code("")
        assert result == ""
    
    def test_attempt_syntax_fix(self, llm_interface):
        """Test syntax fix attempts"""
        # Incomplete function
        code = "def incomplete():\n    \n"
        result = llm_interface._attempt_syntax_fix(code)
        assert "pass" in result or "TODO" in result
        
        # Already valid code
        valid_code = "def complete():\n    return 1"
        result = llm_interface._attempt_syntax_fix(valid_code)
        assert result == valid_code
    
    def test_warmup(self, llm_interface):
        """Test model warmup"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{'text': 'print("hello world")'}]
        }
        
        # Warmup should not raise exceptions
        llm_interface.warmup()
        
        # Should have called model
        llm_interface.model.assert_called()
    
    def test_warmup_failure(self, llm_interface):
        """Test warmup failure handling"""
        # Setup
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.side_effect = Exception("Warmup failed")
        
        # Should not raise exception
        llm_interface.warmup()


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    @patch('pseudocode_translator.llm_interface.ConfigManager')
    @patch('pseudocode_translator.llm_interface.Llama')
    def test_create_llm_interface(self, mock_llama, mock_config_manager):
        """Test create_llm_interface factory function"""
        # Setup mocks
        mock_config = Mock()
        mock_config.llm = Mock()
        mock_config.llm.get_model_path.return_value.exists.return_value = True
        mock_config_manager.load.return_value = mock_config
        
        # Create interface
        interface = create_llm_interface()
        
        assert isinstance(interface, LLMInterface)
        assert interface._initialized is True
        mock_config_manager.load.assert_called_once()
    
    @patch('pseudocode_translator.llm_interface.ConfigManager')
    def test_create_llm_interface_with_config_path(self, mock_config_manager):
        """Test create_llm_interface with custom config path"""
        config_path = "/custom/config.yaml"
        
        with patch('pseudocode_translator.llm_interface.Llama'):
            create_llm_interface(config_path)
        
        mock_config_manager.load.assert_called_once_with(config_path)


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def llm_interface(self):
        config = Mock()
        config.validate.return_value = []
        config.cache_enabled = True
        config.cache_ttl_hours = 24
        config.n_threads = 4
        with patch('pseudocode_translator.llm_interface.Llama'):
            return LLMInterface(config)
    
    def test_translate_empty_instruction(self, llm_interface):
        """Test translating empty instruction"""
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{'text': ''}]
        }
        
        result = llm_interface.translate("")
        assert result == ""
    
    def test_translate_very_long_instruction(self, llm_interface):
        """Test translating very long instruction"""
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{'text': 'def long_function(): pass'}]
        }
        
        long_instruction = "Create a function that " + " and ".join(
            [f"does task {i}" for i in range(1000)]
        )
        
        result = llm_interface.translate(long_instruction)
        assert "def" in result
    
    def test_model_response_without_choices(self, llm_interface):
        """Test handling model response without choices"""
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {}  # No choices
        
        with pytest.raises(RuntimeError):
            llm_interface.translate("Create function")
    
    def test_concurrent_translations(self, llm_interface):
        """Test thread safety of translations"""
        import threading
        
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{'text': 'def concurrent(): pass'}]
        }
        
        results = []
        
        def translate():
            result = llm_interface.translate("Create function")
            results.append(result)
        
        threads = [threading.Thread(target=translate) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 5
        assert all("def concurrent()" in r for r in results)
    
    def test_unicode_handling(self, llm_interface):
        """Test handling of Unicode in instructions and responses"""
        llm_interface._initialized = True
        llm_interface.model = Mock()
        llm_interface.model.return_value = {
            'choices': [{
                'text': 'def greet():\n    return "你好世界 🌍"'
            }]
        }
        
        result = llm_interface.translate("Create function that returns 你好")
        assert "你好世界" in result
        assert "🌍" in result
    
    def test_config_validation_warnings(self):
        """Test handling of configuration validation warnings"""
        config = Mock()
        config.validate.return_value = ["Warning 1", "Warning 2"]
        config.cache_enabled = True
        config.cache_ttl_hours = 24
        
        with patch('pseudocode_translator.llm_interface.Llama'):
            # Should not raise exception, just log warnings
            interface = LLMInterface(config)
            assert interface is not None


@pytest.mark.parametrize("instruction,expected_in_result", [
    ("print hello", "print"),
    ("Create a class", "class"),
    ("Define a function", "def"),
    ("Import numpy", "import"),
])
def test_translation_patterns(instruction, expected_in_result):
    """Parametrized test for common translation patterns"""
    config = Mock()
    config.validate.return_value = []
    config.cache_enabled = False
    
    with patch('pseudocode_translator.llm_interface.Llama') as mock_llama:
        interface = LLMInterface(config)
        interface._initialized = True
        interface.model = Mock()
        interface.model.return_value = {
            'choices': [{
                'text': f'{expected_in_result} something(): pass'
            }]
        }
        
        result = interface.translate(instruction)
        assert expected_in_result in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])