"""
    Script controls the colour of the LED lights based on power or heart rate and bands provided in the relevant
    input files
"""
import datetime as dt
import os
# noinspection PyPackageRequirements,PyUnresolvedReferences
import board
# noinspection PyPackageRequirements,PyUnresolvedReferences
import neopixel

import yaml
import sys
import time
from ant.core import driver, node, event, message
from ant.core.constants import CHANNEL_TYPE_TWOWAY_RECEIVE, TIMEOUT_NEVER

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
# Time delay between changing sensors
TIME_DELAY = 500


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


# Class for ANT+ data
class ANTDeviceMonitor(event.EventCallback):
    """ Detecting Heart Rate Monitor values """
    colormapping: dict[int, tuple]
    power: bool
    start_time: dt.datetime

    def __init__(self, serial, netkey, led_controller):
        """
            Initialise the class for managing the heart rate monitor
        :param str serial:  Serial string of ANT_USB stick, provided as external config file
        :param str netkey:  Hexadecimal number for the ANT stick
        :param function led_controller:  Function which device is passed
        """
        self.serial = serial
        self.netkey = netkey
        self.antnode = None
        self.channel = None
        self.paired = False
        # Function which is called with the new LED colors
        self.update_led = led_controller

    def start(self, power=True):
        """
            Start the node, listening for heart rate or power meter data
            Starts initially looking for power and switches if nothing detected every x minutes
        :param bool power:  Whether setting up for a HRM or PowerMeter
        """
        # Get the relevant zones and color mapping
        zones = get_zones(pth_file=PTH_CONSTANTS_FILE, power=power)
        # Get colors for zones
        self.colormapping = get_zone_colormapping(zones=zones)

        self.power = power
        self._start_antnode()
        self._setup_channel()
        self.channel.registerCallback(self)

        # Store the current time
        self.start_time = dt.datetime.now()

    def stop(self):
        """ Stop the node"""
        if self.channel:
            self.channel.close()
            self.channel.unassign()
        if self.antnode:
            self.antnode.stop()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.stop()

    def _start_antnode(self):
        stick = driver.USB2Driver(self.serial)
        self.paired = False
        self.antnode = node.Node(stick)
        self.antnode.start()

    def _setup_channel(self):
        """
            Setup the channel
        :return None:
        """
        # noinspection PyUnresolvedReferences
        key = node.NetworkKey('N:ANT+', self.netkey)
        self.antnode.setNetworkKey(0, key)
        self.channel = self.antnode.getFreeChannel()

        # Setup channel for power or heart rate
        if self.power:
            self.channel.name = 'C:PowerMeter'
            self.channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
            self.channel.setID(11, 0, 0)
            self.channel.searchTimeout = TIMEOUT_NEVER
            self.channel.period = 8182  # might be 4091 or 8182
            self.channel.frequency = 57
        else:
            self.channel.name = 'C:HRM'
            self.channel.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
            self.channel.setID(120, 0, 0)
            self.channel.searchTimeout = TIMEOUT_NEVER
            self.channel.period = 8070
            self.channel.frequency = 57

        # Open the channel
        self.channel.open()
        self.paired = False
        return None

    def process(self, msg):
        """
            Process data / determine if already connected
        :param object msg:
        :return:
        """
        if isinstance(msg, message.ChannelBroadcastDataMessage):
            # Retrieve data
            if self.power:
                if msg.payload[1] == 0x10:  # Power Main Data Page
                    data = msg.payload[8] * 256 + msg.payload[7]
            else:
                # Retrieve heart rate data and convert to integer
                data = ord(msg.payload[-1])

            # Determine the relevant color
            # noinspection PyUnboundLocalVariable
            color = self.colormapping[data]

            # Check if has been identified as paired and if not will also flash the LEDS and
            # toggle the status
            if self.paired:
                self.update_led(color=color)
            else:
                self.paired = True
                self.update_led(color=color, flash=True)

        elif isinstance(msg, message.ChannelIDMessage):
            self.paired = True
            self.update_led(color=PAIRED_COLOR, flash=True)

        return None

    def change_sensor(self):
        """
            Toggle to setup looking at the other sensor
        :return:
        """
        # Stop the existing channel listener
        self.stop()
        # Start a new listener
        self.start(power=not self.power)


class LEDController:
    def __init__(self, number_of_leds=30):
        """
            Initialise the LED controller
        :param int number_of_leds:  Number of LEDs
        """
        self.pixels = neopixel.NeoPixel(board.D18, number_of_leds)
        # Initialise pixels by rotating colors
        self.change_led_color(color=PAIRED_COLOR, flash=True)
        # Set to off
        self.pixels.color((0, 0, 0))

    def change_led_color(self, color, flash=False):
        """
            Change the color of the LED to that provided as an input value
        :param tuple color:  RGB color to set the LED to
        :param bool flash:  Will flash the LEDs if there is a change in the device that is being connected to
        :return None:
        """
        # Determine whether color is a single value or a list
        if len(color) > 3:
            for x in color:
                # If set to flash then will set to black and then to the color
                if flash:
                    self.pixels.fill((0, 0, 0))
                    time.sleep(0.5)
                # Set to the requested color
                self.pixels.fill(x)
                time.sleep(0.5)

        else:
            self.pixels.fill(color)

        return None


if __name__ == '__main__':
    # Get constants
    ant_settings = get_ant_constants(pth_file=PTH_CONSTANTS_FILE)

    # Setup LEDs
    leds = LEDController(ant_settings['LEDS'])

    with ANTDeviceMonitor(
            serial=ant_settings['SERIAL'],
            netkey=ant_settings['NETKEY'],
            led_controller=leds.change_led_color) as device:

        # Start device
        device.start()
        # Set a timer to refresh the heart rate zones every 30 seconds
        while True:
            try:
                time.sleep(1)
                # Check counter
                if (dt.datetime.now() - device.start_time).total_seconds() > TIME_DELAY:
                    print('Toggling Sensor')
                    device.change_sensor()

            except KeyboardInterrupt:
                sys.exit(0)
