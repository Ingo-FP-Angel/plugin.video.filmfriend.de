# -*- coding: utf-8 -*-

import sys
import urllib
import urllib.parse
import json
from datetime import date, timedelta
import xbmcaddon
import xbmcgui
import xbmcplugin

class lm4:
	def __init__(self):
		self.modes = {
			'libMediathekListDate':self.libMediathekListDate,
			'libMediathekListLetters':self.libMediathekListLetters,
			'libMediathekSearch':self.libMediathekSearch,
		}	
		self.playbackModes = {
			'libMediathekPlayDirect':self.libMediathekPlayDirect
		}
		self.defaultMode = ''

		self.params = {}

	def translation(self,id,addonid=False):
		#return str(id)
		if addonid:
			return xbmcaddon.Addon(id=addonid).getLocalizedString(id)
		elif id < 32000:
			return xbmcaddon.Addon().getLocalizedString(id)
		else:
			return xbmcaddon.Addon(id='script.module.libmediathek4').getLocalizedString(id)

	def sortAZ(self):
		xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)

	def getSearchString(self):
		return 'sport'



	def setSetting(self,k,v):
		return xbmcplugin.setSetting(int(sys.argv[1]), k, v)
		
	def getSetting(self,k):
		return xbmcplugin.getSetting(int(sys.argv[1]), id=k)
		
	def endOfDirectory(self):
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)

	def _buildUri(self,d):
		return d.get('pluginpath', sys.argv[0]) + '?' + urllib.parse.urlencode(d)
	
	def addEntries(self,d):
		lists = []
		#print(json.dumps(d))
		for item in d['items']:
			u = self._buildUri(item['params'])
			#print('Pluginpath')
			#print(self._buildUri(item['params']))
			#print('Item')
			#print(json.dumps(item, indent=4, sort_keys=True))
			

			"""if 'type' in items anitems d['type'] == 'date' and 'airedtime' in items:
				items["name"] = '(' + str(items["airedtime"]) + ') ' + items["name"]
			elif 'type' in items and items['type'] == 'date' and 'time' in items:
				items["name"] = '(' + str(items["date"]) + ') ' + items["name"]
			"""	
			metadata = item['metadata']

			liz=xbmcgui.ListItem(metadata.get('name',''))
			
			ilabels = {
				"Title": 				metadata.get('name',''),
				"Plot": 				metadata.get('plot',metadata.get('plotoutline','')),
				"Plotoutline": 	metadata.get('plotoutline',''),
				"Duration": 		str(metadata.get('duration','')),
				"Mpaa": 				metadata.get('mpaa',''),
				"Aired": 				metadata.get('aired',''),
				"Studio": 			metadata.get('channel',''),
				#"episode": 			metadata.get('episode',None),
				#"season": 			metadata.get('season',''),
				"tvshowtitle": 	metadata.get('tvshowtitle',''),
				"rating": 			metadata.get('rating',''),
				"director": 		metadata.get('directors',''),
				"artist": 			metadata.get('artists',[]),
				"writer": 			metadata.get('writers',''),
				"credits": 			metadata.get('credits',''),
				"genre": 				metadata.get('genres',''),
				"year": 				metadata.get('year',''),
				"premiered": 		metadata.get('premiered',''),
				"premiered": 		metadata.get('originaltitle',''),
				}
			if 'art' in metadata:
				liz.setArt(metadata['art'])
			if 'episode' in metadata:
				liz.setArt(metadata['episode'])
			if 'season' in metadata:
				liz.setArt(metadata['season'])

			
			if 'subtitles' in metadata:#TODO
				liz.addStreamInfo('subtitle', {'language': 'deu'})

			if 'actors' in metadata:
				liz.setCast(metadata['actors'])

			if 'type' in item:
				if item['type'] in ['video', 'live', 'date', 'clip']:
					ilabels['mediatype'] = 'video'
				elif item['type'] in ['tvshow']:
					ilabels['mediatype'] = 'tvshow'
				elif item['type'] in ['shows', 'season']:
					ilabels['mediatype'] = 'season'
				elif item['type'] in ['episode']:
					ilabels['mediatype'] = 'episode'
				elif item['type'] in ['movie']:
					ilabels['mediatype'] = 'movie'
				elif item['type'] in ['sport']:
					ilabels['mediatype'] = 'sport'
				else:
					ilabels['mediatype'] = 'video'
					
			ok=True

			if item['type'] in ['audio','songs']:
				liz.setInfo( type="music", infoLabels=ilabels)
			else:
				liz.setInfo( type="Video", infoLabels=ilabels)
				
			"""	art = {}
			art['thumb'] = d.get('thumb')
			art['landscape'] = d.get('thumb')
			art['poster'] = d.get('thumb')
			art['fanart'] = d.get('fanart',d.get('thumb',fanart))
			art['icon'] = d.get('channelLogo','')
			liz.setArt(art)"""
			
			"""
			if 'customprops' in d:
				for prop in d['customprops']:
					liz.setProperty(prop, d['customprops'][prop])
			"""		
			if item.get('type',None) in ['video', 'live', 'date', 'clip', 'episode', 'audio', 'sport', 'sports', 'movie', 'song']:
				liz.setProperty('IsPlayable', 'true')
				lists.append([u,liz,False])
			else:
				lists.append([u,liz,True])

		if 'content' in d:
			xbmcplugin.setContent(handle=int(sys.argv[1]), content=d['content'] )
		else:
			xbmcplugin.setContent(handle=int(sys.argv[1]), content="files" )
			"""
			if d['type'] in ['video', 'live', 'date', 'clip', 'episode']:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="episodes" )
			elif d['type'] in ['shows', 'season']:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="tvshows" )
			elif d['type'] in ['sport']:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="sport" )
			elif d['type'] in ['movie']:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="movies" )
			elif d['type'] in ['songs']:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="songs" )
			else:
				xbmcplugin.setContent(handle=int(sys.argv[1]), content="files" )
			"""

		
		xbmcplugin.addDirectoryItems(int(sys.argv[1]), lists)

	def play(self,d,external=False):
		if len(d['media']) == 0:#TODO: add error msg
			listitem = xbmcgui.ListItem(path='')
			pluginhandle = int(sys.argv[1])
			xbmcplugin.setResolvedUrl(pluginhandle, False, listitem)
			return

		listitem,url = self._chooseBitrate(d['media'])	
				
		if 'subtitle' in d:
			subs = []
			for subtitle in d['subtitle']:
				if subtitle['type'] == 'srt':
					subs.append(subtitle['url'])
				elif subtitle['type'] == 'ttml':
					import libmediathek3ttml2srt
					subFile = libmediathek3ttml2srt.ttml2Srt(subtitle['url'])
					subs.append(subFile)
				elif subtitle['type'] == 'webvtt':
					import libmediathek3webvtt2srt 
					subFile = libmediathek3webvtt2srt.webvtt2Srt(subtitle['url'])
					subs.append(subFile)
				else:
					log('Subtitle format not supported: ' + subtitle['type'])
			listitem.setSubtitles(subs)
		
		if 'metadata' in d:
			ilabels = {}
			if 'plot' in d['metadata']:
				ilabels['Plot'] = d['metadata']['plot']
			if 'name' in d['metadata']:
				ilabels['Title'] = d['metadata']['name']
			listitem.setInfo( type="Video", infoLabels=ilabels)
			
			art = {}
			if 'thumb' in d['metadata']:
				art['thumb'] = d['metadata']['thumb']
			listitem.setArt(art)
			
		if 'header' in d['media']:
			listitem.setProperty('inputstream.adaptive.stream_headers',d['media']['header'])
		
		if external:
			xbmc.Player().play(url, listitem)
		else:
			pluginhandle = int(sys.argv[1])
			xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
			
	def _chooseBitrate(self,l):
		bitrate = 0
		url = False
		streamType = False
		for item in l:
			if item.get('stream','').lower() == 'hls':#prefer hls
				url = item['url']
				streamType = 'HLS'
				break
			if item.get('stream','').lower() == 'dash':
				url = item['url']
				streamType = 'DASH'
			if item.get('stream','').lower() == 'mp4' and item.get('bitrate',0) >= bitrate:
				bitrate = item.get('bitrate',0)
				url = item['url']
				streamType = 'MP4'
			if item.get('stream','').lower() == 'audio':
				url = item['url']
				streamType = 'AUDIO'
		listitem = xbmcgui.ListItem(path=url)
		if streamType == 'DASH':
			listitem.setProperty('inputstream', 'inputstream.adaptive')
			listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
			if 'licenseserverurl' in item:
				listitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
				listitem.setProperty('inputstream.adaptive.license_key', item['licenseserverurl'])
			#listitem.setProperty('inputstream.adaptive.stream_headers','User-Agent=Mozilla%2F5.0%20%28Windows%20NT%206.1%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F63.0.3239.84%20Safari%2F537.36')
			listitem.setMimeType('application/dash+xml')
			listitem.setContentLookup(False)
		elif streamType == 'HLS':
			listitem.setMimeType('application/vnd.apple.mpegurl')
			listitem.setProperty('inputstream', 'inputstream.adaptive')
			listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
			listitem.setContentLookup(False)
		#elif streamType == 'MP4':
		#	listitem.setMimeType('application/dash+xml')
		#	listitem.setContentLookup(False)

		return listitem,url

	def action(self):	
		self.params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
		mode = self.params.get('mode',self.defaultMode)
		if mode in self.playbackModes:
			self.play(self.playbackModes[mode]())
		else:
			l = self.modes[mode]()
			#print(json.dumps(l))
			self.addEntries(l)
			self.endOfDirectory()	

			
	def libMediathekSearch(self):
		sString = xbmcgui.Dialog().input(self.translation(32139))
		if sString == '':
			xbmcplugin.endOfDirectory(int(sys.argv[1]),succeeded=False)
			return
		return self.searchModes[self.params['searchMode']](urllib.parse.quote(sString))
			
	def libMediathekListLetters(self):
		import string
		result = {'items':[]}
		ignore = self.params.get('ignore','').split(',')
		letters = ['#']
		letters.extend(list(string.ascii_lowercase))
		for letter in letters:
			if not letter in ignore:
				d = {'params':json.loads(self.params['subParams']), 'metadata':{}, 'type':'dir'}
				d['metadata']['name'] = letter.upper()
				d['params']['letter'] = letter
				result['items'].append(d)
		return result
			
	def libMediathekListDate(self):
		result = {'items':[]}
		weekdayDict = { 
			'0': self.translation(32013),#Sonntag
			'1': self.translation(32014),#Montag
			'2': self.translation(32015),#Dienstag
			'3': self.translation(32016),#Mittwoch
			'4': self.translation(32017),#Donnerstag
			'5': self.translation(32018),#Freitag
			'6': self.translation(32019),#Samstag
			}
		
		i = 0
		while i <= 6:
			day = date.today() - timedelta(i)
		
			d = {'params':json.loads(self.params['subParams']), 'metadata':{}, 'type':'dir'}
			d['params']['datum'] = str(i)
			d['params']['yyyymmdd'] = self._calcyyyymmdd(i)
			d['params']['ddmmyyyy'] = self._calcddmmyyyy(i)
			
			if i == 0:
				d['metadata']['name'] = self.translation(32020)
			elif i == 1:
				d['metadata']['name'] = self.translation(32021)
			else:
				d['metadata']['name'] = weekdayDict[day.strftime("%w")]

			result['items'].append(d)
			i += 1

		#if self.params.get('dateChooser',False) == True:
		#	d = {'params':{'mode': mode}, 'metadata':{'name': self.translation(32022)}, 'type':'dir'}
		#	if channel: d['params']['channel'] = channel
		#	result['items'].append(d)
		return result

	def libMediathekPlayDirect(self):
		return {'media':[{'url':self.params['url'], 'stream':self.params['stream']}]}

	def populateDirDate(self,mode,channel=False,dateChooser=False):
		weekdayDict = { 
			'0': self.translation(32013),#Sonntag
			'1': self.translation(32014),#Montag
			'2': self.translation(32015),#Dienstag
			'3': self.translation(32016),#Mittwoch
			'4': self.translation(32017),#Donnerstag
			'5': self.translation(32018),#Freitag
			'6': self.translation(32019),#Samstag
			}
		result = {'items':[]}
		
		i = 0
		while i <= 6:
			day = date.today() - timedelta(i)
		
			d = {'params':{'mode': mode, 'datum': str(i), 'yyyymmdd': self._calcyyyymmdd(i)}, 'metadata':{}, 'type':'dir'}
			if i == 0:
				d['metadata']['name'] = self.translation(32020)
			elif i == 1:
				d['metadata']['name'] = self.translation(32021)
			else:
				d['metadata']['name'] = weekdayDict[day.strftime("%w")]
			if channel:
				d['params']['channel'] = channel

			result['items'].append(d)
			i += 1

		#if self.params.get('dateChooser',False) == True:
		#	d = {'params':{'mode': mode}, 'metadata':{'name': self.translation(32022)}, 'type':'dir'}
		#	if channel: d['params']['channel'] = channel
		#	result['items'].append(d)
		return result

	def _calcyyyymmdd(self,d):
		day = date.today() - timedelta(d)
		return day.strftime('%Y-%m-%d')

	def _calcddmmyyyy(self,d):
		day = date.today() - timedelta(d)
		return day.strftime('%d-%m-%Y')