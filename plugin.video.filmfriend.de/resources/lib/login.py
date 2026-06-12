# -*- coding: utf-8 -*-
import json
import re
import html
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

countries = [
    { "code": "at", "displayName": lm4utils.getTranslation(30032), "libraryListId": "8bd3757f-bb3f-4ffe-9543-3424497ef47d" },
    { "code": "de", "displayName": lm4utils.getTranslation(30033), "libraryListId": "fba2f8b5-6a3a-4da3-b555-21613a88d3ef" },
    { "code": "ch", "displayName": lm4utils.getTranslation(30034), "libraryListId": "b9b657d4-48c4-4827-a257-d1b0b44a278a" },
]


# ==========================================================================
# SWITCH edu-ID / SLSKey (PURA) login helpers (issue #23, e.g. BCU Fribourg)
# ==========================================================================
# edu-ID is a Shibboleth-based OIDC identity provider at login.eduid.ch. Unlike
# the VOEBB-style provider (paths under /oidcp/), the login is a fixed sequence
# of plain HTML form POSTs with no JavaScript, no CSRF token and no PKCE. The
# only state carried between steps is the session cookie plus the
# "execution=e1sN" counter, followed automatically by requests:
#
#   e1s1 local-storage probe -> e1s2 username -> e1s3 password ->
#   e1s4 TOTP (2FA) -> e1s5 auto-submit form -> /connect/callback ->
#   .../sign-in/completed?code=... -> /connect/token (authorization_code)
#
# Because the token response includes a refresh_token under offline_access, the
# TOTP only has to be entered once per login; refreshes are headless afterwards.

def _eduid_hidden_inputs(pageHtml):
    """Return {name: value} for every <input> on the page (value '' if absent).
    Values are HTML-unescaped so entity-encoded fields resolve correctly."""
    fields = {}
    for tag in re.findall(r'<input\b[^>]*>', pageHtml, re.I):
        name = re.search(r'name="([^"]*)"', tag)
        if not name:
            continue
        val = re.search(r'value="([^"]*)"', tag)
        fields[name.group(1)] = (html.unescape(val.group(1)) if val else '')
    return fields


def _eduid_form_action(pageHtml, default):
    """Return the (HTML-unescaped) action of the first <form>, or `default`."""
    m = re.search(r'<form\b[^>]*\baction="([^"]*)"', pageHtml, re.I)
    return html.unescape(m.group(1)) if m else default


def _eduid_form_region(pageHtml):
    """Return the first <form>...</form> block (plus any visible error text) so
    logs show the relevant part of the page rather than the <head>."""
    out = []
    mf = re.search(r'<form\b.*?</form>', pageHtml, re.I | re.S)
    if mf:
        out.append(mf.group(0))
    for m in re.finditer(r'<(div|p|span)[^>]*class="[^"]*(?:error|alert|exception|message|hinweis)[^"]*"[^>]*>(.*?)</\1>',
                         pageHtml, re.I | re.S):
        out.append('ERRBLOCK: ' + re.sub(r'\s+', ' ', m.group(2)).strip())
    return '\n'.join(out)[:1500] if out else '(no form/error block found)'


def _eduid_submit_field(pageHtml, default='_eventId_submit'):
    """edu-ID forms submit via a button named e.g. _eventId_submit or
    _eventId_proceed. Read the real one from the page instead of guessing."""
    m = re.search(r'<button[^>]*\bname="(_eventId_[A-Za-z]+)"', pageHtml, re.I)
    if m:
        return m.group(1)
    m = re.search(r'<input[^>]*\bname="(_eventId_[A-Za-z]+)"', pageHtml, re.I)
    return m.group(1) if m else default


