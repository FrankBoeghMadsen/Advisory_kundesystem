import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SafetyGuardTests(unittest.TestCase):
    def test_ai_functions_require_explicit_external_consent_by_default(self):
        tree = ast.parse(
            (ROOT / "services" / "ai_service.py").read_text(encoding="utf-8")
        )
        functions = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in ("ai_briefing_text", "ai_meeting_followup_text"):
            function = functions[name]
            argument_names = [argument.arg for argument in function.args.args]
            self.assertIn("allow_external", argument_names)
            self.assertIs(function.args.defaults[-1].value, False)

    def test_ai_services_use_local_output_without_explicit_consent(self):
        from services.ai_service import ai_briefing_text, ai_meeting_followup_text

        briefing = ai_briefing_text("Testaktør", "Fortrolig kontekst")
        followup = ai_meeting_followup_text(
            "Testaktør", "Testmøde", "Fortroligt referat", "Fortrolig kontekst"
        )
        self.assertIn("Ekstern AI er ikke anvendt", briefing)
        self.assertIn("Ekstern AI er ikke anvendt", followup)

    def test_dashboard_no_longer_runs_source_sync_during_page_view(self):
        source = (ROOT / "views" / "dashboard.py").read_text(encoding="utf-8")
        self.assertNotIn("sync_existing_actor_sources(", source)

    def test_windows_launcher_binds_only_to_loopback(self):
        launcher = (ROOT / "Start Monitor.bat").read_text(encoding="utf-8")
        self.assertIn("--server.address 127.0.0.1", launcher)
        self.assertNotIn("--server.address 0.0.0.0", launcher)


if __name__ == "__main__":
    unittest.main()
