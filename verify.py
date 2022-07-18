import base64
import re
import time
import random
import logging
import twocaptcha

from appium.webdriver.common.touch_action import TouchAction
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from pathlib import Path
from PIL import Image
from io import BytesIO
from dbc_api_python3 import deathbycaptcha
from twocaptcha import TwoCaptcha

from utils import reduce_img_size, random_sleep, get_absolute_path_str
from utils import resize_img, restrict_image_size, get_random_file_name
from utils import _add_suffix_name


LOGGER = logging.getLogger(__name__)
CAPTCHA_IMAGE_DIR = Path(__file__).parent / 'temp'

class CaptchaTooManyRetryException(Exception):
    pass

class CaptchaErrorTooManyRetryException(Exception):
    pass

class TwoCaptchaAPI:
    """
        User interface level API to resolve sorts of captcha using APIs by 2captcha.com

        API url: https://2captcha.com/2captcha-api

        Python client: https://github.com/2captcha/2captcha-python

        - **New Recaptcha API**

          **What's "new reCAPTCHA/noCAPTCHA"?**

          They're new reCAPTCHA challenges that typically require the user to
          identify and click on certain images. They're not to be confused with
          traditional word/number reCAPTCHAs (those have no images).

          Two different types of New Recaptcha API:

          - **Coordinates API**: Provided a screenshot, the API returns a group of
            coordinates to click.
          - **Image Group API**: Provided a group of (base64-encoded) images,
            the API returns the indexes of the images to click.

          **Image upload restrictions.**

          Image file size is limited to less than 100 KB.
          When the image will be encoded in base64, the size should be lower than 120 KB.
          The supported image formats are JPG, PNG, GIF and BMP.
        """

    image_restrict_size = 1024 * 100  # 100KB

    TWOCAPTCHA_API_KEY = '<your 2captcha api key>'

    def __init__(self, api_key=TWOCAPTCHA_API_KEY, timeout=30):
        """
        Two Captcha API
        :param api_key: API Key of 2Captcha
        :param timeout: Time to wait for response
        """
        self.api_key = api_key
        self.client = None
        self.timeout = timeout
        self.client = TwoCaptcha(self.api_key, defaultTimeout=timeout)

    def get_balance(self):
        """
        Returns balance of 2Captcha
        :return: Returns balance of 2Captcha
        """
        balance = self.client.balance()
        LOGGER.info(f'The balance is {balance}')
        return balance

    def report_failure(self, cid, reason=''):
        """
        It reports when captcha solved wrongly
        :param cid: captcha ID
        :param reason: Reason of failure
        """
        if reason:
            LOGGER.debug(f'Report failed resolving for captcha: {cid},'
                    f' because of {reason}')
        else:
            LOGGER.debug(f'Report failed resolving for captcha: {cid}')
        self.client.report(cid, correct=False)

    def report_success(self, cid, reason=''):
        """
        Reports when captcha solved correctly
        :param cid: captcha ID
        :param reason: Reason of success
        """
        if reason:
            LOGGER.debug(f'Report failed resolving for captcha: {cid}, because of {reason}')
        else:
            LOGGER.debug(f'Report failed resolving for captcha: {cid}')
        self.client.report(cid, correct=True)

    def resolve_recaptcha_with_coordinates_api(self, image_file, hint_text):
        """
        Resolve New Recaptcha from the image file using coordinates API.
        :param image_file: It should be file path
        :param hint_text: Hint text to solve captcha
        """
        real_coordinates = []
        try:
            reduce_factor, b64_img = self.get_restricted_encoded_image(image_file)
            LOGGER.info(f'Captcha image reduce factor: {reduce_factor}')
            captcha = self.client.coordinates(b64_img, hintText=hint_text)

            if 'captchaId' in captcha:
                cid = captcha['captchaId']
                code = captcha['code']
                LOGGER.debug(f"CAPTCHA {cid} solved: {code}")
                coordinates = re.findall('x=(\d+),y=(\d+)', code)
                for x, y in coordinates:
                    real_coordinates.append((int(int(x) * reduce_factor),
                        int(int(y) * reduce_factor)))
                LOGGER.info(f'Real coordinates: {real_coordinates}')
                if not real_coordinates:
                    self.report_failure(cid, reason="co-ordinates are not present")
            else:
                LOGGER.debug(f'CAPTCHA: {captcha}')
        except KeyboardInterrupt as e:
            raise e
        except twocaptcha.TimeoutException as e:
            LOGGER.debug(e)
        except Exception as e:
            LOGGER.debug(f'Error: {e} while solving captcha')
            random_sleep(5, 6)
        return real_coordinates

    @staticmethod
    def get_restricted_encoded_image(image_file, reduce_factor=1, reduce_step=0.125,
            max_img_size=100):
        """
        It returns base64 format of Image with image size less than `max_img_size`KB
        :param image_file: Captcha image path
        :param reduce_factor: Currently reduced factor of original captcha image
        :param reduce_step: Reduce step of every time
        :param max_img_size: Max size of image in KB
        """
        image_file = get_absolute_path_str(image_file)
        img = Image.open(image_file)
        buffer = BytesIO()
        img.save(buffer, format='PNG')

        while (buffer.getbuffer().nbytes / 1024) > max_img_size - 1:
            reduce_factor += reduce_step
            width = int(img.width // reduce_factor)
            height = int(img.height // reduce_factor)

            reduced_img = img.resize((width, height))
            buffer.seek(0)
            buffer.truncate(0)
            reduced_img.save(buffer, format='PNG')
        LOGGER.info(f'Image file reduced to {buffer.getbuffer().nbytes / 1024}kB')
        b64_img = base64.b64encode(buffer.getvalue()).decode()
        return reduce_factor, b64_img

class DeathByCaptchaUI:
    """
    User interface level API to resolve sorts of captcha using APIs by deathbycaptcha.com

    API url: https://deathbycaptcha.com/api

    - **New Recaptcha API**

      **What's "new reCAPTCHA/noCAPTCHA"?**

      They're new reCAPTCHA challenges that typically require the user to
      identify and click on certain images. They're not to be confused with
      traditional word/number reCAPTCHAs (those have no images).

      Two different types of New Recaptcha API:

      - **Coordinates API**: Provided a screenshot, the API returns a group of
        coordinates to click.
      - **Image Group API**: Provided a group of (base64-encoded) images,
        the API returns the indexes of the images to click.

      **Image upload restrictions.**

      Image file size is limited to less than 180 KB.
      When the image will be encoded in base64, the size should be lower than 120 KB.
      The supported image formats are JPG, PNG, GIF and BMP. 
    """

    image_restrict_size = 1024 * 180    # 180KB

    DBC_USERNAME = '<your dbc username>'
    DBC_PASSWORD = '<your dbc password>'

    def __init__(self, username=DBC_USERNAME, password=DBC_PASSWORD,
            authtoken=None, timeout=60, client_type='http'):
        self.username = username
        self.password = password
        self.authtoken = authtoken
        self.client = None
        self.timeout = timeout
        self.client_type = client_type

    def get_client(self, client_type='http'):
        client_type = str.lower(client_type)
        if client_type == 'http':
            self.client = deathbycaptcha.HttpClient(self.username, self.password, self.authtoken)
        elif client_type == 'socket':
            self.client = deathbycaptcha.SocketClient(self.username, self.password, self.authtoken)
        else:
            LOGGER.error('Wrong client type, just use "http" or "socket"')

        return self.client

    def get_same_client(self, client_type='http'):
        """Get the same client for all operations"""
        if not self.client:
            return self.get_client(client_type)
        return self.client

    def get_balance(self):
        self.get_client()
        balance = self.client.get_balance()
        LOGGER.info(f'The balance of "{self.username}": {balance}')
        return balance

    def report_failed_resolving(self, cid, reason=''):
        if reason:
            LOGGER.debug(f'Report failed resolving for captcha: {cid}, because of {reason}')
        else:
            LOGGER.debug(f'Report failed resolving for captcha: {cid}')
        self.client.report(cid)

    def resolve_newrecaptcha_with_coordinates_api(self, image_file,
            timeout=None, same_client=True, report_blank_list=False):
        """Resolve New Recaptcha from the image file using coordinates API.

        Coordinates API FAQ:

        What's the Coordinates API URL?
        To use the Coordinates API you will have to send a HTTP POST Request
        to http://api.dbcapi.me/api/captcha


        What are the POST parameters for the Coordinates API?
        These are::

            username: Your DBC account username
            password: Your DBC account password
            captchafile: a Base64 encoded or Multipart file contents with
            a valid New Recaptcha screenshot type=2: Type 2 specifies this is
            a New Recaptcha Coordinates API

        What's the response from the Coordinates API?

            captcha: id of the provided captcha, if the text field is null,
            you will have to pool the url
            http://api.dbcapi.me/api/captcha/captcha_id until it becomes available

            is_correct:(0 or 1) specifying if the captcha was marked as
            incorrect or unreadable

            text: a json-like nested list, with all the coordinates (x, y)
            to click relative to the image, for example::

                [[23.21, 82.11]]

            where the X coordinate is 23.21 and the Y coordinate is 82.11
        """
        # get one client every time or just use the same client for all operations
        if same_client:
            self.get_same_client(client_type=self.client_type)
        else:
            self.get_client(client_type=self.client_type)

        if isinstance(image_file, Path) or isinstance(image_file, str):
            captcha_file = get_absolute_path_str(image_file)
        else:
            captcha_file = image_file

        if timeout is None:
            timeout = self.timeout

        # Put your CAPTCHA file name or file-like object, and optional
        # solving timeout (in seconds) here:
        captcha = self.client.decode(captcha_file, type=2, timeout=timeout)
        if captcha:
            # The CAPTCHA was solved; captcha["captcha"] item holds its
            # numeric ID, and captcha["text"] item its list of "coordinates".
            cid = captcha['captcha']
            coordinates = captcha['text']
            #  LOGGER.debug(f"CAPTCHA: {captcha}")
            LOGGER.debug(f"CAPTCHA {cid} solved: {coordinates}")

            if not coordinates:  # check if the CAPTCHA was incorrectly solved
                self.report_failed_resolving(cid)
                return False
            else:
                # the coordinates list is string
                result = eval(coordinates)

                # if the result is blank list
                if not result and report_blank_list:
                    self.report_failed_resolving(cid,
                            reason='blank list of result')
                return result
        else:
            LOGGER.debug(f'CAPTCHA: {captcha}')
            return None

    def resolve_newrecaptcha_ui_with_coordinates_api(self, image_file,
            reduce_factor=1, reduce_step=0.125, retry_times=2, timeout=None,
            report_blank_list=False):
        """User interface for resolving New Recaptcha using coordinates API

        :return: (coordinates, reduce_factor) or False
        """
        # reduce image's size
        (image_file, last_reduce_factor) = restrict_image_size(image_file,
                reduce_factor, reduce_step, self.image_restrict_size)
        #  if reduce_factor > 1:
        #      #  image_file = reduce_img_size(image_file, reduce_factor)
        #      image_file = resize_img(image_file, reduce_factor)

        times = 0
        while times <= retry_times:
            try:
                LOGGER.info('Resolve captcha with coordinates API')
                coordinates = self.resolve_newrecaptcha_with_coordinates_api(
                        image_file, timeout=timeout,
                        report_blank_list=report_blank_list)
                if coordinates:
                    return (coordinates, last_reduce_factor)
                elif (not report_blank_list) and (coordinates == []):
                    return (coordinates, last_reduce_factor)
                else:
                    times += 1
                    if times <= retry_times:
                        LOGGER.warning('Failed to resolve captcha,'
                                f' then retry: {times}')
                    continue
            except deathbycaptcha.AccessDeniedException as e:
                # Access to DBC API denied, check your credentials and/or balance
                #  LOGGER.info("error: Access to DBC API denied, check your credentials and/or balance")

                LOGGER.error(e)
                # check if the balance is bellow zero
                balance = self.get_balance()
                if balance < 0:
                    LOGGER.error('Balance is bellow zero, balance: {balance}')
                    return False

                times += 1
                if times <= retry_times:
                    LOGGER.debug(f'AccessDeniedException, then retry: {times}')

                #  LOGGER.debug("Now reduce image's size and then retry")
                #  reduce_factor += reduce_step
                #  LOGGER.debug(f'Reduce factor added by {reduce_step}: '
                #          f'{reduce_factor}')
                #  return self.resolve_newrecaptcha_ui_with_coordinates_api(
                #          image_file, reduce_factor, reduce_step, retry_times,
                #          timeout)
            except (OverflowError, RuntimeError) as e:
                #  LOGGER.error(e)
                raise e
            except Exception as e:
                #  LOGGER.exception(e)
                LOGGER.error(e)
                times += 1
                if times <= retry_times:
                    LOGGER.debug(f'Other exception, then retry: {times}')

        return False

class CaptchaAndroidBaseUI:
    """Base user interface level API for resolving Captcha on android"""
    wait_timeout = 5

    captcha_image_path = CAPTCHA_IMAGE_DIR
    captcha_image_file_name_suffix = '_captcha'
    captcha_image_file_extension = 'png'

    #  client_type = 'socket'
    client_type = 'http'
    client_timeout = 30

    def __init__(self, driver, resolver=None, wait_timeout=wait_timeout):
        self.driver = driver
        if not resolver:
            self.resolver = DeathByCaptchaUI(timeout=self.client_timeout,
                    client_type=self.client_type)
            # If you want to use 2captcha, uncomment the following and comment the above line
            #  self.resolver = TwoCaptchaAPI()
        else:
            self.resolver = resolver

        self.wait_obj = WebDriverWait(self.driver, wait_timeout)

    def find_element(self, element, locator, locator_type=By.XPATH, page=None):
        """Waint for an element, then return it or None"""
        try:
            ele = self.wait_obj.until(
                    EC.presence_of_element_located(
                        (locator_type, locator)))
            if page:
                LOGGER.debug(f'Find the element "{element}" in the page "{page}"')
            else:
                LOGGER.debug(f'Find the element: {element}')
            return ele
        except (NoSuchElementException, TimeoutException) as e:
            if page:
                LOGGER.warning(f'Cannot find the element "{element}" in the page "{page}"')
            else:
                LOGGER.warning(f'Cannot find the element: {element}')

    def click_element(self, element, locator, locator_type=By.XPATH):
        """Find an element, then click and return it, or return None"""
        ele = self.find_element(element, locator, locator_type)
        if ele:
            ele.click()
            LOGGER.debug(f'Click the element: {element}')
            return ele

    def find_page(self, page, element, locator, locator_type=By.XPATH):
        """Find en element of a page, then return it or return None"""
        return self.find_element(element, locator, locator_type, page)

    def save_captcha_effect_img(self, captcha_img_locator, captcha_img_locator_type=By.XPATH,
            img_file=None):
        """Save the effective part of captcha image to a file

        This method is virtual for being overridden by the subclass.

        If file name is None, then create it with random name.
        """
        LOGGER.debug('Use the base class method to save effective captcha image')
        return self.save_captcha_img(captcha_img_locator, captcha_img_locator_type, img_file)

    def save_captcha_img(self, captcha_img_locator, captcha_img_locator_type=By.XPATH,
            img_file=None):
        """Save the captcha image into a file.

        If no file, then create the random file.
        """
        if not img_file:
            LOGGER.debug('Get random image file name, and save captcha image to the file')
            img_file_name = get_random_file_name(suffix=self.captcha_image_file_name_suffix)
            img_file = self.captcha_image_path / (
                    f'{img_file_name}.{self.captcha_image_file_extension}')
        img_file_path = get_absolute_path_str(img_file)
        #  LOGGER.debug(f'CAPTCHA image file: {img_file_path}')

        LOGGER.debug(f'captcha image locator: {captcha_img_locator}')
        LOGGER.debug(f'captcha image locator type: {captcha_img_locator_type}')
        captcha_img = self.driver.find_element(by=captcha_img_locator_type,
                value=captcha_img_locator)

        if captcha_img.screenshot(img_file_path):
            LOGGER.debug(f'Saved CAPTCHA image to file: {img_file_path}')
            return img_file_path
        else:
            LOGGER.info(f'Cannot save the captcha image to the file: {img_file_path}')

    def crop_img(self, src_img_file, dest_img_file, box_size):
        #  LOGGER.debug(
        #          f'Crop the image "{src_img_file}" to "{dest_img_file}"')
        LOGGER.debug(f'Crop box size: {box_size}')

        with Image.open(src_img_file) as im:
            im_crop = im.crop(box_size)
            im_crop.save(dest_img_file)

        return True

    def crop_captcha_img_vertically(self, src_img_file, parent_element, from_element, to_element,
            dest_img_file=None, crop_file_suffix='_crop'):
        """Crop captcha image vertically from one element to another element""" 
        # create destination image file if gaving no one
        if not dest_img_file:
            src_img_file_path = get_absolute_path_str(src_img_file)
            dest_img_file = _add_suffix_name(src_img_file_path, suffix=crop_file_suffix)

        parent_size = parent_element.size
        parent_location = parent_element.location
        from_size = from_element.size
        from_location = from_element.location
        to_size = to_element.size
        to_location = to_element.location

        #  LOGGER.debug(f'parent_size: {parent_size},'
        #          f' parent_location: {parent_location}')
        #  LOGGER.debug(f'from_size: {from_size},'
        #          f' from_location: {from_location}')
        #  LOGGER.debug(f'to_size: {to_size},'
        #          f' to_location: {to_location}')
        #
        #  LOGGER.debug(f'parent bounds: {parent_element.get_attribute("bounds")}')
        #  LOGGER.debug(f'from bounds: {from_element.get_attribute("bounds")}')
        #  LOGGER.debug(f'to bounds: {to_element.get_attribute("bounds")}')

        from_left = from_location['x'] - parent_location['x']
        to_left = to_location['x'] - parent_location['x']
        left = min(from_left, to_left)

        from_right = from_left + from_size['width']
        to_right = to_left + to_size['width']
        right = max(from_right, to_right)

        upper = from_location['y'] - parent_location['y']
        lower = to_location['y'] + to_size['height'] - parent_location['y']
        #  lower = upper + from_size['height'] + to_size['height']

        LOGGER.debug(f'Crop captcha image from one element to another')
        if self.crop_img(src_img_file, dest_img_file, (left, upper, right, lower)):
            return dest_img_file

    def resolve_one_with_coordinates_api(self, captcha_img_locator,
            captcha_img_crop_start_locator, reduce_factor=1,
            reduce_step=0.125, retry_times=3, timeout=30,
            report_blank_list=True, captcha_img_locator_type=By.XPATH,
            captcha_img_crop_start_locator_type=By.XPATH,
            img_file=None, tap_interval=2, need_press=False):
        """Resolve one time for one Captcha image

        report_blank_list = True    # FunCaptcha has no skip operation

        If the captcha image is not cropped, then captcha_img_locator is
        the same with captcha_img_crop_start_locator.

        Resolve successfully, return True;
        Resolve unsuccessfully, return False;
        Resolve successfully and no image to click, return None;
        """
        LOGGER.info('Resolve one time for one captcha image')
        # save captcha image
        captcha_img_file = self.save_captcha_effect_img(captcha_img_locator,
                captcha_img_locator_type=captcha_img_locator_type,
                img_file=img_file)

        # get resolving results from the saved captcha image
        LOGGER.debug('Get resolving results from the saved captcha image')
        results = self.resolver.resolve_newrecaptcha_ui_with_coordinates_api(
                captcha_img_file,
                reduce_factor=reduce_factor,
                reduce_step=reduce_step,
                retry_times=retry_times,
                timeout=timeout,
                report_blank_list=report_blank_list)

        if not results:
            LOGGER.debug('Cannot resolve it')
            return False

        coordinates = results[0]
        last_reduce_factor = results[1]

        # No other images to click, just click skip button
        if (coordinates == []) and (not report_blank_list):
            LOGGER.debug('No images to click')
            return None
        
        # find the captcha image element
        LOGGER.info('Find the captcha image coordinates element, and get the location')
        LOGGER.debug(f'captcha_img_crop_start_locator: '
                f'{captcha_img_crop_start_locator} '
                f'captcha_img_crop_start_locator_type: '
                f'{captcha_img_crop_start_locator_type}')
        captcha_img = self.driver.find_element(
                by=captcha_img_crop_start_locator_type,
                value=captcha_img_crop_start_locator)
        form_x = captcha_img.location['x']
        form_y = captcha_img.location['y']
        LOGGER.debug(f'form_x: {form_x}, form_y: {form_y}')

        LOGGER.info('Click the image with the resolving coordinates')
        LOGGER.debug(f'last_reduce_factor: {last_reduce_factor}')
        for x, y in coordinates:
            real_x = int(x * last_reduce_factor) + form_x
            real_y = int(y * last_reduce_factor) + form_y
            LOGGER.debug(f'Image coordinates: ({real_x}, {real_y})')

            action = TouchAction(self.driver)
            if need_press:
                LOGGER.debug('Press the image')
                #  action.long_press(x=real_x, y=real_y).release().perform()
                action.press(x=real_x, y=real_y).release().perform()
            LOGGER.debug('Tap the image')
            action.tap(x=real_x, y=real_y).perform()

            if tap_interval > 0:
                LOGGER.debug(f'Tap interval: {tap_interval}')
                time.sleep(tap_interval)

        return True

class FuncaptchaAndroidUI(CaptchaAndroidBaseUI):
    """User interface level API for resolving FunCaptcha on android"""
    # step1
    verify_first_page_frame_xpath = (
            '//android.view.View[@resource-id="FunCaptcha"]')

    verify_heading_xpath = (
            '//android.view.View[@resource-id="home_children_heading"]')
    verify_body_xpath = (
            '//android.view.View[@resource-id="home_children_body"]')

    verify_button_xpath = (
            '//android.view.View[@resource-id="home_children_button"]')
    verify_button_xpath1 = (
            '//android.widget.Button[@resource-id="home_children_button"]')
    verify_button_xpath2 = (
            '//android.widget.Button[@resource-id="verifyButton"]')
    verify_button_id = 'home_children_button'

    # step2
    #  captcha_form_xpath = (
    #          '//android.view.View[@resource-id="CaptchaFrame"]')
    captcha_form_xpath = (
            '//android.view.View[@resource-id="fc-iframe-wrap"]')

    reload_button_xpath = ('//android.view.View[@resource-id="fc-iframe-wrap"]'
            '/android.view.View/android.view.View/android.view.View[3]'
            '/android.view.View[2]/android.widget.Button[1]')
    reload_button_xpath1 = ('//android.webkit.WebView/android.webkit.WebView'
            '/android.view.View[2]/android.view.View/android.view.View/'
            'android.view.View/android.view.View/android.view.View/'
            'android.view.View/android.view.View[2]/android.view.View/'
            'android.view.View[1]/android.widget.Button')

    captcha_img_form_xpath = (
            '//android.view.View[@resource-id="game_children_wrapper"]')
    captcha_img_form_game_header_xpath = (
            '//android.view.View[@resource-id="game-header"]')
    captcha_img_group_xapth = (
            '//android.view.View[@resource-id="game_children_wrapper"]')

    try_again_button_xpath = (
            '//android.view.View[@resource-id="wrong_children_button"]')

    # step2, except: Working, please wait
    check_loading_xpath = (
            '//android.widget.Image[@resource-id="checking_children_loadingImg"]')

    wait_timeout = 5

    #  captcha_image_path = PRJ_PATH / 'temp'
    captcha_image_file_name_suffix = '_funcaptcha'
    captcha_image_file_extension = 'png'

    def __init__(self, driver, resolver=None, wait_timeout=wait_timeout):
        super().__init__(driver, resolver, wait_timeout)

    def click_verify_button(self):
        ele = self.click_element('verify button by xpath', self.verify_button_xpath)
        if ele:
            return ele

        ele = self.click_element('verify button by xpath1', self.verify_button_xpath1)
        if ele:
            return ele

        ele = self.click_element('verify button by xpath2', self.verify_button_xpath2)
        if ele:
            return ele

    def click_reload_button(self):
        self.click_element('reload button', self.reload_button_xpath)

    def click_tryagain_button(self):
        self.click_element('try again button', self.try_again_button_xpath)

    # check if this is the FunCaptcha regardless of which captcha page
    def is_captcha_page(self):
        return self.find_page('FunCaptcha page', 'FunCaptcha frame',
                self.verify_first_page_frame_xpath)

    # check if this is the FunCaptcha from outside
    def is_captcha_first_page(self):
        if self.driver.find_elements_by_xpath(self.verify_heading_xpath):
            if self.is_captcha_page():
                return True
        return False

    def is_in_captcha_img_page(self):
        return self.find_page('captcha image page by form xpath', 'captcha image form',
                self.captcha_img_form_xpath) or self.find_page(
                        'captcha image page by header xpath',
                        'image form header',
                        self.captcha_img_form_game_header_xpath)

    def is_in_wrong_result_page(self):
        return self.find_page('wrong result page', 'try again button', self.try_again_button_xpath)

    def is_in_verify_button_page(self):
        return self.find_page('start verify page', 'verify button', self.verify_button_xpath)

    def is_in_check_loading_page(self):
        return self.find_page('Check loading page', 'loading image', self.check_loading_xpath)

    def resolve_all_with_coordinates_api(self, click_start=True,
            reduce_factor=1, reduce_step=0.125, retry_times=3, timeout=20,
            report_blank_list=True, img_file=None, tap_interval=2,
            need_press=False, all_resolve_retry_times=15):
        """Resolve all FunCaptcha images in one step"""
        LOGGER.debug(f'All retry times of resolving: {all_resolve_retry_times}')
        if click_start:
            LOGGER.info('Resolve all FunCaptcha images in one step')
            self.click_verify_button()

        img_page_flag = False
        # check if it is in the page of captcha image
        if self.is_in_captcha_img_page():
            img_page_flag = True
            try:
                result = self.resolve_one_with_coordinates_api(
                    captcha_img_locator=self.captcha_img_group_xapth,
                    captcha_img_crop_start_locator=self.captcha_img_group_xapth,
                    reduce_factor=reduce_factor,
                    reduce_step=reduce_step,
                    retry_times=retry_times,
                    timeout=timeout,
                    report_blank_list=report_blank_list,
                    captcha_img_locator_type=By.XPATH,
                    captcha_img_crop_start_locator_type=By.XPATH,
                    img_file=img_file,
                    tap_interval=tap_interval,
                    need_press=need_press
                )

                all_resolve_retry_times -= 1
                if all_resolve_retry_times <= 0:
                    LOGGER.info('Retry times of resolving are zero, now exit it')
                    raise CaptchaTooManyRetryException
                    #  return False
            except Exception as e:
                LOGGER.error(e)
                return False

        if img_page_flag and result is False:
            LOGGER.info('Cannot resolve it, then click reload button,'
                    ' and play the game again')
            self.click_reload_button()  # change captcha image
            return self.resolve_all_with_coordinates_api(click_start=False,
                    all_resolve_retry_times=all_resolve_retry_times)

        # this condition doesn't exist, because it will report blank list
        if img_page_flag and result is None:
            LOGGER.warning('Result of resolving is None')
            self.click_verify_button()
            return self.resolve_all_with_coordinates_api(click_start=False,
                    all_resolve_retry_times=all_resolve_retry_times)

        # if the game is still going, then continue to verify the captcha
        if self.is_in_captcha_img_page():
            LOGGER.debug('The game is still going, then continue to play')
            #  random_sleep(1, 3)  # wait for new image
            return self.resolve_all_with_coordinates_api(click_start=False,
                    all_resolve_retry_times=all_resolve_retry_times)

        # judge the result by the result page
        if self.is_in_wrong_result_page():
            LOGGER.debug('Wrong resolving, then click try again button,'
                    ' and play the game again')
            self.click_tryagain_button()
            return self.resolve_all_with_coordinates_api(click_start=True,
                    all_resolve_retry_times=all_resolve_retry_times)

        # if it is in start verify page, then play it again
        if self.is_in_verify_button_page():
            LOGGER.debug('Wrong somethings happend, then play it again')
            return self.resolve_all_with_coordinates_api(click_start=True,
                    all_resolve_retry_times=all_resolve_retry_times)

        # if it is in checking loading page, then press reload button
        if self.is_in_check_loading_page():
            LOGGER.debug('Checking loading')
            return self.resolve_all_with_coordinates_api(click_start=True,
                    all_resolve_retry_times=all_resolve_retry_times)

        return True

class RecaptchaAndroidUI(CaptchaAndroidBaseUI):
    """User interface level API for resolving reCaptcha on android"""
    # step1
    verify_first_page_frame_xpath = (
            '//android.view.View[@resource-id="recaptcha_element"]')

    verify_heading_xpath = (
            '//android.view.View[@resource-id="home_children_heading"]')
    verify_body_xpath = (
            '//android.view.View[@resource-id="home_children_body"]')

    #  verify_button_xpath = (
    #          '//android.view.View[@resource-id="home_children_button"]')
    not_robot_checkbox_xpath = (
            '//android.widget.CheckBox[@resource-id="recaptcha-anchor"]')

    # step1, except: Cannot contact reCAPTCHA
    not_contact_title_xpath = (
            '//android.widget.TextView[@resource-id="android:id/alertTitle"]')
    not_contact_message_xpath = (
            '//android.widget.TextView[@resource-id="android:id/message"]')
    not_contact_ok_button_xpath = (
            '//android.widget.Button[@resource-id="android:id/button1"]')

    not_contact_frame_id = 'android:id/content'
    not_contact_title_id = 'android:id/alertTitle'
    not_contact_message_id = 'android:id/message'
    not_contact_ok_button_id = 'android:id/button1'

    # step2: select captcha image
    #  captcha_form_xpath = (
    #          '//android.view.View[@resource-id="CaptchaFrame"]')
    captcha_form_xpath = (
            '//android.view.View[@resource-id="rc-imageselect"]')

    # this element is used to determine if there is a sample image
    # If having two elements of the xpath, then there is a sample image,
    # or there is no sample image.
    above_part_two_elements_xpath = (f'{captcha_form_xpath}/'
            'android.view.View[1]/android.view.View/android.view.View')

    sample_img_xpath = (f'{captcha_form_xpath}/android.view.View[1]/'
            'android.view.View/android.view.View[1]/android.view.View')

    instruction_for_one_xpath = (f'{captcha_form_xpath}/android.view.View[1]/'
            'android.view.View/android.view.View')
    instruction_first_for_one_xpath = (f'{instruction_for_one_xpath}'
            '/android.view.View[1]')
    instruction_second_for_one_xpath = (f'{instruction_for_one_xpath}'
            '/android.view.View[2]')
    instruction_third_for_one_xpath = (f'{instruction_for_one_xpath}'
            '/android.view.View[3]')

    instruction_for_two_xpath = (f'{captcha_form_xpath}/android.view.View[1]/'
            'android.view.View/android.view.View[2]')
    instruction_first_for_two_xpath = (f'{instruction_for_two_xpath}'
            '/android.view.View[1]')
    instruction_second_for_two_xpath = (f'{instruction_for_two_xpath}'
            '/android.view.View[2]')
    instruction_third_for_two_xpath = (f'{instruction_for_two_xpath}'
            '/android.view.View[3]')

    captcha_instruction_xpath = f'{captcha_form_xpath}/android.view.View[1]'
    captcha_img_xpath = f'{captcha_form_xpath}/android.view.View[2]'

    captcha_instruction_xpath1 = f'{captcha_form_xpath}/android.view.View[2]'
    captcha_img_xpath1 = f'{captcha_form_xpath}/android.view.View[3]'

    reload_button_xpath = (
            '//android.widget.Button[@resource-id="recaptcha-reload-button"]')
    audio_button_xpath = (
            '//android.widget.Button[@resource-id="recaptcha-audio-button"]')
    verify_button_xpath = (
            '//android.widget.Button[@resource-id="recaptcha-verify-button"]')

    # step except: check new images or try again
    try_again_tips_xpath = check_new_images_tips_xpath = (
            f'{captcha_form_xpath}/android.view.View[3]/android.view.View')

    # step3, continue
    continue_button_xpath = (
            '//android.widget.Button[@resource-id="continue_button"]')
    # tips of CheckBox of 'not a robot': You are verifiedI'm not a robot
    # tips of CheckBox for exception: Verification expired,
    # check the checkbox again for a new challengeI'm not a robot

    wait_timeout = 5
    #  captcha_image_path = PRJ_PATH / 'temp'
    captcha_image_file_name_suffix = '_recaptcha'
    captcha_image_file_extension = 'png'

    def __init__(self, driver, resolver=None, wait_timeout=wait_timeout):
        super().__init__(driver, resolver, wait_timeout)

    def click_not_robot_checkbox(self):
        self.click_element('not robot checkbox', self.not_robot_checkbox_xpath)

    def click_verify_button(self):
        self.click_element('verify button', self.verify_button_xpath)

    def click_reload_button(self):
        self.click_element('reload button', self.reload_button_xpath)

    def click_not_contact_ok_button(self):
        self.click_element('not contact ok button',
                self.not_contact_ok_button_id, By.ID)

    def click_continue_button(self):
        self.click_element('continue button', self.continue_button_xpath)

    def save_captcha_img_from_form(self, img_file):
        return self.save_captcha_img(img_file=img_file,
                captcha_img_locator=self.captcha_form_xpath)

    def save_captcha_img_from_itself(self, img_file):
        return self.save_captcha_img(img_file=img_file,
                captcha_img_locator=self.captcha_img_xpath)

    def save_captcha_effect_img(self, captcha_img_locator, captcha_img_locator_type=By.XPATH,
            img_file=None, dest_img_file=None):
        """Save the effective part of captcha image to a file

        First, save all parts of it to the file img_file,
        then crop the image from the file to another effective image, then save
        it to the file dest_img_file.

        If file name is None, then create it with random name.
        """
        LOGGER.debug('Use subclass method to save effective part of '
                'captcha image via cropping')
        real_src_img_file = self.save_captcha_img(self.captcha_form_xpath, img_file=img_file)

        parent_element = self.driver.find_element_by_xpath(self.captcha_form_xpath)
        from_element = self.driver.find_element_by_xpath(self.captcha_instruction_xpath)

        # different page structure
        if parent_element.size == from_element.size:
            LOGGER.debug('different page structure')
            from_element = self.driver.find_element_by_xpath(self.captcha_instruction_xpath1)
            to_element = self.driver.find_element_by_xpath(self.captcha_img_xpath1)
        else:
            to_element = self.driver.find_element_by_xpath(self.captcha_img_xpath)
        effect_captcha_img_file = self.crop_captcha_img_vertically(
                real_src_img_file, parent_element, from_element, to_element, dest_img_file)
        LOGGER.debug(f'Effect captcha image file: {effect_captcha_img_file}')

        return effect_captcha_img_file

    # check if this is the reCAPTCHA regardless of which captcha page
    def is_captcha_page(self):
        return self.find_page('reCAPTCHA page', 'reCAPTCHA frame',
                self.verify_first_page_frame_xpath)

    # check if this is the reCAPTCHA from outside
    def is_captcha_first_page(self):
        if self.driver.find_elements_by_xpath(self.not_robot_checkbox_xpath):
            if self.is_captcha_page():
                return True
        return False

    def is_in_captcha_page(self):
        return self.find_page('captcha page', 'captcha image form', self.captcha_form_xpath)

    def is_in_captcha_img_page(self):
        return self.find_page('captcha image page', 'captcha verify button',
                self.verify_button_xpath)

    def is_in_not_contact_page(self):
        return self.find_page('not contact page', 'not contact title',
                self.not_contact_title_id, By.ID)

    def is_in_start_verify_page(self):
        return self.find_page('start verify page', 'not robot checkbox',
                self.not_robot_checkbox_xpath)

    def resolve_all_with_coordinates_api(self, click_start=True,
            reduce_factor=2, reduce_step=0.125, retry_times=2, timeout=20,
            report_blank_list=False, img_file=None, tap_interval=4,
            need_press=False, all_resolve_retry_times=15, all_error_retry_times=3):
        """Resolve all reCaptcha images in one step"""
        LOGGER.debug(f'All retry times of resolving: {all_resolve_retry_times}')
        if click_start:
            LOGGER.info('Resolve all reCaptcha images in one step')
            self.click_not_robot_checkbox()

        img_page_flag = False
        # check if it is in the page of captcha image
        if self.is_in_captcha_img_page():
            img_page_flag = True
            try:
                result = self.resolve_one_with_coordinates_api(
                    captcha_img_locator=self.captcha_form_xpath,
                    captcha_img_crop_start_locator=self.captcha_form_xpath,
                    reduce_factor=reduce_factor,
                    reduce_step=reduce_step,
                    retry_times=retry_times,
                    timeout=timeout,
                    report_blank_list=report_blank_list,
                    captcha_img_locator_type=By.XPATH,
                    captcha_img_crop_start_locator_type=By.XPATH,
                    img_file=img_file,
                    tap_interval=tap_interval,
                    need_press=need_press
                )

                all_resolve_retry_times -= 1
                if all_resolve_retry_times <= 0:
                    LOGGER.info('Retry times of resolving are zero, now exit it')
                    raise CaptchaTooManyRetryException
                    #  return False
            except Exception as e:
                LOGGER.error(e)
                return False

        if img_page_flag and result is False:
            LOGGER.info('Cannot resolve it, then click reload button, and play the game again')
            self.click_reload_button()  # change captcha image
            return self.resolve_all_with_coordinates_api(click_start=False,
                    all_resolve_retry_times=all_resolve_retry_times)

        # no other image to click, just click skip button
        # after clicking skip button, then go on to check the page to
        # check if the resolving is successful.
        if img_page_flag and result is None:
            self.click_verify_button()
            # check if there are images to click
            ele = self.find_element('select all matching images', self.check_new_images_tips_xpath)
            if ele:
                tips = ele.text
                LOGGER.debug(f'Select tips: {tips}')
                if 'select all matching' in tips.lower():
                    return self.resolve_all_with_coordinates_api(click_start=False,
                            all_resolve_retry_times=all_resolve_retry_times)

        if img_page_flag and result is True:
            LOGGER.debug('Clicked all matched images, then click verify button')
            self.click_verify_button()

        # if the game is still going, then continue to verify the captcha
        if self.is_in_captcha_img_page():
            LOGGER.debug('The game is still going, then continue to play')
            #  random_sleep(1, 3)
            return self.resolve_all_with_coordinates_api(click_start=False,
                    all_resolve_retry_times=all_resolve_retry_times)

        # if it is in the page of start verify, then click the checkbox of not a robot
        checkbox = self.is_in_start_verify_page()
        if checkbox:
            text = checkbox.text
            LOGGER.debug(f'CheckBox text: {text}')

            if 'expired' in text.lower() or not text:   # No text or expired
                LOGGER.debug('In "not a robot" page, verification expired '
                        'or new verification, then click the checkbox')
                return self.resolve_all_with_coordinates_api(click_start=True,
                        all_resolve_retry_times=all_resolve_retry_times)

            if 'verified' in text.lower():  # You are verified "I'm not a robot"
                self.click_continue_button()
                return True

        # if it is in the page of not contact, then click button OK
        if self.is_in_not_contact_page():
            all_error_retry_times -= 1
            if all_error_retry_times <= 0:
                LOGGER.error('More than all_error_retry_times: {all_error_retry_times}')
                raise CaptchaErrorTooManyRetryException
            LOGGER.debug('In "not contact" page, then click the button OK')
            self.click_not_contact_ok_button()
            return self.resolve_all_with_coordinates_api(click_start=True,
                    all_resolve_retry_times=all_resolve_retry_times,
                    all_error_retry_times=all_error_retry_times-1)

        return False
