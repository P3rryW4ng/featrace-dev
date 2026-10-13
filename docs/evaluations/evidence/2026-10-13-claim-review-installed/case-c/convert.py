def getHostUserInfo(device_languages):
    return {"systemLanguages": list(device_languages)}

def getHostUserInfoAll(device_languages):
    return {"systemLanguages": list(device_languages)}

def getUserInfoAll(device_languages):
    return {"systemLanguages": list(device_languages[:1])}
