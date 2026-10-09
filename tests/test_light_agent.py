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

    def test_plain_message(self):
        with patch.dict(agent.os.environ,ENV,clear=True),patch.object(agent,"completion",return_value={"content":"OK"}):
            self.assertEqual(agent.answer("OK")["response"],"OK")

    def test_no_key_does_not_connect(self):
        with patch.dict(agent.os.environ,{},clear=True),patch.object(agent,"completion") as send:
            self.assertFalse(agent.answer("ok")["ok"])
            send.assert_not_called()

if __name__=="__main__":
    unittest.main()
