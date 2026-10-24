"""Isolated regression tests for YIFI. No network, GPU or Docker needed."""
import asyncio
import copy
import json
import unittest
from unittest.mock import patch

from app import orchestrator


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return copy.deepcopy(self.payload)


class FakeClient:
    def __init__(self, responses, requests):
        self.responses = list(responses)
        self.requests = requests
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def post(self, url, json):
        self.requests.append({'url': url, 'body': copy.deepcopy(json)})
        if not self.responses:
            raise AssertionError('Unexpected extra model request')
        return FakeResponse(self.responses.pop(0))


def model_reply(content, tool_calls=None):
    message = {'role': 'assistant', 'content': content}
    if tool_calls is not None:
        message['tool_calls'] = tool_calls
    return {'id': 'mock-response', 'object': 'chat.completion', 'choices': [{'index': 0, 'message': message, 'finish_reason': 'stop'}], 'model': 'yifi:4b'}


class OrchestratorTests(unittest.TestCase):
    def run_mock(self, responses, question):
        requests = []
        client = FakeClient(responses, requests)
        with patch.object(orchestrator.httpx, 'AsyncClient', return_value=client):
            answer = asyncio.run(orchestrator.complete({
                'model': 'yifi-auto',
                'messages': [{'role': 'user', 'content': question}],
                'stream': False,
            }))
        return answer, requests

    def test_plain_conversation_has_no_automatic_search_sources(self):
        answer, requests = self.run_mock([model_reply('Bonjour !')], 'Bonjour YIFI')
        content = answer['choices'][0]['message']['content']
        self.assertIn('Bonjour', content)
        self.assertNotIn('Tools actually executed', content)
        self.assertNotIn('Search sources', content)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['body']['model'], 'yifi:4b')

    def test_web_tool_is_advertised_to_the_model(self):
        _, requests = self.run_mock([model_reply('Je peux aider.')], 'Recherche une information')
        tools = requests[0]['body'].get('tools', [])
        names = {tool.get('function', {}).get('name') for tool in tools}
        self.assertIn('web_search', names)
        self.assertIn('github_latest_release', names)

    def test_unverified_api_claim_must_be_blocked(self):
        """Model assertions of API access must not pass through as verified."""
        fabricated = ('Version 3.12.9. Verification reussie via GitHub API. '
                      'https://github.com/python/cpython/releases/tag/3.12.9')
        answer, requests = self.run_mock([model_reply(fabricated)], 'Derniere version CPython ?')
        content = answer['choices'][0]['message']['content']
        self.assertEqual(len(requests), 1)
        self.assertNotIn('Verification reussie via GitHub API', content,
                         'The server must remove or label unverifiable model claims')


    def test_plain_unknown_version_without_provenance_is_not_auto_verified(self):
        answer, requests = self.run_mock([model_reply("Je ne connais pas la version actuelle.")], "Derniere version ?")
        self.assertEqual(answer['choices'][0]['message']['content'], "Je ne connais pas la version actuelle.")
        self.assertEqual(len(requests), 1)

    def test_english_false_provenance_is_blocked(self):
        content = 'I checked the GitHub API and confirmed version 9.9.9'
        answer, _ = self.run_mock([model_reply(content)], 'Current version?')
        self.assertNotIn('I checked the GitHub API', answer['choices'][0]['message']['content'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
