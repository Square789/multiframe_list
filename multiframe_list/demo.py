"""
Shoddy demonstration of the MultiframeList.
To run in, call run_demo().
"""

from random import choice, randint, sample
import tkinter as tk

from multiframe_list.multiframe_list import MultiframeList, END, SELECTION_TYPE, WEIGHT

def priceconv(data):
	return f"${data}"

def getlongest(seq):
	longest = 0
	for i in seq:
		if isinstance(i, (list, tuple)):
			res = getlongest(i)
		else:
			res = len(str(i))
		longest = max(longest, res)
	return longest

class Demo:
	def __init__(self):
		self.root = tk.Tk()
		self.mfl = MultiframeList(self.root, inicolumns = (
				{"name": "Small", "minsize": 40},
				{"name": "Sortercol", "col_id": "sorter"},
				{"name": "Pricecol", "sort": True, "col_id": "sickocol",
					"weight": round(WEIGHT * 3)},
				{"name": "-100", "col_id": "sub_col", "formatter": lambda n: n - 100},
				{"name": "Wide col sorting randomly", "minsize": 200,
					"sort": True, "sortkey": lambda _: randint(1, 100)},
				{"col_id": "cnfcl"},
				{"name": "Doubleclick me", "col_id": "dbc_col", "minsize": 80,
					"dblclick_cmd": self.doubleclick_column_callback},
			),
			active_cell_span_row = False,
			reorderable = True,
		)
		self.mfl.bind(
			"<<MultiframeRightclick>>",
			lambda e: print("Rightclick on", e.widget, "@", self.mfl.get_last_click())
		)
		self.mfl.config_column("sickocol", formatter = priceconv)
		self.mfl.config_column("sorter", sort = True)
		self.mfl.config_column(
			"cnfcl",
			name = "Configured Name",
			sort = True,
			fallback_type = lambda x: int("0" + str(x))
		)
		self.mfl.pack(expand = 1, fill = tk.BOTH)
		self.mfl.add_frames(2)
		self.mfl.remove_frames(1)

		self.randstyle()
		for _ in range(10):
			self.adddata()


		btns = (
			tk.Button(self.root, text="+row",     command=self.adddata),
			tk.Button(self.root, text="-sel",     command=self.remsel),
			tk.Button(self.root, text="---",      command=self.mfl.clear),
			tk.Button(self.root, text="+frame",   command=lambda: self.mfl.add_frames(1)),
			tk.Button(self.root, text="-frame",   command=self.remframe),
			tk.Button(self.root, text="?columns", command=lambda: print(self.mfl.get_columns())),
			tk.Button(self.root, text="?currow",  command=self.getcurrrow),
			tk.Button(self.root, text="?to_end",  command=lambda: self.getcurrrow(END)),
			tk.Button(self.root, text="?curcell", command=lambda: print(self.mfl.get_active_cell())),
			tk.Button(self.root, text="?length",  command=lambda: print(self.mfl.get_length())),
			tk.Button(self.root, text="+column",  command=self.add1col),
			tk.Button(self.root, text="swap01",   command=self.swap01),
			tk.Button(self.root, text="swaprnd",  command=self.swaprand),
			tk.Button(self.root, text="bgstyle",  command=lambda: self.root.tk.eval(
				"ttk::style configure . -background #{0}{0}{0}".format(hex(randint(50, 255))[2:])
			)),
			tk.Button(self.root, text="lbstyle",  command=self.randstyle),
			tk.Button(self.root, text="conf",     command=self.randcfg),
			tk.Button(self.root, text="randac",   command=self.randactive),
		)

		for btn in btns:
			btn.pack(fill = tk.X, side = tk.LEFT)

	def adddata(self):
		self.mfl.insert_row({col_id: randint(0, 100) for col_id in self.mfl.get_columns()})
		self.mfl.format()

	def add1col(self):
		if "newcol" in self.mfl.get_columns():
			if self.mfl.get_columns()["newcol"] != 6:
				print("Please return that column to frame 6, it's where it feels at home.")
				return
			self.mfl.remove_column("newcol")
		else:
			self.mfl.add_columns(
				{"col_id": "newcol", "name": "added @ runtime; wide.",
					"minsize": 30, "weight": 3 * WEIGHT}
			)
			self.mfl.assign_column("newcol", 6)

	def doubleclick_column_callback(self, _):
		x, y = self.mfl.get_active_cell()
		if y is None:
			print("Empty column!")
		else:
			print(f"{self.mfl.get_cell('dbc_col', y)} @ ({x}, {y})")

	def getcurrrow(self, end = None):
		x_idx = self.mfl.get_active_cell()[1]
		if x_idx is None:
			print("No row is selected, cannot tell.")
			return
		outdat, mapdict = self.mfl.get_rows(x_idx, end)
		l_elem = max(getlongest(outdat), getlongest(mapdict.keys()))
		print("|".join(f"{k:<{l_elem}}" for k in mapdict.keys()))
		print("-" * (l_elem + 1) * len(mapdict.keys()))
		for row in outdat:
			print("|".join(f"{i:<{l_elem}}" for i in row))

	def randcfg(self):
		cfg = {
			"listboxheight": randint(5, 10),
			"reorderable": bool(randint(0, 1)),
			"resizable": bool(randint(0, 1)),
			"rightclickbtn": randint(2, 3),
			"selection_type": choice([SELECTION_TYPE.SINGLE, SELECTION_TYPE.MULTIPLE]),
			"active_cell_span_row": bool(randint(0, 1)),
		}
		print(f"Randomly configuring: {cfg!r}")
		self.mfl.config(**cfg)

	def randactive(self):
		length = self.mfl.get_length()
		if length < 1:
			return
		self.mfl.set_active_cell(0, randint(0, length - 1))

	def randstyle(self):
		self.root.tk.eval((
			"ttk::style configure MultiframeList.Listbox -background #{0}{0}{0} -foreground #0000{1}\n"
			"ttk::style configure MultiframeList.Listbox -selectbackground #{1}{2}{3}\n"
			"ttk::style configure MultiframeListReorderInd.TFrame -background #{0}0000\n"
			"ttk::style configure MultiframeListResizeInd.TFrame -background #0000{0}\n"
			"ttk::style configure MultiframeList.ActiveCell -background #{0}{1}{2} -selectbackground #{0}0000\n"
			"ttk::style configure MultiframeList.ActiveRow -background #000000 -selectbackground #333333\n"
		).format(
			f"{randint(120, 255):0>2X}",
			f"{randint(  0, 255):0>2X}",
			f"{randint(  0, 255):0>2X}",
			f"{randint(  0, 255):0>2X}",
		))

	def remframe(self):
		if len(self.mfl.frames) <= 7:
			print("Cannot remove this many frames from example!"); return
		self.mfl.remove_frames(1)

	def remsel(self):
		if not self.mfl.selection:
			print("Make a selection to delete!")
			return
		self.mfl.remove_rows(self.mfl.selection)

	def swap(self, first, second):
		_tmp = self.mfl.get_columns()
		f_frm = _tmp[first]
		s_frm = _tmp[second]
		self.mfl.assign_column(first, None)
		self.mfl.assign_column(second, f_frm)
		self.mfl.assign_column(first, s_frm)

	def swap01(self):
		c_a, c_b = 1, 0
		if self.mfl.get_columns()[0] == 0:
			c_a, c_b = 0, 1
		self.swap(c_a, c_b)

	def swaprand(self):
		l = self.mfl.get_columns().keys()
		a, b = sample(l, 2)
		print(f"Swapping {a} with {b}")
		self.swap(a, b)

def run_demo():
	demo = Demo()
	demo.root.mainloop()
