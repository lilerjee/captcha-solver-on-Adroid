import deathbycaptcha
import json
# Put your DBC account username and password here.
username = "username"
password = "password"
# you can use authtoken instead of user/password combination
# activate and get the authtoken from DBC users panel
authtoken = "authtoken"

# 162.212.173.198:80:bypass:bypass123
# Put the proxy and reCaptcha token data
Captcha_dict = {
    'proxy': 'http://user:password@127.0.0.1:1234',
    'proxytype': 'HTTP',
    'publickey': '029EF0D3-41DE-03E1-6971-466539B47725',
    'pageurl': 'https://clientdemo.demo.com/demo-page'}

# Create a json string
json_Captcha = json.dumps(Captcha_dict)

# client = deathbycaptcha.SocketClient(username, password, authtoken)
# to use http client client = deathbycaptcha.HttpClient(username, password)
client = deathbycaptcha.HttpClient(username, password, authtoken)

try:
    balance = client.get_balance()
    print(balance)

    # Put your CAPTCHA type and Json payload here:
    captcha = client.decode(type=6, funcaptcha_params=json_Captcha)
    if captcha:
        # The CAPTCHA was solved; captcha["captcha"] item holds its
        # numeric ID, and captcha["text"] item its list of "coordinates".
        print ("CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"]))

        if '':  # check if the CAPTCHA was incorrectly solved
            client.report(captcha["captcha"])
except deathbycaptcha.AccessDeniedException:
    # Access to DBC API denied, check your credentials and/or balance
    print ("error: Access to DBC API denied," +
           "check your credentials and/or balance")
