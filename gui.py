# MusicPlayer, https://github.com/albertz/music-player
# Copyright (c) 2012, Albert Zeyer, www.az2000.de
# All rights reserved.
# This code is under the 2-clause BSD license, see License.txt in the root directory of this project.

import sys
import utils, appinfo
from utils import safe_property

# define fallback
def main(): raise NotImplementedError
def guiMain(): pass
def locateFile(filename):
	print "locateFile", utils.convertToUnicode(filename).encode("utf-8")

try:
	# Right now, we can only enable qtgui via cmdline and the only
	# two implementations are Cocoa and Qt. And we always try to enable
	# one of these implementations. That is why the selection looks like
	# this.
	# Later, it might sense to disable the GUI at all and there might be
	# other GUI implementations. Also, maybe the design might change and
	# we could enable multiple GUIs as different separate modules.
	# E.g., the webinterface will in any case be a separate module.
	if sys.platform == "darwin" and not appinfo.args.qtgui:
		from guiCocoa import *
	else:
		# Use Qt as the generic fallback.
		from guiQt import *
except Exception:
	print "error in loading GUI implementation"
	sys.excepthook(*sys.exc_info())
		
class GuiObject:
	"This defines the protocol we must support"
	
	root = None
	parent = None
	attr = None # if this is a child of something, this is the access attrib of the parent.subjectObject
	pos = (0,0)
	size = (0,0)
	autoresize = (False,False,False,False) # wether to modify x,y,w,h on resize
	nativeGuiObject = None	
	subjectObject = None
	DefaultSpace = (8,8)
	OuterSpace = (8,8)
	
	def __repr__(self): return "<%s %r %r>" % (self.__class__.__name__, self.subjectObject, self.attr)

	@safe_property
	@property
	def name(self):
		name = ""
		obj = self
		while True:
			if obj.parent:
				name = "." + obj.attr.name + name
				obj = obj.parent
			else:
				name = obj.subjectObject.__class__.__name__ + name
				break
		return name
	
	@safe_property
	@property
	def innerSize(self): return self.size
	
	def addChild(self, childGuiObject): pass
	
	def allParents(self):
		obj = self
		while obj:
			yield obj
			obj = obj.parent

	def childIter(self): return self.childs.itervalues()
	
	def updateSubjectObject(self):
		if self.parent:
			self.subjectObject = self.attr.__get__(self.parent.subjectObject)
		if getattr(self.subjectObject, "_updateEvent", None):
			self._updateHandler = lambda: do_in_mainthread(self.updateContent, wait=False)
			getattr(self.subjectObject, "_updateEvent").register(self._updateHandler)
		
	def updateContent(self, ev=None, args=None, kwargs=None):
		self.updateSubjectObject()
		for control in self.childIter():
			if control.attr and control.attr.updateHandler:
				try:
					control.attr.updateHandler(self.subjectObject, control.attr, ev, args, kwargs)
				except Exception:
					sys.excepthook(*sys.exc_info())
			control.updateContent(ev, args, kwargs)
	
	def guiObjectsInLine(self):
		obj = self
		while True:
			if not getattr(obj, "leftGuiObject", None): break
			obj = obj.leftGuiObject
		while obj:
			yield obj
			obj = getattr(obj, "rightGuiObject", None)

	def layoutLine(self):
		line = list(self.guiObjectsInLine())
		minY = min([control.pos[1] for control in line])
		maxH = max([control.size[1] for control in line])
		
		x = self.parent.OuterSpace[0]
		for control in line:
			spaceX = self.parent.DefaultSpace[0]
			if control.attr.spaceX is not None: spaceX = control.attr.spaceX

			w,h = control.size
			y = minY + (maxH - h) / 2.
			
			control.pos = (x,y)
			
			x += w + spaceX

		varWidthControl = None
		for control in line:
			if control.attr.variableWidth:
				varWidthControl = control
				break
		if not varWidthControl:
			varWidthControl = line[-1]
			if varWidthControl.attr.variableWidth is False:
				# It explicitely doesn't want to be of variable size.
				return
		x = self.parent.innerSize[0] - self.parent.OuterSpace[0]
		for control in reversed(line):
			w,h = control.size
			y = control.pos[1]
	
			if control is varWidthControl:
				w = x - control.pos[0]
				x = control.pos[0]
				control.pos = (x,y)
				control.size = (w,h)
				control.autoresize = (False,False,True,False)
				break
			else:
				x -= w
				control.pos = (x,y)
				control.size = (w,h)
				control.autoresize = (True,False,False,False)

				spaceX = self.parent.DefaultSpace[0]
				if control.attr.spaceX is not None: spaceX = control.attr.spaceX
				x -= spaceX
	
	def childGuiObjectsInColumn(self):
		obj = self.firstChildGuiObject
		while obj:
			yield obj
			while getattr(obj, "rightGuiObject", None):
				obj = obj.rightGuiObject
			obj = getattr(obj, "bottomGuiObject", None)
		
	def layout(self):		
		lastVertControls = list(self.childGuiObjectsInColumn())
		if not lastVertControls: return
		if not self.autoresize[3]:
			w,h = self.size
			lastCtr = lastVertControls[-1]
			h = lastCtr.pos[1] + lastCtr.size[1]
			self.size = (w,h)
			return
		varHeightControl = None
		for control in lastVertControls:
			if control.attr.variableHeight:
				varHeightControl = control
				break
		if not varHeightControl:
			varHeightControl = lastVertControls[-1]
		y = self.innerSize[1] - self.OuterSpace[1]
		for control in reversed(lastVertControls):
			w,h = control.size
			x = control.pos[0]
			
			if control is varHeightControl:
				h = y - control.pos[1]
				y = control.pos[1]
				control.pos = (x,y)
				control.size = (w,h)
				control.autoresize = control.autoresize[0:3] + (True,)
				control.layout()
				break
			else:
				y -= h
				for lineControl in control.guiObjectsInLine():
					lineControl.pos = (lineControl.pos[0],y)
					lineControl.autoresize = lineControl.autoresize[0:1] + (True,) + lineControl.autoresize[2:4]
				y -= self.DefaultSpace[1]
	
	firstChildGuiObject = None
	childs = {} # (attrName -> guiObject) map. this might change...
	def setupChilds(self):
		"If this is a container (a generic object), this does the layouting of the childs"

		self.updateSubjectObject()
		self.firstChildGuiObject = None
		self.childs = {}
		x, y = self.OuterSpace
		maxX, maxY = 0, 0
		lastControl = None
		
		for attr in iterUserAttribs(self.subjectObject):
			control = buildControl(attr, self)
			if not self.firstChildGuiObject:
				self.firstChildGuiObject = control
			if attr.hasUpdateEvent():
				def controlUpdateHandler(control=control):
					do_in_mainthread(control.updateContent, wait=False)
				control._updateHandler = controlUpdateHandler
				attr.updateEvent(self.subjectObject).register(control._updateHandler)
			self.addChild(control)
			self.childs[attr.name] = control
			
			spaceX, spaceY = self.DefaultSpace
			if attr.spaceX is not None: spaceX = attr.spaceX
			if attr.spaceY is not None: spaceY = attr.spaceY
			
			if attr.alignRight and lastControl: # align next right
				x = lastControl.pos[0] + lastControl.size[0] + spaceX
				# y from before
				control.leftGuiObject = lastControl
				if lastControl:
					lastControl.rightGuiObject = control
				
			elif lastControl: # align next below
				x = self.OuterSpace[0]
				y = maxY + spaceY
				control.topGuiObject = lastControl
				if lastControl:
					lastControl.layoutLine()
					lastControl.bottomGuiObject = control
			
			else: # very first
				pass
			
			control.pos = (x,y)

			lastControl = control
			maxX = max(maxX, control.pos[0] + control.size[0])
			maxY = max(maxY, control.pos[1] + control.size[1])
		
			control.updateContent()
		
		if lastControl:
			lastControl.layoutLine()
			self.layout()
					
		# Handy for now. This return might change.
		return (maxX + self.OuterSpace[0], maxY + self.OuterSpace[1])

	
# This function is later supposed to give the right gui context
# depending where we call it from. This can maybe be managed/set via
# contextlib or so.
# The context itself is supposed to provide objects like window list,
# current selected song (needed for SongEdit), etc.
# Right now, we just support a single context.
def ctx():
	global _ctx
	if _ctx: return _ctx
	from utils import Event, initBy
	class Ctx(object):
		@property
		def curSelectedSong(self):
			song = getattr(self, "_curSelectedSong", None)
			if song: return song
			# otherwise fall back to current song.
			# it's better to have always one so if the window is created,
			# the layout is correct.
			# this is actually a hack: better would be if the re-layouting
			# would work correctly in that case. we really should work
			# out some generic nice and clean update-handling...
			import State
			return State.state.curSong
		
		@curSelectedSong.setter
		def curSelectedSong(self, obj):
			self._curSelectedSong = obj
			self.curSelectedSong_updateEvent.push()
			
		@initBy
		def curSelectedSong_updateEvent(self): return Event()

	_ctx = Ctx()
	return _ctx
_ctx = None
