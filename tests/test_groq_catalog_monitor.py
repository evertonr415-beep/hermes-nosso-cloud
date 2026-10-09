"""Regression tests for Groq catalogue monitor (no external calls)."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("catalog_monitor",Path(__file__).resolve().parents[1]/"hermes-groq-catalog-monitor.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Response:
    def __init__(self,data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size): return self.data[:size]

class MonitorTests(unittest.TestCase):
    def setUp(self): mod._cache.update(until=0.0,result=None)

    def test_filters_safety_models(self):
        data={"data":[{"id":"qwen/new-model","active":True},
                      {"id":"llama-3.3-70b-versatile","active":True},
                      {"id":"meta-llama/llama-guard","active":True},
                      {"id":"qwen/disabled","active":False}]}
        self.assertEqual(mod.candidate_ids(data),["llama-3.3-70b-versatile","qwen/new-model"])

    def test_authenticated_cached_bounded_read(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            self.assertEqual(timeout,5)
            return Response(json.dumps({"data":[{"id":"qwen/future","active":True}]}).encode())
        with patch.dict("os.environ",{"GROQ_API_KEY":"gsk_"+"x"*30}):
            first=mod.check_catalog(opener=opener,now=100.0)
            second=mod.check_catalog(opener=opener,now=101.0)
        self.assertEqual(first,second)
        self.assertEqual(first["free_status"],"unverified")
        self.assertEqual(len(calls),1)

    def test_no_credentials_no_network(self):
        with patch.dict("os.environ",{"GROQ_API_KEY":""}):
            self.assertEqual(mod.check_catalog(now=100.0)["error"],"groq_not_configured")

if __name__=="__main__": unittest.main()
