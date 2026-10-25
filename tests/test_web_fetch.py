import asyncio
import socket
import unittest
from unittest.mock import patch

from app.tools import web_fetch as module


def fake_public(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))]


def fake_private(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', port))]


class _FakeContent:
    def __init__(self, chunks):
        self.chunks = chunks

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


class _FakeResponse:
    def __init__(self, status=200, headers=None, chunks=()):
        self.status = status
        self.headers = headers or {'content-type': 'text/html'}
        self.content = _FakeContent(chunks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def raise_for_status(self):
        if self.status >= 400:
            raise module.aiohttp.ClientResponseError(None, (), status=self.status)


class _FakeSession:
    reply = None
    seen_kwargs = None
    captured_connector = None

    def __init__(self, *args, **kwargs):
        type(self).captured_connector = kwargs.get('connector')
        type(self).seen_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def get(self, url, **kwargs):
        type(self).seen_kwargs = kwargs
        return type(self).reply


class WebFetchTests(unittest.TestCase):
    def test_blocks_localhost(self):
        self.assertIn('error', asyncio.run(module.web_fetch({'url': 'https://localhost/private'})))

    def test_blocks_http(self):
        self.assertIn('error', asyncio.run(module.web_fetch({'url': 'http://github.com/test'})))

    def test_blocks_unlisted_domain(self):
        self.assertIn('error', asyncio.run(module.web_fetch({'url': 'https://random.example.com/private'})))

    def test_blocks_private_dns_resolution(self):
        with patch.object(module.socket, 'getaddrinfo', side_effect=fake_private):
            result = asyncio.run(module.web_fetch({'url': 'https://github.com/ollama/ollama'}))
        self.assertIn('non-public', result['error'])

    def test_pinned_resolver_cannot_lookup_other_hosts(self):
        resolver = module._PinnedResolver('github.com', '93.184.216.34')
        async def run():
            answer = await resolver.resolve('github.com', 443)
            self.assertEqual(answer[0]['host'], '93.184.216.34')
            with self.assertRaises(OSError):
                await resolver.resolve('localhost', 443)
        asyncio.run(run())

    def test_fetches_html_and_strips_scripts(self):
        html = b'<html><h1>Release notes</h1><script>unsafe</script><p>Test content.</p></html>'
        _FakeSession.reply = _FakeResponse(chunks=[html])
        with patch.object(module.socket, 'getaddrinfo', side_effect=fake_public), patch.object(module.aiohttp, 'ClientSession', _FakeSession):
            result = asyncio.run(module.web_fetch({'url': 'https://github.com/ollama/ollama'}))
        self.assertIn('Release notes', result['content'])
        self.assertIn('Test content', result['content'])
        self.assertNotIn('unsafe', result['content'])
        self.assertFalse(_FakeSession.seen_kwargs['allow_redirects'])
        self.assertEqual(_FakeSession.captured_connector._resolver.ip, '93.184.216.34')

    def test_redirect_is_refused(self):
        _FakeSession.reply = _FakeResponse(status=302, headers={'location': 'https://localhost/secret'})
        with patch.object(module.socket, 'getaddrinfo', side_effect=fake_public), patch.object(module.aiohttp, 'ClientSession', _FakeSession):
            result = asyncio.run(module.web_fetch({'url': 'https://github.com/redirect'}))
        self.assertIn('Redirect refused', result['error'])

    def test_oversized_response_is_truncated(self):
        _FakeSession.reply = _FakeResponse(headers={'content-type': 'text/plain'}, chunks=[b'A' * (module.MAX_BYTES + 300)])
        with patch.object(module.socket, 'getaddrinfo', side_effect=fake_public), patch.object(module.aiohttp, 'ClientSession', _FakeSession):
            result = asyncio.run(module.web_fetch({'url': 'https://github.com/big'}))
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['content']), module.MAX_CHARS)


if __name__ == '__main__':
    unittest.main()
