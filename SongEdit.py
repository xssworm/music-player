# -*- coding: utf-8 -*-
# MusicPlayer, https://github.com/albertz/music-player
# Copyright (c) 2012, Albert Zeyer, www.az2000.de
# All rights reserved.
# This code is under the 2-clause BSD license, see License.txt in the root directory of this project.

from utils import UserAttrib, Event, initBy
import Traits

# Note: I'm not too happy with all the complicated update handling here...
# In general, the design is ok. But it needs some more specification
# and then some drastic simplification. Most of it should be one-liners.

class SongEdit:
	@initBy
	def _updateEvent(self): return Event()
	
	def __init__(self, ctx=None):
		if not ctx:
			import gui
			ctx = gui.ctx()
			assert ctx, "no gui context"
		self.ctx = ctx
		self._updateHandler = lambda: self._updateEvent.push()
		ctx.curSelectedSong_updateEvent.register(self._updateHandler)
		
	@UserAttrib(type=Traits.Object)
	@property
	def song(self):
		return self.ctx.curSelectedSong	

	@UserAttrib(type=Traits.EditableText)
	def artist(self, updateText=None):
		if self.song:
			if updateText:
				self.song.artist = updateText
			return self.song.artist
		return ""
	
	@UserAttrib(type=Traits.EditableText)
	def title(self, updateText=None):
		if self.song:
			if updateText:
				self.song.title = updateText
			return self.song.title
		return ""

	@staticmethod
	def _convertTagsToText(tags):
		def txtForTag(tag):
			value = tags[tag]
			if value >= 1: return tag
			return tag + ":" + str(value) 
		return " ".join(map(txtForTag, sorted(tags.keys())))

	@staticmethod
	def _convertTextToTags(txt):
		pass
	
	# todo...
	#@UserAttrib(type=Traits.EditableText)
	def tags(self, updateText=None):
		if self.song:
			return self._convertTagsToText(self.song.tags)
		return ""

	@UserAttrib(type=Traits.Table(keys=("key", "value")), variableHeight=True)
	@property
	def metadata(self):
		d = dict(self.song.metadata)
		for key in ("artist","title","url","rating","tags"):
			try: d[key] = unicode(getattr(self.song, key))
			except AttributeError: pass			
		l = []
		for key,value in d.items():
			l += [{"key": key, "value": value}]
		return l
	@metadata.setUpdateEvent
	@property
	def metadata_updateEvent(self): return self.song._updateEvent