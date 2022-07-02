"""
    Script controls the colour of the LED lights based on power or heart rate and bands provided in the relevant
    input files
"""

import yaml
import sys
import time
# from ant.core import driver, node, event, message, log
# from ant.core.constants import CHANNEL_TYPE_TWOWAY_RECEIVE, TIMEOUT_NEVER


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

    # Convert all items into a float
    zones = [float(x) for x in zones_to_process]
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

# # Class for managing heart rate monitor
# class HRM(event.EventCallback):
#     """ Detecting Heart Rate Monitor values """
#     def __init__(self, serial, netkey):
#         """
#             Initialise the class for managing the heart rate monitor
#         :param str serial:  Serial number of ANT_USB stick, provided as external config file
#         :param netkey:
#         """
#         self.serial = serial
#         self.netkey = netkey
#         self.antnode = None
#         self.channel = None
#
#     def start(self):
#         print("starting node")
#         self._start_antnode()
#         self._setup_channel()
#         self.channel.registerCallback(self)
#         print("start listening for hr events")
#
#     def stop(self):
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
#             print("heart rate is {}".format(ord(msg.payload[-1])))
