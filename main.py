import traceback
import json
import subprocess
from time import sleep

from paho.mqtt import client as mqtt_client
import base
import light_func
from bind_device_status_listener import disconnect_client, init_status_listener_client
from light_func import switch_to_game_before_light, close_light
import device_opreation
import RPi.GPIO as GPIO
from low_power import low_power_loop 

config: dict
client: mqtt_client.Client

def clear_status_topic(_client, userdata, rc):
    print("disconnect..")
    client.publish(base.status_topic, retain=True, qos=1)


def publish_status():
    status_data = json.dumps({
        "alias": config["alias"],
        "bind_uuid": config["bind_uuid"],
        "fps": config["fps"],
        "ip_address": base.get_most_likely_ip(),
    }).encode('utf-8')
    client.publish(base.status_topic, status_data, retain=True, qos=1)


def handle_command(_client, userdata, msg):
    dic = json.loads(msg.payload.decode())
    command = dic["command"]
    if command == "update_config":
        param = dic["param"]
        for key, value in param.items():
            if config[key] == value:
                continue
            config[key] = value
            if key == "bind_uuid" and value:
                disconnect_client()
                init_status_listener_client()
            elif key == "bind_uuid" and not value:
                switch_to_game_before_light()
                disconnect_client()
        base.cover_config_file()
        publish_status()
    elif command == "shutdown":
        close_light()
        subprocess.Popen(["shutdown", "-h", "now"])


def main():
    base.initialize()
    global config
    config = base.config
    
    # 创建推送状态和监听命令的mqtt客户端
    global client
    client = mqtt_client.Client()
    client.on_disconnect = clear_status_topic
    client.will_set(base.status_topic, retain=True, qos=1)
    client.connect('api.localserver.com', 1883)
    client.subscribe(topic=base.cmd_topic, qos=1)
    client.on_message = handle_command
    publish_status()
    client.loop_start()

    init_status_listener_client()

    low_power_loop(client)


if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)

    light_func.initialize()
    device_opreation.initialize()
    switch_to_game_before_light()
    
    while True:
        try:
            main()
        except BaseException as e:
            traceback.print_exc()
            sleep(0.2)

