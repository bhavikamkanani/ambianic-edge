"""Test configuration functions."""
import logging
import logging.handlers
import os
from time import sleep
import ambianic
from ambianic.server import AmbianicServer
from ambianic.config_mgm import fileutils
from ambianic import server, config_manager, logger
import yaml
import pytest

log = logging.getLogger(__name__)


class Watch:
    """Utililty to watch for changes"""

    def __init__(self):
        self.changed = False
        self.config = None

    def on_change(self, config):
        log.info("NEW CONF CALLBACK: %s", config)
        self.changed = True
        self.config = config


def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    config_manager.stop()


def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
     method."""
    config_manager.stop()


def test_get_workdir_env():
    os.environ['AMBIANIC_DIR'] = "/foo"
    assert ambianic.get_work_dir() == "/foo"
    os.environ['AMBIANIC_DIR'] = ""
    assert ambianic.get_work_dir() == ambianic.DEFAULT_WORK_DIR


def test_no_config():
    conf = server._configure('/')
    assert not conf


def test_log_config_with_file():
    _dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(_dir, '.__test-log.txt')
    log_config = {
        'file': log_path,
    }
    logger.configure(config=log_config)
    handlers = logging.getLogger().handlers
    log_fn = None
    for h in handlers:
        if isinstance(h, logging.handlers.RotatingFileHandler):
            log_fn = h.baseFilename
            assert log_fn == log_config['file']
    # at least one log file name should be configured
    assert log_fn


def test_log_config_without_file():
    log_config = {
    }
    logger.configure(config=log_config)
    handlers = logging.getLogger().handlers
    for h in handlers:
        assert not isinstance(h, logging.handlers.RotatingFileHandler)


def test_log_config_with_debug_level():
    log_config = {
        'level': 'DEBUG'
    }
    logger.configure(config=log_config)
    root_logger = logging.getLogger()
    effective_level = root_logger.getEffectiveLevel()
    lname = logging.getLevelName(effective_level)
    assert lname == log_config['level']


def test_log_config_with_warning_level():
    log_config = {
        'level': 'WARNING'
    }
    logger.configure(config=log_config)
    root_logger = logging.getLogger()
    effective_level = root_logger.getEffectiveLevel()
    lname = logging.getLevelName(effective_level)
    assert lname == log_config['level']


def test_log_config_without_level():
    log_config = {}
    logger.configure(config=log_config)
    root_logger = logging.getLogger()
    effective_level = root_logger.getEffectiveLevel()
    assert effective_level == logger.DEFAULT_FILE_LOG_LEVEL


def test_log_config_bad_level1():
    log_config = {
        'level': '_COOCOO_'
    }
    logger.configure(config=log_config)
    root_logger = logging.getLogger()
    effective_level = root_logger.getEffectiveLevel()
    assert effective_level == logger.DEFAULT_FILE_LOG_LEVEL


def test_log_config_bad_level2():
    log_config = {
        'level': 2.56
    }
    logger.configure(config=log_config)
    root_logger = logging.getLogger()
    effective_level = root_logger.getEffectiveLevel()
    assert effective_level == logger.DEFAULT_FILE_LOG_LEVEL


def test_config_with_secrets():
    config_manager.SECRETS_FILE = 'test-config-secrets.yaml'
    config_manager.CONFIG_FILE = 'test-config.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    conf = server._configure(_dir)
    assert conf is not None
    assert conf['logging']['level'] == 'DEBUG'
    assert conf['sources']['front_door_camera']['uri'] == 'secret_uri'


def test_config_without_secrets_failed_ref():
    config_manager.SECRETS_FILE = '__no__secrets__.lmay__'
    config_manager.CONFIG_FILE = 'test-config.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    conf = server._configure(_dir)
    assert not conf


def test_config_without_secrets_no_ref():
    config_manager.SECRETS_FILE = '__no__secrets__.lmay__'
    config_manager.CONFIG_FILE = 'test-config2.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    conf = server._configure(_dir)
    assert conf is not None
    assert conf['logging']['level'] == 'DEBUG'
    assert conf['sources']['front_door_camera']['uri'] == 'no_secret_uri'


def test_no_pipelines():
    config_manager.CONFIG_FILE = 'test-config-no-pipelines.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    conf = server._configure(_dir)
    assert not conf


def test_reload():

    config_manager.CONFIG_FILE = 'test-config.1.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    config1 = {"logging": {"level": "INFO"}}
    config_file = os.path.join(_dir, config_manager.CONFIG_FILE)

    # write 1
    fileutils.save(config_file, config1)

    loaded_config = config_manager.load(_dir)

    assert config1["logging"]["level"] == loaded_config["logging"]["level"]

    watcher = Watch()

    config_manager.register_handler(watcher.on_change)

    # write 2
    config2 = {"logging": {"level": "WARN"}}
    fileutils.save(config_file, config2)

    # wait for polling to happen
    wait = 5
    while not watcher.changed:
        sleep(1)
        wait -= 1
        if wait == 0:
            raise Exception("Failed to detect change")

    assert loaded_config["logging"]["level"] == watcher.config[
        "logging"]["level"]
    assert loaded_config["logging"]["level"] == config2["logging"]["level"]


def test_callback():

    config_manager.CONFIG_FILE = 'test-config.2.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    config1 = {"test": True}
    config_file = os.path.join(_dir, config_manager.CONFIG_FILE)

    fileutils.save(config_file, config1)
    config_manager.load(_dir)

    watcher = Watch()

    config_manager.register_handler(watcher.on_change)
    fileutils.save(config_file, config1)

    # wait for polling to happen
    wait = 3
    while not watcher.changed:
        sleep(.5)
        wait -= 1
        if wait == 0:
            raise Exception("Failed to detect change")

    assert watcher.changed


def test_config_getters():

    config_manager.stop()
    config_manager.CONFIG_FILE = 'test-config2.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    config_manager.load(_dir)

    assert config_manager.get_ai_models() is not None
    assert config_manager.get_ai_model("image_detection") is not None

    assert config_manager.get_sources() is not None
    assert config_manager.get_source("front_door_camera") is not None

    assert config_manager.get_data_dir() is not None


def test_handlers_mgm():

    def test1(config):
        pass

    # reset state
    config_manager.stop()
    assert len(config_manager.handlers) == 0

    config_manager.register_handler(test1)
    assert len(config_manager.handlers) == 1

    config_manager.unregister_handler(test1)
    assert len(config_manager.handlers) == 0


def test_clean_stop():
    config_manager.CONFIG_FILE = 'test-config.yaml'
    _dir = os.path.dirname(os.path.abspath(__file__))
    config_manager.load(_dir)
    config_manager.stop()
    assert config_manager.watch_thread is None
