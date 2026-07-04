# -*- coding: utf-8 -*-
import re
import urllib.parse

import requests
import xbmcaddon
import xbmcgui

import resources.lib.external.libmediathek4utils as lm4utils

### Uncomment the following lines if you want to debug HTTP traffic
#import logging
#from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1
#logging.basicConfig()
#logging.getLogger().setLevel(logging.DEBUG)
#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')

base = 'https://api.tenant-group.frontend.vod.filmwerte.de/v7/'
providerBase = 'https://api.tenant.frontend.vod.filmwerte.de/v11/'
apiBase = 'https://api.tenant.frontend.vod.filmwerte.de'
client = 'filmwerte-vod-frontend'

countries = [
    { "code": "at", "displayName": lm4utils.getTranslation(30032), "libraryListId": "8bd3757f-bb3f-4ffe-9543-3424497ef47d" },
    { "code": "de", "displayName": lm4utils.getTranslation(30033), "libraryListId": "fba2f8b5-6a3a-4da3-b555-21613a88d3ef" },
    { "code": "ch", "displayName": lm4utils.getTranslation(30034), "libraryListId": "b9b657d4-48c4-4827-a257-d1b0b44a278a" },
]

def pick():
    previousCountry = lm4utils.getSetting('country')
    previousLibrary = lm4utils.getSetting('library')
    lm4utils.log(f'[{__addonid__}] previousCountry: {previousCountry}')
    lm4utils.log(f'[{__addonid__}] previousLibrary: {previousLibrary}')
    # this only happens on first use after updating from v1.0.9 or earlier to v1.0.10 or later
    # up to v1.0.9 only Germany was supported and there was no country setting
    # so set country to de if it was empty but a library had already been selected
    if previousCountry == "" and not previousLibrary == "":
        previousCountry = "de"
        lm4utils.log(f'[{__addonid__}] updated empty previousCountry to "de" because library was set')

    c = []
    cidx = -1
    for idx, country in enumerate(countries):
        c.append(xbmcgui.ListItem(country["displayName"]))
        if country["code"] == previousCountry:
            cidx = idx

    lm4utils.log(f'[{__addonid__}] preselect index for country: {cidx}')
    i = xbmcgui.Dialog().select(lm4utils.getTranslation(30031), c, preselect = cidx)
    lm4utils.log(f'[{__addonid__}] selected index for country: {i}')

    if i == -1: # selection was canceled
        return

    country = countries[i]

    # get all supported libraries of the selected country
    j = requests.get(f'{base}{country["libraryListId"]}/sign-in').json()
    l = []
    cidx = -1
    for idx, item in enumerate(j['tenants']):
        l.append(xbmcgui.ListItem(f'{item["displayCategory"]} - {item["displayName"]}'))
        if item["displayName"] == previousLibrary:
            cidx = idx
            
    i = xbmcgui.Dialog().select(lm4utils.getTranslation(30010), l, preselect = cidx)
    lm4utils.log(f'[{__addonid__}] selected index for library: {i}')

    if i == -1: # selection was canceled
        return

    domain = j['tenants'][int(i)]['clients']['web']['domain']
    tenant = j['tenants'][int(i)]['id']
    library = j['tenants'][int(i)]['displayName']
    lm4utils.log(f'[{__addonid__}] selected library: {library}')
    lm4utils.log(f'[{__addonid__}] tenant id of selected library: {tenant}')

    # get information about the possible login providers of the selected library
    r = requests.get(f'{providerBase}{tenant}/sign-in')
    if r.text == '':
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return

    j = r.json()
    lm4utils.log(f'[{__addonid__}] provider info of selected library: {j}')

    # provider types that are supported in order of preference
    supportedProviderTypes = [
        {'type': 'external', 'kind': 'OpenId'},
        {'type': 'delegated', 'kind': None},
        {'type': 'delegated', 'kind': 'Ip'},
    ]

    providerType = None
    providerKind = None
    for pType in supportedProviderTypes:
        matchedProvider = next((pt for pt in j[pType['type']] if pt['providerKind'] == pType['kind']), None)
        if matchedProvider is not None:
            providerType = pType['type']
            providerKind = pType['kind']
            provider = matchedProvider['provider']
            break

    if providerType is None:
        # no supported provider type was found -> show error
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30511))
        return

    if providerKind == 'OpenId':
        # ask for consent to grant access to the age rating during login
        ret = xbmcgui.Dialog().yesno(lm4utils.getTranslation(30514), lm4utils.getTranslation(30515),
                                     lm4utils.getTranslation(30516), lm4utils.getTranslation(30517))
        if not ret:
            return

    lm4utils.log(f'[{__addonid__}] provider type/kind to use for selected library: {providerType}/{providerKind}')

    username = lm4utils.getSetting('username')
    password = lm4utils.getSetting('password')
    if not providerKind == "Ip":
        username = xbmcgui.Dialog().input(lm4utils.getTranslation(30500), defaultt=username)
        if username == '':
            lm4utils.displayMsg(lm4utils.getTranslation(30501), lm4utils.getTranslation(30502))
            return

        password = xbmcgui.Dialog().input(lm4utils.getTranslation(30503), defaultt=password)
        if password == '':
            lm4utils.displayMsg(lm4utils.getTranslation(30504), lm4utils.getTranslation(30505))
            return

    usernameEncoded = urllib.parse.quote_plus(username)
    passwordEncoded = urllib.parse.quote_plus(password)

    if providerType == 'delegated':
        # starting in v1.1.0 we switched from tenant specific client to general UI client
        # previous way stopped working after the Hamburg library switched their system and authentication
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            "Content-Type": 'application/x-www-form-urlencoded',
        }
        formdata = f'client_id={client}&username={usernameEncoded}&password={passwordEncoded}&scope=offline_access&grant_type=password&provider={provider}'

        j = requests.post(f'{apiBase}/connect/token', headers=headers, data=formdata).json()
    else:
        session = requests.session()

        # VISIT API SIGN-IN PAGE
        authExternalUrl = f'{apiBase}/connect/authorize?client_id={client}&response_type=code&scope=offline_access&provider={provider}&redirect_uri=https://{domain}/de/sign-in/completed'
        headers = {
            'Accept-Language': 'de, en;q=0.8, *;q=0.5'
        }
        lm4utils.log(f'[{__addonid__}] authorize-external GET: {authExternalUrl}')
        response = session.get(authExternalUrl, headers=headers)
        loginFormUrl = response.url
        lm4utils.log(f'[{__addonid__}] authorize-external status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] authorize-external headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] authorize-external body: {response.text}')
        lm4utils.log(f'[{__addonid__}] authorize-external redirect to: {loginFormUrl}')

        # LOGIN FORM
        parsedUrl = urllib.parse.urlparse(loginFormUrl)
        baseUrl = f'{parsedUrl.scheme}://{parsedUrl.hostname}'
        loginBaseUrl = f'{baseUrl}{parsedUrl.path}'
        lm4utils.log(f'[{__addonid__}] loginBaseUrl: {loginBaseUrl}')

        # Find form action in <form action="MATCH" ...>
        match = re.search(r'<form[^>]*action="([^"]+)"', response.text)
        if match is None:
            lm4utils.log(f'[{__addonid__}] could not find login form action in response body')
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
            return

        action_value = match.group(1)
        loginSubmitUrl = urllib.parse.urljoin(loginBaseUrl, action_value)

        formdata = f'L%23AUSW={usernameEncoded}&LPASSW={passwordEncoded}&LLOGIN=Anmelden'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Origin': baseUrl,
            'Referer': loginFormUrl,
            "Content-Type": 'application/x-www-form-urlencoded',
            "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] user/pass submit POST: {loginSubmitUrl}')
        response = session.post(loginSubmitUrl, headers=headers, data=formdata)
        lm4utils.log(f'[{__addonid__}] user/pass submit status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] user/pass submit headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] user/pass submit body: {response.text}')

        ### TODO check for "Ausweisnummer unbekannt" or "Das angegebene Passwort ist falsch" for nice user info
        ### TODO finally stop if page after user/pass submission still contains e.g. the LPASSW form field
        ### TODO Error message is in <div class="hinweis fehler">...</div>

        # CONSENT FORM
        consentFormUrl = response.url
        parsedUrl = urllib.parse.urlparse(consentFormUrl)
        consentBaseUrl = f'{parsedUrl.scheme}://{parsedUrl.hostname}{parsedUrl.path}'
        lm4utils.log(f'[{__addonid__}] consentBaseUrl: {consentBaseUrl}')

        # Find form action in <form action="MATCH" ...>
        match = re.search(r'<form[^>]*action="([^"]+)"', response.text)
        if match is None:
            lm4utils.log(f'[{__addonid__}] could not find consent form action in response body')
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
            return

        action_value = match.group(1)
        consentUrl = urllib.parse.urljoin(consentBaseUrl, action_value)

        formdata = 'CLOGIN=Zustimmen+und+fortfahren'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Origin': baseUrl,
            'Referer': loginSubmitUrl,
            "Content-Type": 'application/x-www-form-urlencoded',
            "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] consent POST: {consentUrl}')
        response = session.post(consentUrl, headers=headers, data=formdata)
        lm4utils.log(f'[{__addonid__}] consent status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] consent headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] consent body: {response.text}')

        # GET BEARER TOKENS
        parsedUrl = urllib.parse.urlparse(response.url)
        completedUrl = f'{parsedUrl.scheme}://{parsedUrl.hostname}{parsedUrl.path}'
        completedUrlEncoded = urllib.parse.quote(completedUrl)

        # Extract 'code' from completion url query params
        code = urllib.parse.parse_qs(parsedUrl.query).get('code', [None])[0]
        if code is None:
            lm4utils.log(f'[{__addonid__}] no auth code found in final redirect: {response.url}')
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
            return

        tokenUrl = f'{apiBase}/connect/token'
        formdata = f'client_id={client}&grant_type=authorization_code&code={code}&redirect_uri={completedUrlEncoded}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Origin': baseUrl,
            'Referer': loginFormUrl,
            "Content-Type": 'application/x-www-form-urlencoded',
            "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] token POST: {tokenUrl}')
        response = requests.post(tokenUrl, headers=headers, data=formdata)
        lm4utils.log(f'[{__addonid__}] token status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] token headers: {response.headers}')
        # not logging the response.text here as this would leak the access token
        j = response.json()

    # common handling of the token response
    if 'error' in j:
        if j['error'] == 'InvalidCredentials':
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
        elif j['error'] == 'Locked':
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30518))
        else:
            lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return

    lm4utils.setSetting('country', country["code"])
    lm4utils.setSetting('domain', domain)
    lm4utils.setSetting('tenant', tenant)
    lm4utils.setSetting('library', library)
    lm4utils.setSetting('username', username)
    lm4utils.setSetting('provider', provider)
    lm4utils.setSetting('provider_type', providerType)
    lm4utils.setSetting('access_token', j['access_token'])
    lm4utils.setSetting('refresh_token', j['refresh_token'])
