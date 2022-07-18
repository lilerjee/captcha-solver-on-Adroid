简介
====

这是个运行在Android平台上的用来解析CAPTCHA人机识别系统(reCAPTCHA/funCAPTCHA)的客户端软件,
这个客户端使用了其他网站提供的CAPTCHA人机识别系统服务(例如Deathbycaptcha, 2captcha).

这个客户端是从我创建的Twitter自动化机器人系统里面提取出来的，没有测试这个提取出来的结果，
但是我可以保证这个客户端可以解析两种不同的CAPTCHA人机识别系统：reCAPTCHA和funCAPTCHA.

你可以基于这个客户端来创建其他类型的CAPTCHA人机系统解析方案客户端.

原因
====

为什么创建运行Android平台上的用来解析CAPTCHA人机识别系统的客户端呢？

CAPTCHA人机识别系统服务提供者一般提供了用户友好的基于浏览器的客户端及其相关API，
但是基本上没有提供用户友好的基于Android的客户端，仅仅提供了相关的API，用户不得不自己
创建可以直接使用的用户友好的基于相关API的客户端。

所以为了解析在Android上面的CAPTCHA人机识别系统, 我创建了用户友好的基于相关API的客户端。

原理
====

这个客户端把CAPTCHA图片截图下来，然后把这个截图缩小以满足CAPTCHA服务提供者的大小限制，
然后通过API把这个缩小的截图发送到CAPTCHA服务器。获取到服务器返回的结果(正确图片的坐标)后，
客户端就会从原始的坐标计算正确的坐标, 然后点击正确的CAPTCHA图片。

这个客户端包含两层，第一层是CAPTCHA人机识别系统解析服务提供者的API客户端，例如 ``DeathByCaptchaUI``,
用来与解析服务器进行通信与获取解析后的结果；第二层是CAPTCHA人机识别系统的解析API客户端，例如
``FuncaptchaAndroidUI``, 用来针对具体的CAPTCHA处理特定的解析逻辑。

用法
====

#. 安装依赖及CAPTCHA服务提供者提供的客户端::

     pip install -r requirements.txt

   如果你想用Deathbycaptcha提供的CAPTCHA解析服务，请按照下面去做：

     - 下载 `Death By Captcha API`__, 解压缩然后放到项目根目录下面（实际上已经存在于这个库里面了）

    __ https://static.deathbycaptcha.com/files/dbc_api_v4_6_3_python3.zip

#. 在CAPTCHA服务提供者的页面上创建自己的用户名与密码，然后在文件 ``verify.py`` 里面修改它们
   (包括图片大小限制)::

      class TwoCaptchaAPI:
          image_restrict_size = 1024 * 100  # 100KB

          TWOCAPTCHA_API_KEY = '<your 2captcha api key>'


      class DeathByCaptchaUI:
          image_restrict_size = 1024 * 180    # 180KB

          DBC_USERNAME = '<your dbc username>'
          DBC_PASSWORD = '<your dbc password>'

#. 创建或者选择CAPTCHA的 ``resolver`` (CAPTCHA解析服务提供者的API)
   (在脚本里面已经存在了两个resolver: ``DeathByCaptchaUI``, and ``TwoCaptchaAPI``)::

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

#. 有可能需要调整一些元素的定位器(locator)与一些CAPTCHA解析算法

   刚开始创建这个客户端是为了解析出现在Twitter里面的CAPTCHA人机识别系统, 所以有可能一些元素的定位器
   与页面结构不一样，如果这个客户端不能工作，请根据特定的页面结构调整它们。

   例如::

     class FuncaptchaAndroidUI(CaptchaAndroidBaseUI):
      """User interface level API for resolving FunCaptcha on android"""
      # step1
      verify_first_page_frame_xpath = (
              '//android.view.View[@resource-id="FunCaptcha"]')

      verify_heading_xpath = (
              '//android.view.View[@resource-id="home_children_heading"]')

#. 用下面的代码集成这个客户端到你的脚本里面::

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

许可证
======

MIT License