def _signInEduId(session, response, domain, username, password):
    """
    Drive the SWITCH edu-ID / SLSKey (PURA) Shibboleth login to completion.

    `session`  : the requests.Session already used for /connect/authorize
    `response` : the page we landed on after following the authorize redirects
                 (expected to be the first Shibboleth step, execution=e1s1)
    `domain`   : the tenant domain, e.g. 'bcufribourg.filmfriend.ch'
    `username` / `password` : edu-ID credentials already collected by pick()

    Returns the token dict {access_token, token_type, expires_in, refresh_token}
    on success, or None on failure (after showing an error dialog).
    """
    # Match the proven standalone flow exactly: pass only a Referer header per
    # POST and let requests handle Content-Type/encoding. Extra headers (Origin,
    # Sec-Fetch-*, hardcoded Content-Type) are what diverged from the working
    # script, so we drop them.

    # --- e1s1: local-storage probe. Claim success with an empty value so the
    #     IdP proceeds without a real browser. If edu-ID ever tightens this,
    #     the known fallback is to instead post shib_idp_ls_supported=false.
    fields = _eduid_hidden_inputs(response.text)
    for k in list(fields):
        if k.startswith('shib_idp_ls_success'):
            fields[k] = 'true'
    fields.setdefault('_eventId_proceed', '')
    target = urllib.parse.urljoin(response.url, _eduid_form_action(response.text, response.url))
    lm4utils.log(f'[{__addonid__}] edu-ID e1s1 local-storage probe POST: {target}')
    response = session.post(target, headers={'Referer': response.url}, data=fields)
    lm4utils.log(f'[{__addonid__}] edu-ID now on: {response.url} ({response.status_code})')
    lm4utils.log(f'[{__addonid__}] edu-ID after-e1s1 form: {_eduid_form_region(response.text)}')

    if 'e1s2' not in response.url:
        lm4utils.log(f'[{__addonid__}] edu-ID did not reach username step (e1s2)')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return None

    # --- e1s2: username. Post the minimal field set, exactly like the
    #     reference flow (extra scraped hidden fields cause the IdP to reject).
    submitField = _eduid_submit_field(response.text)
    fields = {'j_username': username, submitField: ''}
    lm4utils.log(f'[{__addonid__}] edu-ID e1s2 submit field: {submitField}; fields: {list(fields.keys())}')
    target = urllib.parse.urljoin(response.url, _eduid_form_action(response.text, response.url))
    lm4utils.log(f'[{__addonid__}] edu-ID e1s2 username POST: {target}')
    response = session.post(target, headers={'Referer': response.url}, data=fields)
    lm4utils.log(f'[{__addonid__}] edu-ID now on: {response.url} ({response.status_code})')
    lm4utils.log(f'[{__addonid__}] edu-ID after-username form: {_eduid_form_region(response.text)}')

    if 'e1s3' not in response.url:
        # unknown account / username rejected
        lm4utils.log(f'[{__addonid__}] edu-ID did not reach password step (e1s3)')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
        return None

    # --- e1s3: password. Minimal field set (j_username + j_password + submit),
    #     matching the reference flow. Scraping/echoing extra hidden fields here
    #     makes edu-ID reject the password, so we keep it lean.
    submitField = _eduid_submit_field(response.text)
    fields = {'j_username': username, 'j_password': password, submitField: ''}
    lm4utils.log(f'[{__addonid__}] edu-ID e1s3 submit field: {submitField}; fields: {list(fields.keys())}')
    target = urllib.parse.urljoin(response.url, _eduid_form_action(response.text, response.url))

    # --- DIAGNOSTIC: log runtime + exactly how the password is encoded on the wire ---
    try:
        import requests as _rq, urllib3 as _u3, sys as _sys
        lm4utils.log(f'[{__addonid__}] DIAG python={_sys.version}')
        lm4utils.log(f'[{__addonid__}] DIAG requests={_rq.__version__} urllib3={_u3.__version__}')
    except Exception as _e:
        lm4utils.log(f'[{__addonid__}] DIAG version probe failed: {_e}')
    # password length + per-char ordinals (NOT the password itself) to catch dialog mangling
    lm4utils.log(f'[{__addonid__}] DIAG pw len={len(password)} ords={[ord(ch) for ch in password]}')
    # what requests will actually send as the body, built the same way requests builds it
    try:
        _prepped = _rq.models.PreparedRequest()
        _prepped.prepare_body(data=fields, files=None)
        _body = _prepped.body
        if isinstance(_body, bytes):
            _body = _body.decode('latin-1', 'replace')
        # mask the username local part but keep structure + the encoded password token visible
        lm4utils.log(f'[{__addonid__}] DIAG encoded body len={len(_body)}')
        # log only the j_password segment so we see its encoding
        for _seg in _body.split('&'):
            if _seg.startswith('j_password='):
                lm4utils.log(f'[{__addonid__}] DIAG j_password segment={_seg}')
    except Exception as _e:
        lm4utils.log(f'[{__addonid__}] DIAG body probe failed: {_e}')
    # --- END DIAGNOSTIC ---

    lm4utils.log(f'[{__addonid__}] edu-ID e1s3 password POST: {target}')
    response = session.post(target, headers={'Referer': response.url}, data=fields)
    lm4utils.log(f'[{__addonid__}] edu-ID now on: {response.url} ({response.status_code})')
    lm4utils.log(f'[{__addonid__}] edu-ID after-password form: {_eduid_form_region(response.text)}')

    # edu-ID advances the execution counter even when it re-renders the
    # password form with an error, so the URL alone is not a reliable success
    # signal. Treat a page that still contains a j_password field as a rejected
    # password rather than a reached-OTP state.
    stillPassword = ('name="j_password"' in response.text or "name='j_password'" in response.text)
    hasOtp = ('name="j_otp"' in response.text or "name='j_otp'" in response.text)
    if stillPassword and not hasOtp:
        lm4utils.log(f'[{__addonid__}] edu-ID still on password form after e1s3 - password rejected')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
        return None
    if not hasOtp:
        lm4utils.log(f'[{__addonid__}] edu-ID did not reach a 2FA (j_otp) form after password step')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return None

    # --- e1s4: TOTP / 2FA. Ask only now, so a wrong password never burns a code.
    # TODO: move this prompt string to the language files (suggested id 30520).
    otp = xbmcgui.Dialog().input('SWITCH edu-ID: 6-stelliger Authenticator-Code / Code authentificateur')
    if otp == '':
        return None
    # --- e1s4: OTP. Minimal field set, matching the reference flow.
    lm4utils.log(f'[{__addonid__}] edu-ID e1s4 form region: {_eduid_form_region(response.text)}')
    submitField = _eduid_submit_field(response.text)
    fields = {'j_otp': otp.strip(), submitField: ''}
    lm4utils.log(f'[{__addonid__}] edu-ID e1s4 submit field: {submitField}; fields: {list(fields.keys())}')
    target = urllib.parse.urljoin(response.url, _eduid_form_action(response.text, response.url))
    lm4utils.log(f'[{__addonid__}] edu-ID e1s4 TOTP POST: {target}')
    response = session.post(target, headers={'Referer': response.url}, data=fields)
    lm4utils.log(f'[{__addonid__}] edu-ID now on: {response.url} ({response.status_code})')

    # --- After TOTP: edu-ID returns an auto-submitting form (the browser would
    #     run document.forms[0].submit()). It may be an execution=e1s5
    #     local-storage probe, or a direct self-submitting POST to
    #     /connect/callback carrying the code. Re-post whatever form we get,
    #     a few hops, until a ?code= appears in the URL.
    code = None
    for _ in range(4):
        code = urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query).get('code', [None])[0]
        if code:
            break
        m = re.search(r'<form\b[^>]*\baction="([^"]*)"', response.text, re.I)
        if not m:
            break
        target = urllib.parse.urljoin(response.url, html.unescape(m.group(1)))
        fields = _eduid_hidden_inputs(response.text)
        for k in list(fields):
            if k.startswith('shib_idp_ls_success'):
                fields[k] = 'true'
        fields.setdefault('_eventId_proceed', '')
        lm4utils.log(f'[{__addonid__}] edu-ID auto-submit form POST: {target}')
        response = session.post(target, headers={'Referer': response.url}, data=fields)
        lm4utils.log(f'[{__addonid__}] edu-ID now on: {response.url} ({response.status_code})')

    if not code:
        # no code -> wrong/expired TOTP, or the IdP returned an error page
        lm4utils.log(f'[{__addonid__}] edu-ID no authorization code obtained ({response.status_code})')
        lm4utils.log(f'[{__addonid__}] edu-ID final form region: {_eduid_form_region(response.text)}')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
        return None

    lm4utils.log(f'[{__addonid__}] edu-ID authorization code obtained')

    # --- Token exchange (authorization_code grant, public client, no secret).
    # NOTE: redirect_uri here MUST match the one sent to /connect/authorize.
    tokenData = {
        'client_id': 'filmwerte-vod-frontend',
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': f'https://{domain}/de/sign-in/completed',
    }
    lm4utils.log(f'[{__addonid__}] edu-ID token exchange POST')
    r = session.post('https://api.tenant.frontend.vod.filmwerte.de/connect/token',
                     data=tokenData)
    if r.status_code != 200:
        lm4utils.log(f'[{__addonid__}] edu-ID token exchange failed ({r.status_code}): {r.text[:300]}')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return None

    j = r.json()
    if not j.get('access_token') or not j.get('refresh_token'):
        lm4utils.log(f'[{__addonid__}] edu-ID token response missing tokens: {j}')
        lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
        return None

    lm4utils.log(f'[{__addonid__}] edu-ID login successful')
    return j


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

    if providerType == 'delegated':
        # starting in v1.1.0 we switched from tenant specific client to general UI client
        # previous way stopped working after the Hamburg library switched their system and authentication
        client_id = f'filmwerte-vod-frontend'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            "Content-Type": 'application/x-www-form-urlencoded',
        }
        usernameEncoded = urllib.parse.quote_plus(username)
        passwordEncoded = urllib.parse.quote_plus(password)
        formdata = f'client_id={client_id}&username={usernameEncoded}&password={passwordEncoded}&scope=offline_access&grant_type=password&provider={provider}'

        j = requests.post('https://api.tenant.frontend.vod.filmwerte.de/connect/token', headers=headers, data=formdata).json()
        if 'error' in j:
            if j['error'] == 'InvalidCredentials':
                lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30508))
            elif j['error'] == 'Locked':
                lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30518))
            else:
                lm4utils.displayMsg(lm4utils.getTranslation(30506), lm4utils.getTranslation(30507))
            return
    else:
        session = requests.session()

        # Detect SWITCH edu-ID / SLSKey (PURA) libraries (e.g. BCU Fribourg, issue #23).
        # The general /connect/authorize kickoff redirects edu-ID tenants to
        # login.eduid.ch; VOEBB-style tenants go to a /oidcp/ host instead, so
        # we can branch on where the first redirect lands.
        eduidAuthorizeUrl = (
            'https://api.tenant.frontend.vod.filmwerte.de/connect/authorize'
            '?client_id=filmwerte-vod-frontend&response_type=code'
            '&scope=offline_access'
            f'&provider={provider}&state={tenant}'
            f'&redirect_uri=https://{domain}/de/sign-in/completed'
        )
        lm4utils.log(f'[{__addonid__}] authorize GET: {eduidAuthorizeUrl}')
        probe = session.get(eduidAuthorizeUrl, headers={'Accept-Language': 'de, fr;q=0.8, en;q=0.5'})
        lm4utils.log(f'[{__addonid__}] authorize landed on: {probe.url} ({probe.status_code})')

        if 'eduid.ch' in probe.url or 'execution=e1s' in probe.url:
            # ---- SWITCH edu-ID / SLSKey (PURA) Shibboleth flow ----
            j = _signInEduId(session, probe, domain, username, password)
            if j is None:
                return
        else:
            # ---- existing VOEBB-style /oidcp/ flow (unchanged) ----
            # NOTE: the probe above added one extra GET in the non-edu-ID case,
            # which is harmless; the VOEBB flow re-initiates its own authorize
            # below. The two kickoffs can be unified later if desired.
            # initialize external login, follow redirects to land on username/password page
            authExternalUrl = f'https://api.vod.filmwerte.de/connect/authorize-external?clientId=tenant-{tenant}-filmwerte-vod-frontend&provider={provider}&redirectUri=https://{domain}/de/sign-in/completed'
            headers = {
                'Accept-Language': 'de, en;q=0.8, *;q=0.5'
            }
            lm4utils.log(f'[{__addonid__}] authorize-external GET: {authExternalUrl}')
            response = session.get(authExternalUrl, headers=headers)
            lm4utils.log(f'[{__addonid__}] authorize-external status: {response.status_code}')
            lm4utils.log(f'[{__addonid__}] authorize-external headers: {response.headers}')
            lm4utils.log(f'[{__addonid__}] authorize-external body: {response.text}')

            # we should have been redirected to something like https://www.voebb.de/oidcp/authorize?{some query string}
            index = response.history[0].headers['Location'].index('?')
            baseUrl = response.history[0].headers['Location'][0:index]
            baseUrl = baseUrl.replace('/oidcp/authorize', '')

            # post username and password, will land us on intermediate page to confirm access to age rating
            usernameEncoded = urllib.parse.quote_plus(username)
            passwordEncoded = urllib.parse.quote_plus(password)
            formdata = f'L%23AUSW={usernameEncoded}&LPASSW={passwordEncoded}&LLOGIN=Anmelden'
            logincheckUrl = baseUrl + '/oidcp/logincheck'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Origin': baseUrl,
                'Referer': baseUrl + '/oidcp/authorize',
                "Content-Type": 'application/x-www-form-urlencoded',
                "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'de, en;q=0.8, *;q=0.5',
            }
            lm4utils.log(f'[{__addonid__}] user/pass submit POST: {logincheckUrl}')
            response = session.post(logincheckUrl, headers=headers, data=formdata)
            lm4utils.log(f'[{__addonid__}] user/pass submit status: {response.status_code}')
            lm4utils.log(f'[{__addonid__}] user/pass submit headers: {response.headers}')
            lm4utils.log(f'[{__addonid__}] user/pass submit body: {response.text}')

            ### TODO check for "Ausweisnummer unbekannt" or "Das angegebene Passwort ist falsch" for nice user info
            ### TODO finally stop if page after user/pass submission still contains e.g. the LPASSW form field
            ### TODO Error message is in <div class="hinweis fehler">...</div>

            # post agreement to transfer age rating, not auto following redirects as that would skip over token info
            formdata = 'CLOGIN=Zustimmen+und+fortfahren'
            consentUrl = baseUrl + '/oidcp/consent'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Origin': baseUrl,
                'Referer': logincheckUrl,
                "Content-Type": 'application/x-www-form-urlencoded',
                "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'de, en;q=0.8, *;q=0.5',
            }
            lm4utils.log(f'[{__addonid__}] consent submit POST: {consentUrl}')
            lm4utils.log(f'[{__addonid__}] consent submit formdata: {formdata}')
            response = session.post(consentUrl, headers=headers, data=formdata, allow_redirects=False)
            lm4utils.log(f'[{__addonid__}] consent submit status: {response.status_code}')
            lm4utils.log(f'[{__addonid__}] consent submit headers: {response.headers}')
            lm4utils.log(f'[{__addonid__}] consent submit body: {response.text}')

            # should be https://api.vod.filmwerte.de/authorize/callback-{provider id}?code={some auth code}?state={some state}
            firstRedirectUrl = response.headers['Location']
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Referer': logincheckUrl,
                "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'de, en;q=0.8, *;q=0.5',
            }
            lm4utils.log(f'[{__addonid__}] first redirect GET: {firstRedirectUrl}')
            response = session.get(firstRedirectUrl, headers=headers, allow_redirects=False)
            lm4utils.log(f'[{__addonid__}] first redirect status: {response.status_code}')
            lm4utils.log(f'[{__addonid__}] first redirect headers: {response.headers}')
            lm4utils.log(f'[{__addonid__}] first redirect body: {response.text}')

            # should be https://api.vod.filmwerte.de/connect/authorize-callback
            secondRedirectUrl = response.headers['Location']
            if not secondRedirectUrl.startswith("https://"):
                secondRedirectUrl = 'https://api.vod.filmwerte.de' + secondRedirectUrl
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                'Upgrade-Insecure-Requests': '1',
                'Referer': logincheckUrl,
                "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'de, en;q=0.8, *;q=0.5',
            }
            lm4utils.log(f'[{__addonid__}] second redirect GET: {secondRedirectUrl}')
            response = session.get(secondRedirectUrl, headers=headers, allow_redirects=False)
            lm4utils.log(f'[{__addonid__}] second redirect status: {response.status_code}')
            lm4utils.log(f'[{__addonid__}] second redirect headers: {response.headers}')
            lm4utils.log(f'[{__addonid__}] second redirect body: {response.text}')

            # should be https://{domain}/de/sign-in/completed#{token information exchanged from auth code}
            # no need to follow, just parse the URL fragments
            thirdRedirectUrl = response.headers["Location"]
            lm4utils.log(f'[{__addonid__}] third redirect GET: {thirdRedirectUrl}')
            parsedToken = re.search(r".*access_token=(.*)&token_type=(.*)&expires_in=(.*)&refresh_token=(.*)",
                                    thirdRedirectUrl)
            j = {
                "access_token": parsedToken.group(1),
                "token_type": parsedToken.group(2),
                "expires_in": parsedToken.group(3),
                "refresh_token": parsedToken.group(4),
            }
            lm4utils.log(f'[{__addonid__}] parsed token information: {json.dumps(j)}')

    lm4utils.setSetting('country', country["code"])
    lm4utils.setSetting('domain', domain)
    lm4utils.setSetting('tenant', tenant)
    lm4utils.setSetting('library', library)
    lm4utils.setSetting('username', username)
    lm4utils.setSetting('provider', provider)
    lm4utils.setSetting('provider_type', providerType)
    lm4utils.setSetting('access_token', j['access_token'])
    lm4utils.setSetting('refresh_token', j['refresh_token'])
