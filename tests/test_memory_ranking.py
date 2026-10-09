"""Offline tests of memory ranking and context compression."""
import importlib.util
import pathlib
import unittest
spec=importlib.util.spec_from_file_location("router",pathlib.Path(__file__).resolve().parents[1]/"hermes-global-model-router.py")
router=importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)
class RetrievalTests(unittest.TestCase):
    def test_rank_deduplicate_and_bound(self):
        rows=["A câmera de segurança em Arapongas foi instalada.\nA câmera de segurança em Arapongas foi instalada.",
              "O sistema de câmeras em Arapongas está ativo.\nOutra informação sem relevância."]
        actual=router.compact_retrieved_memory("câmera segurança Arapongas",rows)
        self.assertEqual(len(actual),2)
        self.assertLessEqual(sum(map(len,actual)),1800)
    def test_sensitive_config_is_excluded(self):
        result=router.compact_retrieved_memory("segurança projeto",["API_KEY: segurança projeto segredo","O projeto de segurança municipal segue ativo."])
        self.assertEqual(len(result),1)
        self.assertNotIn("segredo",result[0])
    def test_empty_or_unrelated(self):
        self.assertEqual(router.compact_retrieved_memory("previsão do tempo",["Planejamento de obras municipais"]),[])
if __name__=="__main__": unittest.main()
