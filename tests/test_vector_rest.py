"""Offline regression tests for Groq Qwen guidance and vector REST helper."""
import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("hermes_router",pathlib.Path(__file__).resolve().parents[1]/"hermes-global-model-router.py")
router=importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

class Response:
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,n): return b'[]'

class VectorTests(unittest.TestCase):
    def test_valid_authenticated_request(self):
        calls=[]
        def opener(req,timeout):
            calls.append((req,timeout))
            return Response()
        rows=router.search_supabase_vectors([0.0]*384,rpc_name="match_private_vectors",
            base_url="https://example.supabase.co",api_key="sb_publishable_test",
            access_token="a"*48,limit=3,opener=opener)
        self.assertEqual(rows,[])
        req,timeout=calls[0]
        self.assertEqual(timeout,8)
        self.assertTrue(req.full_url.endswith("/rest/v1/rpc/match_private_vectors"))
        self.assertEqual(json.loads(req.data)["match_count"],3)

    def test_no_network_without_user_token(self):
        with self.assertRaises(ValueError):
            router.search_supabase_vectors([0.0]*384,rpc_name="match_private_vectors",
                base_url="https://example.supabase.co",api_key="key",access_token="")

    def test_invalid_vectors_rejected(self):
        with self.assertRaises(ValueError):
            router.search_supabase_vectors([0.1],rpc_name="match_private_vectors")

    def test_private_guidance(self):
        self.assertIn("internally",router.GROQ_QWEN_SYSTEM_PROMPT)
        self.assertIn("Do not reveal hidden chain-of-thought",router.GROQ_QWEN_SYSTEM_PROMPT)

if __name__=="__main__": unittest.main()
