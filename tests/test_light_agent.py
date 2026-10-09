"""Offline regression checks for Hermes advanced mode; no real API access."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

source=Path(__file__).resolve().parents[1]/"hermes-light-agent.py"
spec=importlib.util.spec_from_file_location("hermes_agent_test",source)
agent=importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)
ENV={"GROQ_API_KEY":"gsk_"+"a"*40,"HERMES_GROQ_MODEL":"qwen/qwen3.8-27b"}

class AdvancedTests(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(agent.run_tool("calculate",'{"expression":"(12+8)*3"}')["result"],60)
        self.assertIn("error",agent.run_tool("calculate",'{"expression":"__import__(1)"}'))
        self.assertIn("error",agent.run_tool("calculate",'{"expression":"2**9999999"}'))

    def test_clock(self):
        self.assertIn("local_time",agent.run_tool("current_time",'{"timezone":"America/Sao_Paulo"}'))
        self.assertIn("error",agent.run_tool("current_time",'{"timezone":"Europe/London"}'))

    def test_wikipedia_search_only_uses_fixed_public_host(self):
        from unittest.mock import MagicMock
        payload=json.dumps({"query":{"search":[
            {"title":"Arapongas","snippet":"<span>Município</span> do Paraná"}
        ]}}).encode()
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=payload
        with patch.object(agent.urllib.request,"urlopen",return_value=fake) as request:
            result=agent.run_tool("wikipedia_search",'{"query":"Arapongas","language":"pt"}')
        self.assertEqual(result["results"][0]["title"],"Arapongas")
        self.assertIn("Município",result["results"][0]["snippet"])
        self.assertNotIn("<span>",result["results"][0]["snippet"])
        url=request.call_args.args[0].full_url
        self.assertTrue(url.startswith("https://pt.wikipedia.org/w/api.php?"))
        self.assertIn("srlimit=3",url)

    def test_wikipedia_rejects_arbitrary_language_and_tokens(self):
        with patch.object(agent.urllib.request,"urlopen") as request:
            self.assertIn("error",agent.run_tool("wikipedia_search",'{"query":"Arapongas","language":"fr"}'))
            secret="gsk_"+"x"*30
            args=json.dumps({"query":secret,"language":"pt"})
            self.assertIn("error",agent.run_tool("wikipedia_search",args))
            request.assert_not_called()

    def test_clock_real_tool_returns_aware_iso_time(self):
        from datetime import datetime
        response=agent.run_tool("current_time",'{"timezone":"America/Sao_Paulo"}')
        timestamp=datetime.fromisoformat(response["local_time"])
        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(),-3*3600)

    def test_shell_and_arbitrary_urls_blocked(self):
        self.assertEqual(agent.run_tool("run_shell",'{"cmd":"id"}'),{"error":"tool_not_allowed"})
        self.assertEqual(agent.run_tool("open_url",'{"url":"http://169.254.169.254"}'),{"error":"tool_not_allowed"})

    def test_tool_loop(self):
        c={"id":"call1","type":"function","function":{"name":"calculate","arguments":'{"expression":"2+3"}'}}
        msgs=[{"content":None,"tool_calls":[c]},{"content":"O resultado é 5."}]
        with patch.dict(agent.os.environ,ENV,clear=True),patch.object(agent,"completion",side_effect=msgs) as send:
            res=agent.answer("Quanto é 2+3?")
        self.assertTrue(res["ok"])
        self.assertEqual(res["tools_used"],1)
        self.assertEqual(res["response"],"O resultado é 5.")
        self.assertIn('"result": 5',send.call_args_list[1].args[0][-1]["content"])

    def test_explicit_sao_paulo_and_wikipedia_requests_call_tools_without_model(self):
        prompt="consulte o horário de São Paulo e pesquisar Arapongas na Wikipédia."
        invoked=[]
        def fake(name, arguments):
            params=json.loads(arguments)
            invoked.append((name,params))
            if name=="current_time":
                return {"local_time":"2026-10-09T13:50:00-03:00"}
            if name=="wikipedia_search":
                return {"results":[{"title":"Arapongas","snippet":"Município do Paraná",
                                    "url":"https://pt.wikipedia.org/wiki/Arapongas"}]}
            self.fail("unexpected tool "+str(name))
        with patch.dict(agent.os.environ,ENV,clear=True), \
             patch.object(agent,"run_tool",side_effect=fake), \
             patch.object(agent,"completion") as model:
            result=agent.answer(prompt)
        self.assertTrue(result["ok"])
        self.assertEqual(result["tools_used"],2)
        self.assertEqual([x[0] for x in invoked],["current_time","wikipedia_search"])
        self.assertEqual(invoked[1][1]["query"],"Arapongas")
        self.assertIn("2026-10-09T13:50",result["response"])
        self.assertIn("https://pt.wikipedia.org/wiki/Arapongas",result["response"])
        model.assert_not_called()

    def test_wikipedia_failure_does_not_invent_city_facts(self):
        with patch.dict(agent.os.environ,ENV,clear=True), \
             patch.object(agent,"run_tool",return_value={"error":"network_unavailable"}), \
             patch.object(agent,"completion") as model:
            result=agent.answer("Pesquise Arapongas na Wikipédia")
        self.assertTrue(result["ok"])
        self.assertEqual(result["tools_used"],0)
        self.assertIn("Não foi possível",result["response"])
        self.assertNotIn("fundação",result["response"].lower())
        model.assert_not_called()

    def test_explicit_calculator_must_use_calculator_tool(self):
        prompt="Use a calculadora para calcular (125+375)×4."
        with patch.dict(agent.os.environ,ENV,clear=True), \
             patch.object(agent,"completion") as model:
            result=agent.answer(prompt)
        self.assertTrue(result["ok"])
        self.assertEqual(result["tools_used"],1)
        self.assertIn("2000",result["response"])
        model.assert_not_called()

    def test_general_advanced_question_remains_model_driven(self):
        with patch.dict(agent.os.environ,ENV,clear=True), \
             patch.object(agent,"completion",return_value={"content":"Uma explicação."}) as model:
            result=agent.answer("Explique o que é um banco de dados relacional")
        self.assertTrue(result["ok"])
        self.assertEqual(result["tools_used"],0)
        model.assert_called_once()

    def test_wikipedia_result_contains_generated_article_url(self):
        from unittest.mock import MagicMock
        body=json.dumps({"query":{"search":[{"title":"Arapongas","snippet":"Cidade do Paraná"}]}}).encode()
        response=MagicMock()
        response.__enter__.return_value.read.return_value=body
        with patch.object(agent.urllib.request,"urlopen",return_value=response):
            result=agent.run_tool("wikipedia_search",'{"query":"Arapongas","language":"pt"}')
        self.assertEqual(result["results"][0]["url"],"https://pt.wikipedia.org/wiki/Arapongas")

    def test_plain_message(self):
        with patch.dict(agent.os.environ,ENV,clear=True),patch.object(agent,"completion",return_value={"content":"OK"}):
            self.assertEqual(agent.answer("OK")["response"],"OK")

    def test_no_key_does_not_connect(self):
        with patch.dict(agent.os.environ,{},clear=True),patch.object(agent,"completion") as send:
            self.assertFalse(agent.answer("ok")["ok"])
            send.assert_not_called()

if __name__=="__main__":
    unittest.main()
