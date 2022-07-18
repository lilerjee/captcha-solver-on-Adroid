`中文文档 <./README.cn.rst>`_

Introduction
============

This is the CAPTCHA(reCAPTCHA/funCAPTCHA) solving client on Android, which uses the CAPTCHA solving
services provided by other websites(e.g. Deathbycaptcha, 2captcha).

The client is extracted from the Twitter robot system created by me, and I don't test the extracted
result, but I make sure the client can solve the two different CAPTCHAs: reCAPTCHA, and funCAPTCHA.

You can create other CAPTCHA solving clients based on the client.

Reason
======

Why did I create the CAPTCHA solving client on Android?

The CAPTCHA solving service providers supply user-friendly browser-based client and the relevant
APIs, but cannot provide user-friendly android-based client, just the relevant APIs. The users have
to create the user-friendly client using the relevant APIs which can be used directly.

So in order to solve the CAPTCHA problem on Android, I create the user-friendly client using the
relevant APIs.

Rationale
=========

The client captures the image of CAPTCHA, then reduced the size of the image in order to meet the
restriction of CAPTCHA server, and sends the reduced size image to the CAPTCHA server using its API.
Since getting the result (the coordinates of right images) from the CAPTCHA server, the client
calculate the right coordinates from the original ones, then click the right images.

This client consists of two layers, and the first is the CAPTCHA service provider API client,
e.g. ``DeathByCaptchaUI``, which is used to communicate with the CAPTCHA server and get the solving
result from the server; the second is the CAPTCHA solving API client on Android,
e.g. ``FuncaptchaAndroidUI``, which is used to deal with the particular logic of solving specific
CAPTCHA on Android.

Usage
=====

#. Install the dependencies and CAPTCHA client provided by CAPTCHA solving services::

     pip install -r requirements.txt

   If you want to use the CAPTCHA service by Deathbycaptcha, please do the following:

   - Download `Death By Captcha API`__, then unzip and put it into the root directory
     of the project. (This folder has existed in repository)

   __ https://static.deathbycaptcha.com/files/dbc_api_v4_6_3_python3.zip

#. Create your username and password on webpage of CAPTCHA solving services,
   and modify them(including image size restriction) in script file ``verify.py``::

    class TwoCaptchaAPI:
        image_restrict_size = 1024 * 100  # 100KB

        TWOCAPTCHA_API_KEY = '<your 2captcha api key>'


    class DeathByCaptchaUI:
        image_restrict_size = 1024 * 180    # 180KB

        DBC_USERNAME = '<your dbc username>'
        DBC_PASSWORD = '<your dbc password>'

#. Create or select the ``resolver`` (CAPTCHA service provider API) for CAPTCHA
   (There are two resolver existing in the script: ``DeathByCaptchaUI``, and ``TwoCaptchaAPI``)::

    class CaptchaAndroidBaseUI:
        def __init__(self, driver, resolver=None, wait_timeout=wait_timeout):
            self.driver = driver
            if not resolver:
                self.resolver = DeathByCaptchaUI(timeout=self.client_timeout,
                        client_type=self.client_type)
                # If you want to use 2captcha, uncomment the following and comment the above line
                #  self.resolver = TwoCaptchaAPI()
            else:
                self.resolver = resolver

#. Maybe need to adjust the locators or the algorithm of solving CAPTCHAs.

   The is the client created for CAPTCHAs which appear on Twitter. So maybe the locators of some
   elements are different or the page structures are different, If the client cannot work, please
   adjust them according the specific page structures.

   For example::

     class FuncaptchaAndroidUI(CaptchaAndroidBaseUI):
      """User interface level API for resolving FunCaptcha on android"""
      # step1
      verify_first_page_frame_xpath = (
              '//android.view.View[@resource-id="FunCaptcha"]')

      verify_heading_xpath = (
              '//android.view.View[@resource-id="home_children_heading"]')


#. Integrate the client into your script by using the following code::

    from verify import RecaptchaAndroidUI, FuncaptchaAndroidUI
    from conf import RECAPTCHA_ALL_RETRY_TIMES, FUNCAPTCHA_ALL_RETRY_TIMES

    RECAPTCHA_ALL_RETRY_TIMES = 15  # the number of captcha images to resolve
    FUNCAPTCHA_ALL_RETRY_TIMES = 20  # the number of captcha images to resolve

    # resolve reCAPTCHA
    recaptcha = RecaptchaAndroidUI(self.app_driver)
    if recaptcha.is_captcha_first_page():
        LOGGER.info('Resovling reCAPTCHA')
        if recaptcha.resolve_all_with_coordinates_api(
                all_resolve_retry_times=RECAPTCHA_ALL_RETRY_TIMES):
            LOGGER.info('reCAPTCHA is resolved')
        else:
            LOGGER.info('reCAPTCHA cannot be resolved')

    # resolve FunCaptcha
    funcaptcha = FuncaptchaAndroidUI(self.app_driver)
    if funcaptcha.is_captcha_first_page():
        LOGGER.info('Resovling FunCaptcha')
        if funcaptcha.resolve_all_with_coordinates_api(
                all_resolve_retry_times=RECAPTCHA_ALL_RETRY_TIMES):
            LOGGER.info('FunCaptcha is resolved')
        else:
            LOGGER.info('FunCaptcha cannot be resolved')

License
=======

MIT License
