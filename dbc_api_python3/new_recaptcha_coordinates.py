import deathbycaptcha

 # Put your DBC account username and password here.
username = "noborderz"
password = r"/+eQm@>;Q:Td8?MA"
# you can use authtoken instead of user/password combination
# activate and get the authtoken from DBC users panel
authtoken = ""
captcha_file = 'test_traffic_light.png'  # image
#  captcha_file = 'test_bus.png'  # image
#  captcha_file = 'test_vehicles.png'  # image
captcha_file = './captcha_small.png'  # image
captcha_file = './captcha_puzzle.png'  # image
captcha_file = '../FunCaptcha_small.png'  # image

#  client = deathbycaptcha.SocketClient(username, password)
#to use http client
client = deathbycaptcha.HttpClient(username, password)


try:
    balance = client.get_balance()
    print(balance)

    # Put your CAPTCHA file name or file-like object, and optional
    # solving timeout (in seconds) here:
    captcha = client.decode(captcha_file, type=2, timeout=60)
    if captcha:
        # The CAPTCHA was solved; captcha["captcha"] item holds its
        # numeric ID, and captcha["text"] item its list of "coordinates".
        print ("CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"]))
        #  print(type(captcha["text"]))

        if '':  # check if the CAPTCHA was incorrectly solved
            client.report(captcha["captcha"])
    else:
        print(captcha)
except deathbycaptcha.AccessDeniedException:
    # Access to DBC API denied, check your credentials and/or balance
    print ("error: Access to DBC API denied, check your credentials and/or balance")
