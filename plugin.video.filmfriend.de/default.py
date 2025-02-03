# -*- coding: utf-8 -*-
import resources.lib.jsonparser as jsonParser
from resources.lib.external.libmediathek4 import lm4

class filmfriend(lm4):
	genres = {
		'Comedy': '70b11c59-d444-4500-adb6-da13bd6b008f',
		'Science Fiction' : '80e5e84a-aaf5-4eec-a505-e4697bbf77e4',
		'Love': '6b3f307c-573b-4f5a-a349-aea9486f826c',
		'Action': '1a67afb4-ab9f-4889-a2ae-91a447e365fc',
		'Adventure': 'b82bb7bb-4851-4346-840e-f283fe14182a',
		'Drama': 'cf068584-15f1-4347-8352-e447b4203dee',
		'Thriller': '076a8606-5b38-483d-a93e-8786be0be6cd',
		'Animation': '854f579d-4e06-4708-a57d-17384692b1f2',
		'Crime': '68dc0b86-890b-416a-a9c8-1342ee79c304',
		}
	
	def __init__(self):
		lm4.__init__(self)
		self.defaultMode = 'listMain'

		self.modes.update({
			'listSearch': self.listSearch,
			'listMain': self.listMain,
			'listVideos': self.listVideos,
			'listWatchList': self.listWatchList,
			'listGenres': self.listGenres,
		})

		self.searchModes = {
			'listVideoSearch': self.listVideoSearch,
		}

		self.playbackModes = {
			'playVideo':self.playVideo,
		}

	def listMain(self):
		l = []
		l.append({'metadata':{'name':self.translation(32030)}, 'type':'dir', 'params':{'mode':'listSearch', 'content':'videos',  'params':'?facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Video&kinds=Series&videoKinds=Movie&&&&orderBy=ActiveSinceDateTime&sortDirection=Descending&skip=0&take=20'}})
		l.append({'metadata':{'name':self.translation(32031)}, 'type':'dir', 'params':{'mode':'listSearch', 'content':'videos',  'params':'?facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Video&videoKinds=Movie&&&&orderBy=MonthlyImpressionScore&sortDirection=Descending&skip=0&take=20'}})
		l.append({'metadata':{'name': 'Genres'}, 'type':'dir', 'params':{'mode':'listGenres', 'content':'videos',  'params':'?totalCount=true&take=500&sortOrder=RecentlyAdded'}})
		l.append({'metadata':{'name':self.translation(30600)}, 'type':'dir', 'params':{'mode':'listSearch', 'content':'tvshows', 'params':'?facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Series&&languageIsoCode=EN&orderBy=EnglishOrder&sortDirection=Ascending&skip=0&take=500'}})
		l.append({'metadata':{'name':self.translation(30601)}, 'type':'dir', 'params':{'mode':'listSearch', 'content':'movies',  'params':'?facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Video&videoKinds=Movie&categories=d36cbed2-7569-4b94-9080-03ce79c2ecee&orderBy=EnglishOrder&sortDirection=Ascending&skip=0&take=500'}})
		l.append({'metadata':{'name':self.translation(30602)}, 'type':'dir', 'params':{'mode':'listWatchList', 'content':'videos',  'params':'?totalCount=true&take=500&sortOrder=RecentlyAdded'}})
		l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'searchMode':'listVideoSearch'}, 'type':'dir'})
		return {'items':l,'name':'root'}

	def listGenres(self):
		l = []
		for genre in self.genres:
			l.append({'metadata':{'name': genre}, 'type':'dir', 'params':{'mode':'listSearch', 'content':'videos',  'params': f'?facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Video&kinds=Series&videoKinds=Movie&genres={self.genres[genre]}&&&orderBy=EnglishOrder&sortDirection=Ascending&skip=0&take=500'}})
		
		return {'items':l}
    
	def listSearch(self):
		return jsonParser.parseSearch(self.params['params'],self.params['content'])

	def listWatchList(self):
		return jsonParser.parseWatchList(self.params['params'],self.params['content'])

	def listVideoSearch(self,searchString):
		return jsonParser.parseSearch(f'?search={searchString}&facets=Kind&facets=VideoKind&facets=Categories&facets=Genres&facets=GameSituations&facets=AgeRecommendation&facets=AudioLanguages&facets=AudioDescriptionLanguages&facets=SubtitleLanguages&facets=ClosedCaptionLanguages&kinds=Video&kinds=Series&kinds=Person&videoKinds=Movie&languageIsoCode=EN&orderBy=Score&sortDirection=Descending&skip=0&take=30')

	def listVideos(self):
		return jsonParser.parseVideos(self.params['id'],self.params['content'])

	def playVideo(self):
		return jsonParser.getVideoUrl(self.params['video'])

if sys.argv[1] == 'libraryPicker':
	import resources.lib.login as login
	login.pick()
elif sys.argv[1] == 'libraryLogin':
	import resources.lib.login as login
	login.login()
else:
	p = filmfriend()
	p.action()
