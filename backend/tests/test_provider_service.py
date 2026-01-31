import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.provider_service import (
    chat_with_provider, stream_chat_with_provider, get_available_models_by_provider,
    get_provider_status, validate_provider_api_key, encrypt_api_key, decrypt_api_key
)
from core.providers import PROVIDER_CONFIGS

class TestProviderService:
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.test_messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]
        self.test_model = "openai/gpt-3.5-turbo"
        self.test_provider = "openai"
        self.test_api_key = "test-api-key-12345"

    @pytest.mark.asyncio
    async def test_chat_with_provider_success(self):
        """Test successful chat completion with provider."""
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Hello! I'm doing well, thank you."
            mock_completion.return_value = mock_response
            
            with patch('services.provider_service.get_provider_api_key', return_value=self.test_api_key):
                result = await chat_with_provider(self.test_messages, self.test_model)
                
                assert result == "Hello! I'm doing well, thank you."
                mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_provider_invalid_messages(self):
        """Test chat with invalid messages."""
        invalid_messages = [{"invalid": "message"}]
        
        result = await chat_with_provider(invalid_messages, self.test_model)
        assert result is None

    @pytest.mark.asyncio
    async def test_chat_with_provider_unknown_provider(self):
        """Test chat with unknown provider."""
        unknown_model = "unknown/model"
        
        result = await chat_with_provider(self.test_messages, unknown_model)
        assert result is None

    @pytest.mark.asyncio
    async def test_stream_chat_with_provider_success(self):
        """Test successful streaming chat completion."""
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            # Mock streaming response
            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock()]
            mock_chunk1.choices[0].delta.content = "Hello"
            
            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock()]
            mock_chunk2.choices[0].delta.content = " there!"
            
            async def mock_stream():
                yield mock_chunk1
                yield mock_chunk2
            
            mock_completion.return_value = mock_stream()
            
            with patch('services.provider_service.get_provider_api_key', return_value=self.test_api_key):
                chunks = []
                async for chunk in stream_chat_with_provider(self.test_messages, self.test_model):
                    chunks.append(chunk)
                
                assert len(chunks) == 2
                assert "Hello" in chunks[0]
                assert " there!" in chunks[1]

    @pytest.mark.asyncio
    async def test_get_available_models_by_provider(self):
        """Test getting available models by provider."""
        with patch('services.provider_service._get_ollama_models', return_value=['llama3.1', 'mistral']):
            models = await get_available_models_by_provider()
            
            assert 'ollama' in models
            assert 'openai' in models
            assert 'anthropic' in models
            assert models['ollama'] == ['llama3.1', 'mistral']
            assert 'gpt-3.5-turbo' in models['openai']

    @pytest.mark.asyncio
    async def test_get_provider_status_ollama(self):
        """Test getting Ollama provider status."""
        with patch('services.provider_service._get_ollama_models', return_value=['llama3.1']):
            status = await get_provider_status('ollama')
            
            assert status['provider_id'] == 'ollama'
            assert status['name'] == 'Ollama'
            assert status['configured'] is True
            assert status['available'] is True
            assert status['model_count'] == 1

    @pytest.mark.asyncio
    async def test_get_provider_status_cloud_provider(self):
        """Test getting cloud provider status."""
        with patch('services.provider_service.get_provider_api_key', return_value=self.test_api_key):
            status = await get_provider_status('openai')
            
            assert status['provider_id'] == 'openai'
            assert status['name'] == 'OpenAI'
            assert status['configured'] is True
            assert status['available'] is True

    @pytest.mark.asyncio
    async def test_get_provider_status_unconfigured(self):
        """Test getting status for unconfigured provider."""
        with patch('services.provider_service.get_provider_api_key', return_value=None):
            with patch('os.getenv', return_value=None):
                status = await get_provider_status('openai')
                
                assert status['provider_id'] == 'openai'
                assert status['configured'] is False
                assert status['available'] is False

    @pytest.mark.asyncio
    async def test_validate_provider_api_key_success(self):
        """Test successful API key validation."""
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_completion.return_value = mock_response
            
            result = await validate_provider_api_key('openai', self.test_api_key)
            
            assert result['valid'] is True
            assert 'successfully' in result['message']

    @pytest.mark.asyncio
    async def test_validate_provider_api_key_invalid(self):
        """Test API key validation with invalid key."""
        from openai import AuthenticationError
        
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            # Create a proper AuthenticationError with required parameters
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_completion.side_effect = AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}}
            )
            
            result = await validate_provider_api_key('openai', 'invalid-key')
            
            assert result['valid'] is False
            assert 'Invalid API key' in result['error']

    @pytest.mark.asyncio
    async def test_validate_provider_api_key_ollama(self):
        """Test API key validation for Ollama (should always pass)."""
        result = await validate_provider_api_key('ollama', '')
        
        assert result['valid'] is True
        assert "doesn't require" in result['message']

    def test_encryption_decryption(self):
        """Test API key encryption and decryption."""
        original_key = "test-api-key-12345"
        
        # Test encryption
        encrypted = encrypt_api_key(original_key)
        assert encrypted != original_key
        assert len(encrypted) > 0
        
        # Test decryption
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original_key

    def test_encryption_empty_key(self):
        """Test encryption/decryption with empty key."""
        assert encrypt_api_key("") == ""
        assert decrypt_api_key("") == ""

    def test_provider_configs_loaded(self):
        """Test that provider configurations are properly loaded."""
        assert len(PROVIDER_CONFIGS) == 7
        assert 'ollama' in PROVIDER_CONFIGS
        assert 'openai' in PROVIDER_CONFIGS
        assert 'anthropic' in PROVIDER_CONFIGS
        assert 'google' in PROVIDER_CONFIGS
        assert 'openrouter' in PROVIDER_CONFIGS
        assert 'groq' in PROVIDER_CONFIGS
        assert 'sambanova' in PROVIDER_CONFIGS

    def test_provider_config_structure(self):
        """Test that provider configurations have required fields."""
        for provider_id, config in PROVIDER_CONFIGS.items():
            assert 'name' in config
            assert 'model_prefix' in config
            assert 'default_models' in config
            assert 'supports_streaming' in config
            assert 'requires_max_tokens' in config
            
            if provider_id != 'ollama':
                assert 'api_key_env' in config
                assert config['api_key_env'] is not None

    @pytest.mark.asyncio
    async def test_anthropic_max_tokens_parameter(self):
        """Test that Anthropic requests include max_tokens parameter."""
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_completion.return_value = mock_response
            
            with patch('services.provider_service.get_provider_api_key', return_value=self.test_api_key):
                await chat_with_provider(self.test_messages, "anthropic/claude-3-haiku-20240307")
                
                # Check that max_tokens was included in the call
                call_args = mock_completion.call_args
                assert 'max_tokens' in call_args.kwargs
                assert call_args.kwargs['max_tokens'] == 4096

    @pytest.mark.asyncio
    async def test_error_handling_network_error(self):
        """Test error handling for network errors."""
        with patch('services.provider_service.litellm.acompletion') as mock_completion:
            mock_completion.side_effect = Exception("Network error")
            
            with patch('services.provider_service.get_provider_api_key', return_value=self.test_api_key):
                result = await chat_with_provider(self.test_messages, self.test_model)
                
                assert result is None

    @pytest.mark.asyncio
    async def test_backward_compatibility_functions(self):
        """Test backward compatibility functions work correctly."""
        from services.provider_service import chat_with_ollama, stream_chat_with_ollama
        
        with patch('services.provider_service.chat_with_provider') as mock_chat:
            mock_chat.return_value = "Test response"
            
            result = await chat_with_ollama(self.test_messages, "llama3.1")
            
            assert result == "Test response"
            mock_chat.assert_called_once_with(self.test_messages, "ollama/llama3.1", 1.15)

    @pytest.mark.asyncio
    async def test_model_prefix_handling(self):
        """Test that model prefixes are handled correctly."""
        test_cases = [
            ("llama3.1", "ollama", "ollama/llama3.1"),
            ("gpt-3.5-turbo", "openai", "openai/gpt-3.5-turbo"),
            ("openai/gpt-4", "openai", "openai/gpt-4"),  # Already has prefix
        ]
        
        for model, provider, expected in test_cases:
            from core.providers import get_model_with_prefix
            result = get_model_with_prefix(provider, model)
            assert result == expected
