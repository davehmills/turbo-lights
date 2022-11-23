"""
    Scripts that relate to testable items

"""
import os
import math

import yaml

# CONSTANTS
PTH_CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'INPUT_CONSTANTS.yaml')
PAIRED_COLOR = (
    (132, 132, 130),  # Grey
    (0, 0, 255),  # Blue
    (0, 204, 34),  # Green
    (255, 255, 0),  # Yellow
    (255, 128, 0),  # Orange
    (255, 0, 0),  # Red
    (251, 3, 201)  # Purple
)

# LED strip configuration:
# LED_COUNT      = 30      # Number of LED pixels.
LED_PIN = 18      # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


def get_zones(pth_file, power=True):
    """
        Script imports the zones to consider for heart rate or power
    :param str pth_file:  Path to the YAML file that contains the zones
    :param bool power:  Whether power or heart rates zones are being considered (optional=True)
    :return list zones:  Returns a list showing the zones which should be considered
    """
    # Import the yaml file
    with open(pth_file, 'r') as f:
        file_contents: dict = yaml.safe_load(f)

    # Determine either the heart rate or power data, converting to float if needed
    if power:
        zones_to_process = file_contents['POWER']['zones']
    else:
        zones_to_process = file_contents['HEART RATE']['zones']

    # Convert all items into a integer
    zones = [int(x) for x in zones_to_process]
    return zones


def get_ant_constants(pth_file):
    """
        Retrieves all the constants associated with detecting ANT input changes
    :param str pth_file:  YAML file which contains input constants
    :return dict ant_constants:  Dictionary of inputs
    """
    # Import the yaml file
    with open(pth_file, 'r') as f:
        file_contents: dict = yaml.safe_load(f)

    # Extract constants from YAML file
    serial = file_contents['ANT']['SERIAL']
    # Netkey
    netkey = file_contents['ANT']['NETKEY']
    # LEDS requires conversion to integer
    number_leds = int(file_contents['ANT']['LEDS'])
    # time delay requires conversion to int
    time_delay = int(file_contents['ANT']['TIME_DELAY'])
    # Number of seconds to sample power data
    number_of_seconds = int(file_contents['ANT']['POWER_AVERAGING'])

    # Convert to dictionary
    ant_constants = dict()
    ant_constants['SERIAL'] = serial
    ant_constants['NETKEY'] = netkey
    ant_constants['LEDS'] = number_leds
    ant_constants['TIME_DELAY'] = time_delay

    # TODO: Need to convert this input into number of values based on sampling rate (frequency)
    ant_constants['NUMBER_POWER_VALUES'] = number_of_seconds

    return ant_constants


def get_zone_colormapping(zones, number_of_leds):
    """
        Colors to use for each zone, based on: https://zwiftinsider.com/power-zone-colors/
        Align the colors with the zones such that there is a lookup dictionary for each heart rate zone determining
            the color that should be set
    :param list zones:
    :param int number_of_leds:  Number of leds being considered
    :return dict color_zones:  Dictionary of zones to colors
    """

    # Grey
    z1 = (132, 132, 130)
    # Blue
    z2 = (0, 0, 255)
    # Green
    z3 = (0, 204, 34)
    # Yellow
    z4 = (255, 255, 0)
    # Orange
    z5 = (255, 128, 0)
    # Red
    z6 = (255, 0, 0)
    # Purple - Required an extra color due to number of zones
    z7 = (251, 3, 201)
    # White - Required for extreme effort levels
    z8 = (255, 255, 255)
    # Combine into a single set
    colormapping = (z1, z2, z3, z4, z5, z6, z7, z8)

    color_zones = dict()
    # Loop through each entry in the zones and set the corresponding color (except the last one)
    for i, zone_value in enumerate(zones[:-1]):
        # Calculate power change / led
        led_step = number_of_leds / (zones[i+1] - zones[i])

        # Define a new dictionary
        temp_color_zones = {
            x: (
                (number_of_leds - math.floor((x - zones[i]) * led_step), colormapping[i]),
                (math.floor((x - zones[i]) * led_step), colormapping[i+1])
            ) for x in range(zone_value, zones[i+1])}
        # Combine into dictionary
        color_zones.update(temp_color_zones)

    return color_zones


def number_of_leds_calc(value, limits):
    """
        Calculated the number of LEDS that need to be set the upper color and how many the lower color
    :param int value: Value (power or HR) to consider
    :param tuple limits:  Upper and lower limits to consider
    :return int number_of_leds:  Number of LEDS to set to the upper color
    """

    # Using min and max to find closest value in list
    lower_value = limits[min(range(len(limits)), key=lambda i: abs(limits[i]-value))]
    upper_value = limits[max(range(len(limits)), key=lambda i: abs(limits[i]-value))]
