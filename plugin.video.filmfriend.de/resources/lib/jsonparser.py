# -*- coding: utf-8 -*-
# import pyjwt as jwt
import time

import requests
import xbmcaddon
import xbmcgui

import resources.lib.external.libmediathek4utils as lm4utils

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')

base = 'https://api.vod.filmwerte.de/api/v1/'

german = {
	'order':'GermanName',

	'synopsis':'germanSynopsis',
	'title':'germanTitle',
	'name':'germanName',
	'teaser':'germanTeaser',
}

english = {
	'order':'EnglishName',

	'synopsis':'englishSynopsis',
	'title':'englishTitle',
	'name':'englishName',
	'teaser':'englishTeaser',
}

french = {
	'order':'FrenchName',

	'synopsis':'frenchSynopsis',
	'title':'frenchTitle',
	'name':'frenchName',
	'teaser':'frenchTeaser',
}

italian = {
	'order':'ItalianName',

	'synopsis':'italianSynopsis',
	'title':'italianTitle',
	'name':'italianName',
	'teaser':'italianTeaser',
}

languages = {
	'en':english,
	'de':german,
	'fr':french,
	'it':italian,
}

langCode = lm4utils.getSetting('language')
if langCode in ['system', '']:
	l = lm4utils.getISO6391()
	if l in languages:
		langCode = l
	else:
		langCode = 'en'

lang = languages[langCode]

def fetchJson(url,headers=None):
	if headers is None:
		headers = {
			'Accept-Language': langCode
		}
	else:
		headers.update({
			'Accept-Language': langCode
		})

	response = requests.get(url,headers=headers)
	if response.status_code == 401:
		xbmcgui.Dialog().ok(__addonname__, lm4utils.getTranslation(30509))
		return
	if response.status_code > 299:
		raise RuntimeError(f"Fetching '{url}' failed with code '{response.status_code}' and optional message '{response.text}'")

	return response.json()

def parseMain():
	j = requests.get(f'{base}tenant-groups/21960588-0518-4dd3-89e5-f25ba5bf5631/navigation').json()

def parseWatchList(params,content='videos'):
	_checkTokenExpired()
	token = lm4utils.getTokenWithErrorNotification()
	if token is None or token == '':
		return _emptyPage(content)

	headers = {
		'Authorization':f'Bearer {token}'
	}

	j = fetchJson(f'https://api.tenant.frontend.vod.filmwerte.de/v11/{lm4utils.getSetting("tenant")}/watchlist{params}',headers)
	return parseResponse(j,content)

def parseSearch(params,content='videos'):
	j = fetchJson(f'{base}/tenant-groups/fba2f8b5-6a3a-4da3-b555-21613a88d3ef/search{params}')
	return parseResponse(j,content)

