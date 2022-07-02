import unittest
import os

import led_control


test_data_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class TestYAMLImportZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pth_test_file = os.path.join(test_data_folder, 'test_INPUT_CONSTANTS.yaml')

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


class TestYAMLImportANTConstants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pth_test_file = os.path.join(test_data_folder, 'test_INPUT_CONSTANTS.yaml')

    def test_ant_constants(self):
        """ Test importing of power zone data """
        ant_constants = led_control.get_ant_constants(pth_file=self.pth_test_file)

        # Confirm some specific attributes
        self.assertEqual(len(ant_constants), 2)
        self.assertEqual(ant_constants['SERIAL'], '/dev/ttyUSB0')

    def test_file_missing(self):
        """ Tests running correctly if file is missing """
        with self.assertRaises(FileNotFoundError):
            led_control.get_ant_constants(pth_file='Missing file')


class HeartRateColorZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.zones_hr = list((0, 141, 150, 158, 167, 172, 178, 255))
        cls.zones_power = list((0, 155, 214, 247, 267, 298, 340, 3000))

    def test_hr_zone_colormapping(self):
        """ Test importing of power zone data """
        test_zones = self.zones_hr
        zone_colormapping = led_control.get_zone_colormapping(zones=test_zones)

        # Confirm some specific attributes
        self.assertEqual(len(zone_colormapping), max(test_zones))
        self.assertEqual(min(zone_colormapping.keys()), min(test_zones))
        self.assertEqual(max(zone_colormapping.keys()), max(test_zones) - 1)

    def test_power_zone_colormapping(self):
        """ Test importing of power zone data """
        test_zones = self.zones_power
        zone_colormapping = led_control.get_zone_colormapping(zones=test_zones)

        # Confirm some specific attributes
        self.assertEqual(len(zone_colormapping), max(test_zones))
        self.assertEqual(min(zone_colormapping.keys()), min(test_zones))
        self.assertEqual(max(zone_colormapping.keys()), max(test_zones) - 1)


if __name__ == '__main__':
    unittest.main()
