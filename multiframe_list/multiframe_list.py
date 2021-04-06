"""
A module that brings the MultiframeList class with it.
Its purpose is to display items and their properties over
several colums and easily format, sort and manage them as part of a UI.
"""

import os

import tkinter as tk
import tkinter.ttk as ttk
from operator import itemgetter

__version__ = "2.4.0"
__author__ = "Square789"

BLANK = ""

_DEF_LISTBOX_WIDTH = 20
DRAG_THRES = 15
MIN_WIDTH = 30
WEIGHT = 1000

ALL = "all"
END = "end"

class DRAGINTENT:
	REORDER = 1
	RESIZE = 2

def _drag_intent(x, frame):
	if x < (MIN_WIDTH // 2) and frame != 0:
		return DRAGINTENT.RESIZE
	return DRAGINTENT.REORDER

SORTSYM = ("\u25B2", "\u25BC", "\u25A0") #desc, asc, none

SCROLLCOMMAND = \
"""if {{[tk windowingsystem] eq "aqua"}} {{
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
}}"""

class _Column():
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
		This option gets passed to the grid geometry manager. It will be 60 px
		at minimum.
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

	class Config():
		__slots__ = (
			"name", "sort", "minsize", "weight", "w_width", "formatter", "fallback_type",
		)
		def __init__(
			self,
			name = "<NO_NAME>",
			sort = False,
			minsize = 0,
			weight = 1,
			w_width = _DEF_LISTBOX_WIDTH,
			formatter = None,
			fallback_type = None,
		):
			self.name = name
			self.sort = sort
			self.minsize = minsize
			self.weight = weight
			self.w_width = w_width
			self.formatter = formatter
			self.fallback_type = fallback_type

	def __init__(self, mfl, col_id=None, **kwargs):
		if not isinstance(mfl, MultiframeList):
			raise TypeError("Bad Column parent, must be MultiframeList.")
		self.mfl = mfl
		self.assignedframe = None
		self.dragged = False
		self.pressed = None

		self._cnfcmd = {
			"name": self._cnf_name, "sort": self._cnf_sort,
			"minsize": self._cnf_minsize, "weight": lambda: False,
			"formatter": self._cnf_formatter, "w_width": self._cnf_w_width,
			"fallback_type": lambda: False,
		}

		if col_id is None:
			self.col_id = self._generate_col_id()
		else:
			if col_id in self.mfl.columns:
				raise ValueError(f"Column id {col_id!r} is already in use!")
			self.col_id = col_id

		self.data = [BLANK for _ in range(self.mfl.length)]
		self.sortstate = 2 # 0 if next sort will be descending, else 1

		self.cnf = self.Config(**kwargs)

	def __repr__(self):
		return (
			f"<{type(self).__name__} of {type(self.mfl).__name__} at "
			f"0x{id(self):016X}, col_id: {self.col_id}>"
		)

	def __len__(self):
		return len(self.data)

	def _generate_col_id(self):
		curid = 0
		while curid in self.mfl.columns:
			curid += 1
		return curid

	def _cnf_formatter(self): # NOTE: YES OR NO?
		self.format()

	# def _cnf_grid(self):
	#	if self.assignedframe is None:
	#		return
	#	cur_grid = self.mfl.framecontainer.grid_columnconfigure(self.assignedframe)
	#	callargs = {}
	#	for value in ("minsize", ):
	#		if cur_grid[value] != getattr(self.cnf, value):
	#			callargs[value] = getattr(self.cnf, value)
	#	if callargs:
	#		self.mfl.framecontainer.grid_columnconfigure(self.assignedframe, **callargs)

	def _cnf_minsize(self):
		if self.assignedframe is None:
			return
		self.mfl.framecontainer.grid_columnconfigure(
			self.assignedframe, minsize = max(self.cnf.minsize, MIN_WIDTH)
		)

	def _cnf_name(self):
		if self.assignedframe is None:
			return
		self.mfl.frames[self.assignedframe][2].config(text = self.cnf.name)

	def _cnf_sort(self):
		if self.assignedframe is None:
			return
		if self.cnf.sort:
			self.set_sortstate(self.sortstate)
		else:
			self.mfl.frames[self.assignedframe][3].configure(text = BLANK)

	def _cnf_w_width(self):
		if self.assignedframe is None:
			return
		self.mfl.frames[self.assignedframe][1].configure(width = self.cnf.w_width)

	def _label_on_buttonpress(self, evt):
		self.pressed = evt.x

	def _label_on_leave(self, evt):
		evt.widget.configure(cursor = "arrow")

	def _label_on_motion(self, evt):
		if self.pressed is not None:
			if self.dragged:
				self.mfl._on_column_drag(evt, self.assignedframe, self.dragged)
			elif not self.dragged and abs(evt.x - self.pressed) > DRAG_THRES:
				self.dragged = _drag_intent(self.pressed, self.assignedframe)
		else:
			cur = "sb_h_double_arrow" if \
				_drag_intent(evt.x, self.assignedframe) == DRAGINTENT.RESIZE else "arrow"
			evt.widget.configure(cursor = cur)

	def _label_on_release(self, evt):
		if not self.dragged and self.cnf.sort:
			self.mfl.sort(None, self)
		elif self.dragged:
			self.mfl._on_column_release(evt, self.assignedframe, self.dragged)
		self.dragged = False
		self.pressed = None

	def config(self, **kw):
		if not kw:
			return {s: getattr(self.cnf, s) for s in self.cnf.__slots__}
		for k, v in kw.items():
			if not k in self.Config.__slots__:
				raise ValueError(
					f"Unkown configuration arg {k!r}, must be one of "
					f"{', '.join(self.Config.__slots__)}."
				)
			setattr(self.cnf, k, v)
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
			if self.cnf.formatter is not None:
				self.mfl.frames[self.assignedframe][1].insert(index, self.cnf.formatter(elem))
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
		`self.cnf.formatter` and displays result.
		If exclusively is set (as an iterable), only specified indices
		will be formatted.
		"""
		if self.cnf.formatter is None or self.assignedframe is None:#
			return
		if exclusively is None:
			f_data = [self.cnf.formatter(i) for i in self.data]
			self.mfl.frames[self.assignedframe][1].delete(0, tk.END)
			self.mfl.frames[self.assignedframe][1].insert(tk.END, *f_data)
		else:
			for i in exclusively:
				tmp = self.data[i]
				self.mfl.frames[self.assignedframe][1].delete(i)
				self.mfl.frames[self.assignedframe][1].insert(i, self.cnf.formatter(tmp))

	def setdisplay(self, wanted_frame):
		"""
		Sets the display frame of the column to wanted_frame. To unregister,
		set it no None.
		May raise IndexError.
		"""
		if wanted_frame is None:
			self.being_dragged = self.being_pressed = False
			# This block effectively undoes anything the `_cnf_*` methods and the block below
			# do to the widgets and tries to get them into the default state.
			self.mfl._clear_frame(self.assignedframe)
			self.assignedframe = wanted_frame
			return

		self.assignedframe = wanted_frame
		self.mfl.frames[self.assignedframe][2].bind("<ButtonPress-1>", self._label_on_buttonpress)
		self.mfl.frames[self.assignedframe][2].bind("<Leave>", self._label_on_leave)
		self.mfl.frames[self.assignedframe][2].bind("<Motion>", self._label_on_motion)
		self.mfl.frames[self.assignedframe][2].bind("<ButtonRelease-1>", self._label_on_release)
		self.set_sortstate(self.sortstate)
		# NOTE: I don't think these two recurring lines warrant their own
		# "setframetodata" method.
		self.mfl.frames[self.assignedframe][1].delete(0, tk.END)
		self.mfl.frames[self.assignedframe][1].insert(tk.END, *self.data)
		for fnc in set(self._cnfcmd.values()):
			fnc()

	def set_sortstate(self, to):
		"""
		Sets the column's sortstate, also updating it on the UI if it is being
		displayed and sortable.
		"""
		if self.assignedframe is not None and self.cnf.sort:
			self.mfl.frames[self.assignedframe][3].configure(text = SORTSYM[to])
		self.sortstate = to


class MultiframeList(ttk.Frame):
	"""
	Instantiates a multiframe tkinter based list, for rough description
	see module docstring.

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

	class Config():
		__slots__ = ("listboxheight", "rightclickbtn", "reorderable")
		def __init__(
			self, listboxheight = 10, rightclickbtn = "3",
			reorderable = False
		):
			self.listboxheight = listboxheight
			self.rightclickbtn = rightclickbtn
			self.reorderable = reorderable

	def __init__(self, master, inicolumns = None, **kwargs):
		"""
		Arguments:
		Instantiation only:

		master - parent object, should be tkinter root or a tkinter widget

		inicolumns <List<Dict>>: The columns here will be created and displayed
			upon instantiation.
			The dicts supplied should take form of Column constructor kwargs. See
			the `multiframe_list._Column` class for a list of acceptable kwargs.

		Modifiable during runtime:

		rightclickbtn <Str>: The button that will trigger the MultiframeRightclick
			virtual event. It is "3" (standard) on Windows, this may differ from
			platform to platform.

		listboxheight <Int>: The height (In items) the listboxes will take up.
			10 by tkinter default.

		reorderable <Bool>: Whether the columns of the MultiframeList should be
			reorderable by the user dragging and dropping the column headers.

		"""
		super().__init__(master, takefocus = True)

		self.master = master
		self.cnf = self.Config(**kwargs)

		self.bind("<Up>", lambda _: self._on_arr_y(-1))
		self.bind("<Down>", lambda _: self._on_arr_y(1))
		self.bind("<Left>", lambda _: self._on_arr_x(-1, False))
		self.bind("<Right>", lambda _: self._on_arr_x(1, False))
		self.bind("<Control-Left>", lambda _: self._on_arr_x(-1, True))
		self.bind("<Control-Right>", lambda _: self._on_arr_x(1, True))
		self.bind("d", lambda _: print(self.curcellx, self.curcelly))
		self.bind("D", lambda _: print(self.curcellx, self.curcelly))
		if os.name == "nt":
			ctxtmen_btn = "App"
		elif os.name == "posix":
			ctxtmen_btn = "Menu"
		else:
			ctxtmen_btn = None

		if ctxtmen_btn is not None:
			self.bind(f"<KeyPress-{ctxtmen_btn}>", self.__callback_menu_button)

		self.ttkhookstyle = ttk.Style()
		self.bind("<<ThemeChanged>>", self.__themeupdate)

		self.curcellx = None
		self.curcelly = None
		self.coordx = None
		self.coordy = None

		self.pressed_frame = None
		self.pressed_x = None
		self.dragging = False

		self.scrollbar = ttk.Scrollbar(self, command = self.__scrollallbar)
		self.framecontainer = ttk.Frame(self)
		self.framecontainer.grid_rowconfigure(0, weight = 1)
		self._listboxheight_hack = ttk.Frame(self, width = 0)

		self.resize_highlight = ttk.Frame(
			self.framecontainer, style = "MultiframeListResizeInd.TFrame"
		)
		self.reorder_highlight = ttk.Frame(
			self.framecontainer, style = "MultiframeListReorderInd.TFrame"
		)
		self.frames = [] # Each frame contains interface elements for display.
		self.columns = {} # Columns will provide data storage capability as
		# well as some metadata.

		self.length = 0

		if inicolumns is not None:
			self.addframes(len(inicolumns))
			# using self.addcolumns would require iterating a dict relying
			# on the fact it's sorted, i don't like that so we copypaste 2 lines
			for index, colopt in enumerate(inicolumns):
				new_col = _Column(self, **colopt)
				new_col.setdisplay(index)
				self.columns[new_col.col_id] = new_col

		self.scrollbar.pack(fill = tk.Y, expand = 0, side = tk.RIGHT)
		self.framecontainer.pack(expand = 1, fill = tk.BOTH, side = tk.RIGHT)
		self._listboxheight_hack.pack(expand = 0, fill = tk.Y, side = tk.RIGHT)

	#====USER METHODS====

	def addcolumns(self, *coldicts):
		"""
		Takes any amount of dicts, then adds columns where the column
		constructor receives the dicts as kwargs. See the
		multiframe_list._Column class for a list of acceptable kwargs.
		"""
		for coldict in coldicts:
			new_col = _Column(self, **coldict)
			# Columns will give themselves a proper id
			self.columns[new_col.col_id] = new_col

	def addframes(self, amount):
		"""
		Adds amount of frames, display slots in a way, fills their listboxes
		up with empty strings and immediatedly displays them.
		"""
		startindex = len(self.frames)
		for i in range(amount):
			new_frame = [None for _ in range(4)]
			rcb = self.cnf.rightclickbtn
			curindex = startindex + i

			self.frames.append(new_frame)

			new_frame[0] = ttk.Frame(self.framecontainer)
			new_frame[0].grid_rowconfigure(1, weight = 1)
			new_frame[0].grid_columnconfigure(0, weight = 1)

			new_frame[1] = tk.Listbox(
				new_frame[0], exportselection = False, takefocus = False,
				height = self.cnf.listboxheight
			)
			new_frame[2] = ttk.Label(
				new_frame[0], text = BLANK, anchor = tk.W,
				style = "MultiframeListTitle.TLabel"
			)
			new_frame[3] = ttk.Label(
				new_frame[0], text = BLANK, anchor = tk.W,
				style = "MultiframeListSortInd.TLabel"
			)

			# REMOVE Listbox bindings from listboxes
			new_frame[1].bindtags((new_frame[1].bindtags()[0], '.', 'all'))
			def _handler_m1(event, self = self, button = 1, frameindex = curindex):
				return self.__setindex_lb(event, button, frameindex)
			def _handler_m3(event, self = self, button = rcb, frameindex = curindex):
				return self.__setindex_lb(event, button, frameindex)
			new_frame[1].bind(f"<Button-{rcb}>", _handler_m3)
			new_frame[1].bind("<Button-1>", _handler_m1)
			self.tk.eval(SCROLLCOMMAND.format(w = new_frame[1]._w))
			new_frame[1].configure(
				**self._get_listbox_conf(new_frame[1]),
				yscrollcommand = self.__scrollalllistbox
			)
			self._clear_frame(curindex)

			new_frame[3].grid(row = 0, column = 1, sticky = "news") # sort_indicator
			new_frame[2].grid(row = 0, column = 0, sticky = "news") # label
			new_frame[1].grid(row = 1, column = 0, sticky = "news", columnspan = 2) # listbox
			new_frame[0].grid(row = 0, column = curindex, sticky = "news") # frame
			new_frame[0].grid_propagate(False)

			self._listboxheight_hack.configure(height = new_frame[1].winfo_reqheight())

		self._y_selection_redraw()

	def assigncolumn(self, col_id, req_frame):
		"""
		Sets display of a column given by its column id to req_frame.
		The same frame may not be occupied by multiple columns and must
		exist. Set req_frame to None to hide the column.
		"""
		if req_frame is not None:
			self.frames[req_frame] # Raises error on failure
			for col in self.columns.values():
				if col.assignedframe == req_frame:
					raise RuntimeError(
						f"Frame {req_frame} is already in use by column {col.col_id!r}"
					)
		col = self._get_col_by_id(col_id)
		col.setdisplay(req_frame)
		self._y_selection_redraw()

	def clear(self):
		"""Clears the MultiframeList."""
		for col in self.columns.values():
			col.data_clear()
		self.length = 0
		self._set_curcellx(None)
		self.curcelly = None
		self.__lengthmod_callback()

	def config(self, **kwargs):
		"""
		Change configuration options of the MultiframeList/underlying frame.
		List of MultiframeList options, all others will be routed to the frame:

		-listboxheight: Height of the listboxes in displayed rows. Change this
			if the tkinter default of 10 doesn't work out for you.
		"""
		for mfl_arg in self.Config.__slots__:
			if mfl_arg in kwargs:
				old_value = getattr(self.cnf, mfl_arg)
				setattr(self.cnf, mfl_arg, kwargs.pop(mfl_arg))
				try:
					getattr(self, f"_cnf_{mfl_arg}")(old_value)
				except AttributeError:
					pass
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
		Also, if indices is specified, only the indices included in that list
		will be formatted.

		! Call this after all input has been performed !
		"""
		if indices is not None:
			tmp = self.length - 1
			for i in indices:
				if i > tmp:
					raise ValueError("Index is out of range.")
		if targetcols is None:
			for col in self.columns.values():
				col.format(exclusively = indices)
		else:
			for col_id in targetcols:
				self._get_col_by_id(col_id).format(exclusively = indices)
		self._y_selection_redraw()

	def getcolumns(self):
		"""
		Returns a dict where key is a column id and value is the column's
		current display slot (frame). Value is None if the column is hidden.
		"""
		return {c.col_id: c.assignedframe for c in self.columns.values()}

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
		self.columns.pop(col_id)

	def removeframes(self, amount):
		"""
		Safely remove the specified amount of frames from the
		MultiframeList, unregistering all related elements.
		"""
		to_purge = range(len(self.frames) - 1, len(self.frames) - amount - 1, -1)
		for col in self.columns.values():
			if col.assignedframe in to_purge:
				col.setdisplay(None)
		for i in to_purge:
			if self.curcellx is not None and self.curcellx >= i:
				self._set_curcellx(i - 1)
			self.framecontainer.grid_columnconfigure(i, weight = 0)
			self.frames[i][0].destroy()
			self.frames.pop(i)

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
		if isinstance(x, int) and x >= len(self.frames):
			raise ValueError("New x selection out of range.")
		if isinstance(y, int) and y >= self.length:
			raise ValueError("New y selection exceeds length.")
		self._set_curcellx(x)
		self.curcelly = y
		if y is not None:
			for i in self.frames:
				i[1].see(self.curcelly)
		self._y_selection_redraw()
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	#==DATA MODIFICATION, ALL==

	def insertrow(self, data, insindex = None, reset_sortstate = True):
		"""
		Inserts a row of data into the MultiframeList.

		Data should be supplied in the shape of a dict where a key is a
		column's id and the corresponding value is the element that should
		be appended to the column.
		If insindex is not specified, data will be appended, else inserted
			at the given position.
			The function takes an optional reset_sortstate parameter to control whether
		or not to reset the sortstates on all columns. (Default True)
		"""
		if reset_sortstate:
			self._reset_sortstate()
		for col in self.columns.values():
			if col.col_id in data:
				col.data_insert(data.pop(col.col_id), insindex)
			else:
				col.data_insert(BLANK, insindex)
		self.length += 1
		self.__lengthmod_callback()

	def removerow(self, index):
		"""
		Deletes the entire row at index.
		"""
		if index > (self.length - 1):
			raise IndexError("Index to remove out of range.")
		for col in self.columns.values():
			col.data_pop(index)
		self.length -= 1
		self.__lengthmod_callback()

	def setdata(self, data, reset_sortstate = True):
		"""
		Sets the data of the MultiframeList, clearing everything beforehand.

		Data has to be supplied as a dict where:
			- key is a column id
			- value is a list of values the column targeted by key should be set to.
			If the lists are of differing lengths, a ValueError will be raised.
		The function takes an optional reset_sortstate parameter to control whether
		or not to reset the sortstates on all columns. (Default True)
		"""
		if not data:
			self.clear(); return
		ln = len(data[next(iter(data))])
		if any(len(d) != ln for d in data.values()):
			raise ValueError("Differing lengths in supplied column data.")
		if reset_sortstate:
			self._reset_sortstate()
		for col in self.columns.values():
			if col.col_id in data:
				col.data_set(data.pop(col.col_id))
			else:
				col.data_set([BLANK for _ in range(ln)])
		self.length = ln
		self.__lengthmod_callback()
		self._set_curcellx(None)
		self.curcelly = None

	def setcell(self, col_to_mod, y, data, reset_sortstate = True):
		"""
		Sets the cell in col_to_mod at y to data.
		Formatter is applied automatically, if present.
		The function takes an optional reset_sortstate parameter to control whether
		or not to reset the sortstates on all columns. (Default True)
		"""
		if reset_sortstate:
			self._reset_sortstate()
		col = self._get_col_by_id(col_to_mod)
		if y > (self.length - 1):
			raise IndexError("Cell index does not exist.")
		col.data_pop(y)
		col.data_insert(data, y)

	def setcolumn(self, col_to_mod, data, reset_sortstate = True):
		"""
		Sets column specified by col_to_mod to data.
		Raises an exception if length differs from the rest of the columns.
		The function takes an optional reset_sortstate parameter to control whether		
		or not to reset the sortstates on all columns. (Default True)
		"""
		if reset_sortstate:
			self._reset_sortstate()
		targetcol = self._get_col_by_id(col_to_mod)
		datalen = len(data)
		if len(self.columns) == 1:
			targetcol.data_set(data)
			self.length = datalen
			self.__lengthmod_callback()
		else:
			for col in self.columns.values():
				if len(col.data) != datalen:
					raise ValueError(
						"Length of supplied column data is different from length of " \
						"column {col.col_id!r}."
					)
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
		col_id_map = {col_id: i for i, col_id in enumerate(self.columns.keys())}
		r_data = [[col.data[idx] for col in self.columns.values()] for idx in range(start, end)]
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

	def sort(self, _, call_col):
		"""
		Sort the list, modifying all column's data.

		This function is designed to only be called through labels,
		taking an event placeholder (which is ignored), followed by the
		calling column where id, sortstate and - if needed - the
		fallback type are read from.
		"""
		sortstate = call_col.sortstate
		caller_id = call_col.col_id
		scroll = self._scroll_get()
		new_sortstate = abs(int(sortstate) - 1)
		rev = bool(new_sortstate)
		call_col.set_sortstate(new_sortstate)
		for col in self.columns.values(): # reset sortstate of other columns
			if col.col_id != caller_id:
				col.set_sortstate(2)
		tmpdat, colidmap = self.getrows(ALL)
		datacol_index = colidmap[caller_id]
		try:
			tmpdat = sorted(tmpdat, key = itemgetter(datacol_index), reverse = rev)
		except TypeError:
			fb_type = call_col.config().fallback_type
			if fb_type is None:
				raise
			for i, _ in enumerate(tmpdat):
				tmpdat[i][datacol_index] = fb_type(tmpdat[i][datacol_index])
			tmpdat = sorted(tmpdat, key = itemgetter(datacol_index), reverse = rev)
		newdat = {}
		for col_id in colidmap:
			datacol_i = colidmap[col_id]
			newdat[col_id] = [i[datacol_i] for i in tmpdat]
		self.setdata(newdat, reset_sortstate = False)
		self.format()
		self._scroll_restore(scroll)

	#====INTERNAL METHODS - cnf====

	def _cnf_listboxheight(self, _):
		"""
		Callback for when the listbox height is changed via the
		config method.
		"""
		for frame in self.frames:
			frame[1].configure(height = self.cnf.listboxheight)
		if self.frames:
			self._listboxheight_hack.configure(height = self.frames[0][1].winfo_reqheight())

	def _cnf_rightclickbtn(self, old):
		"""
		Callback for when rightclickbtn is changed via the config
		method.
		"""
		for idx, frame in enumerate(self.frames):
			def _right_click_handler(
				event, self = self, button = self.cnf.rightclickbtn, frameidx = idx
			):
				return self.__setindex_lb(event, button, frameidx)
			frame[1].unbind(f"<Button-{old}>")
			frame[1].bind(f"<Button-{self.cnf.rightclickbtn}>", _right_click_handler)

	#====INTERNAL METHODS====

	def _clear_frame(self, frame_idx):
		"""
		Will set up default bindings on a frame, and clear its label,
		sort and listbox, as well as reset its grid manager parameters.
		Usable for a part of the work that goes into removing a column
		from a frame or initial setup.
		"""
		tgt_frame = self.frames[frame_idx]
		tgt_frame[0].configure(width = -1)
		tgt_frame[1].delete(0, tk.END)
		tgt_frame[1].insert(0, *(BLANK for _ in range(self.length)))
		tgt_frame[1].configure(width = _DEF_LISTBOX_WIDTH)
		tgt_frame[2].configure(text = BLANK)
		tgt_frame[2].bind("<Button-1>",
			lambda e: self._on_empty_frame_press(e, frame_idx)
		)
		tgt_frame[2].bind("<ButtonRelease-1>",
			lambda e: self._on_empty_frame_release(e, frame_idx)
		)
		tgt_frame[2].bind("<Leave>",
			lambda e: self._on_empty_frame_leave(e, frame_idx)
		)
		tgt_frame[2].bind("<Motion>",
			lambda e: self._on_empty_frame_motion(e, frame_idx)
		)
		tgt_frame[3].configure(text = BLANK)
		self.framecontainer.grid_columnconfigure(frame_idx, weight = WEIGHT, minsize = 0)

	def _get_clamps(self, dragged_frame):
		c_frame = self.frames[dragged_frame]
		p_frame = self.frames[dragged_frame - 1]
		return (
			p_frame[0].winfo_x() +
				self.framecontainer.grid_columnconfigure(dragged_frame - 1)["minsize"],
			c_frame[0].winfo_width() + c_frame[0].winfo_x() -
				self.framecontainer.grid_columnconfigure(dragged_frame)["minsize"]
		)

	def _get_clamped_resize_pos(self, dragged_frame, event):
		"""
		Return the position a resize operation started on the label of frame
		`dragged_frame` should be at, relative to the MultiframeList's position.
		"""
		cmin, cmax = self._get_clamps(dragged_frame)
		abs_pos = event.widget.winfo_rootx() + event.x - self.framecontainer.winfo_rootx()
		return max(cmin, min(abs_pos, cmax))

	def _get_col_by_id(self, col_id):
		"""
		Returns the column specified by col_id, raises an exception if it
		is not found.
		"""
		col = self.columns.get(col_id)
		if col is None:
			raise ValueError(f"No column with column id {col_id!r}!")
		return col

	def _get_col_by_frame(self, frame):
		"""
		Returns the column in `frame` or None if there is none in it.
		"""
		for col in self.columns.values():
			if col.assignedframe == frame:
				return col
		return None

	def _get_frame_at_x(self, x):
		"""
		Return frame index of the frame at screen pixel position x,
		clamping to 0 and (len(self.frames) - 1).
		"""
		highlight_idx = -1
		for frame in self.frames:
			if frame[1].winfo_rootx() > x:
				break
			highlight_idx += 1
		return max(highlight_idx, 0)

	def _get_listbox_conf(self, listbox, xactive = False):
		"""
		Create a dict of style options based on the ttk Style settings in
		`style_identifier` that listboxes can be directly configured with.

		The listbox passed to the method will be queried for its config and
		only configuration keys it returns present in the output dict.
		"""
		conf = self._DEFAULT_LISTBOX_CONFIG.copy()
		to_query = (".", "MultiframeList.Listbox")
		for style in to_query + (("XActive.MultiframeList.Listbox", ) if xactive else ()):
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
		return int(fm[fm.index("-linespace") + 1]) + 1 + 2 * int(lb["selectborderwidth"])

	def _get_index_from_mouse_y(self, lb, y_pos):
		"""
		Calculates the index of a listbox from pixel y position
		by measuring font height, y offset and border settings.
		"""
		offset = int(lb.yview()[0] * self.length)
		borderwidth = int(lb["borderwidth"])
		e_height = self._get_listbox_entry_height(lb)
		return ((y_pos - borderwidth) // e_height) + offset

	def _on_arr_x(self, direction, with_ctrl):
		"""
		Executed when the MultiframeList receives <Left> and <Right> events,
		triggered by the user pressing the arrow keys. Optionally these
		may also have been called with the ctrl key held.
		If with_ctrl is specified, the contents of the currently active
		frame will be swapped with the one next to it.
		"""
		if self.curcelly is None and self.length > 0:
			self.curcelly = 0
			self._y_selection_redraw()
		oldx = self.curcellx
		newx = 0 if oldx is None else oldx + direction
		if newx < 0 or newx > len(self.frames) - 1:
			return
		self._set_curcellx(newx)
		if with_ctrl and oldx is not None:
			self._swap_by_frame(oldx, newx)
			self._y_selection_redraw()

	def _on_arr_y(self, direction):
		"""
		Executed when the MultiframeList receives <Up> and <Down> events,
		triggered by the user pressing the arrow keys.
		"""
		if self.curcellx is None and self.frames:
			self._set_curcellx(0)
		newy = 0 if self.curcelly is None else self.curcelly + direction
		if newy < 0 or newy > self.length - 1:
			return
		self.curcelly = newy
		self._y_selection_redraw()
		for i in self.frames:
			i[1].see(self.curcelly)
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	def _on_column_release(self, event, released_frame, drag_intent):
		if drag_intent == DRAGINTENT.REORDER:
			self.reorder_highlight.place_forget()
			self._swap_by_frame(
				self._get_frame_at_x(event.widget.winfo_rootx() + event.x),
				released_frame
			)
		elif drag_intent == DRAGINTENT.RESIZE:
			self.resize_highlight.place_forget()
			total_weight = (
				self.framecontainer.grid_columnconfigure(released_frame)["weight"] +
				self.framecontainer.grid_columnconfigure(released_frame - 1)["weight"]
			)
			minclamp, maxclamp = self._get_clamps(released_frame)
			maxclamp += (1 if maxclamp == minclamp else 0) # Paranoia to prevent zero div
			pos = (self._get_clamped_resize_pos(released_frame, event) - minclamp)
			# Subtracting minclamp from maxclamp will effectively get the area pos moves in
			first_weight = round((pos / (maxclamp - minclamp)) * total_weight)
			scnd_weight = total_weight - first_weight
			self.framecontainer.grid_columnconfigure(released_frame, weight = scnd_weight)
			self.framecontainer.grid_columnconfigure(released_frame - 1, weight = first_weight)

	def _on_column_drag(self, event, dragged_frame, drag_intent):
		if drag_intent == DRAGINTENT.REORDER:
			highlight_idx = self._get_frame_at_x(event.widget.winfo_rootx() + event.x)
			self.reorder_highlight.place(
				x = self.frames[highlight_idx][0].winfo_x(),
				y = self.frames[highlight_idx][1].winfo_y(),
				width = 3, height = self.frames[highlight_idx][1].winfo_height()
			)
			self.reorder_highlight.tkraise()
		elif drag_intent == DRAGINTENT.RESIZE:
			self.resize_highlight.place(
				x = self._get_clamped_resize_pos(dragged_frame, event),
				y = self.frames[0][1].winfo_y(),
				width = 3, height = self.frames[0][1].winfo_height()
			)
			self.resize_highlight.tkraise()

	def _on_empty_frame_leave(self, evt, _):
		evt.widget.configure(cursor = "arrow")

	def _on_empty_frame_motion(self, evt, fidx):
		if self.pressed_frame is not None:
			if self.dragging is not None:
				self._on_column_drag(evt, fidx, self.dragging)
			elif not self.dragging and abs(evt.x - self.pressed_x) > DRAG_THRES:
				self.dragging = _drag_intent(evt.x, self.pressed_frame)

	def _on_empty_frame_press(self, evt, fidx):
		self.pressed_frame = fidx
		self.pressed_x = evt.x

	def _on_empty_frame_release(self, evt, fidx):
		if self.dragging is not None:
			self._on_column_release(evt, fidx, self.dragging)
		self.pressed_frame = self.pressed_x = None
		self.dragging = None

	def _swap_by_frame(self, tgt_frame, src_frame):
		"""
		Swaps the contents of two frames. Whether any, none or both of them
		are blank is handled properly. 
		"""
		tgt_col = src_col = None
		for tcol_id, col in self.columns.items():
			if col.assignedframe == tgt_frame:
				tgt_col = self.columns[tcol_id]
			if col.assignedframe == src_frame:
				src_col = self.columns[tcol_id]
		if tgt_col is src_col: # They're the same or both None, no action required
			return
		scroll = self._scroll_get()
		if src_col is not None: src_col.setdisplay(None)
		if tgt_col is not None: tgt_col.setdisplay(None)
		if src_col is not None: src_col.setdisplay(tgt_frame)
		if tgt_col is not None: tgt_col.setdisplay(src_frame)
		self._scroll_restore(scroll)
		self._y_selection_redraw()

	def _y_selection_redraw(self):
		"""
		Should be called after `self.curcelly` is modified.
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

	def _set_curcellx(self, new_x):
		"""
		Use this for any change to `self.curcellx`.
		Will configure the `XActive` style appropiately.
		NOTE maybe use a @property setter?
		"""
		old_x = self.curcellx
		self.curcellx = new_x
		if old_x is not None:
			self.frames[old_x][1].configure(
				**self._get_listbox_conf(self.frames[old_x][1])
			)
		if new_x is not None:
			self.frames[new_x][1].configure(
				**self._get_listbox_conf(self.frames[new_x][1], True)
			)

	def _scroll_get(self):
		if not self.frames:
			return None
		return self.frames[0][1].yview()[0]

	def _scroll_restore(self, scroll):
		if scroll is not None:
			self.__scrollalllistbox(scroll, 1.0)

	def _reset_sortstate(self):
		"""
		Reset the sortstate of all columns to 2.
		"""
		for column in self.columns.values():
			column.set_sortstate(2)

	def __getdisplayedcolumns(self):
		"""
		Returns a list of references to the columns that are displaying
		their data currently, sorted starting at 0.
		"""
		return sorted(
			[c for c in self.columns.values() if c.assignedframe is not None],
			key = lambda col: col.assignedframe
		)

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
		existingframes = range(len(self.frames))
		assignedframes = [col.assignedframe for col in self.columns.values()]
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
		self._set_curcellx(frameindex)
		self._y_selection_redraw()
		self.coordx = self.frames[frameindex][0].winfo_rootx() + event.x
		self.coordy = self.frames[frameindex][0].winfo_rooty() + 20 + event.y
		self.event_generate("<<MultiframeSelect>>", when = "tail")
		if button == self.cnf.rightclickbtn:
			self.event_generate("<<MultiframeRightclick>>", when = "tail")

	def __lengthmod_callback(self):
		"""
		Should be called after the MultiframeList's length was
		modified. This method updates frames without a column so the amount
		of blank strings in them stays correct and modifies the current
		selection index in case it is out of bounds.
		"""
		for fi in self.__getemptyframes():
			curframelen = self.frames[fi][1].size()
			if curframelen > self.length:
				self.frames[fi][1].delete(self.length, tk.END)
			elif curframelen < self.length:
				self.frames[fi][1].insert(
					tk.END, *(BLANK for _ in range(self.length - curframelen))
				)
		if self.curcelly is None:
			return
		if self.curcelly > self.length - 1:
			self.curcelly = self.length - 1
		if self.curcelly < 0:
			self.curcelly = None
		self._y_selection_redraw()

	def __scrollallbar(self, *args):
		"""Bound to the scrollbar; Will scroll listboxes."""
		# args can have 2 or 3 values
		for i in self.frames:
			i[1].yview(*args)

	def __scrollalllistbox(self, a, b):
		"""Bound to all listboxes so that they will scroll the other ones
		and scrollbar.
		"""
		for i in self.frames:
			i[1].yview_moveto(a)
		self.scrollbar.set(a, b)

	def __themeupdate(self, _):
		"""
		Called from event binding when the current theme changes.
		Changes Listbox look, as those are not available as ttk variants.
		"""
		if self.frames:
			conf = self._get_listbox_conf(self.frames[0][1])
			axconf = self._get_listbox_conf(self.frames[0][1], True)
		for i, f in enumerate(self.frames):
			f[1].configure(**(axconf if i == self.curcellx else conf))

if __name__ == "__main__":
	from multiframe_list.demo import run_demo
	run_demo()
