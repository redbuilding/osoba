import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.summaries import router as summaries_router


def make_app():
    app = FastAPI()
    app.include_router(summaries_router)
    return app


def test_get_and_set_summary_settings():
    app = make_app()
    client = TestClient(app)

    with patch('api.summaries.get_user_settings', return_value={"chat_summaries": {"model_name": "openai/gpt-4o-mini"}}):
        r = client.get('/api/summaries/settings')
        assert r.status_code == 200
        assert r.json()['model_name'] == 'openai/gpt-4o-mini'

    saved = {}
    def fake_get_settings(user_id='default'):
        return saved.get(user_id, {})

    def fake_save_settings(user_id='default', settings=None):
        saved[user_id] = settings or {}
        return True

    app = make_app()
    client = TestClient(app)
    with patch('api.summaries.get_user_settings', side_effect=fake_get_settings), \
         patch('api.summaries.save_user_settings', side_effect=fake_save_settings):
        r = client.post('/api/summaries/settings', json={"model_name": "ollama/qwen2.5:7b-instruct"})
        assert r.status_code == 200
        assert r.json()['success'] is True
        assert saved['default']['chat_summaries']['model_name'] == 'ollama/qwen2.5:7b-instruct'


def test_generate_summary_success_and_trim():
    app = make_app()
    client = TestClient(app)

    # Build fake messages; two simple messages
    fake_messages = [
        MagicMock(role='user', content='Tell me how to deploy this app.'),
        MagicMock(role='assistant', content='Use Docker + CI/CD pipeline, and set up environment variables.'),
    ]

    long_text = 'A' * 1000  # ensure we test 750-char trimming

    with patch('api.summaries.crud.get_messages_by_conv_id', return_value=fake_messages), \
         patch('api.summaries.get_user_settings', return_value={"chat_summaries": {"model_name": "openai/gpt-4o-mini"}}), \
         patch('api.summaries.chat_with_provider', return_value=long_text), \
         patch('api.summaries.crud.update_conversation_summary', return_value=True) as mock_update:
        r = client.post('/api/summaries/generate', json={"conversation_id": "abc123"})
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert len(data['summary']) <= 750
        # update called with trimmed text
        called_summary = mock_update.call_args[0][1]
        assert len(called_summary) <= 750


def test_generate_summary_404_when_missing_conv():
    app = make_app()
    client = TestClient(app)

    with patch('db.crud.get_messages_by_conv_id', return_value=None):
        r = client.post('/api/summaries/generate', json={"conversation_id": "missing"})
        assert r.status_code == 404
