import json
from unittest.mock import patch, MagicMock

import pytest

from app import app, score_recipe_match, RECIPE_CACHE


@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()


def test_find_recipes_requires_ingredients(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    resp = client.post('/api/find-recipes', json={'ingredients': []})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_find_recipes_rejects_too_many_ingredients(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    resp = client.post('/api/find-recipes', json={'ingredients': ['x'] * 30})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_find_recipes_requires_api_key(client, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    resp = client.post('/api/find-recipes', json={'ingredients': ['chicken']})
    assert resp.status_code == 400
    assert 'GEMINI_API_KEY' in resp.get_json()['error']


def test_find_recipes_scores_and_sorts(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')

    fake_response = MagicMock()
    fake_response.text = json.dumps({
        'recipes': [
            {
                'name': 'Low Match',
                'url': 'https://example.com/low',
                'calories': 400,
                'ingredients': [
                    {'name': 'chicken', 'owned': True},
                    {'name': 'truffle oil', 'owned': False},
                    {'name': 'saffron', 'owned': False},
                ],
                'instructions': ['Step 1'],
                'match_score': 99,
                'match_reason': 'model guess',
            },
            {
                'name': 'High Match',
                'url': 'https://example.com/high',
                'calories': 300,
                'ingredients': [
                    {'name': 'chicken', 'owned': True},
                    {'name': 'garlic', 'owned': True},
                ],
                'instructions': ['Step 1'],
                'match_score': 10,
                'match_reason': 'model guess',
            },
        ]
    })

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch('app.genai.Client', return_value=fake_client):
        resp = client.post('/api/find-recipes', json={'ingredients': ['chicken', 'garlic']})

    assert resp.status_code == 200
    data = resp.get_json()
    recipes = data['recipes']
    # The deterministic evaluation layer should override the model's score
    # and sort the better-matching recipe first, regardless of what the model guessed.
    assert recipes[0]['name'] == 'High Match'
    assert recipes[0]['match_score'] == 100
    assert recipes[1]['match_score'] == 33


def test_find_recipes_uses_cache_on_repeat_request(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    RECIPE_CACHE.clear()

    fake_response = MagicMock()
    fake_response.text = json.dumps({
        'recipes': [{
            'name': 'Cached Recipe',
            'url': 'https://example.com/cached',
            'calories': 200,
            'ingredients': [{'name': 'chicken', 'owned': True}],
            'instructions': ['Step 1'],
            'match_score': 50,
            'match_reason': 'model guess',
        }]
    })
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch('app.genai.Client', return_value=fake_client):
        first = client.post('/api/find-recipes', json={'ingredients': ['chicken']})
        second = client.post('/api/find-recipes', json={'ingredients': ['Chicken']})

    assert first.status_code == 200
    assert second.status_code == 200
    # Second request (different casing, same ingredient set) should hit the cache,
    # so the Gemini client should only have been called once.
    assert fake_client.models.generate_content.call_count == 1
    RECIPE_CACHE.clear()


def test_score_recipe_match_no_ingredients():
    assert score_recipe_match({'ingredients': []}) == 0


def test_score_recipe_match_partial():
    recipe = {'ingredients': [{'owned': True}, {'owned': False}]}
    assert score_recipe_match(recipe) == 50
