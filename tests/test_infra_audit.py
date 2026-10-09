"""Offline tests for explicitly approved network inspection boundaries."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("audit",pathlib.Path(__file__).resolve().parents[1]/"hermes-infra-audit.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AuditTests(unittest.TestCase):
    def test_no_hosts_configured(self):
        with patch.dict("os.environ",{"HERMES_AUDIT_ALLOWED_HOSTS":""}):
            with self.assertRaises(ValueError):
                m.check_connectivity("example.org")

    def test_reject_private_network(self):
        with patch.dict("os.environ",{"HERMES_AUDIT_ALLOWED_HOSTS":"localhost"}):
            with self.assertRaises(ValueError):
                m.check_connectivity("localhost")

    def test_reject_arbitrary_ports(self):
        with patch.object(m,"_approved_hostname",return_value=["8.8.8.8"]):
            with self.assertRaises(ValueError):
                m.check_connectivity("example.org",ports=[22])

    def test_api_read_only_and_header_restricted(self):
        with patch.object(m,"_validate_url",return_value="https://example.org"):
            with self.assertRaises(ValueError):
                m.authorized_http_request("https://example.org",method="POST")
            with self.assertRaises(ValueError):
                m.authorized_http_request("https://example.org",headers={"Cookie":"secret"})

    def test_html_outline_parsing(self):
        p=m.HtmlOutline()
        p.feed('<main id="app" class="home"><style>h1{font-weight:bold}</style><h1>Example</h1></main>')
        self.assertEqual(p.nodes[0]["tag"],"main")
        self.assertIn("font-weight", "".join(p.styles))
if __name__=="__main__": unittest.main()