def parseResponse(responseJson,content='videos'):
	res = _emptyPage(content)
	if responseJson is None or 'results' not in responseJson:
		return res
	for item in responseJson['results']:
		result = item
		if 'result' in item:
			result = item['result']
		else:
			result = item[item['kind'].lower()]
		if item['kind'] == 'Series':
			d = {'type':'tvshow', 'params':{'mode':'listSearch', 'content':'tvshows'}, 'metadata':{'art':{}}}
			d['metadata']['name'] = _getString(result,'title')
			d['metadata']['plot'] = _getString(result,'synopsis')
			d['metadata']['art'] = _getArt(result)

			d['params']['params'] = f'?kinds=Season&series={result["id"]}&orderBy={lang["order"]}&sortDirection=Ascending'
			res['items'].append(d)


		elif item['kind'] == 'Season':
			d = {'type':'season', 'params':{'mode':'listSearch', 'content':'episodes'}, 'metadata':{'art':{},'genres':[]}}
			d['metadata']['name'] = f"{_getString(result['series'],'title')} - Season {str(result['seasonNumber'])}"
			d['metadata']['plot'] = _getString(result,'synopsis')

			d['metadata']['season'] = result['seasonNumber']
			d['metadata']['mpaa'] = result['motionPictureContentRating']
			d['metadata']['art'] = _getArt(result)
			if 'genres' in result['series']:
				for genre in result['series']['genres']:
					d['metadata']['genres'].append(_getString(genre,'name'))
			if 'releaseDate' in result:
				d['metadata']['year'] = result['releaseDate'][:4]
				d['metadata']['premiered'] = result['releaseDate'][:10]
				d['metadata']['aired'] = result['releaseDate'][:10]

			d['params']['params'] = f'?kinds=Video&season={result["id"]}&orderBy={lang["order"]}&sortDirection=Ascending'
			res['items'].append(d)


		elif item['kind'] == 'Video' or item['kind'] == 'Movie':
			d = {'type':'movie', 'params':{'mode':'playVideo'}, 'metadata':{'art':{},'actors':[],'directors':[],'artists':[],'writers':[],'genres':[],'credits':[]}}
			d['metadata']['name'] = _getString(result,'title')
			if 'originalTitle' in result:
				d['metadata']['originaltitle'] = result['originalTitle']
			d['metadata']['plot'] = _getString(result,'synopsis')
			d['metadata']['plotoutline'] = _getString(result,'teaser')

			if 'season' in result:
				d['metadata']['season'] = result['season']['seasonNumber']
			if 'episodeNumber' in result:
				d['metadata']['episode'] = result['episodeNumber']
				d['type'] = 'episode'
			d['metadata']['duration'] = result['runtime']
			if 'releaseDate' in result:
				d['metadata']['year'] = result['releaseDate'][:4]
				d['metadata']['premiered'] = result['releaseDate'][:10]
				d['metadata']['aired'] = result['releaseDate'][:10]
			d['metadata']['art'] = _getArt(result)

			if 'participations' in result:
				for participant in result['participations']:
					if participant['kind'] in ['Actor', 'Voice']:
						d['metadata']['actors'].append({'role':participant.get('englishDescription',''),'name':_getName(participant)})
					elif participant['kind'] in ['Director', 'Producer']:
						d['metadata']['directors'].append(_getName(participant))
					elif participant['kind'] == 'Composer':
						d['metadata']['artists'].append(_getName(participant))
					elif participant['kind'] in ['Writer', 'Editor']:
						d['metadata']['writers'].append(_getName(participant))
					elif participant['kind'] in ['Misc', 'Camera']:
						d['metadata']['credits'].append(_getName(participant))
			if 'genres' in result:
				for genre in result['genres']:
					d['metadata']['genres'].append(_getString(genre,'name'))

			d['params']['video'] = result["id"]
			res['items'].append(d)

		else:
			lm4utils.log(f'[{__addonid__}] Unsupported kind of media: {item["kind"]}')

	return res

def getVideoUrl(videoId):
	_checkTokenExpired()
	token = lm4utils.getTokenWithErrorNotification()
	if token is None or token == '':
		return _emptyMedia()

	headers = {
		'Authorization':f'Bearer {lm4utils.getSetting("access_token")}'
	}

	# first check the media type and if it's currently available
	mediaType = "movies"
	hasDetails = False
	available = False
	response = requests.get(f'https://api.tenant.frontend.vod.filmwerte.de/v11/{lm4utils.getSetting("tenant")}/{mediaType}/{videoId}',headers=headers)
	if response.status_code == 200:
		hasDetails = True
		available = response.json()["state"]["kind"] == "Active"
		response = requests.get(f'https://api.tenant.frontend.vod.filmwerte.de/v11/{lm4utils.getSetting("tenant")}/{mediaType}/{videoId}/uri',headers=headers)
	elif response.status_code == 404:
		# fallback: try if it's an episode
		mediaType = "episodes"
		response = requests.get(f'https://api.tenant.frontend.vod.filmwerte.de/v11/{lm4utils.getSetting("tenant")}/{mediaType}/{videoId}',headers=headers)
		if response.status_code == 200:
			hasDetails = True
			available = response.json()["state"]["kind"] == "Active"
			response = requests.get(f'https://api.tenant.frontend.vod.filmwerte.de/v11/{lm4utils.getSetting("tenant")}/{mediaType}/{videoId}/uri',headers=headers)
		else:
			lm4utils.log(f"[{__addonid__}] Unexpected status code when getting media details with fallback: {response.status_code}.")
	else:
		lm4utils.log(f"[{__addonid__}] Unexpected status code when getting media details: {response.status_code}.")

	if hasDetails and not available:
		lm4utils.displayMsg(lm4utils.getTranslation(30603), lm4utils.getTranslation(30604))
		return _emptyMedia()

	videoInfo = response.json()
	url = f'{videoInfo["mpegDash"]}'
	wvheaders = '&content-type='
	licenseserverurl = f'{videoInfo["widevineLicenseServerUri"]}|{wvheaders}|R{{SSM}}|'
	return {'media':[{'url':url, 'licenseserverurl':licenseserverurl, 'type': 'video', 'stream':'DASH'}]}

