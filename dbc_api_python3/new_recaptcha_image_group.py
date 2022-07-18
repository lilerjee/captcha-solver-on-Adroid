import deathbycaptcha

# Put your DBC account username and password here.
username = "jrbp1972"
password = "Password001"
# you can use authtoken instead of user/password combination
# activate and get the authtoken from DBC users panel
authtoken = ""
captcha_file = "test2.jpg"  # image
banner = "banner.jpg"  # image banner
banner_text = "select all pizza:"  # banner text

# client = deathbycaptcha.SocketClient(username, password, authtoken)
#to use http client use:
client = deathbycaptcha.HttpClient(username, password, authtoken)


try:
    balance = client.get_balance()
    print(balance)

    # Put your CAPTCHA file name or file-like object, and optional
    # solving timeout (in seconds) here:
    captcha = client.decode(
        captcha_file, type=3, banner=banner, banner_text=banner_text)
    #you can supply optional `grid` argument to decode() call, with a
    #string like 3x3 or 2x4, defining what grid individual images were located at
    #example:
    #captcha = client.decode(
    #    captcha_file, type=3, banner=banner, banner_text=banner_text, grid="2x4")
    #see 2x4.png example image to have an idea what that images look like
    #If you wont supply `grid` argument, dbc will attempt to autodetect the grid

    if captcha:
        # The CAPTCHA was solved; captcha["captcha"] item holds its
        # numeric ID, and captcha["text"] is a json-like list of the index for each image that should be clicked.
        print ("CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"]))

        if '':  # check if the CAPTCHA was incorrectly solved
            client.report(captcha["captcha"])
except deathbycaptcha.AccessDeniedException:
    # Access to DBC API denied, check your credentials and/or balance
    print ("error: Access to DBC API denied, check your credentials and/or balance")
