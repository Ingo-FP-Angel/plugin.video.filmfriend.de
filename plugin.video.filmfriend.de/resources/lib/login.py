# -*- coding: utf-8 -*-
import http.cookiejar as cookielib
import json
import re
import urllib.parse

import requests
import resources.lib.external.libmediathek4utils as lm4utils
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')

base = 'https://api.tenant-group.frontend.vod.filmwerte.de/v7/'
providerBase = 'https://api.tenant.frontend.vod.filmwerte.de/v11/'

def pick():
    j = requests.get(f'{base}fba2f8b5-6a3a-4da3-b555-21613a88d3ef/sign-in').json()
    l = []
    for item in j['tenants']:
        l.append(xbmcgui.ListItem(f'{item["displayCategory"]} - {item["displayName"]}'))
    i = xbmcgui.Dialog().select(lm4utils.getTranslation(30010), l)

    domain = j['tenants'][int(i)]['clients']['web']['domain']
    tenant = j['tenants'][int(i)]['id']
    library = j['tenants'][int(i)]['displayName']

    r = requests.get(f'{providerBase}{tenant}/sign-in')
    if r.text == '':
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return

    j = r.json()

    ### TODO proper translations
    if len(j['external']) > 0:
        ret = xbmcgui.Dialog().yesno(
            'Einwilligung zur Datenübermittlung',
            'Mit dem Login akzeptieren Sie die Datenübermittlung wie beim Login per Browser, i.d.R. Ihre Altersfreigabe',
            'Abbrechen',
            'Zustimmen'
        )
        if not ret:
            return
        providerType = 'external'
    else:
        providerType = 'delegated'

    username = xbmcgui.Dialog().input(lm4utils.getTranslation(30500))
    if username == '':
        lm4utils.displayMsg(lm4utils.getTranslation(30501), lm4utils.getTranslation(30502))
        return

    password = xbmcgui.Dialog().input(lm4utils.getTranslation(30503))
    if password == '':
        lm4utils.displayMsg(lm4utils.getTranslation(30504), lm4utils.getTranslation(30505))
        return

    provider = j[providerType][0]['provider']
    client_id = f'tenant-{tenant}-filmwerte-vod-frontend'

    if provider == 'delegated':
        files = {'client_id': (None, client_id), 'provider': (None, provider), 'username': (None, username),
                 'password': (None, password), 'scope': (None, 'filmwerte-vod-api offline_access')}
        j = requests.post('https://api.vod.filmwerte.de/connect/authorize-external', files=files).json()
        if 'error' in j:
            if j['error'] == 'InvalidCredentials':
                lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
            else:
                lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
            return
    else:
        cookieJar = cookielib.LWPCookieJar()
        authExternalUrl = f'https://api.vod.filmwerte.de/connect/authorize-external?clientId=tenant-{tenant}-filmwerte-vod-frontend&provider={provider}&redirectUri=https://{domain}/de/sign-in/completed'
        headers = {
            'Accept-Language': 'de, en;q=0.8, *;q=0.5'
        }
        lm4utils.log(f'[{__addonid__}] authorize-external GET: {authExternalUrl}')
        response = requests.get(authExternalUrl, headers=headers, cookies=cookieJar)
        for respCookie in response.cookies:
            cookieJar.set_cookie(respCookie)
        lm4utils.log(f'[{__addonid__}] authorize-external status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] authorize-external headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] authorize-external body: {response.text}')

        index = response.history[0].headers['Location'].index('?')
        baseUrl = response.history[0].headers['Location'][0:index]  # e.g. https://www.voebb.de/oidcp/authorize
        baseUrl = baseUrl.replace('/oidcp/authorize', '')

        usernameEncoded = urllib.parse.quote_plus(username)
        passwordEncoded = urllib.parse.quote_plus(password)
        formdata = f'L%23AUSW={usernameEncoded}&LPASSW={passwordEncoded}&LLOGIN=Anmelden'
        logincheckUrl = baseUrl + '/oidcp/logincheck'
        headers = {
            'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Origin':                    baseUrl,
            'Referer':                   baseUrl + '/oidcp/authorize',
            "Content-Type":              'application/x-www-form-urlencoded',
            "Accept":                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language':           'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] user/pass submit POST: {logincheckUrl}')
        response = requests.post(logincheckUrl, headers=headers, data=formdata, cookies=cookieJar)
        for respCookie in response.cookies:
            cookieJar.set_cookie(respCookie)
        lm4utils.log(f'[{__addonid__}] user/pass submit status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] user/pass submit headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] user/pass submit body: {response.text}')

        ### TODO check for "Ausweisnummer unbekannt" or "Das angegebene Passwort ist falsch" for nice user info
        ### TODO finally stop if page after user/pass submission still contains e.g. the LPASSW form field
        ### TODO Error message is in <div class="hinweis fehler">...</div>

        formdata = 'CLOGIN=Zustimmen+und+fortfahren'
        consentUrl = baseUrl + '/oidcp/consent'
        headers = {
            'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Origin':                    baseUrl,
            'Referer':                   logincheckUrl,
            "Content-Type":              'application/x-www-form-urlencoded',
            "Accept":                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language':           'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] consent submit POST: {consentUrl}')
        lm4utils.log(f'[{__addonid__}] consent submit formdata: {formdata}')
        response = requests.post(consentUrl, headers=headers, data=formdata, cookies=cookieJar, allow_redirects=False)
        for respCookie in response.cookies:
            cookieJar.set_cookie(respCookie)
        lm4utils.log(f'[{__addonid__}] consent submit status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] consent submit headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] consent submit body: {response.text}')

        # should be https://api.vod.filmwerte.de/authorize/callback-{provider id}?code={some auth code}
        firstRedirectUrl = response.headers['Location']
        headers = {
            'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Referer':                   logincheckUrl,
            "Accept":                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language':           'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] first redirect GET: {firstRedirectUrl}')
        response = requests.get(firstRedirectUrl, headers=headers, cookies=cookieJar, allow_redirects=False)
        for respCookie in response.cookies:
            cookieJar.set_cookie(respCookie)
        lm4utils.log(f'[{__addonid__}] first redirect status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] first redirect headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] first redirect body: {response.text}')

        # should be https://api.vod.filmwerte.de/connect/authorize-callback
        ### TODO check that it does not contain '?errorEvent=aborted' (or maybe just let it run into an exception?)
        ### TODO don't know why we always get the aborted error...
        secondRedirectUrl = response.headers['Location']
        if not secondRedirectUrl.startswith("https://"):
            secondRedirectUrl = 'https://api.vod.filmwerte.de' + secondRedirectUrl
        headers = {
            'User-Agent':                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Upgrade-Insecure-Requests': '1',
            'Referer':                   logincheckUrl,
            "Accept":                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language':           'de, en;q=0.8, *;q=0.5',
        }
        lm4utils.log(f'[{__addonid__}] second redirect GET: {secondRedirectUrl}')
        response = requests.get(secondRedirectUrl, headers=headers, cookies=cookieJar, allow_redirects=False)
        for respCookie in response.cookies:
            cookieJar.set_cookie(respCookie)
        lm4utils.log(f'[{__addonid__}] second redirect status: {response.status_code}')
        lm4utils.log(f'[{__addonid__}] second redirect headers: {response.headers}')
        lm4utils.log(f'[{__addonid__}] second redirect body: {response.text}')

        # should be https://{domain}/de/sign-in/completed#{token information exchanged from auth code}
        # no need to follow, just parse the URL fragments
        thirdRedirectUrl = response.headers["Location"]
        lm4utils.log(f'[{__addonid__}] third redirect GET: {thirdRedirectUrl}')
        parsedToken = re.search(r".*access_token=(.*)&token_type=(.*)&expires_in=(.*)&refresh_token=(.*)", thirdRedirectUrl)
        j = {
            "access_token": parsedToken.groups(1),
            "token_type": parsedToken.groups(2),
            "expires_in": parsedToken.groups(3),
            "refresh_token": parsedToken.groups(4),
        }
        lm4utils.log(f'[{__addonid__}] parsed token information: {json.dumps(j)}')

        return j

    lm4utils.setSetting('domain', domain)
    lm4utils.setSetting('tenant', tenant)
    lm4utils.setSetting('library', library)
    lm4utils.setSetting('username', username)
    lm4utils.setSetting('access_token', j['access_token'])
    lm4utils.setSetting('refresh_token', j['refresh_token'])
