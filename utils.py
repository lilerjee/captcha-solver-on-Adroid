import logging
import os
import random
import time
import uuid

from pathlib import Path
from PIL import Image


LOGGER = logging.getLogger(__name__)

def random_sleep(min_sleep_time=1, max_sleep_time=5):
    """
    Random sleep
    :param min_sleep_time: Min Sleep time
    :param max_sleep_time: Max Sleeep time
    """
    sleep_time = random.randint(min_sleep_time, max_sleep_time)
    LOGGER.debug(f'Random sleep: {sleep_time}')
    time.sleep(sleep_time)

def get_random_file_name(min_len=10, max_len=20, suffix=''):
    return ''.join(random.choices(uuid.uuid4().hex,
        k=random.randrange(min_len, max_len))) + suffix

def _add_suffix_name(fname, suffix='_small', repeate=False):
    fnames = fname.split('.')
    if len(fnames) == 1:
        if not repeate:
            return fname if fname.endswith(suffix) else (fname + suffix)
        else:
            return fname + suffix

    else:
        if not repeate:
            names = '.'.join(fnames[:-1])
            return fname if names.endswith(suffix) else (
                    names + suffix + '.' + fnames[-1])
        else:
            return '.'.join(fnames[:-1]) + suffix + '.' + fnames[-1]

def resize_img(img_file, reduce_factor=1):
    # reduce the image's size
    img = Image.open(img_file)
    #  LOGGER.debug(f'Original image size: {img.size}')
    #  LOGGER.debug(f'Original file size: {os.path.getsize(img_file)}')
    #  LOGGER.debug(f'Resize factor: {reduce_factor}')

    width = int(img.size[0] / reduce_factor)
    height = int(img.size[1] / reduce_factor)

    if isinstance(img_file, Path):
        img_file_path = str(img_file.absolute())
    else:
        img_file_path = img_file

    small_img_file = _add_suffix_name(img_file_path)

    small_img = img.resize((width, height))
    #  small_img = img.resize(reduce_factor)
    small_img.save(small_img_file)
    #  LOGGER.debug(f'Resized image size: {small_img.size}')
    #  LOGGER.debug(f'Resized file size: {os.path.getsize(small_img_file)}')

    return small_img_file

def restrict_image_size(img_file, reduce_factor, reduce_step, restrict_size):
    """Reduce the image file size to let it be less than restricting size"""
    img_file_size = os.path.getsize(img_file)

    if img_file_size <= restrict_size:
        reduced_img_file = img_file

    times = 0
    while img_file_size > restrict_size:
        reduce_factor += reduce_step
        reduced_img_file = resize_img(img_file, reduce_factor)
        img_file_size = os.path.getsize(reduced_img_file)
        times += 1

    LOGGER.debug(f'Reduced image file: {reduced_img_file}')
    LOGGER.debug(f'After {times} times of reducing, the image file size'
                 f' {img_file_size} is less than {restrict_size}')
    return (reduced_img_file, reduce_factor)

def reduce_img_size(img_file, reduce_factor=1):
    # reduce the image's size
    img = Image.open(img_file)
    LOGGER.info(f'Original image size: {img.size}')
    LOGGER.info(f'Original file size: {os.path.getsize(img_file)}')
    LOGGER.info(f'Reduce factor: {reduce_factor}')

    #  width = int(img.size[0] // reduce_factor)
    #  height = int(img.size[1] // reduce_factor)

    if isinstance(img_file, Path):
        img_file_path = str(img_file.absolute())
    else:
        img_file_path = img_file

    small_img_file = _add_suffix_name(img_file_path)

    #  small_img = img.resize((width, height), Image.ANTIALIAS)
    small_img = img.reduce(reduce_factor)
    small_img.save(small_img_file)
    LOGGER.info(f'Reduced image size: {small_img.size}')
    LOGGER.info(f'Reduced file size: {os.path.getsize(small_img_file)}')

    return small_img_file

def get_absolute_path_str(path):
    if isinstance(path, Path):
        absolute_path = str(path.absolute())
    elif isinstance(path, str):
        absolute_path = os.path.abspath(path)
    else:
        LOGGER.debug(f'Other type of path: {type(path)}')
        absolute_path = path

    #  LOGGER.debug(f'Absolute path: "{absolute_path}" from "{path}"')
    return absolute_path
