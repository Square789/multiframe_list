"""
A module that brings the MultiframeList class with it.
Its purpose is to display items and their properties over
several colums and easily format, sort and manage them as part of a UI.
"""

import os

import tkinter as tk
import tkinter.ttk as ttk
from operator import itemgetter

__version__ = "2.3.0"
__author__ = "Square789"

BLANK = ""

_DEF_LISTBOX_WIDTH = 20
_DEF_RCBTN = "3"

_DEF_COL_OPT = {
	"name": "<NO_NAME>",
	"sort": False,
	"minsize": 0,
	"weight": 1,
	"w_width": _DEF_LISTBOX_WIDTH,
	"formatter": None,
	"fallback_type": None
}

_DEF_MFL_OPT = {
	"listboxheight": 10,
}

ALL = "all"
END = "end"
COLUMN = "column"
ROW = "row"

SORTSYM = ("\u25B2", "\u25BC", "\u25A0") #desc, asc, none

class Column():
	"""
	Class whose purpose is to store data and information regarding a
	column. Can be assigned to frames of a MultiframeList, displaying
	its data in there.
	##################################################################
	!!! Columns should not be instantiated or controlled directly, !!!
	!!! only through methods of a MultiframeList.				   !!!
	##################################################################
	Required args:

	mfl: Parent, must be a MultiframeList

	Optional args:

	col_id: The identifying name of the column it will be addressed by.
		This is recommended to be a descriptive name set by the developer.
		If not specified, is set to an integer that is not
		in use by another Column. May not be changed after creation.
	names: Name to appear in the label and title the column.
	sort: Whether the column should sort the entire MultiframeList when its
		label is clicked.
	w_width: The width the widgets in this Column's occupied frame
		should have, measured in text units.
		The tkinter default for the label is 0, for the listbox 20, it is
		possible that the listbox stretches further than it should.
		! NOT TO BE CONFUSED WITH minsize !
	minsize: Specify the minimum amount of pixels the column should occupy.
		This option gets passed to the grid geometry manager.
		! NOT TO BE CONFUSED WITH w_width !
	weight: Weight parameter according to the grid geometry manager.
	formatter: A function that formats each element in a column's datalist.
		This is especially useful for i. e. dates, where you want
		to be able to sort by a unix timestamp but still be able to have the
		dates in a human-readable format.
	fallback_type: A datatype that all elements of the column will be converted
		to in case it has to be sorted. If not specified and elements are of
		different types, an exception will be raised.
	"""
	# COLUMNS ARE RESPONSIBLE FOR UI UPDATING. GENERAL FLOW LIKE THIS:
	# USER INTERFACES WITH THE MFL, MFL KEEPS TRACK OF A FEW LISTS AND
	# VARS, VALIDATES, GIVES COMMANDS TO COLUMNS, COLUMNS UPDATE UI
	# THEMSELVES

	def __init__(self, mfl, col_id=None, **kwargs):
		if not isinstance(mfl, MultiframeList):
			raise TypeError("Bad Column parent, must be MultiframeList.")
		self.mfl = mfl
		self.assignedframe = None

		self._cnfcmd = {
			"name": self._cnf_name, "sort": self._cnf_sort,
			"minsize": self._cnf_grid, "weight": self._cnf_grid,
			"formatter": self._cnf_formatter, "w_width": self._cnf_w_width,
			"fallback_type": lambda: False,
		}

		if col_id is None:
			self.col_id = self._generate_col_id()
		else:
			for col in self.mfl.columns:
				if col.col_id == col_id:
					raise ValueError(
						"Column id {} is already in use!".format(
						col_id.__repr__())
					)
			self.col_id = col_id

		self.data = [BLANK for _ in range(self.mfl.length)]
		self.sortstate = 2 # 0 if next sort will be descending, else 1

		self.cnf = _DEF_COL_OPT.copy()
		self.cnf.update(kwargs)

	def __repr__(self):
		return "<{} of {} at {}, col_id: {}>".format(
			self.__class__.__name__, self.mfl.__class__.__name__,
			hex(id(self.mfl)), self.col_id)

	def __len__(self):
		return len(self.data)

	def _generate_col_id(self):
		curid = 0
		idok = False
		while not idok:
			for col in self.mfl.columns:
				if col.col_id == curid:
					curid += 1
					break
			else:
				idok = True
		return curid

	def _cnf_formatter(self): # NOTE: YES OR NO?
		self.format()

	def _cnf_grid(self):
		if self.assignedframe is not None:
			curr_grid = self.mfl.framecontainer.grid_columnconfigure(
				self.assignedframe)
			callargs = {}
			for value in ("minsize", "weight"):
				if curr_grid[value] != self.cnf[value]:
					callargs[value] = self.cnf[value]
			if callargs:
				self.mfl.framecontainer.grid_columnconfigure(self.assignedframe,
					**callargs)

	def _cnf_name(self):
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][2].config(
				text = self.cnf["name"] )

	def _cnf_sort(self):
		if self.assignedframe is not None:
			if self.cnf["sort"]:
				self.set_sortstate(self.sortstate)
				self.mfl.frames[self.assignedframe][2].bind("<Button-1>",
					lambda _: self.mfl.sort(_, self))
			else:
				self.mfl.frames[self.assignedframe][3].configure(text = BLANK)
				self.mfl.frames[self.assignedframe][2].unbind("<Button-1>")

	def _cnf_w_width(self):
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][1].configure(
				width = self.cnf["w_width"])

	def config(self, **kw):
		if not kw:
			return self.cnf
		for k in kw:
			if not k in self._cnfcmd:
				raise ValueError("Unkown configuration arg \"{}\", must be "
					"one of {}.".format(k, ", ".join(self._cnfcmd.keys())))
			self.cnf[k] = kw[k]
			self._cnfcmd[k]()

	def data_clear(self):
		"""Clears self.data, refreshes interface, if assigned a frame."""
		self.data.clear()
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][1].delete(0, tk.END)

	def data_insert(self, elem, index=None):
		"""
		Inserts elem to self.data at index and refreshes interface, if
		assigned a frame. If index is not specified, elem will be appended
		instead.
		"""
		if index is not None:
			self.data.insert(index, elem)
		else:
			self.data.append(elem)
			index = tk.END
		if self.assignedframe is not None:
			if self.cnf["formatter"] is not None:
				self.mfl.frames[self.assignedframe][1].insert(index,
					self.cnf["formatter"](elem))
			else:
				self.mfl.frames[self.assignedframe][1].insert(index, elem)

	def data_pop(self, index):
		"""
		Pops the element at index, refreshes interface if assigned a
		frame.
		"""
		self.data.pop(index)
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][1].delete(index)

	def data_set(self, newdata):
		"""
		Sets the column's data to the list specified, refreshes interface
		if assigned a frame.
		"""
		if not isinstance(newdata, list):
			raise TypeError("Data has to be a list!")
		self.data = newdata
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][1].delete(0, tk.END)
			self.mfl.frames[self.assignedframe][1].insert(tk.END, *self.data)

	def format(self, exclusively = None):
		"""
		If interface frame is specified, runs all data through
		self.cnf["formatter"] and displays result.
		If exclusively is set (as an iterable),
		only specified indices will be formatted.
		"""
		if self.cnf["formatter"] is not None and self.assignedframe is not None:
			if exclusively is None:
				f_data = [self.cnf["formatter"](i) for i in self.data]
				self.mfl.frames[self.assignedframe][1].delete(0, tk.END)
				self.mfl.frames[self.assignedframe][1].insert(tk.END, *f_data)
			else:
				for i in exclusively:
					tmp = self.data[i]
					self.mfl.frames[self.assignedframe][1].delete(i)
					self.mfl.frames[self.assignedframe][1].insert(i, self.cnf["formatter"](tmp))

	def setdisplay(self, wanted_frame):
		"""
		Sets the display frame of the column to wanted_frame. To unregister,
		set it no None.
		May raise IndexError.
		"""
		self.assignedframe = wanted_frame
		if self.assignedframe is not None:
			for fnc in self._cnfcmd.values():
				fnc() # configure the frame
			self.set_sortstate(self.sortstate)
			self.mfl.frames[self.assignedframe][1].delete(0, tk.END)
			self.mfl.frames[self.assignedframe][1].insert(tk.END, *self.data)
			# NOTE: I don't think these two recurring lines warrant their own
			# "setframetodata" method.

	def set_sortstate(self, to):
		"""
		Sets the column's sortstate, causing it to update on the UI.
		"""
		if self.assignedframe is not None:
			if self.cnf["sort"]:
				self.mfl.frames[self.assignedframe][3].configure(text = SORTSYM[to])
		self.sortstate = to


