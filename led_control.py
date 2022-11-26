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
import color_setting

# noinspection PyPackageRequirements
import board
# noinspection PyUnresolvedReferences
import neopixel

# noinspection PyUnresolvedReferences
from rpi_ws281x import *
import argparse

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


# Class for ANT+ data
class Monitor:
    """ Detecting Heart Rate Monitor values """
    colormapping: dict[int, tuple]
    power: bool
    start_time: dt.datetime
    channel_power: Channel
    channel_hr: Channel
    time_counter: dt.datetime

    def __init__(self, serial, netkey, led_controller, time_delay, number_measurements_to_average):
        """
            Initialise the class for managing the heart rate monitor
        :param str serial:  Serial string of ANT_USB stick, provided as external config file
        :param list netkey:  Hexadecimal number for the ANT stick
        :param instance led_controller:  Function which device is passed
        :param int time_delay:  Maximum delay to allow before toggling input
        :param int number_measurements_to_average:  Number of individual measurements to average
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

        # Stores the previous power values and keeps count of the number of power measurements
        # that have been processed
        self.previous_color_value = (1000, 1000, 1000)
        self.counter = 0

        # Get the relevant zones and color mapping
        zones_power = color_setting.get_zones(pth_file=PTH_CONSTANTS_FILE, power=True)
        zones_hr = color_setting.get_zones(pth_file=PTH_CONSTANTS_FILE, power=False)
        # Get colors for zones
        self.colormapping_power = color_setting.get_zone_colormapping(
            zones=zones_power, number_of_leds=self.update_led.number_leds
        )
        self.colormapping_hr = color_setting.get_zone_colormapping(
            zones=zones_hr, number_of_leds=self.update_led.number_leds
        )

        # Holders for previous power values
        self.previous_power_values = [0]*number_measurements_to_average

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
        channel = self.antnode.new_channel(Channel.Type.BIDIRECTIONAL_RECEIVE)

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
        # Store the time power data was last updated
        self.power_last_update = dt.datetime.now()
        self.counter += 1

        # Get power data and relevant color
        new_power_value = data[6]

        # Add to rolling average store
        # Remove last value and add new value to rolling average store
        del self.previous_power_values[0]
        self.previous_power_values.append(new_power_value)

        # # Calculate average and determine new color
        average_power = int(sum(self.previous_power_values) / len(self.previous_power_values))
        new_color = self.colormapping_power[average_power]

        # Transfer to using power data if not already
        if not self.power:
            self.power = True
            self.update_led.set_led_color_range(color=new_color, flash=True)
            self.previous_color_value = new_color
        else:
            # Check whether the color has actually changed and only update the LEDs
            # if the color has actually changed
            if new_color != self.previous_color_value:
                self.previous_color_value = new_color
                self.update_led.set_led_color_range(new_color)
                # self.update_led.change_led_color(color=new_color)

                self.counter = 0

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
                self.update_led.set_led_color_range(color=color, flash=True)
                self.power = False
        else:
            self.update_led(color=color)


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

        # Number of leds being controlled
        self.number_leds = number_of_leds
        
        # Create NeoPixel object with appropriate configuration.
        # noinspection PyUnresolvedReferences
        self.strip = neopixel.NeoPixel(board.D18, number_of_leds, bpp=3, brightness=1.0)

        # Initialise pixels by rotating colors
        self.change_led_color(color=PAIRED_COLOR, flash=True)

    def set_led_color_range(self, setting, flash=False):
        """
            Specifies the color and number of leds to set
        :param tuple setting:
        :param bool flash:  If set to True then will flash the leds 10 times with the same setting
        :return:
        """
        # Extract settings
        color1 = setting[0][1]
        color2 = setting[1][1]
        leds1 = setting[0][0]
        leds2 = setting[1][0]

        # Set leds to the appropriate color
        self.strip[:leds1] = color1
        self.strip[leds2:] = color2

        if flash:
            for x in range(10):
                self.strip.fill((0, 0, 0))
                time.sleep(0.05)
                self.strip[:leds1] = color1
                self.strip[leds2:] = color2

        return None

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
                    # self.color_wipe((0, 0, 0))
                    self.color_set(x)
                    
                # Set to the requested color
                # self.color_wipe(x)
                self.color_set(x)
                # time.sleep(0.2)

        else:
            # Flash LEDS if changing sensor
            if flash:
                for x in range(5):
                    # self.color_wipe(color)
                    self.color_set(color)
                    # time.sleep(0.2)
            # Finally set the color that LED is supposed to be
            # self.color_wipe(color)
            self.color_set(color)

        # # Add in 1 second delay here to avoid changing too often
        # time.sleep(0.2)

        return None

    def color_set(self, color):
        """ Change all pixels at the same time """
        # Convert to RGB
        self.strip.fill((int(color[0]), int(color[1]), int(color[2])))
        
        return None


if __name__ == '__main__':
    # Get constants
    ant_settings = color_setting.get_ant_constants(pth_file=PTH_CONSTANTS_FILE)

    # Setup LEDs
    leds = LEDController(ant_settings['LEDS'])

    # Create monitor and establish instance
    monitor = Monitor(
        serial=ant_settings['SERIAL'],
        netkey=[0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45],
        led_controller=leds,
        time_delay=ant_settings['TIME_DELAY'],
        number_measurements_to_average=ant_settings['NUMBER_POWER_VALUES']
    )

    monitor.initialise_channels()

    try:
        # Open the channels
        monitor.channel_power.open()
        print('power channel_opened')
        # monitor.channel_hr.open()
        # print('hr channel_opened')
        # Start the node
        monitor.antnode.start()
        monitor.time_counter = dt.datetime.now()
        print('node started')
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        leds.strip.deinit()
        sys.exit(0)
    finally:
        monitor.antnode.stop()
        leds.strip.deinit()
