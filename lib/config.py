import os

# Config.py, Set the flight software operation mode

CONF_NONE = 0
CONF_PAYLOAD = 1
CONF_CONTAINER = 2  
CONF_ROCKET = 3

FSW_CONF = CONF_PAYLOAD

config_file_path = 'lib/config.txt'

if not os.path.exists(config_file_path):
    print(f"#################################################################\n\nConfig file does not exist: {config_file_path}, Creating default config file...\n\n#################################################################")

    initial_conf_file_content = """# Config.txt
# Select the FSW operation mode
# Currently supports PAYLOAD, CONTAINER, ROCKET
SELECTED=PAYLOAD
# SELECTED=NONE
# SELECTED=CONTAINER
# SELECTED=ROCKET"""

    try:
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        
        with open(config_file_path, 'w') as file:
            file.write(initial_conf_file_content)
        
        print(f"Default config file created: {config_file_path}")
        print("Please review and modify the configuration as needed.")
        
    except Exception as e:
        print(f"Error creating config file: {e}")
        raise FileNotFoundError(f"Failed to create configuration file: {config_file_path}")

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
            print("########################################################################################\n\n"                                                          
                    " ##                         ##                                             ##              \n"
                    " ##       ######   ######   ##        #####   ######   ######   ##  ##   ######   ######  \n"
                    " ######   ##  ##   ##  ##   ######       ##   ##  ##   ##       ##  ##     ##     ##       \n"
                    " ##  ##   ######   ##  ##   ##  ##   ######   ######   ######   ##  ##     ##     ######   \n"
                    " ##  ##   ##       ######   ##  ##   ##  ##   ##           ##   ##  ##     ##         ##   \n"
                    " ##  ##   #####    ##       ##  ##   ######   #####    ######   ######     ####   ######   \n"
                    "                   ##                                                                      \n"
                    "########################################################################################\n")
            FSW_CONF = CONF_PAYLOAD
            break

