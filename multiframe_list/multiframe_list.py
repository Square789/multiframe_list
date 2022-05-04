"""
A module that brings the MultiframeList class with it.
Its purpose is to display items and their properties over
several colums and easily format, sort and manage them as part of a UI.
"""

from enum import IntEnum
from operator import itemgetter
import os
import tkinter as tk
import tkinter.ttk as ttk

__version__ = "4.0.1"
__author__ = "Square789"

NoneType = type(None)

BLANK = ""
_DEF_LISTBOX_WIDTH = 20
DRAG_THRES = 10
MIN_WIDTH = 30
WEIGHT = 1000

ALL = "all"
END = "end"

class DRAGINTENT(IntEnum):
	REORDER = 0
	RESIZE = 1

class SELECTION_TYPE(IntEnum):
	SINGLE = 0
	MULTIPLE = 1

def _drag_intent(x, frame):
	if x < (MIN_WIDTH // 2) and frame != 0:
		return DRAGINTENT.RESIZE
	return DRAGINTENT.REORDER

def _find_consecutive_sequences(lst):
	"""
	Given a **descendedly sorted list**, returns a list of ranges
	of all consecutively descending ranges of numbers in the
	given list. Duplicate numbers following one another are treated
	as a single number.
	Example: `[6, 5, 5, 4, 2, 1]` -> `[range(4, 7), range(1, 3)]`
	"""
	if not lst:
		return []
	last_start = lst[0]
	last = None
	res = []
	for x in lst:
		if last is not None and last != x and last != x + 1:
			res.append(range(last, last_start + 1))
			last_start = x
		last = x
	res.append(range(last, last_start + 1))
	return res

SORTSYM = ("\u25B2", "\u25BC", "\u25A0") # desc, asc, none

# State modifier flags for tk event. These are hardcoded by tuple position
# in tkinter.
def with_shift(e):
	return bool(e.state & 1)

def with_ctrl(e):
	return bool(e.state & 4)

SCROLLCOMMAND = """
if {{[tk windowingsystem] eq "aqua"}} {{
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
}}
"""

class _Column():
	"""
	Class whose purpose is to store data and information regarding a
	column. Can be assigned to frames of a MultiframeList, displaying
	its data in there.
	!!! Columns should not be instantiated or controlled directly,
	only through methods of a MultiframeList !!!
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
	sortkey: A function that will be used to sort values in this column,
		just like the regular `sorted` `key` kwarg.
	minsize: Specify the minimum amount of pixels the column should be wide.
		This option gets passed to the grid geometry manager and will at least
		be `MIN_WIDTH`.
	weight: Weight parameter, passed to the grid geometry manager. Note that
		it should be in proportion with `WEIGHT`, as default weights are very large.
	formatter: A function that formats each element in a column's datalist.
		This is especially useful for i. e. dates, where you want
		to be able to sort by a unix timestamp but still be able to have the
		dates in a human-readable format.
	fallback_type: A datatype that all elements of the column will be converted
		to in case it has to be sorted and the sort fails due to a TypeError.
		Note that this will modify the contained elements upon sorting and is
		meant for type correction if they are entered uncleanly. For a key
		function, see `sortkey`.
		If not specified and elements are of different types, exception will be
		raised normally.
	dblclick_cmd: A command that will be run when the column is double-clicked.
		Will be called with an event as only parameter.
	"""
	# COLUMNS ARE RESPONSIBLE FOR UI UPDATING. GENERAL FLOW LIKE THIS:
	# USER INTERFACES WITH THE MFL, MFL KEEPS TRACK OF A FEW LISTS AND
	# VARS, VALIDATES, GIVES COMMANDS TO COLUMNS, COLUMNS UPDATE UI
	# THEMSELVES

	class Config():
		__slots__ = (
			"name", "sort", "sortkey", "minsize", "weight", "formatter",
			"fallback_type", "dblclick_cmd",
		)
		def __init__(
			self,
			name = BLANK, sort = False, sortkey = None,
			minsize = MIN_WIDTH, weight = WEIGHT, formatter = None,
			fallback_type = None, dblclick_cmd = None,
		):
			self.name = name
			self.sort = sort
			self.sortkey = sortkey
			self.minsize = minsize
			self.weight = weight
			self.formatter = formatter
			self.fallback_type = fallback_type
			self.dblclick_cmd = dblclick_cmd

	def __init__(self, mfl, col_id = None, **kwargs):
		if not isinstance(mfl, MultiframeList):
			raise TypeError("Bad Column parent, must be MultiframeList.")
		self.mfl = mfl
		self.assignedframe = None

		self._cnfcmd = {
			"name": self._cnf_name, "sort": self._cnf_sort,
			"sortkey": lambda: False, "minsize": self._cnf_grid,
			"weight": self._cnf_grid, "formatter": self.format,
			"fallback_type": lambda: False, "dblclick_cmd": self._cnf_dblclick_cmd,
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

	def _cnf_dblclick_cmd(self):
		if self.assignedframe is None:
			return
		if self.cnf.dblclick_cmd is None:
			self.mfl.frames[self.assignedframe][1].unbind("<Double-Button-1>")
		else:
			self.mfl.frames[self.assignedframe][1].bind(
				"<Double-Button-1>", self.cnf.dblclick_cmd
			)

	def _cnf_grid(self):
		# Hacky corrector
		if self.cnf.minsize < MIN_WIDTH:
			self.cnf.minsize = MIN_WIDTH
		if self.assignedframe is None:
			return
		cur_grid = self.mfl.framecontainer.grid_columnconfigure(self.assignedframe)
		callargs = {}
		for value in ("minsize", "weight"):
			if cur_grid[value] != getattr(self.cnf, value):
				callargs[value] = getattr(self.cnf, value)
		if callargs:
			self.mfl.framecontainer.grid_columnconfigure(self.assignedframe, **callargs)

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

	def data_delete(self, from_, to = None):
		"""
		Removes the elements from `from_` to `to` (end-exclusive), or
		just `from_` if `to` is not given. No effect if `to` <= `from_`.
		Refreshes interface if assigned a frame.
		"""
		to = from_ + 1 if to is None else to
		if to <= from_:
			return
		self.data = self.data[:from_] + self.data[to:]
		if self.assignedframe is not None:
			self.mfl.frames[self.assignedframe][1].delete(from_, to - 1)

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
		self.mfl.frames[self.assignedframe][2].bind(
			"<ButtonPress-1>",
			lambda evt: self.mfl._on_frame_header_press(evt, self.assignedframe)
		)
		self.mfl.frames[self.assignedframe][2].bind(
			"<Leave>",
			self.mfl._on_frame_header_leave
		)
		self.mfl.frames[self.assignedframe][2].bind(
			"<Motion>",
			lambda evt: self.mfl._on_frame_header_motion(evt, self.assignedframe)
		)
		self.mfl.frames[self.assignedframe][2].bind(
			"<ButtonRelease-1>",
			lambda evt: self.mfl._on_frame_header_release(evt, self.assignedframe)
		)
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
	A multiframe tkinter based listview, for rough description see module docstring.

	A terrible idea of a feature:
		The MultiframeList will grab the currently active theme (as well as
			listen to the <<ThemeChanged>> event) and attempt to apply style
			configuration options in the current theme's style called
			"MultiframeList.Listbox" to its listboxes, as those are not
			available as ttk variants.
		The column title labels listen to the style "MultiframeListTitle.TLabel"
		The column sort indicators listen to the style "MultiframeListSortInd.Tlabel"
		The reorder/resizing indicators listen to the styles
			"MultiframeListResizeInd.TFrame" and "MultiframeListReorderInd.TFrame".
		The styles "MultiframeList.ActiveCell" and "MultiframeList.ActiveRow" are
			responsible for the colors of the active cell. They are implemented by
			calling the listboxes' `itemconfigure` method and thus only support the
			arguments given by it: `foreground`, `background`, `selectforeground` and
			`selectbackground`.
			"ActiveRow" is only relevant if the MultiframeList is configured to color
			the active cell's row as well.

	The list broadcasts the Virtual event "<<MultiframeSelect>>" after the selection
		is modified in any way.
	The list broadcasts the Virtual event "<<MultiframeRightclick>>" whenever the right
		click mouse button is released or the context menu button is pressed.
	The list will reset the active selection when Escape is pressed.
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

	_DEFAULT_ITEMCONFIGURE = {
		"background": "",
		"foreground": "",
		"selectbackground": "",
		"selectforeground": "",
	}

	class Config():
		__slots__ = (
			"rightclickbtn", "click_key", "listboxheight", "reorderable",
			"resizable", "selection_type", "active_cell_span_row", "active_cell_style",
			"active_cell_row_style",
		)
		def __init__(
			self, rightclickbtn = "3", click_key = "space", listboxheight = 10,
			reorderable = False, resizable = False, selection_type = SELECTION_TYPE.MULTIPLE,
			active_cell_span_row = False, active_cell_style = None, active_cell_row_style = None,
		):
			self.rightclickbtn = rightclickbtn
			self.click_key = click_key
			self.listboxheight = listboxheight
			self.reorderable = reorderable
			self.resizable = resizable
			self.selection_type = selection_type
			self.active_cell_span_row = active_cell_span_row
			self.active_cell_style = {} if active_cell_style is None \
				else active_cell_style
			self.active_cell_row_style = {} if active_cell_row_style is None \
				else active_cell_row_style

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

		rightclickbtn <Str>: The mouse button that will trigger the
			MultiframeRightclick virtual event. It is "3" (standard) on Windows,
			this may differ from platform to platform.

		click_key <Str>: The key to be used for clicking cells via keyboard
			navigation. "space" by default.

		listboxheight <Int>: The height (In items) the listboxes will take up.
			10 by tkinter default.

		reorderable <Bool>: Whether the columns of the MultiframeList should be
			reorderable by the user dragging and dropping the column headers
			as well as Ctrl-Left/Ctrl-Right. False by default.

		resizable <Bool>: Whether the columns of the MultiframeList should be
			resizable by the user dragging the column headers. False by default.

		selection_type <SELECTION_TYPE>: Selection type to use for the MultiframeList.
			When changed, the selection will be cleared. MULTIPLE by default.

		active_cell_span_row <Bool>: Whether the selected active cell will apply a
			per-item style across its entire row. False by default.
		"""
		super().__init__(master, takefocus = True)

		self.master = master
		self.cnf = self.Config(**kwargs)

		self.bind("<Up>", lambda e: self._on_arrow_y(e, -1))
		self.bind("<Down>", lambda e: self._on_arrow_y(e, 1))
		self.bind("<Left>", lambda e: self._on_arrow_x(e, -1))
		self.bind("<Right>", lambda e: self._on_arrow_x(e, 1))

		if os.name == "nt":
			ctxtmen_btn = "App"
		elif os.name == "posix":
			ctxtmen_btn = "Menu"
		else:
			ctxtmen_btn = None
		if ctxtmen_btn is not None:
			self.bind(f"<KeyPress-{ctxtmen_btn}>", self._on_menu_button)
		self.bind(f"<KeyPress-{self.cnf.click_key}>", self._on_click_key)
		self.bind(f"<Escape>", lambda _: self._selection_clear(with_event = True))

		self.ttk_style = ttk.Style()
		self.bind("<<ThemeChanged>>", self._theme_update)

		# Last direct cell that was interacted with
		self.active_cell_x = None
		self.active_cell_y = None
		# Listbox-local coordinate the interaction was made at
		self.coordx = None
		self.coordy = None
		# Selected items 
		self.selection = set()
		# --Stolen-- borrowed from tk, the first item a selection was started
		# with, used for expanding it via shift-clicks/Up-Downs
		self._selection_anchor = None
		# The element last dragged over in a mouse dragging selection.
		# Does not include the initially clicked element.
		self._last_dragged_over_element = None
		# The last ButtonPress event for a click on a listbox.
		# If None, no selection is being made.
		self._last_click_event = None

		self._active_cell_style, self._active_row_style = self._load_active_cell_style()

		# Frame index of the last pressed frame header
		self.pressed_frame = None
		# X Position of the last pressed frame header's press event.
		self.pressed_x = None
		# Current dragintent
		self.dragging = None

		self.scrollbar = ttk.Scrollbar(self, command = self._scrollallbar)
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
			self.add_frames(len(inicolumns))
			# using self.add_columns would require iterating a dict relying
			# on the fact it's sorted, i don't like that so we copypaste 2 lines
			for index, colopt in enumerate(inicolumns):
				new_col = _Column(self, **colopt)
				new_col.setdisplay(index)
				self.columns[new_col.col_id] = new_col

		self.scrollbar.pack(fill = tk.Y, expand = 0, side = tk.RIGHT)
		self.framecontainer.pack(expand = 1, fill = tk.BOTH, side = tk.RIGHT)
		self._listboxheight_hack.pack(expand = 0, fill = tk.Y, side = tk.RIGHT)

	#====USER METHODS====

	def add_columns(self, *coldicts):
		"""
		Takes any amount of dicts, then adds columns where the column
		constructor receives the dicts as kwargs. See the
		multiframe_list._Column class for a list of acceptable kwargs.
		"""
		for coldict in coldicts:
			new_col = _Column(self, **coldict)
			# Columns will give themselves a proper id
			self.columns[new_col.col_id] = new_col

	def add_frames(self, amount):
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

			def _m1_press_handler(event, curindex = curindex):
				return self._on_listbox_mouse_press(event, 1, curindex)
			def _m1_release_handler(event, curindex = curindex):
				return self._on_listbox_mouse_release(event, 1, curindex)
			def _motion_handler(event, curindex = curindex):
				return self._on_listbox_mouse_motion(event, 1, curindex)
			def _rcb_press_handler(event, rcb = rcb, curindex = curindex):
				return self._on_listbox_mouse_press(event, rcb, curindex)
			def _rcb_release_handler(event, rcb = rcb, curindex = curindex):
				return self._on_listbox_mouse_release(event, rcb, curindex)
			new_frame[1].bind("<Button-1>", _m1_press_handler)
			new_frame[1].bind("<ButtonRelease-1>", _m1_release_handler)
			new_frame[1].bind("<Motion>", _motion_handler)
			new_frame[1].bind(f"<Button-{rcb}>", _rcb_press_handler)
			new_frame[1].bind(f"<ButtonRelease-{rcb}>", _rcb_release_handler)
			self.tk.eval(SCROLLCOMMAND.format(w = new_frame[1]._w))
			new_frame[1].configure(
				**self._get_listbox_conf(new_frame[1]),
				yscrollcommand = self._scrollalllistbox
			)
			self._clear_frame(curindex)

			new_frame[3].grid(row = 0, column = 1, sticky = "news") # sort_indicator
			new_frame[2].grid(row = 0, column = 0, sticky = "news") # label
			new_frame[1].grid(row = 1, column = 0, sticky = "news", columnspan = 2) # listbox
			new_frame[0].grid(row = 0, column = curindex, sticky = "news") # frame
			new_frame[0].grid_propagate(False)
			# For some reason necessary so the grid manager reacts to the new frame,
			# in conjunction with the <Configure> event below
			self.framecontainer.update_idletasks()

			self._listboxheight_hack.configure(height = new_frame[1].winfo_reqheight())

		self.framecontainer.event_generate("<Configure>")
		self._redraw_active_cell()
		self._redraw_selection()

	def assign_column(self, col_id, req_frame):
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
		self._get_col_by_id(col_id).setdisplay(req_frame)
		self._redraw_active_cell()
		self._redraw_selection()

	def clear(self):
		"""Clears the MultiframeList."""
		# self._set_active_cell(None, None)
		self._set_length(0)
		for col in self.columns.values():
			col.data_clear()

	def config(self, **kwargs):
		"""
		Change configuration options of the MultiframeList/underlying frame.
		All non-MultiframeList options will be routed to the frame:

		For configurable options, see the `Modifiable during runtime` section
		in the `__init__` docstring.
		"""
		for mfl_arg in self.Config.__slots__:
			if mfl_arg in kwargs:
				old_value = getattr(self.cnf, mfl_arg)
				setattr(self.cnf, mfl_arg, kwargs.pop(mfl_arg))
				cnf_method = None
				try:
					cnf_method = getattr(self, f"_cnf_{mfl_arg}")
				except AttributeError:
					pass
				# To prevent catching and AttributeError in the cnf method
				if cnf_method is not None:
					cnf_method(old_value)
		super().configure(**kwargs)

	def config_column(self, col_id, **cnf):
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
		self._redraw_active_cell()
		self._redraw_selection()

	def get_active_cell(self):
		"""
		Returns the coordinates of the currently selected active cell as a
		tuple of length 2; (0, 0) starting in the top left corner;
		The two values may also be None.
		"""
		return (self.active_cell_x, self.active_cell_y)

	def get_columns(self):
		"""
		Returns a dict where key is a column id and value is the column's
		current display slot (frame). Value is None if the column is hidden.
		"""
		return {c.col_id: c.assignedframe for c in self.columns.values()}

	def get_last_click(self):
		"""
		Returns the absolute screen coordinates the last user interaction
		was made at as a tuple. May consist of int or None.
		This method can be used to get coordinates to open a popup window at.
		"""
		return (self.coordx, self.coordy)

	def get_length(self):
		"""Returns length of the MultiframeList."""
		return self.length

	def get_selection(self):
		"""
		Returns the selection of the MultiframeList.
		If in SINGLE selection mode, returns only the selected index
		or `None`, otherwise passes through the selection set.
		This mainly serves as convenience for the SINGLE selection
		type, it is preferrable to check for selection emptiness
		with simply `if mfl.selection:`
		"""
		if self.cnf.selection_type is SELECTION_TYPE.SINGLE:
			return next(iter(self.selection)) if self.selection else None
		else:
			return self.selection

	def remove_column(self, col_id):
		"""
		Deletes the column addressed by col_id, safely unregistering all
		related elements.
		"""
		self.assign_column(col_id, None)
		self.columns.pop(col_id)

	def remove_frames(self, amount):
		"""
		Safely remove the specified amount of frames from the
		MultiframeList, unregistering all related elements.
		"""
		to_purge = range(len(self.frames) - 1, len(self.frames) - amount - 1, -1)
		for col in self.columns.values():
			if col.assignedframe in to_purge:
				col.setdisplay(None)
		for i in to_purge:
			if self.active_cell_x is not None and self.active_cell_x >= i:
				self._set_active_cell(i - 1, self.active_cell_y)
			self.framecontainer.grid_columnconfigure(i, weight = 0, minsize = 0)
			# update in conjunction with the <Configure> event is for some
			# reason necessary so the grid manager actually releases
			# the space occupied by the deleted frames and redistributes it.
			self.frames[i][0].destroy()
			self.framecontainer.update()
			self.frames.pop(i)
		self.framecontainer.event_generate("<Configure>")

	def set_active_cell(self, x, y):
		"""
		Sets the active cell to the specified x and y coordinates.
		You may also pass None to any of those.
		If outside of viewport, the frames will be scrolled towards the
		new index.
		"""
		if not all(isinstance(v, (int, NoneType)) for v in (x, y)):
			raise TypeError("Invalid type for x and/or y coordinate.")
		if isinstance(x, int) and x >= len(self.frames):
			raise ValueError("New x selection out of range.")
		if isinstance(y, int) and y >= self.length:
			raise ValueError("New y selection exceeds length.")
		self._set_active_cell(x, y)
		if y is not None:
			for i in self.frames:
				i[1].see(self.active_cell_y)
		self._redraw_selection()

	def set_selection(self, new_selection):
		"""
		Sets the listbox' selection to be made out of only these
		contained within the given iterable or index and generates
		a <<MultiframeSelect>> event.
		If the selection type does not allow the selection to be made
		up of multiple indices when multiple are passed in, the last
		item in the iterable will be the selection.
		Will set the view to look at the last index.
		"""
		# Wasteful iteration just to look at the last idx but whatever
		new_selection = tuple(new_selection)
		self._selection_set(new_selection)
		self.event_generate("<<MultiframeSelect>>", when = "tail")
		if new_selection:
			for i in self.frames:
				i[1].see(new_selection[-1])

	#==DATA MODIFICATION==

	def insert_row(self, data, insindex = None, reset_sortstate = True):
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
			col.data_insert(data.get(col.col_id, BLANK), insindex)
		self._set_length(self.length + 1)

	def remove_rows(self, what, to = None):
		"""
		If `what` is an int, deletes the rows from `what` to `to`
		(end-exclusive).
		If `to` is not given, only removes the row at `what`.
		Has no effect if `to` <= `what`.
		If `what` is not an int, it must be a container and all indices its
		iteration yields will be removed. `to` will be ignored.
		Properly sets the length and will clear the selection
		Raises an IndexError if any index should be out of the list's range. 
		"""
		if isinstance(what, int):
			to = what + 1 if to is None else to
			if what < 0 or what > (self.length - 1):
				raise IndexError(f"`from` index {what} out of range.")
			if to < 0 or to > self.length:
				raise IndexError(f"`to` index {what} out of range.")
			to_delete = [range(what, to)]
		else:
			# Must be reversed to delete entries starting from the back,
			# otherwise deletion of selection blocks will affect others
			to_delete = sorted(what, reverse = True)
			if to_delete and to_delete[0] > self.length - 1:
				raise IndexError(f"Inaccessible deletion index: {to_delete[0]}")
			if to_delete and to_delete[-1] < 0:
				raise IndexError(f"Inaccessible deletion index: {to_delete[-1]}")
			to_delete = _find_consecutive_sequences(to_delete)
		self._set_length(self.length - sum(len(rng) for rng in to_delete))
		for rng in to_delete:
			for col in self.columns.values():
				col.data_delete(rng.start, rng.stop)
		self._redraw_active_cell()

	def set_data(self, data, reset_sortstate = True):
		"""
		Sets the data of the MultiframeList, clearing everything beforehand.

		Data has to be supplied as a dict where:
			- key is a column id
			- value is a list of values the column targeted by key should be set to.
			If the lists are of differing lengths, a ValueError will be raised.
		The function takes an optional reset_sortstate parameter to control whether
		or not to reset the sortstates on all columns. (Default True)
		"""
		self.clear()
		if not data:
			return
		ln = len(data[next(iter(data))])
		if any(len(d) != ln for d in data.values()):
			raise ValueError("Differing lengths in supplied column data.")
		if reset_sortstate:
			self._reset_sortstate()
		for col in self.columns.values():
			if col.col_id in data:
				col.data_set(data[col.col_id])
			else:
				col.data_set([BLANK for _ in range(ln)])
		self._set_length(ln)

	def set_cell(self, col_to_mod, y, data, reset_sortstate = True):
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
		col.data_delete(y)
		col.data_insert(data, y)

	def set_column(self, col_to_mod, data, reset_sortstate = True):
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
			self._set_length(datalen)
		else:
			for col in self.columns.values():
				if len(col.data) != datalen:
					raise ValueError(
						"Length of supplied column data is different from length of " \
						"column {col.col_id!r}."
					)
			targetcol.data_set(data)

	#==DATA RETRIEVAL==

	def get_rows(self, start, end = None):
		"""
		Retrieves rows between a start and an optional end parameter.

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
		if start == ALL:
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

	def get_column(self, col_id):
		"""Returns the data of the column with col_id as a list."""
		col = self._get_col_by_id(col_id)
		return col.data

	def get_cell(self, col_id, y):
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
		caller_id = call_col.col_id
		scroll = self._scroll_get()

		new_sortstate = abs(int(call_col.sortstate) - 1)
		rev = bool(new_sortstate)
		call_col.set_sortstate(new_sortstate)
		for col in self.columns.values(): # reset sortstate of other columns
			if col.col_id != caller_id:
				col.set_sortstate(2)

		tmpdat, colidmap = self.get_rows(ALL)
		datacol_index = colidmap[caller_id]
		keyfunc_internal = itemgetter(datacol_index)
		if call_col.cnf.sortkey is not None:
			keyfunc = lambda e: call_col.cnf.sortkey(keyfunc_internal(e))
		else:
			keyfunc = keyfunc_internal

		try:
			tmpdat = sorted(tmpdat, key = keyfunc, reverse = rev)
		except TypeError:
			fb_type = call_col.cnf.fallback_type
			if fb_type is None:
				raise
			for i, _ in enumerate(tmpdat):
				tmpdat[i][datacol_index] = fb_type(tmpdat[i][datacol_index])
			tmpdat = sorted(tmpdat, key = keyfunc, reverse = rev)
		newdat = {
			col_id: [r[idx] for r in tmpdat]
			for col_id, idx in colidmap.items()
		}
		self.set_data(newdat, reset_sortstate = False)
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
			def _right_click_handler(event, button = self.cnf.rightclickbtn, frameidx = idx):
				return self._on_listbox_mouse_press(event, button, frameidx)
			frame[1].unbind(f"<Button-{old}>")
			frame[1].bind(f"<Button-{self.cnf.rightclickbtn}>", _right_click_handler)

	def _cnf_selection_type(self, _):
		"""
		Callback for when the selection type is changed via the config
		method.
		"""
		self._selection_clear()

	def _cnf_active_cell_span_row(self, old):
		"""
		Callback for when active_cell_span_row is changed.
		Will refresh the active cell highlights.
		"""
		# NOTE: Extremely hacky but works so whatever
		cur = self.cnf.active_cell_span_row
		self.cnf.active_cell_span_row = old
		self._undraw_active_cell()
		self.cnf.active_cell_span_row = cur
		self._redraw_active_cell()

	#====INTERNAL METHODS====

	def _clear_frame(self, frame_idx):
		"""
		Will set up default bindings on a frame, and clear its label,
		sort and listbox, as well as reset its grid manager parameters.
		Usable for a part of the work that goes into removing a column
		from a frame or initial setup.
		"""
		tgt_frame = self.frames[frame_idx]
		tgt_frame[1].delete(0, tk.END)
		tgt_frame[1].insert(0, *(BLANK for _ in range(self.length)))
		tgt_frame[1].configure(width = _DEF_LISTBOX_WIDTH)
		tgt_frame[1].unbind("<Double-Button-1>")
		tgt_frame[2].configure(text = BLANK)
		tgt_frame[2].bind("<Button-1>",
			lambda e: self._on_frame_header_press(e, frame_idx)
		)
		tgt_frame[2].bind("<ButtonRelease-1>",
			lambda e: self._on_frame_header_release(e, frame_idx)
		)
		tgt_frame[2].bind("<Leave>", self._on_frame_header_leave)
		tgt_frame[2].bind("<Motion>",
			lambda e: self._on_frame_header_motion(e, frame_idx)
		)
		tgt_frame[3].configure(text = BLANK)
		self.framecontainer.grid_columnconfigure(frame_idx,
			weight = WEIGHT, minsize = MIN_WIDTH
		)

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
		Returns the position a resize operation started on the label of frame
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
		"""Returns the column in `frame` or None if there is none in it."""
		for col in self.columns.values():
			if col.assignedframe == frame:
				return col
		return None

	def _get_empty_frames(self):
		"""Returns the indexes of all frames that are not assigned a column."""
		assignedframes = [col.assignedframe for col in self.columns.values()]
		return [f for f in range(len(self.frames)) if not f in assignedframes]

	def _get_frame_at_x(self, x):
		"""
		Returns frame index of the frame at screen pixel position x,
		clamping to 0 and (len(self.frames) - 1).
		"""
		highlight_idx = -1
		for frame in self.frames:
			if frame[1].winfo_rootx() > x:
				break
			highlight_idx += 1
		return max(highlight_idx, 0)

	def _get_listbox_conf(self, listbox):
		"""
		Creates a dict of style options based on the ttk Style settings in
		`style_identifier` that listboxes can be directly configured with.

		The listbox passed to the method will be queried for its config and
		only configuration keys it returns present in the output dict.
		"""
		conf = self._DEFAULT_LISTBOX_CONFIG.copy()
		to_query = (".", "MultiframeList.Listbox")
		for style in to_query:
			cur_style_cnf = self.ttk_style.configure(style)
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

	def _load_active_cell_style(self):
		"""
		Returns a 2-value tuple of the active cell style and the active
		row style, with default values if none are given in the style
		database.
		"""
		ac = self._DEFAULT_ITEMCONFIGURE.copy()
		ac.update(self.ttk_style.configure("MultiframeList.ActiveCell") or {})
		ar = self._DEFAULT_ITEMCONFIGURE.copy()
		ar.update(self.ttk_style.configure("MultiframeList.ActiveRow") or {})

		return ac, ar

	def _on_arrow_x(self, event, direction):
		"""
		Executed when the MultiframeList receives <Left> and <Right> events,
		triggered by the user pressing the arrow keys.
		"""
		new_x = 0 if self.active_cell_x is None and self.frames else self.active_cell_x + direction
		new_y = 0 if self.active_cell_y is None and self.length > 0 else self.active_cell_y
		if new_x < 0 or new_x > len(self.frames) - 1:
			return
		self._set_active_cell(new_x, new_y)

	def _on_arrow_y(self, event, direction):
		"""
		Executed when the MultiframeList receives <Up> and <Down> events,
		triggered by the user pressing the arrow keys. Changes
		`self.active_cell_y`. It may be called with the control and the shift key
		held, in which case it will arrange for multiple item selection.
		"""
		new_x = 0 if self.active_cell_x is None and self.frames else self.active_cell_x
		new_y = 0 if self.active_cell_y is None else self.active_cell_y + direction
		if new_y < 0 or new_y > self.length - 1:
			return
		self._set_active_cell(new_x, new_y)
		for i in self.frames:
			i[1].see(self.active_cell_y)

		selection_made = True
		if with_shift(event):
			self._selection_set_from_anchor(self.active_cell_y, clear = not with_ctrl(event))
		elif with_ctrl(event):
			selection_made = False
		else:
			self._selection_set(self.active_cell_y)
		if selection_made:
			self.event_generate("<<MultiframeSelect>>", when = "tail")

	def _on_click_key(self, event):
		"""
		Called when the "click" key (Space by default) is pressed.
		Generates a <<MultiframeSelect>> event and modifies the
		selection depending on whether shift and ctrl were being held.
		"""
		new_x = 0 if self.active_cell_x is None and self.frames else self.active_cell_x
		new_y = 0 if self.active_cell_y is None and self.length > 0 else self.active_cell_y
		if new_y is None or new_x is None:
			return

		self._set_active_cell(new_x, new_y)
		if with_shift(event):
			self._selection_set_from_anchor(self.active_cell_y, clear = not with_ctrl(event))
		elif with_ctrl(event):
			self._selection_anchor = None
			self._selection_set_item(self.active_cell_y, toggle = True)
		else:
			self._selection_set(self.active_cell_y)
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	def _on_column_release(self, event, released_frame, drag_intent):
		if drag_intent is DRAGINTENT.REORDER and self.cnf.reorderable:
			self.reorder_highlight.place_forget()
			self._swap_by_frame(
				self._get_frame_at_x(event.widget.winfo_rootx() + event.x),
				released_frame
			)
		elif drag_intent is DRAGINTENT.RESIZE and self.cnf.resizable:
			# Shouldn't really happen, but you can never be too sure
			if released_frame == 0:
				return
			self.resize_highlight.place_forget()
			total_weight = (
				self.framecontainer.grid_columnconfigure(released_frame)["weight"] +
				self.framecontainer.grid_columnconfigure(released_frame - 1)["weight"]
			)
			minclamp, maxclamp = self._get_clamps(released_frame)
			maxclamp += (1 if maxclamp == minclamp else 0) # Prevent zero div
			pos = (self._get_clamped_resize_pos(released_frame, event) - minclamp)
			# Subtracting minclamp from maxclamp will effectively get the area pos moves in
			prv_weight = round((pos / (maxclamp - minclamp)) * total_weight)
			rel_weight = total_weight - prv_weight
			for fidx, weight in ((released_frame, rel_weight), (released_frame - 1, prv_weight)):
				col = self._get_col_by_frame(fidx)
				if col is None:
					self.framecontainer.grid_columnconfigure(fidx, weight = weight)
				else:
					col.config(weight = weight)
		elif self.dragging is None:
			rcol = self._get_col_by_frame(released_frame)
			if rcol is not None and rcol.cnf.sort:
				self.sort(None, rcol)

	def _on_column_drag(self, event, dragged_frame):
		if self.dragging is DRAGINTENT.REORDER and self.cnf.reorderable:
			highlight_idx = self._get_frame_at_x(event.widget.winfo_rootx() + event.x)
			self.reorder_highlight.place(
				x = self.frames[highlight_idx][0].winfo_x(),
				y = self.frames[highlight_idx][1].winfo_y(),
				width = 3, height = self.frames[highlight_idx][1].winfo_height()
			)
			self.reorder_highlight.tkraise()
		elif self.dragging is DRAGINTENT.RESIZE and self.cnf.resizable:
			self.resize_highlight.place(
				x = self._get_clamped_resize_pos(dragged_frame, event),
				y = self.frames[0][1].winfo_y(),
				width = 3, height = self.frames[0][1].winfo_height()
			)
			self.resize_highlight.tkraise()

	def _on_frame_header_leave(self, evt):
		evt.widget.configure(cursor = "arrow")

	def _on_frame_header_motion(self, evt, fidx):
		if self.pressed_frame is not None:
			if self.dragging is not None:
				self._on_column_drag(evt, fidx)
			elif self.dragging is None and abs(evt.x - self.pressed_x) > DRAG_THRES:
				self.dragging = _drag_intent(self.pressed_x, self.pressed_frame)
		else:
			evt.widget.configure(
				cursor = "sb_h_double_arrow" if
				_drag_intent(evt.x, fidx) is DRAGINTENT.RESIZE and self.cnf.resizable
				else "arrow"
			)

	def _on_frame_header_press(self, evt, fidx):
		"""
		Callback to register the pressed frame and initial press position
		while dragging.
		"""
		self.pressed_frame = fidx
		self.pressed_x = evt.x

	def _on_frame_header_release(self, evt, fidx):
		"""
		Callback to reset press variables and invoke release handler after
		dragging a column header.
		"""
		self._on_column_release(evt, fidx, self.dragging)
		self.pressed_frame = self.pressed_x = None
		self.dragging = None

	def _on_listbox_mouse_motion(self, event, button, frameindex):
		"""
		Called by listboxes whenever a mousebutton is dragged.
		Will set the selection in accordance to whether the click the
		drag stems from was done with ctrl/shift, the selection anchor
		and the selection type.
		"""
		if self._last_click_event is None:
			return
		hovered = self._get_index_from_mouse_y(self.frames[frameindex][1], event.y)
		if hovered < 0:
			return
		hovered = min(hovered, self.length - 1)
		if self._last_dragged_over_element == hovered:
			return
		self._last_dragged_over_element = hovered
		self._set_active_cell(frameindex, hovered)
		if with_ctrl(event):
			self._selection_set_item(hovered, toggle = True)
		elif with_shift(event):
			self._selection_set_item(hovered)
		else:
			self._selection_set_from_anchor(hovered)
		for i in self.frames:
			i[1].see(hovered)
		self.event_generate("<<MultiframeSelect>>", when = "tail")

	def _on_listbox_mouse_press(self, event, button, frameindex):
		"""
		Called by listboxes whenever a mouse button is pressed on them.
		Sets the active cell to the cell under the mouse pointer and
		sets internal drag selection variables.
		"""
		# Reset focus to mfl, all mouse events will still go to the listbox
		self.focus()
		if self.length == 0:
			return
		tosel = self._get_index_from_mouse_y(self.frames[frameindex][1], event.y)
		if tosel < 0:
			return
		tosel = min(tosel, self.length - 1)
		self._set_active_cell(frameindex, tosel)
		if button != self.cnf.rightclickbtn or tosel not in self.selection:
			# NOTE: these should be handled differently / behave very
			# specifically in the windows listboxes but tbh who cares
			if with_shift(event):
				self._selection_set_from_anchor(tosel)
			elif with_ctrl(event):
				self._selection_set_item(tosel, toggle = True)
			else:
				self._selection_set(tosel)

			self.event_generate("<<MultiframeSelect>>", when = "tail")

		self._last_dragged_over_element = tosel
		self._last_click_event = event

	def _on_listbox_mouse_release(self, event, button, frameindex):
		"""
		Called by listboxes when the mouse is released over them.
		If the released button was the rightclick one, generates a
		<<MultiframeRightclick>> event.
		Resets click variables.
		"""
		if self._last_click_event is None:
			return

		self.coordx = self.frames[frameindex][0].winfo_rootx() + event.x
		self.coordy = self.frames[frameindex][0].winfo_rooty() + 20 + event.y
		self._last_dragged_over_element = None
		self._last_click_event = None
		if button == self.cnf.rightclickbtn:
			self.event_generate("<<MultiframeRightclick>>", when = "tail")

	def _on_menu_button(self, _):
		"""
		User has pressed the menu button.
		This generates a <<MultiframeRightclick>> event and modifies
		self.coord[xy] to an appropriate value.
		"""
		if not self.frames:
			return
		if self.active_cell_y is None:
			return
		local_actcellx = 0 if self.active_cell_x is None else self.active_cell_x
		pseudo_lbl = self.frames[local_actcellx][0]
		pseudo_lbx = self.frames[local_actcellx][1]
		first_offset = pseudo_lbx.yview()[0]
		entry_height = self._get_listbox_entry_height(pseudo_lbx)
		tmp_x = pseudo_lbl.winfo_rootx() + 5
		tmp_y = entry_height * (self.active_cell_y - (self.length * first_offset)) + \
			20 + pseudo_lbl.winfo_rooty()
		tmp_x = int(round(tmp_x))
		tmp_y = int(round(tmp_y))
		tmp_y = max(tmp_y, 0) + 10
		self.coordx = tmp_x
		self.coordy = tmp_y
		self.event_generate("<<MultiframeRightclick>>", when = "tail")

	def _redraw_active_cell(self):
		"""
		Sets the active cell's itemconfigurations.
		Should be used after e.g. new frames have been added or reordered.
		"""
		if self.active_cell_x is None or self.active_cell_y is None:
			return
		if self.cnf.active_cell_span_row:
			for idx, i in enumerate(self.frames):
				i[1].itemconfigure(self.active_cell_y, **(
					self._active_cell_style
					if idx == self.active_cell_x else
					self._active_row_style
				))
		else:
			self.frames[self.active_cell_x][1].itemconfigure(
				self.active_cell_y, self._active_cell_style
			)

	def _redraw_selection(self):
		"""
		Sets the visual selection to the selected indices in each frame's
		listbox.
		"""
		for i in self.frames:
			i[1].selection_clear(0, tk.END)
		if self.selection is None:
			return
		for idx in self.selection:
			for i in self.frames:
				i[1].selection_set(idx)

	def _reset_sortstate(self):
		"""
		Reset the sortstate of all columns to 2.
		"""
		for column in self.columns.values():
			column.set_sortstate(2)

	def _swap_by_frame(self, tgt_frame, src_frame):
		"""
		Swaps the contents of two frames. Whether any, none or both of them
		are blank is handled properly. Will copy over the weight from empty
		frames as their `weight` is the only "configurable" option they have
		stored in them. (Implicitly by the user resizing them).
		If the 
		"""
		tgt_col = src_col = None
		tgt_col = self._get_col_by_frame(tgt_frame)
		src_col = self._get_col_by_frame(src_frame)
		# They're the same, no action required
		if tgt_col == src_col and tgt_col is not None:
			return
		scroll = self._scroll_get()
		src_w = self.framecontainer.grid_columnconfigure(src_frame)["weight"] \
			if src_col is None else None
		tgt_w = self.framecontainer.grid_columnconfigure(tgt_frame)["weight"] \
			if tgt_col is None else None
		if src_col is not None:
			src_col.setdisplay(None)
		if tgt_col is not None:
			tgt_col.setdisplay(None)
		if src_col is not None:
			src_col.setdisplay(tgt_frame)
		else:
			self.framecontainer.grid_columnconfigure(tgt_frame, weight = src_w)
		if tgt_col is not None:
			tgt_col.setdisplay(src_frame)
		else:
			self.framecontainer.grid_columnconfigure(src_frame, weight = tgt_w)
		self._scroll_restore(scroll)
		self._redraw_active_cell()
		self._redraw_selection()

	def _scroll_get(self):
		if not self.frames:
			return None
		return self.frames[0][1].yview()[0]

	def _scroll_restore(self, scroll):
		if scroll is not None:
			self._scrollalllistbox(scroll, 1.0)

	def _scrollallbar(self, *args):
		"""Bound to the scrollbar; Will scroll listboxes."""
		# args can have 2 or 3 values
		for i in self.frames:
			i[1].yview(*args)

	def _scrollalllistbox(self, a, b):
		"""Bound to all listboxes so that they will scroll the other ones
		and scrollbar.
		"""
		for i in self.frames:
			i[1].yview_moveto(a)
		self.scrollbar.set(a, b)

	def _selection_clear(self, redraw = True, with_event = False):
		"""
		Clears the selection anchor and the selection.
		If `redraw` is `True`, will also redraw the selection.
		If `with_event` is `True`, a <<MultiframeSelect>> event will
		be generated if the selection was not empty beforehand.
		"""
		was_not_empty = bool(self.selection)
		self._selection_anchor = None
		self.selection.clear()
		if redraw:
			self._redraw_selection()
		if with_event and was_not_empty:
			self.event_generate("<<MultiframeSelect>>", when = "tail")

	def _selection_set(self, new, anchor = None, toggle = False):
		"""
		Clears and then sets the selection to the given iterable or single index.
		If `anchor` is not `None`, the selection anchor will be set to `anchor`.
		Otherwise, anchor will be set to the first value seen in the new selection set,
		whose order can possibly not be guaranteed.
		`toggle` will be passed on to all calls to `self._selection_set_item`.
		"""
		self._selection_clear(False)
		if anchor is not None:
			self._selection_anchor = anchor
		if isinstance(new, int):
			self._selection_set_item(new, False, toggle)
		else:
			for idx in new:
				self._selection_set_item(idx, False, toggle)
		self._redraw_selection()

	def _selection_set_from_anchor(self, target, toggle = False, clear = True):
		"""
		If the selection mode is `MULTIPLE`, sets the selection from the current
		anchor to the given target index. If the anchor does not exist, will set
		the selection as just the target item and make it the new anchor.
		If the selection mode is `SINGLE`, will simply set the selection to `target`.
		`toggle` will be passed on to `self._selection_set`.
		Only relevant for `MULTIPLE` selection mode, if `clear` is set to `False`,
		the current selection will be kept and the new selection added as a union to it.
		"""
		if self.cnf.selection_type is SELECTION_TYPE.SINGLE or self._selection_anchor is None:
			self._selection_set(target, toggle = toggle)
			return
		step = -1 if target < self._selection_anchor else 1
		new_sel = set() if clear else self.selection.copy()
		new_sel.update(range(self._selection_anchor, target + step, step))
		self._selection_set(new_sel, self._selection_anchor, toggle)

	def _selection_set_item(self, idx, redraw = True, toggle = False):
		"""
		Adds a new index to the MultiframeList's selection, be it in single
		or multiple selection mode. If the selection mode is SINGLE, the
		selection will be cleared. If the selection anchor is None, it
		will be set to the given item.
		If `redraw` is `True`, will redraw the selection.
		If `toggle` is `True`, will toggle the index instead of setting it.
		"""
		if self.cnf.selection_type is SELECTION_TYPE.SINGLE:
			self._selection_clear(False)
		if self._selection_anchor is None:
			self._selection_anchor = idx
		if toggle and idx in self.selection:
			self.selection.remove(idx)
		else:
			self.selection.add(idx)
		if redraw:
			self._redraw_selection()

	def _set_active_cell(self, new_x, new_y):
		"""
		Sets the active cell to the new values and updates its highlights
		appropiately. The values may be `None`, to keep one of the fields
		unchanged, pass in `self.active_cell_x|y` as needed.
		"""
		old_x = self.active_cell_x
		old_y = self.active_cell_y

		if new_x != old_x:
			self.active_cell_x = new_x
			if old_x is not None and old_y is not None:
				self.frames[old_x][1].itemconfigure(old_y, **(
					self._active_row_style
					if self.cnf.active_cell_span_row else
					self._DEFAULT_ITEMCONFIGURE
				))
			if new_x is not None and new_y is not None:
				self.frames[new_x][1].itemconfigure(new_y, **self._active_cell_style)

		if new_y != old_y:
			if old_y is not None:
				self._undraw_active_cell()
			self.active_cell_y = new_y
			self._redraw_active_cell()

	def _set_length(self, new_length):
		"""
		Use this for any change to `self.length`. This method updates
		frames without a column so the amount of blank strings in them
		stays correct, clears the selection generating an event if it
		was not empty previously, will adjust the active cell if it runs
		out of bounds and clear the click/dragging event.
		"""
		self.length = new_length

		# Will cause errors otherwise if change occurs while user is dragging
		self._last_click_event = None
		self._last_dragged_over_element = None

		if self.active_cell_y is not None:
			new_ay = self.active_cell_y
			if new_ay > self.length - 1:
				new_ay = self.length - 1 if self.length > 0 else None
			if new_ay != self.active_cell_y:
				self._set_active_cell(self.active_cell_x, new_ay)
		self._selection_clear(with_event = True)

		for fi in self._get_empty_frames():
			curframelen = self.frames[fi][1].size()
			if curframelen > self.length:
				self.frames[fi][1].delete(self.length, tk.END)
			elif curframelen < self.length:
				self.frames[fi][1].insert(
					tk.END, *(BLANK for _ in range(self.length - curframelen))
				)

	def _theme_update(self, _):
		"""
		Called from event binding when the current theme changes.
		Changes Listbox look, as those are not available as ttk variants,
		and updates the active cell style.
		"""
		self._active_cell_style, self._active_row_style = self._load_active_cell_style()

		if not self.frames:
			return

		conf = self._get_listbox_conf(self.frames[0][1])
		for f in self.frames:
			f[1].configure(**conf)

		self._redraw_active_cell()

	def _undraw_active_cell(self):
		"""
		Removes all itemconfigure options on the active cell/the active
		cell's row, depending on `self.cnf.active_cell_span_row`.
		"""
		if self.active_cell_y is None:
			return
		if self.cnf.active_cell_span_row:
			for f in self.frames:
				f[1].itemconfigure(self.active_cell_y, **self._DEFAULT_ITEMCONFIGURE)
		else:
			self.frames[self.active_cell_x][1].itemconfigure(
				self.active_cell_y, **self._DEFAULT_ITEMCONFIGURE
			)


if __name__ == "__main__":
	from multiframe_list.demo import run_demo
	run_demo()
