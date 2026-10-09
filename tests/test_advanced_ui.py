"""Offline UI regression: sidebar Advanced must not navigate to Railway."""
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from importlib.machinery import SourceFileLoader
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
ABS_MAP={
    "/opt/hermes-render/hermes-simple.py":"hermes-simple.py",
    "/usr/local/bin/hermes-global-model-router":"hermes-global-model-router.py",
    "/usr/local/bin/hermes-light-agent":"hermes-light-agent.py",
}
_REAL_INIT=SourceFileLoader.__init__

def redirect_loader(self,name,path):
    return _REAL_INIT(self,name,str(ROOT/ABS_MAP[path]) if path in ABS_MAP else path)

with patch.object(SourceFileLoader,"__init__",redirect_loader):
    spec=importlib.util.spec_from_file_location("hermes_light_ui_test",ROOT/"hermes-render-light-web.py")
    app=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)

class AdvancedUiTests(unittest.TestCase):
    def test_sidebar_button_is_local_not_external(self):
        markup=app.simple.HTML
        self.assertIn('id="advanced-mode-link"',markup)
        self.assertIn('type="button"',markup)
        self.assertNotIn('target="_blank">⚙ Avançado',markup)
        self.assertNotIn('href="/">⚙ Avançado',markup)

    def test_switch_to_advanced_selected_with_click(self):
        markup=app.simple.HTML
        self.assertIn('<option value="advanced">Avançado',markup)
        self.assertIn("advancedButton.onclick=()=>{",markup)
        self.assertIn("$('#model').value='advanced';",markup)
        self.assertIn("$('#sidebar').classList.remove('open');",markup)
        self.assertIn("input.focus();",markup)

    def test_basic_chat_keeps_original_router(self):
        with patch.dict(os.environ,{"HERMES_INFERENCE_MODE":"groq"},clear=False), \
             patch.object(app.router,"run",return_value={"ok":True,"response":"normal","provider":"groq-free"}) as run, \
             patch.object(app.agent,"answer") as advanced:
            output,via=app.chat_via_global_router({"input":"olá","route":"auto"})
        self.assertEqual(via,"groq-free")
        self.assertEqual(output["output"][0]["content"][0]["text"],"normal")
        run.assert_called_once()
        advanced.assert_not_called()

    def test_advanced_request_uses_agent_not_basic_router(self):
        with patch.dict(os.environ,{"HERMES_INFERENCE_MODE":"groq","HERMES_AGENT_TOOLS_ENABLED":"1"},clear=False), \
             patch.object(app.router,"run") as basic, \
             patch.object(app.agent,"answer",return_value={"ok":True,"response":"avançado","provider":"groq-free-advanced"}) as advanced:
            output,via=app.chat_via_global_router({"input":"2+3","route":"advanced"})
        self.assertEqual(via,"groq-free-advanced")
        self.assertEqual(output["output"][0]["content"][0]["text"],"avançado")
        basic.assert_not_called()
        advanced.assert_called_once_with("2+3")

    def test_generated_browser_script_syntax(self):
        if not shutil.which("node"):
            self.skipTest("Node.js unavailable")
        scripts=re.findall(r"<script>(.*?)</script>",app.simple.HTML,flags=re.S)
        self.assertEqual(len(scripts),1)
        result=subprocess.run(["node","--check"],input=scripts[0],capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":
    unittest.main()
