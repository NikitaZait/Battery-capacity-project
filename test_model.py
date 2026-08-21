import unittest
from battery_model import BatterySimulator

class TestBatterySimulator(unittest.TestCase):
    def test_default_simulation(self):
        sim = BatterySimulator()
        results = sim.run_simulation()
        
        self.assertIn('time', results)
        self.assertIn('soc', results)
        self.assertIn('temp', results)
        self.assertGreater(len(results['time']), 10)
        self.assertLessEqual(results['final_soc_pct'], 100.0)
        self.assertGreaterEqual(results['final_temp_c'], 25.0)

    def test_zero_laps(self):
        sim = BatterySimulator(track_config={'num_laps': 0})
        results = sim.run_simulation()
        self.assertEqual(results['total_time_s'], 0.0)
        self.assertEqual(results['final_soc_pct'], 100.0)

if __name__ == '__main__':
    unittest.main()
