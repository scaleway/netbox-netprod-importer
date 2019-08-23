import appdirs
import errno
import logging
import os
import yaml
import urllib3

from netbox_netprod_importer import __appname__


logger = logging.getLogger("virt_backup")

os.environ["XDG_CONFIG_DIRS"] = "/etc"
CONFIG_DIRS = (
    appdirs.user_config_dir(__appname__),
    appdirs.site_config_dir(__appname__),
)
CONFIG_FILENAME = "config.yml"


def get_config(custom_path=None):
    """
    Get config file and load it with yaml
    :returns: loaded config in yaml, as a dict object
    """
    if getattr(get_config, "cache", None):
        return get_config.cache

    if custom_path:
        config_path = custom_path
    elif os.environ.get("CONFIG_PATH"):
        config_path = os.environ["CONFIG_PATH"]
    else:
        for d in CONFIG_DIRS:
            config_path = os.path.join(d, CONFIG_FILENAME)
            if os.path.isfile(config_path):
                break
    try:
        with open(config_path, "r") as config_file:
            conf = yaml.safe_load(config_file)
            get_config.cache = conf
            if conf.get("loglevel", None):
                numeric_level = getattr(logging, conf.get("loglevel").upper())
                if not isinstance(numeric_level, int):
                    raise ValueError('Invalid log level: %s' \
                                     % conf.get("loglevel"))
            else:
                numeric_level = logging.ERROR
            logging.basicConfig(level=numeric_level,
                                format="%(levelname)s: %(name)s: %(message)s"
                                )
            if conf.get("disable_ssl_warnings", False):
                urllib3.disable_warnings()
            return conf
    except FileNotFoundError as e:
        logger.debug(e)
        if custom_path or os.environ.get("CONFIG_PATH"):
            logger.error(
                "Configuration file {} not found.".format(
                    custom_path or os.environ["CONFIG_PATH"]
                )
            )
        else:
            logger.error(
                "No configuration file can be found. Please create a "
                "config.yml in one of these directories:\n"
                "{}".format(", ".join(CONFIG_DIRS))
            )
        raise FileNotFoundError


def load_config(custom_path=None):
    get_config(custom_path)
