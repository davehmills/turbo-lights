import unittest
import os

import led_control


test_data_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class TestYAMLImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pth_test_file = os.path.join(test_data_folder, 'test_zones.yaml')

    def test_power_zone_import(self):
        """ Test importing of power zone data """
        zones = led_control.get_zones(pth_file=self.pth_test_file)

        # Confirm some specific attributes
        self.assertEqual(len(zones), 8)
        self.assertEqual(min(zones), 0.0)
        self.assertEqual(max(zones), 3000.0)

    def test_heart_rate_zone_import(self):
        """ Test importing of heart rate zone data """
        zones = led_control.get_zones(pth_file=self.pth_test_file, power=False)

        # Confirm some specific attributes
        self.assertEqual(len(zones), 8)
        self.assertEqual(min(zones), 0.0)
        self.assertEqual(max(zones), 255.0)

    def test_file_missing(self):
        """ Tests running correctly if file is missing """
        with self.assertRaises(FileNotFoundError):
            led_control.get_zones(pth_file='Missing file')


if __name__ == '__main__':
    unittest.main()
