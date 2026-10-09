import unittest
import time
import os
from unittest.mock import patch, MagicMock
from src.analyzer import analyze_feedback
from src.offer_generator import generate_special_offer
from src.aegis import AegisDebateOrchestrator
from src.karabakh_routing import run_failover_simulation

class TestKOIPEnterpriseSuite(unittest.TestCase):

    # --- 1. Analyzer Tests ---
    def test_analyzer_high_churn(self):
        with patch("os.getenv", return_value="sk-valid-key"):
            with patch("src.analyzer.OpenAI") as mock_client:
                mock_response = MagicMock()
                mock_response.choices[0].message.content = '{"sentiment": "NEGATIVE", "core_issue": "Network drop", "priority": "CRITICAL"}'
                mock_client.return_value.chat.completions.create.return_value = mock_response
                
                result = analyze_feedback("I am very angry and want to leave.")
                self.assertEqual(result.get("sentiment"), "NEGATIVE")
                self.assertEqual(result.get("priority"), "CRITICAL")

    def test_analyzer_fallback(self):
        with patch("os.getenv", return_value=None):
            result = analyze_feedback("Bərbad")
            self.assertEqual(result["sentiment"].lower(), "negative")

    # --- 2. Offer Generator Guardrail Tests ---
    def test_margin_limit_guardrail(self):
        customer_data = {
            "customer_id": "AZC-001",
            "margin_limit_percentage": 10,
            "monthly_spend_azn": 100,
            "lifetime_value_azn": 1200,
            "name": "Test",
            "product": "Test Prod"
        }
        analysis = {"sentiment": "negative", "churn_risk": 95, "priority": "CRITICAL"}
        
        with patch("src.offer_generator.OpenAI") as mock_client:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"discount_percentage": 50}'
            mock_client.return_value.chat.completions.create.return_value = mock_response
            
            with patch("os.getenv", return_value="sk-test"):
                result = generate_special_offer("Help", analysis, customer_data)
                self.assertLessEqual(result["offer_params"]["max_discount"], customer_data["margin_limit_percentage"])

    # --- 3. Aegis Multi-Agent Debate Tests ---
    def test_aegis_debate_orchestrator(self):
        with patch("src.aegis._call_llm") as mock_llm:
            mock_llm.side_effect = [
                "Maddə 14.2 CRITICAL riskdir.",
                "HIGH risk. Marja mənfiyə düşür.",
                "REDLINE_AMENDMENT_APPROVED: 15% tavan qoyuldu."
            ]
            
            orchestrator = AegisDebateOrchestrator()
            result = orchestrator.run_debate()
            
            self.assertEqual(result["status"], "CONSENSUS_REACHED")
            self.assertEqual(len(result["debate_transcript"]), 3)
            self.assertEqual(result["debate_transcript"][0]["risk"], "CRITICAL")
            self.assertEqual(result["debate_transcript"][1]["risk"], "HIGH")
            self.assertIn("REDLINE", result["redline"]["synthesis_text"])

    def test_aegis_no_api_key(self):
        with patch("src.aegis.client", None):
            orchestrator = AegisDebateOrchestrator()
            result = orchestrator.run_debate()
            self.assertIn("OFFLINE DEMO MODE", result["debate_transcript"][0]["text"])

    # --- 4. Karabakh Routing Telemetry Tests ---
    def test_karabakh_normal_routing(self):
        res = run_failover_simulation(fault_node=None)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("FIBER", res["normal_route"]["mediums"])
        self.assertEqual(res["brigade_saved_azn"], 0)

    def test_karabakh_failover_routing(self):
        res = run_failover_simulation(fault_node="Agdam_Node_01")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["fault_injected"], "Agdam_Node_01")
        self.assertIn("SATELLITE", res["failover_route"]["mediums"])
        self.assertEqual(res["brigade_saved_azn"], 2400)

    def test_karabakh_routing_latency(self):
        start = time.time()
        run_failover_simulation(fault_node="Agdam_Node_01")
        end = time.time()
        self.assertLess(end - start, 0.05)

if __name__ == "__main__":
    unittest.main()
