import unittest
from battery_model import BatterySimulator
from f1_tracks import F1_TRACKS, get_track_keys

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

    def test_f1_presets(self):
        keys = get_track_keys()
        self.assertEqual(keys, ["monza", "monaco", "interlagos"])
        
        for key in keys:
            track = F1_TRACKS[key]
            segments = track["segments"]
            xs, ys, total_len = BatterySimulator.get_track_coordinates_from_segments(segments)
            self.assertGreater(total_len, 1000)
            self.assertEqual(len(xs), len(ys))
            # Test zero-gap closure
            gap = ((xs[-1] - xs[0])**2 + (ys[-1] - ys[0])**2)**0.5
            self.assertAlmostEqual(gap, 0.0, places=5)

if __name__ == '__main__':
    unittest.main()
