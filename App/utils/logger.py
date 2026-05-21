# -*- coding: utf-8 -*-
import logging
import os
import datetime

from functools import lru_cache

import App.core.settings as config

# TODO: responder que es esto?
@lru_cache
def get_settings():
    return config.Settings()

settings = get_settings()

from logging.handlers import RotatingFileHandler


class SingletonType(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class MyLogger(object, metaclass=SingletonType):
    _logger = None

    def __init__(self):
        self._logger = logging.getLogger("crumbs")
        self._logger.setLevel(config.settings.log_level)

        formatter = logging.Formatter('%(asctime)s - [%(levelname)s | %(filename)s:%(lineno)s] > %(message)s')

        now = datetime.datetime.now()
        dirname = config.settings.log_route

        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        fileHandler = RotatingFileHandler(dirname +
                                          now.strftime(str(settings.log_nomenclature)) +
                                          ".log", maxBytes=config.settings.log_file_size,
                                          backupCount=config.settings.log_backup_count
                                          )
        streamHandler = logging.StreamHandler()

        fileHandler.setFormatter(formatter)
        streamHandler.setFormatter(formatter)

        self._logger.addHandler(fileHandler)
        self._logger.addHandler(streamHandler)

    def get_logger(self):
        return self._logger