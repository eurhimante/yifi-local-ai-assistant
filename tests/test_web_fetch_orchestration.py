"""Mock tool-calling integration for web_fetch; no internet, Docker, or Ollama."""
import asyncio
import copy
import json
import unittest
from unittest.mock import AsyncMock, patch
from app import orchestrator

class Reply:
    def __init__(self, message):
        self.message = message
    def raise_for_status(self): pass
    def json(self):
        return {"id":"fake", "choices":[{"message":copy.deepcopy(self.message)}]}

class Client:
    def __init__(self, messages):
        self.replies=[Reply(m) for m in messages]
        self.requests=[]
    async def __aenter__(self): return self
    async def __aexit__(self,*args): return False
    async def post(self,url,json):
        self.requests.append(copy.deepcopy(json))
        return self.replies.pop(0)

class TestWebFetchOrchestration(unittest.TestCase):
    def run_case(self, tool_result):
        call={"id":"call1", "type":"function", "function":{"name":"web_fetch", "arguments":json.dumps({"url":"https://docs.python.org/3/library/asyncio.html"})}}
        replies=[{"role":"assistant","content":"", "tool_calls":[call]}, {"role":"assistant", "content":"Voici les informations de la page."}]
        client=Client(replies)
        with patch.object(orchestrator.httpx,"AsyncClient",return_value=client), patch.object(orchestrator,"web_fetch",new_callable=AsyncMock,return_value=tool_result) as fetch:
            answer=asyncio.run(orchestrator.complete({"messages":[{"role":"user","content":"Lis docs.python.org"}],"stream":False}))
        return answer, client.requests, fetch

    def test_fetch_advertised(self):
        answer,req,fetch=self.run_case({"url":"https://docs.python.org/3/library/asyncio.html","content":"asyncio"})
        names={t["function"]["name"] for t in req[0]["tools"]}
        self.assertEqual(names,{"web_search","web_fetch","github_latest_release"})

    def test_success_provenance_is_server_generated(self):
        answer,req,fetch=self.run_case({"url":"https://docs.python.org/3/library/asyncio.html","content":"asyncio","verification":"Page fetched"})
        fetch.assert_awaited_once()
        self.assertEqual(req[1]["messages"][-1]["name"],"web_fetch")
        content=answer["choices"][0]["message"]["content"]
        self.assertIn("web_fetch: page text retrieved",content)
        self.assertIn("not independently verified",content)

    def test_fetch_error_does_not_claim_page_read(self):
        answer,req,fetch=self.run_case({"error":"Redirect refused"})
        content=answer["choices"][0]["message"]["content"]
        self.assertIn("web_fetch: attempted; page not retrieved",content)
        self.assertNotIn("web_fetch: page text retrieved",content)

if __name__=="__main__": unittest.main()
