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
# noinspection PyUnresolvedReferences
from rpi_ws281x import *
import argparse

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

    # Convert to dictionary
    ant_constants = dict()
    ant_constants['SERIAL'] = serial
    ant_constants['NETKEY'] = netkey
    ant_constants['LEDS'] = number_leds
    ant_constants['TIME_DELAY'] = time_delay

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
        :param list netkey:  Hexadecimal number for the ANT stick
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
        self.power = True

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
        print('initialising')
        self.antnode = Node()
        self.antnode.set_network_key(0x00, self.netkey)
        
        self.channel_power = self._setup_channel(power=True)
        print('power_channel_setup')
        # self.channel_hr = self._setup_channel(power=False)
        # print('hr_channel_setup')

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
        # channel = self.antnode.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)
        channel = self.antnode.new_channel(Channel.Type.UNIDIRECTIONAL_RECEIVE_ONLY)

        if power:
            channel.on_broadcast_data = self.on_power_data
            channel.on_burst_data = self.on_power_data

            channel.set_period(8182)  # might be 4091 or 8182
            channel.set_search_timeout(30)
            channel.set_rf_freq(57)
            channel.set_id(0, 11, 0)
            channel.enable_extended_messages(1)

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
        # print('POWER DATA = {}'.format(data))
        # Believe power = number 6
        print('POWER = {}'.format(data[1][6]))
        # print(data)
        # # TODO: Specific numbers to be determined
        # data_value = int(data[7] * 256 + data[6])
        # color = self.colormapping_power[data_value]
        #
        # # Store the time power data was last updated
        # self.power_last_update = dt.datetime.now()
        #
        # # Transfer to using power data if not already
        # if not self.power:
        #     self.power = True
        #     self.update_led(color=color, flash=True)
        # else:
        #     self.update_led(color=color)

    def on_hr_data(self, data):
        """ Function runs whenever power data is received """
        # Get hr data and transfer to relevant color
        print('HR Data = {}'.format(data))
        # print(data)
        
        # data_value = int(data[7])
        # color = self.colormapping_hr[data_value]
        #
        # # Ser hr update time
        # self.hr_last_update = dt.datetime.now()
        #
        # # If power data hasn't been updated in a while, transfer to hr data
        # if self.power:
        #     if (self.hr_last_update - self.power_last_update).total_seconds() > self.time_delay:
        #         self.update_led(color=color, flash=True)
        #         self.power = False
        # else:
        #     self.update_led(color=color)


class LEDController:
    def __init__(self, number_of_leds=30):
        """
            Initialise the LED controller
        :param int number_of_leds:  Number of LEDs
        """
        # Process arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
        _ = parser.parse_args()
        
        # Create NeoPixel object with appropriate configuration.
        # noinspection PyUnresolvedReferences
        self.strip = Adafruit_NeoPixel(
            number_of_leds, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL
        )
        # Initialise the library (must be called once before other functions).
        self.strip.begin()
        
        # Initialise pixels by rotating colors
        self.change_led_color(color=PAIRED_COLOR, flash=True)

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
                    self.color_wipe((0, 0, 0))
                # Set to the requested color
                self.color_wipe(x)

        else:
            # Flash LEDS if changing sensor
            if flash:
                for x in range(5):
                    self.color_wipe(color)
            # Finally set the color that LED is supposed to be
            self.color_wipe(color)

        # Add in 1 second delay here to avoid changing too often
        time.sleep(1)

        return None

    def color_wipe(self, color, wait_ms=5):
        """Wipe color across display a pixel at a time."""
        # Convert to RGB
        color = Color(color[0], color[1], color[2])
        
        for i in range(self.strip.numPixels()):
            print(i)
            print(color)
            self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(wait_ms/1000.0)


if __name__ == '__main__':
    # Get constants
    ant_settings = get_ant_constants(pth_file=PTH_CONSTANTS_FILE)

    # Setup LEDs
    leds = LEDController(ant_settings['LEDS'])

    # Create monitor and establish instance
    monitor = Monitor(
        serial=ant_settings['SERIAL'],
        netkey=[0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45],
        led_controller=leds.change_led_color,
        time_delay=ant_settings['TIME_DELAY']
    )

    monitor.initialise_channels()

    try:

        # Start channels
        # Start the node
        monitor.antnode.start()
        print('node started')
        # Open the channels
        monitor.channel_power.open()
        print('power channel_opened')
        # monitor.channel_hr.open()
        # print('hr channel_opened')

        while True:
            time.sleep(0.01)

    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        print('closing down')
        monitor.antnode.stop()
        leds.change_led_color(color=(0, 0, 0))
        print('completed')