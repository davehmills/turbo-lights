"""
    Script controls the colour of the LED lights based on power or heart rate and bands provided in the relevant
    input files

    Utilised openant which can be retrieved using following:
        git clone https://github.com/pirower/openant/
        cd openant
        sudo python3 setup.py install

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
from ant.easy.node import Node
from ant.easy.channel import Channel

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
class Monitor:
    """ Detecting Heart Rate Monitor values """
    colormapping: dict[int, tuple]
    power: bool
    start_time: dt.datetime
    channel_power: Channel
    channel_hr: Channel

    def __init__(self, serial, netkey, led_controller, time_delay):
        """
            Initialise the class for managing the heart rate monitor
        :param str serial:  Serial string of ANT_USB stick, provided as external config file
        :param str netkey:  Hexadecimal number for the ANT stick
        :param function led_controller:  Function which device is passed
        :param int time_delay:  Maximum delay to allow before toggling input
        """
        # Set timestamps to zero
        self.power_last_update = None
        self.hr_last_update = None

        self.serial = serial
        self.netkey = netkey
        self.antnode = None
        self.channel = None
        self.paired = False
        # Function which is called with the new LED colors
        self.update_led = led_controller
        self.time_delay = time_delay

        # Get the relevant zones and color mapping
        zones_power = get_zones(pth_file=PTH_CONSTANTS_FILE, power=True)
        zones_hr = get_zones(pth_file=PTH_CONSTANTS_FILE, power=False)
        # Get colors for zones
        self.colormapping_power = get_zone_colormapping(zones=zones_power)
        self.colormapping_hr = get_zone_colormapping(zones=zones_hr)

    def initialise_channels(self):
        """
            Start the node, listening for heart rate or power meter data
            Starts initially looking for power and switches if nothing detected every x minutes
        """
        # Initialise node
        self.antnode = Node()
        self.antnode.set_network_key(0x00, self.netkey)
        self.channel_power = self._setup_channel(power=True)
        self.channel_hr = self._setup_channel(power=False)

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

    def _setup_channel(self, power=False):
        """
            Setup the channel for either HR or Power
        :param bool power:  Set to True for power channel
        :return None:
        """
        # Create new channel set to receive data
        channel = self.antnode.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

        if power:
            channel.on_broadcast_data = self.on_power_data
            channel.on_burst_data = self.on_power_data

            channel.set_period(8182)  # might be 4091 or 8182
            channel.set_search_timeout(30)
            channel.set_rf_freq(57)
            channel.set_id(0, 121, 0)

        else:
            channel.on_broadcast_data = self.on_hr_data
            channel.on_burst_data = self.on_hr_data

            channel.set_period(8070)
            channel.set_search_timeout(12)
            channel.set_rf_freq(57)
            channel.set_id(0, 120, 0)

        return channel

    def on_power_data(self, data):
        """ Function runs whenever power data is received """
        # Get power data and relevant color
        data_value = int(data[8] * 256 + data[7])
        color = self.colormapping_power[data_value]

        # Store the time power data was last updated
        self.power_last_update = dt.datetime.now()

        # Transfer to using power data if not already
        if not self.power:
            self.power = True
            self.update_led(color=color, flash=True)
        else:
            self.update_led(color=color)

    def on_hr_data(self, data):
        """ Function runs whenever power data is received """
        # Get hr data and transfer to relevant color
        data_value = int(data[7])
        color = self.colormapping_hr[data_value]

        # Ser hr update time
        self.hr_last_update = dt.datetime.now()

        # If power data hasn't been updated in a while, transfer to hr data
        if self.power:
            if (self.hr_last_update - self.power_last_update).total_seconds() > self.time_delay:
                self.update_led(color=color, flash=True)
                self.power = False
        else:
            self.update_led(color=color)


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
            # Flash LEDS if changing sensor
            if flash:
                for x in range(5):
                    self.pixels.fill(color)
                    time.sleep(0.5)
                    self.pixels.fill((0, 0, 0))
            # Finally set the color that LED is supposed to be
            self.pixels.fill(color)

        # Add in 1 second delay here to avoid changing too often
        time.sleep(1)

        return None


if __name__ == '__main__':
    # Get constants
    ant_settings = get_ant_constants(pth_file=PTH_CONSTANTS_FILE)

    # Setup LEDs
    leds = LEDController(ant_settings['LEDS'])

    # Create monitor and establish instance
    monitor = Monitor(
        serial=ant_settings['SERIAL'],
        netkey=ant_settings['NETKEY'],
        led_controller=leds.change_led_color,
        time_delay=ant_settings['TIME_DELAY']
    )

    monitor.initialise_channels()

    # Start channels
    try:
        # Open the channels
        monitor.channel_power.open()
        monitor.channel_hr.open()
        # Start the node
        monitor.antnode.start()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        monitor.antnode.stop()