class MultiframeList(ttk.Frame):
	"""
	Instantiates a multiframe tkinter based list

	Arguments:
	Instantiation only:
	master - parent object, should be tkinter root or a tkinter widget

	inicolumns <List<Dict>>: The columns here will be created and displayed
		upon instantiation.
		The dicts supplied should take form of Column constructor kwargs. See
		the `multiframe_list.Column` class for a list of acceptable kwargs.

	rightclickbtn <Str>: The button that will trigger the MultiframeRightclick
		virtual event. It is "3" (standard) on Windows, this may differ from
		platform to platform.

	Modifiable during runtime:
	listboxheight <Int>: The height (In items) the listboxes will take up.
		10 by tkinter default.

	A terrible idea of a feature:
		The MultiframeList will grab the currently active theme (as well as
		listen to the <<ThemeChanged>> event) and attempt to apply style
		configuration options in the current theme's style called
		"MultiframeList.Listbox" to its listboxes, as those are not available
		as ttk variants.
		The column title labels listen to the style "MultiframeListTitle.TLabel"
		The column sort indicators listen to the style "MultiframeLisSortInd.Tlabel"
	The list broadcasts the Virtual event "<<MultiframeSelect>>" to its parent
		whenever something is selected.
	The list broadcasts the Virtual event "<<MultiframeRightclick>>" to its
		parent whenever a right click is performed or the context menu button
		is pressed.
	"""
	_DEFAULT_LISTBOX_CONFIG = {
		"activestyle": "underline",
		"background": "#FFFFFF",
		"borderwidth": 1,
		"cursor": "",
		"disabledforeground": "#6D6D6D",
		"font": "TkDefaultFont",
		"foreground": "#000000",
		"highlightbackground": "#FFFFFF",
		"highlightcolor": "#B4B4B4",
		"highlightthickness": 1,
		"justify": "left",
		"relief": "sunken",
		"selectbackground": "#3399FF",
		"selectborderwidth": 0,
		"selectforeground": "#FFFFFF",
	}

	def __init__(self, master, inicolumns = None, rightclickbtn = None, **kwargs):
		super().__init__(master, takefocus = True)

		self.master = master
		self.cnf = _DEF_MFL_OPT.copy()

		self.bind("<Down>", lambda _: self.__setindex_arr(1))
		self.bind("<Up>", lambda _: self.__setindex_arr(-1))
		if os.name == "nt":
			ctxtmen_btn = "App"
		elif os.name == "posix":
			ctxtmen_btn = "Menu"
		else:
			ctxtmen_btn = None

		if ctxtmen_btn is not None:
			self.bind("<KeyPress-{}>".format(ctxtmen_btn), self.__callback_menu_button)

		self.ttkhookstyle = ttk.Style()
		self.bind("<<ThemeChanged>>", self.__themeupdate)

		self.curcellx = None
		self.curcelly = None
		self.coordx = None
		self.coordy = None

		self.scrollbar = ttk.Scrollbar(self, command = self.__scrollallbar)
		self.framecontainer = ttk.Frame(self)
		self.framecontainer.grid_rowconfigure(0, weight = 1)
		self.framecontainer.grid_columnconfigure(tk.ALL, weight = 1)

		self.frames = [] # Each frame contains interface elements for display.
		self.columns = [] # Columns will provide data storage capability as
		# well as some metadata.

		self.length = 0

		self.rightclickbtn = rightclickbtn if rightclickbtn is not None else _DEF_RCBTN

		for k in kwargs:
			if not k in self.cnf:
				raise ValueError("Unknown configuration argument: \"\"".format(k))
			self.cnf[k] = kwargs[k]
			getattr(self, "_cnf_{}".format(k))()

		if inicolumns is not None:
			self.addframes(len(inicolumns))
			for index, colopt in enumerate(inicolumns):
				self.columns.append(Column(self, **colopt))
				self.columns[-1].setdisplay(index)

		self.scrollbar.pack(fill = tk.Y, expand = 0, side = tk.RIGHT)
		self.framecontainer.pack(expand = 1, fill = tk.BOTH, side = tk.RIGHT)

	#====USER METHODS====

	def addcolumns(self, *coldicts):
		"""
		Takes any amount of dicts, then adds columns where the column
		constructor receives the dicts as kwargs. See the
		multiframe_list.Column class for a list of acceptable kwargs.
		"""
		for coldict in coldicts:
			self.columns.append(Column(self, **coldict))

	def addframes(self, amount):
		"""
		Adds amount of frames, display slots in a way, fills their listboxes
		up with empty strings and immediatedly displays them.
		"""
		startindex = len(self.frames)
		for i in range(amount):
			self.frames.append([])
			curindex = startindex + i
			rcb = self.rightclickbtn
			self.frames[curindex].append(ttk.Frame(self.framecontainer))
			self.frames[curindex][0].grid_rowconfigure(1, weight = 1)
			self.frames[curindex][0].grid_columnconfigure(0, weight = 1)

			self.frames[curindex].append(tk.Listbox(self.frames[curindex][0],
				exportselection = False, takefocus = False, height = self.cnf["listboxheight"]))
			self.frames[curindex].append(ttk.Label(self.frames[curindex][0],
				text = BLANK, anchor = tk.W, style = "MultiframeListTitle.TLabel"))
			self.frames[curindex].append(ttk.Label(self.frames[curindex][0],
				text = BLANK, anchor = tk.W, style = "MultiframeListSortInd.TLabel"))
			instance_name = self.frames[curindex][1].bindtags()[0]
			# REMOVE Listbox bindings from listboxes
			self.frames[curindex][1].bindtags((instance_name, '.', 'all'))
			def _handler_m1(event, self = self, button = 1, frameindex = curindex):
				return self.__setindex_lb(event, button, frameindex)
			def _handler_m3(event, self = self, button = rcb, frameindex = curindex):
				return self.__setindex_lb(event, button, frameindex)

			self.frames[curindex][1].bind("<Button-" + rcb + ">", _handler_m3)
			self.frames[curindex][1].bind("<Button-1>", _handler_m1)
			self.tk.eval("""if {{[tk windowingsystem] eq "aqua"}} {{
	bind {w} <MouseWheel> {{
		%W yview scroll [expr {{- (%D)}}] units
	}}
	bind {w} <Option-MouseWheel> {{
		%W yview scroll [expr {{-10 * (%D)}}] units
	}}
	bind {w} <Shift-MouseWheel> {{
		%W xview scroll [expr {{- (%D)}}] units
	}}
	bind {w} <Shift-Option-MouseWheel> {{
		%W xview scroll [expr {{-10 * (%D)}}] units
	}}
}} else {{
	bind {w} <MouseWheel> {{
		%W yview scroll [expr {{- (%D / 120) * 4}}] units
	}}
	bind {w} <Shift-MouseWheel> {{
		%W xview scroll [expr {{- (%D / 120) * 4}}] units
	}}
}}

if {{"x11" eq [tk windowingsystem]}} {{
	bind {w} <4> {{
	if {{!$tk_strictMotif}} {{
		%W yview scroll -5 units
	}}
	}}
	bind {w} <Shift-4> {{
	if {{!$tk_strictMotif}} {{
		%W xview scroll -5 units
	}}
	}}
	bind {w} <5> {{
	if {{!$tk_strictMotif}} {{
		%W yview scroll 5 units
	}}
	}}
	bind {w} <Shift-5> {{
	if {{!$tk_strictMotif}} {{
		%W xview scroll 5 units
	}}
	}}
}}""".format(w = self.frames[curindex][1]._w)) # *vomits*

			self.frames[curindex][1].config(yscrollcommand = self.__scrollalllistbox)
			self.frames[curindex][1].insert(tk.END, *(BLANK for _ in range(self.length)))
			self.frames[curindex][1].configure(
				self._get_listbox_conf(self.frames[curindex][1]))

			self.frames[curindex][3].grid(row = 0, column = 1, sticky = "news") #grid sort_indicator
			self.frames[curindex][2].grid(row = 0, column = 0, sticky = "news") #grid label
			self.frames[curindex][1].grid(row = 1, column = 0, sticky = "news", #grid listbox
				columnspan = 2)
			self.frames[curindex][0].grid(row = 0, column = curindex, sticky = "news") #grid frame

	def assigncolumn(self, col_id, req_frame):
		"""
		Sets display of a column given by its column id to req_frame.
		The same frame may not be occupied by multiple columns and must
		exist. Set req_frame to None to hide the column.
		"""
		if req_frame is not None:
			self.frames[req_frame] # Raises error on failure
			for col in self.columns:
				if col.assignedframe == req_frame:
					raise RuntimeError("Frame {} is already in use by column "
						"\"{}\"".format(req_frame, col.col_id))
		col = self._get_col_by_id(col_id)
		old_frame = col.assignedframe
		col.setdisplay(req_frame)
		# old frame is now column-less, so the list itself has to revert it
		if old_frame is None:
			return
		old_frameobj = self.frames[old_frame]
		old_frameobj[3].configure(text = BLANK)
		old_frameobj[2].configure(text = BLANK)
		old_frameobj[2].unbind("<Button-1>")
		old_frameobj[1].delete(0, tk.END)
		old_frameobj[1].insert(0, *[BLANK
			for _ in range(self.length)])
		self.framecontainer.grid_columnconfigure(old_frame,
			weight = 1, minsize = 0)
		old_frameobj[1].configure(width = _DEF_LISTBOX_WIDTH)

	def clear(self):
		"""Clears the MultiframeList."""
		for col in self.columns:
			col.data_clear()
		self.length = 0
		self.curcellx = None
		self.curcelly = None
		self.__lengthmod_callback()

	def config(self, **kwargs):
		"""
		Change configuration options of the MultiframeList/underlying frame.
		List of MultiframeList options, all others will be routed to the frame:

		-listboxheight: Height of the listboxes in displayed rows. Change this
			if the tkinter default of 10 doesn't work out for you.
		"""
		l = kwargs.pop("listboxheight")
		if l is not None:
			self.cnf["listboxheight"] = l
			self._cnf_listboxheight()
		super().configure(**kwargs)

	def configcolumn(self, col_id, **cnf):
		"""
		Update the configuration of the column referenced by col_id
		with the values specified in cnf as kwargs.
		"""
		col = self._get_col_by_id(col_id)
		col.config(**cnf)

	def format(self, targetcols = None, indices = None):
		"""
		Format the entire list based on the formatter functions in columns.
		Optionally, a list of columns to be formatted can be supplied by their
		id, which will leave all non-mentioned columns alone.
		Also, if index is specified, only the indices included in that list
		will be formatted.

		! Call this after all input has been performed !
		"""
		if indices is not None:
			for i in indices:
				tmp = self.length - 1
				if i > tmp:
					raise ValueError("Index is out of range.")
		if targetcols is None:
			for col in self.columns:
				col.format(exclusively = indices)
		else:
			for col_id in targetcols:
				self._get_col_by_id(col_id).format(exclusively = indices)
		self.__selectionmod_callback()

	def getcolumns(self):
		"""
		Returns a dict where key is a column id and value is the column's
		current display slot (frame). Value is None if the column is hidden.
		"""
		return {c.col_id: c.assignedframe for c in self.columns}

	def getselectedcell(self):
		"""
		Returns the coordinates of the currently selected cell as a tuple
		of length 2; (0, 0) starting in the top left corner;
		The two values may also be None.
		"""
		return (self.curcellx, self.curcelly)

	def getlastclick(self):
		"""
		Returns the absolute screen coordinates the last user interaction
		was made at as a tuple. May consist of int or None.
		This method can be used to get coordinates to open a popup window at.
		"""
		return (self.coordx, self.coordy)

	def getlen(self):
		"""Returns length of the MultiframeList."""
		return self.length

	def removecolumn(self, col_id):
		"""
		Deletes the column addressed by col_id, safely unregistering all
		related elements.
		"""
		col = self._get_col_by_id(col_id)
		self.assigncolumn(col_id, None)
		for i, j in enumerate(self.columns):
			if j.col_id == col_id:
				self.columns.pop(i)
				break
		del col

	def removeframes(self, amount):
		"""
		Safely remove the specified amount of frames from the
		MultiframeList, unregistering all related elements.
		"""
		to_purge = range(len(self.frames) - 1,
			len(self.frames) - amount - 1, -1)
		for col in self.columns:
			if col.assignedframe in to_purge:
				col.setdisplay(None)
		for i in to_purge:
			if self.curcellx is not None:
				if self.curcellx >= i:
					self.curcellx = i - 1
			self.frames[i][0].destroy()
			self.frames.pop(i)

	def removerow(self, index):
		"""Will delete the entire row at index."""
		if index > (self.length - 1):
			raise IndexError("Index to remove out of range.")
		for col in self.columns:
			col.data_pop(index)
		self.length -= 1
		self.__lengthmod_callback()

	def setselectedcell(self, x, y):
		"""
		Sets the selected cell to the specified x and y coordinates.
		You may also pass None to any of those.
		If outside of viewport, the frames will be scrolled towards the
		new index.

		Will generate a <<MultiframeSelect>> event.
		"""
		if not all(isinstance(v, (int, None)) for v in (x, y)):
			raise TypeError("Invalid type for x and/or y coordinate.")
		if x >= len(self.frames):
			raise ValueError("New x selection out of range.")
		if y >= self.length:
			raise ValueError("New y selection exceeds length.")
		self.curcellx = x
		self.curcelly = y
		if y is not None:
			for i in self.frames:
				i[1].see(self.curcelly)
		self.__selectionmod_callback()
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	#==DATA MODIFICATION, ALL==

	def insertrow(self, data, insindex = None):
		"""
		Inserts a row of data into the MultiframeList.

		Data should be supplied in the shape of a dict where a key is a
		column's id and the corresponding value is the element that should
		be appended to the column.
		If insindex is not specified, data will be appended, else inserted
			at the given position.
		"""
		for col in self.columns:
			if col.col_id in data:
				col.data_insert(data.pop(col.col_id), insindex)
			else:
				col.data_insert(BLANK, insindex)
		self.length += 1
		self.__lengthmod_callback()

	def setdata(self, data, reset_sortstate = True):
		"""
		Sets the data of the MultiframeList, clearing everything beforehand.

		Data has to be supplied as a dict where:
			- key is a column id
			- value is a list of values the column targeted by key should be set to.
			If the lists are of differing lengths, a ValueError will be raised.
		The function takes an optional reset_sortstate parameter to control whether
		or not to reset the sortstates on the columns. (Default True)
		"""
		if not data:
			self.clear(); return
		ln = len(data[next(iter(data))])
		if reset_sortstate:
			for col in self.columns:
				col.set_sortstate(2)
		for k in data:
			if len(data[k]) != ln:
				raise ValueError("Differing lengths in supplied column data.")
		for col in self.columns:
			if col.col_id in data:
				col.data_set(data.pop(col.col_id))
			else:
				col.data_set([BLANK for _ in range(ln)])
		self.length = ln
		self.curcellx, self.curcelly = None, None
		self.__lengthmod_callback()

	def setcell(self, col_to_mod, y, data):
		"""Sets the cell in col_to_mod at y to data."""
		col = self._get_col_by_id(col_to_mod)
		if y > (self.length - 1):
			raise IndexError("Cell index does not exist.")
		col.data_pop(y)
		col.data_insert(data, y)

	def setcolumn(self, col_to_mod, data):
		"""
		Sets column specified by col_to_mod to data.
		Raises an exception if length differs from the rest of the columns.
		"""
		for col in self.columns:
			col.set_sortstate(2)
		targetcol = self._get_col_by_id(col_to_mod)
		datalen = len(data)
		if len(self.columns) == 1:
			targetcol.data_set(data)
			self.length = datalen
			self.__lengthmod_callback()
			return
		for col in self.columns:
			if len(col.data) != datalen:
				raise ValueError("Length of supplied column data is "
					"different from other lengths.")
		targetcol.data_set(data)

	#==DATA RETRIEVAL, DICT, ALL==

	def getrows(self, start, end = None):
		"""
		Retrieve rows between a start and an optional end parameter.

		If end is omitted, only the row indexed at start will be included.
		If end is set to END, all data from start to the end of the
		MultiframeListbox will be returned.
		If start is set to ALL, all data that is present in the
		MultiframeListbox' columns will be included.
		This method will return two elements:
		A two-dimensional list that contains the requested rows from start to
			end, a row being unformatted data.
		A dict where the values are integers and the keys all column's ids.
			The integer for a column gives the index of all sub-lists in the
			first returned list that make up the data of a column, in order.

		For example, if the return values were:
		[["egg", "2", ""], ["foo", "3", "Comment"], ["bar", "0", ""]] and
		{"name_col":0, "comment_col":2, "rating_col":1}, the data of the
		column "name_col" would be ["egg", "foo", "bar"], "rating_col"
		["2", "3", "0"] and "comment_col" ["", "Comment", ""].
		"""
		if start == "all":
			start = 0
			end = self.length
		if end == END:
			end = self.length
		if end is None:
			end = start + 1
		col_id_map = {c.col_id: ci for ci, c in enumerate(self.columns)}
		r_data = [[col.data[idx] for col in self.columns] for idx in range(start, end)]
		# Performance location: out the window, on the sidewalk
		return r_data, col_id_map

	def getcolumn(self, col_id):
		"""Returns the data of the colum with col_id as a list."""
		col = self._get_col_by_id(col_id)
		return col.data

	def getcell(self, col_id, y):
		"""Returns element y of the column specified by col_id."""
		col = self._get_col_by_id(col_id)
		return col.data[y]

	#====SORT METHOD====

	def sort(self, _evt, call_col):
		"""
		Sort the list, modifying all column's data.

		This function is designed to only be called through labels,
		taking an event placeholder (which is ignored), followed by the
		calling column where id, sortstate and - if needed - the
		fallback type are read from.
		"""
		sortstate = call_col.sortstate
		caller_id = call_col.col_id
		scroll = None
		if len(self.frames) != 0:
			scroll = self.frames[0][1].yview()[0]
		rev = False
		new_sortstate = abs(int(sortstate) - 1)
		if new_sortstate:
			rev = True
		call_col.set_sortstate(new_sortstate)
		for col in self.getcolumns(): # reset sortstate of other columns
			if col != caller_id:
				self._get_col_by_id(col).set_sortstate(2)
		tmpdat, colidmap = self.getrows(ALL)
		datacol_index = colidmap[caller_id]
		try:
			tmpdat = sorted(tmpdat, key = itemgetter(datacol_index),
				reverse = rev)
		except TypeError:
			fb_type = call_col.config()["fallback_type"]
			if fb_type is None: raise
			for i in range(len(tmpdat)):
				tmpdat[i][datacol_index] = fb_type(tmpdat[i][datacol_index])
			tmpdat = sorted(tmpdat, key = itemgetter(datacol_index),
				reverse = rev)
		newdat = {}
		for col_id in colidmap:
			datacol_i = colidmap[col_id]
			newdat[col_id] = [i[datacol_i] for i in tmpdat]
		self.setdata(newdat, reset_sortstate = False)
		self.format()
		if scroll is not None:
			self.__scrollalllistbox(scroll, 1.0)

	#====INTERNAL METHODS====

	def _cnf_listboxheight(self):
		"""
		Callback for when the listbox height is changed via the
		config method.
		"""
		for frame in self.frames:
			frame[1].configure(height = self.cnf["listboxheight"])

	def _get_col_by_id(self, col_id):
		"""
		Returns the column specified by col_id, raises an exception if it
		is not found.
		"""
		for col in self.columns:
			if col.col_id == col_id:
				return col
		raise ValueError("No column with column id \"{}\".".format(col_id))

	def _get_listbox_conf(self, listbox):
		"""
		Create a dict of style options based on the ttk Style settings
		that listboxes can be directly configured with.

		The listbox passed to the method will be queried for its config and
		only configuration keys it returns present in the output dict.
		"""
		conf = self._DEFAULT_LISTBOX_CONFIG.copy()
		for style in (".", "MultiframeList.Listbox"):
			cur_style_cnf = self.ttkhookstyle.configure(style)
			if cur_style_cnf is not None:
				conf.update(cur_style_cnf)
		ok_options = listbox.configure().keys()
		conf = {k: v for k, v in conf.items() if k in ok_options}
		return conf

	def _get_listbox_entry_height(self, lb):
		"""
		Returns the height of a listbox' entry by measuring its
		font and border width parameters.
		"""
		fm = self.tk.call("font", "metrics", lb["font"]).split()
		return int(fm[fm.index("-linespace") + 1]) + 1 + \
			2 * int(lb["selectborderwidth"])

	def _get_index_from_mouse_y(self, lb, y_pos):
		"""
		Calculates the index of a listbox from pixel y position
		by measuring font height, y offset and border settings.
		"""
		offset = int(lb.yview()[0] * self.length)
		borderwidth = int(lb["borderwidth"])
		e_height = self._get_listbox_entry_height(lb)
		return ((y_pos - borderwidth) // e_height) + offset

	def __getdisplayedcolumns(self):
		"""
		Returns a list of references to the columns that are displaying
		their data currently, sorted starting at 0.
		"""
		return sorted([i for i in self.columns if i.assignedframe is not None],
			key = lambda col: col.assignedframe)

	def __callback_menu_button(self, _):
		"""
		User has pressed the menu button.
		This generates a <<MultiframeRightclick>> event and modifies
		self.coord[xy] to an appropriate value.
		"""
		if not self.frames:
			return
		if self.curcelly is None:
			return
		if self.curcellx is None:
			local_curcellx = 0
		else:
			local_curcellx = self.curcellx
		pseudo_lbl = self.frames[local_curcellx][0]
		pseudo_lbx = self.frames[local_curcellx][1]
		first_offset = pseudo_lbx.yview()[0]
		entry_height = self._get_listbox_entry_height(pseudo_lbx)
		tmp_x = pseudo_lbl.winfo_rootx() + 5
		tmp_y = entry_height * (self.curcelly - (self.length * first_offset)) + \
			20 + pseudo_lbl.winfo_rooty()
		tmp_x = int(round(tmp_x))
		tmp_y = int(round(tmp_y))
		if tmp_y < 0:
			tmp_y = 0
		tmp_y += 10
		self.coordx = tmp_x
		self.coordy = tmp_y
		self.event_generate("<<MultiframeRightclick>>", when = "tail")

	def __getemptyframes(self):
		"""Returns the indexes of all frames that are not assigned a column."""
		existingframes = list(range(len(self.frames)))
		assignedframes = [col.assignedframe for col in self.columns]
		return [f for f in existingframes if not f in assignedframes]

	def __relay_focus(self, *_):
		"""
		Called by frames when they are clicked so focus is given to the
		MultiframeList Frame itself.
		"""
		self.focus()

	def __setindex_lb(self, event, button, frameindex):
		"""Called by listboxes; GENERATES EVENT, sets the current index."""
		self.__relay_focus()
		if self.length == 0:
			return
		tosel = self._get_index_from_mouse_y(self.frames[frameindex][1], event.y)
		if tosel < 0:
			return
		if tosel >= self.length:
			tosel = self.length - 1
		self.curcelly = tosel
		self.curcellx = frameindex
		self.__selectionmod_callback()
		self.coordx = self.frames[frameindex][0].winfo_rootx() + event.x
		self.coordy = self.frames[frameindex][0].winfo_rooty() + 20 + event.y
		self.event_generate("<<MultiframeSelect>>", when = "tail")
		if button == self.rightclickbtn:
			self.event_generate("<<MultiframeRightclick>>", when = "tail")

	def __setindex_arr(self, direction):
		"""
		Executed when the MultiframeList receives <Up> and <Down> events,
		triggered by the user pressing the arrow keys.
		"""
		if self.curcelly == None:
			tosel = 0
		else:
			tosel = self.curcelly
			tosel += direction
		if tosel < 0 or tosel > self.length - 1:
			return
		self.curcelly = tosel
		self.__selectionmod_callback()
		for i in self.frames:
			i[1].see(self.curcelly)
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	def __lengthmod_callback(self):
		"""
		Called by some methods after the MultiframeList's length was
		modified. This method updates frames without a column so the amount
		of blank strings in them stays correct and modifies the current
		selection index in case it is out of bounds.
		"""
		for fi in self.__getemptyframes():
			curframelen = self.frames[fi][1].size()
			if curframelen != self.length:
				if curframelen > self.length:
					self.frames[fi][1].delete(self.length, tk.END)
				else: # curframelen < self.length
					self.frames[fi][1].insert(tk.END,
						*(BLANK for _ in range(self.length - curframelen)))
		if self.curcelly is None: return
		if self.curcelly > self.length - 1:
			self.curcelly = self.length - 1
		if self.curcelly < 0:
			self.curcelly = None
		self.__selectionmod_callback()

	def __scrollallbar(self, a, b, c = None):
		"""Bound to the scrollbar; Will scroll listboxes."""
		#c only appears when holding mouse and scrolling on the scrollbar
		if c:
			for i in self.frames:
				i[1].yview(a, b, c)
		else:
			for i in self.frames:
				i[1].yview(a, b)

	def __scrollalllistbox(self, a, b):
		"""Bound to all listboxes so that they will scroll the other ones
		and scrollbar.
		"""
		for i in self.frames:
			i[1].yview_moveto(a)
		self.scrollbar.set(a, b)

	def __selectionmod_callback(self):
		"""
		Called after selection (self.curcell[x/y]) is modified.
		Purely cosmetic effect, as actual selection access should only
		occur via self.getselectedcell()
		"""
		sel = self.curcelly
		if sel is None:
			for i in self.frames:
				i[1].selection_clear(0, tk.END)
			return
		for i in self.frames:
			i[1].selection_clear(0, tk.END)
			i[1].selection_set(sel)
			i[1].activate(sel)

	def __themeupdate(self, _):
		"""
		Called from event binding when the current theme changes.
		Changes Listbox look, as those are not available as ttk variants.
		"""
		if self.frames:
			conf = self._get_listbox_conf(self.frames[0][1])
		for i in self.frames:
			lbwidg = i[1]
			lbwidg.configure(**conf)

if __name__ == "__main__":
	from multiframe_list.demo import run_demo
	print("Running mfl", __version__)
	run_demo()
