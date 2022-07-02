"""
    Script controls the colour of the LED lights based on power or heart rate and bands provided in the relevant
    input files
"""

import yaml


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

