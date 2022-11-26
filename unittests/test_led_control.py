import unittest
import os

import color_setting


test_data_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data')


class TestYAMLImportZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pth_test_file = os.path.join(test_data_folder, 'test_INPUT_CONSTANTS.yaml')

    def test_power_zone_import(self):
        """ Test importing of power zone data """
        zones = color_setting.get_zones(pth_file=self.pth_test_file)

        # Confirm some specific attributes
        self.assertEqual(len(zones), 8)
        self.assertEqual(min(zones), 0.0)
        self.assertEqual(max(zones), 3000.0)

    def test_heart_rate_zone_import(self):
        """ Test importing of heart rate zone data """
        zones = color_setting.get_zones(pth_file=self.pth_test_file, power=False)

        # Confirm some specific attributes
        self.assertEqual(len(zones), 8)
        self.assertEqual(min(zones), 0.0)
        self.assertEqual(max(zones), 255.0)

    def test_file_missing(self):
        """ Tests running correctly if file is missing """
        with self.assertRaises(FileNotFoundError):
            color_setting.get_zones(pth_file='Missing file')


class TestYAMLImportANTConstants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pth_test_file = os.path.join(test_data_folder, 'test_INPUT_CONSTANTS.yaml')

    def test_ant_constants(self):
        """ Test importing of power zone data """
        ant_constants = color_setting.get_ant_constants(pth_file=self.pth_test_file)

        # Confirm some specific attributes
        self.assertEqual(len(ant_constants), 2)
        self.assertEqual(ant_constants['SERIAL'], '/dev/ttyUSB0')

    def test_file_missing(self):
        """ Tests running correctly if file is missing """
        with self.assertRaises(FileNotFoundError):
            color_setting.get_ant_constants(pth_file='Missing file')


class HeartRateColorZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.zones_hr = list((0, 141, 150, 158, 167, 172, 178, 255))
        cls.zones_power = list((0, 155, 214, 247, 267, 298, 340, 3000))

    def test_hr_zone_colormapping(self):
        """ Test importing of power zone data """
        test_zones = self.zones_hr
        zone_colormapping = color_setting.get_zone_colormapping(zones=test_zones, number_of_leds=100)

        # Confirm some specific attributes
        self.assertEqual(len(zone_colormapping), max(test_zones))
        self.assertEqual(min(zone_colormapping.keys()), min(test_zones))
        self.assertEqual(max(zone_colormapping.keys()), max(test_zones) - 1)
        # Confirm the LED setting values are correct
        self.assertEqual(zone_colormapping[0][0][0], 100)
        self.assertEqual(zone_colormapping[0][1][0], 0)

    def test_power_zone_colormapping(self):
        """ Test importing of power zone data """
        test_zones = self.zones_power
        zone_colormapping = color_setting.get_zone_colormapping(zones=test_zones, number_of_leds=100)

        # Confirm some specific attributes
        self.assertEqual(len(zone_colormapping), max(test_zones))
        self.assertEqual(min(zone_colormapping.keys()), min(test_zones))
        self.assertEqual(max(zone_colormapping.keys()), max(test_zones) - 1)
        # Confirm the LED setting values are correct
        self.assertEqual(zone_colormapping[0][0][0], 100)
        self.assertEqual(zone_colormapping[0][1][0], 0)

        setting = zone_colormapping[0]
        # Extract settings
        color1 = setting[0][1]
        color2 = setting[1][1]
        leds1 = setting[0][0]
        leds2 = setting[1][0]

        # Set leds to the appropriate color
        print('leds1 = ' + str(leds1) + ' and color1 = ' + str(color1))
        print('leds2 = ' + str(leds2) + ' and color2 = ' + str(color2))



if __name__ == '__main__':
    unittest.main()
