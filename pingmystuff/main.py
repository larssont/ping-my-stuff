import requests
import yaml
import argparse
from cerberus import Validator
from schema_config import schema

config_file = ""
config = {}


def load_config():
    global config
    with open(config_file) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)


def write_config():
    with open(config_file, "w") as file:
        yaml.dump(config, file)


def validate_conf():
    v = Validator(schema)
    if not v.validate(config):
        raise Exception(v.errors)


def insert_str_vars(str_, str_vars):
    new_str = str_
    for key, value in str_vars.items():
        old = f"{{{{ {key} }}}}"
        new_str = new_str.replace(old, str(value))
    return new_str


def get_args():
    global config_file
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="YAML config file path")
    args = parser.parse_args()
    config_file = args.config


def send_notification(notifier_opt, status, site):
    site_opt = config["sites"][site]
    data = dict.get(notifier_opt, "data")
    if data is None:
        data = {}

    conf_vars = {"name": site, "address": site_opt["address"], "status": status}

    msg = get_status_text(status, config["sites"][site]["consider_up"])
    msg = insert_str_vars(msg, conf_vars)

    data[notifier_opt["messageDataName"]] = msg
    address = notifier_opt["address"]
    requests.post(address, data=data)


def check_notifiers(site, status):
    for notifier_opt in config["notifiers"].values():
        if site in notifier_opt["sites"]:
            send_notification(notifier_opt, status, site)


def get_status(address):
    return requests.get(address).status_code


def get_status_text(status, status_list):
    if status in status_list:
        return config["message"]["up"]
    return config["message"]["down"]


def has_status_changed(site_opt, new_status):
    consider_up = site_opt["consider_up"]
    old_status = site_opt.get("status")

    if new_status != old_status:
        if old_status in consider_up or new_status in consider_up:
            return True

    return False


def run():
    sites = config["sites"]
    for site, site_opt in sites.items():
        new_status = get_status(site_opt["address"])
        if has_status_changed(site_opt, new_status):
            check_notifiers(site, new_status)
            sites[site]["status"] = new_status
            write_config()


def main():
    get_args()
    load_config()
    validate_conf()
    run()


if __name__ == "__main__":
    main()