def _emptyPage(content='videos'):
	return {'items': [], 'content': content, 'pagination': {'currentPage': 0}}

def _emptyMedia():
	return {'media':[]}

def _checkTokenExpired():
	# do nothing for the moment, as importing cryptography (via pyjwt) results in the plugin not loading at all because
	# "PyO3 modules may only be initialized once per interpreter process"
	return
	tokenString = lm4utils.getSetting("access_token")
	isExpired = False
	try:
		token = jwt.decode(tokenString, key="", algorithms=["RSA256"], options={"verify_signature":False, "verify_aud":False})
		expiry = token['exp']
		if expiry <= time.time():
			isExpired = True
	except jwt.exceptions.ExpiredSignatureError:
		isExpired = True
	
	if isExpired:
		lm4utils.log(f"[{__addon__}] Access token expired. Will fetch new token.")
		_getNewToken()

def _getNewToken():
	refresh_token = lm4utils.getSetting('refresh_token')
	if refresh_token is None or refresh_token == '':
		lm4utils.log(f"[{__addon__}] Cannot fetch new access token. Refresh token is missing.")
		return False
	files = {'client_id':(None, f'tenant-{lm4utils.getSetting("tenant")}-filmwerte-vod-frontend'),'grant_type':(None, 'refresh_token'),'refresh_token':(None, refresh_token),'scope':(None, 'filmwerte-vod-api offline_access')}
	j = requests.post('https://api.vod.filmwerte.de/connect/token', files=files).json()
	lm4utils.setSetting('access_token', j['access_token'])
	lm4utils.setSetting('refresh_token', j['refresh_token'])
	return j['access_token']

def _getString(d,k):
	try:
		s = d.get(lang[k], '')
		if s != '':
			return s
		else:
			return d[english[k]]
	except:
		try:
			return d.get(k)
		except:
			return ''

def _getName(participant):
	if 'firstName' in participant['person']:
		return f"{participant['person']['firstName']} {participant['person']['lastName']}"
	else:
		return participant['person']['lastName']

def _getArt(item):
	thumb = ''
	fanart = ''
	poster = ''
	banner = ''
	if 'artworkUris' in item:
		for art in item['artworkUris']:
			if art['kind'] == 'Thumbnail' and thumb == '':
				thumb = art['resolution2x']
			elif art['kind'] == 'Thumbnail' and fanart == '':
				fanart = art['resolution4x']
			elif art['kind'] == 'Background':
				fanart = art['resolution1080']
			elif art['kind'] == 'CoverPortrait' and poster == '':
				poster = art['resolution4x']
			elif art['kind'] == 'Teaser' and banner == '':
				banner = art['resolution720']
	else:
		for art in item['artworks']:
			if art['kind'] == 'Thumbnail' and thumb == '':
				thumb = art['uri']['thumbnail2x']
			elif art['kind'] == 'Thumbnail' and fanart == '':
				fanart = art['uri']['resolution4x']
			elif art['kind'] == 'Background':
				fanart = art['uri']['resolution1080']
			elif art['kind'] == 'CoverPortrait' and poster == '':
				poster = art['uri']['thumbnail4x']
			elif art['kind'] == 'Teaser' and banner == '':
				banner = art['uri']['resolution720']
	return {'thumb':thumb, 'fanart':fanart, 'poster':poster, 'banner':banner}
