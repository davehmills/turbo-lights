"""
    Script controls the colour of the LED lights based on power or heart rate and bands provided in the relevant
    input files
"""
import os

import yaml
import sys
import time
from ant.core import driver, node, event, message, log
from ant.core.constants import CHANNEL_TYPE_TWOWAY_RECEIVE, TIMEOUT_NEVER

# CONSTANTS
PTH_CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'INPUT_CONSTANTS.yaml')


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
    # Netkey requires conversion to hex
    netkey = file_contents['ANT']['NETKEY']

    # Convert to dictionary
    ant_constants = dict()
    ant_constants['SERIAL'] = serial
    ant_constants['NETKEY'] = netkey

    return ant_constants


def get_zone_colormapping(zones):
    """
        Colors to use for each zone, based on: https://zwiftinsider.com/power-zone-colors/
        Align the colors with the zones such that there is a lookup dictionary for each heart rate zone determining
            the color that should be set
    :param list zones:
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
    # Combine into a single set
    colormapping = (z1, z2, z3, z4, z5, z6, z7)

    color_zones = dict()
    # Loop through each entry in the zones and set the corresponding color (except the last one)
    for i, zone_value in enumerate(zones[:-1]):
        # Define a new dictionary
        temp_color_zones = {x: colormapping[i] for x in range(zone_value, zones[i+1])}
        # Combine into dictionary
        color_zones.update(temp_color_zones)

    return color_zones


# Class for managing heart rate monitor
# class HRM(event.EventCallback):
#     """ Detecting Heart Rate Monitor values """
#     def __init__(self, serial, netkey, hr_colormapping):
#         """
#             Initialise the class for managing the heart rate monitor
#         :param str serial:  Serial string of ANT_USB stick, provided as external config file
#         :param str netkey:  Hexidecimal number for the ANT stick
#         :param dict hr_colormapping:  Zones associated with HR color mapping
#         """
#         self.serial = serial
#         self.netkey = netkey
#         self.antnode = None
#         self.channel = None
#         self.hr_colormapping = hr_colormapping
#
#     def start(self):
#         """ Start the node, listening for heart rate data """
#         self._start_antnode()
#         self._setup_channel()
#         self.channel.registerCallback(self)
#
#     def stop(self):
#         """ Stop the node"""
#         if self.channel:
#             self.channel.close()
#             self.channel.unassign()
#         if self.antnode:
#             self.antnode.stop()
#
#     def __enter__(self):
#         return self
#
#     def __exit__(self, type_, value, traceback):
#         self.stop()
#
#     def _start_antnode(self):
#         stick = driver.USB2Driver(self.serial)
#         self.antnode = node.Node(stick)
#         self.antnode.start()
#
#     def _setup_channel(self):
#         key = node.NetworkKey('N:ANT+', self.netkey)
#         self.antnode.setNetworkKey(0, key)
#         self.channel = self.antnode.getFreeChannel()
#         self.channel.name = 'C:HRM'
#         self.channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
#         self.channel.setID(120, 0, 0)
#         self.channel.setSearchTimeout(TIMEOUT_NEVER)
#         self.channel.setPeriod(8070)
#         self.channel.setFrequency(57)
#         self.channel.open()
#
#     def process(self, msg):
#         if isinstance(msg, message.ChannelBroadcastDataMessage):
#             # Get heart rate and color for LEDS
#             heart_rate = ord(msg.payload[-1])
#             color = self.hr_colormapping[heart_rate]
#             print("heart rate is {}".format(ord(msg.payload[-1])))
#
#
# if __name__ == '__main__':
#     # Get constants
#     ant_constants = get_ant_constants(pth_file=PTH_CONSTANTS_FILE)
#     hr_zones = get_zones(pth_file=PTH_CONSTANTS_FILE, power=False)
#
#     # Get colors for HR zones
#     hr_zones_colormapping = get_zone_colormapping(zones=hr_zones)
#
#     # TODO: Need to add in something here to determine whether HRM or POWER METER is detected, checking every x seconds
#     with HRM(serial=ant_constants['SERIAL'], netkey=ant_constants['NETKEY'], hr_colormapping=hr_zones_colormapping) as hrm:
#         hrm.start()
#         # Set a timer to refresh the heart rate zones every 30 seconds
#         while True:
#             try:
#                 time.sleep(1)
#             except KeyboardInterrupt:
#                 sys.exit(0)
