import os

# Config.py, Set the flight software operation mode

CONF_NONE = 0
CONF_PAYLOAD = 1
CONF_CONTAINER = 2  
CONF_ROCKET = 3

FSW_CONF = CONF_PAYLOAD

config_file_path = 'lib/config.txt'

if not os.path.exists(config_file_path):
    print(f"#################################################################\n\nConfig file does not exist: {config_file_path}, Configure the config file to run FSW!\n\n#################################################################")

    initial_conf_file_content = """# Config.txt
# Select the FSW operation mode
# Currently supports PAYLOAD, CONTAINER, ROCKET
SELECTED=NONE
# SELECTED=PAYLOAD
# SELECTED=CONTAINER
# SELECTED=ROCKET"""

    with open(config_file_path, 'w') as file:
        file.write(initial_conf_file_content)

    raise FileNotFoundError(f"Required configuration file not found: {config_file_path}")

else:
    with open(config_file_path, 'r') as file:
        lines = file.readlines()

    config_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
    for config_line in config_lines:
        config_line = config_line.strip().replace(" ", "").replace("\t", "")
        if config_line == "SELECTED=NONE":
            FSW_CONF = CONF_NONE
            print("#################################################################\n\n NONE SELECTED \n\n#################################################################")
            break
        elif config_line == "SELECTED=PAYLOAD":
            print("#################################################################\n\n PAYLOAD SELECTED \n\n#################################################################")
            FSW_CONF = CONF_PAYLOAD
            break
        elif config_line == "SELECTED=CONTAINER":
            print("#################################################################\n\n CONTAINER SELECTED \n\n#################################################################")
            FSW_CONF = CONF_CONTAINER
            break
        elif config_line == "SELECTED=ROCKET":
            print("#################################################################\n\n ROCKET SELECTED \n\n#################################################################")
            FSW_CONF = CONF_ROCKET
            break
