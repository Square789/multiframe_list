"""
Shoddy demonstration of the MultiframeList.
To run in, call run_demo().
"""

from random import randint, sample
import tkinter as tk

from multiframe_list.multiframe_list import MultiframeList, END

def priceconv(data):
	return str(data) + "$"

class Demo:
	def __init__(self):
		self.root = tk.Tk()
		self.mfl = MultiframeList(self.root, inicolumns=(
			{"name": "Small", "w_width": 10},
			{"name": "Sortercol", "col_id": "sorter"},
			{"name": "Pricecol", "sort": True, "col_id": "sickocol"},
			{"name": "-100", "col_id": "sub_col", "formatter": lambda n: n-100},
			{"name": "Wide col", "w_width": 30},
			{"name": "unconf name", "col_id": "cnfcl"},
		))
		self.mfl.configcolumn("sickocol", formatter = priceconv)
		self.mfl.configcolumn("sorter", sort = True)
		self.mfl.configcolumn("cnfcl", name = "Configured Name", sort = True,
			fallback_type = lambda x: int("0" + str(x)))
		self.mfl.pack(expand = 1, fill = tk.BOTH)
		self.mfl.addframes(2)
		self.mfl.removeframes(1)

		btns = (
			tk.Button(self.root, text="+row",     command=self.adddata),
			tk.Button(self.root, text="-row",     command=self.remrow),
			tk.Button(self.root, text="---",      command=self.mfl.clear),
			tk.Button(self.root, text="+frame",   command=lambda: self.mfl.addframes(1)),
			tk.Button(self.root, text="-frame",   command=self.remframe),
			tk.Button(self.root, text="?columns", command=lambda: print(self.mfl.getcolumns())),
			tk.Button(self.root, text="?currow",  command=self.getcurrrow),
			tk.Button(self.root, text="?to_end",  command=lambda: self.getcurrrow(END)),
			tk.Button(self.root, text="?curcell", command=lambda: print(self.mfl.getselectedcell())),
			tk.Button(self.root, text="?length",  command=lambda: print(self.mfl.getlen())),
			tk.Button(self.root, text="+column",  command=self.add1col),
			tk.Button(self.root, text="swap01",   command=self.swap01),
			tk.Button(self.root, text="swaprnd",  command=self.swaprand),
			tk.Button(self.root, text="bgstyle",  command=lambda: self.root.tk.eval(
				"ttk::style configure . -background #{0}{0}{0}".format(hex(randint(50, 255))[2:])
			)),
			tk.Button(self.root, text="lbstyle",  command=lambda: self.root.tk.eval(
				"ttk::style configure MultiframeList.Listbox -background #{0}{0}{0} -foreground #0000{1:0>2}".format(
					hex(randint(120, 255))[2:], hex(randint(0, 255))[2:]
				)
			)),
			tk.Button(self.root, text="conf",     command=lambda: self.mfl.config(
				listboxheight=randint(5, 10)
			)),
		)
		for btn in btns:
			btn.pack(fill = tk.X, side = tk.LEFT)

	def adddata(self):
		self.mfl.insertrow({col_id: randint(0, 100)
			for col_id in self.mfl.getcolumns()})
		self.mfl.format()

	def add1col(self):
		if "newcol" in self.mfl.getcolumns():
			if self.mfl.getcolumns()["newcol"] != 6:
				print("Please return that column to frame 6, it's where it feels at home.")
				return
			self.mfl.removecolumn("newcol")
		else:
			self.mfl.addcolumns({"col_id": "newcol", "name": "added @ runtime; wide.",
				"w_width": 35, "minsize": 30, "weight": 3})
			self.mfl.assigncolumn("newcol", 6)

	def getcurrrow(self, end = None):
		x_idx = self.mfl.getselectedcell()[1]
		if x_idx is None:
			print("No row is selected, cannot tell."); return
		outdat, mapdict = self.mfl.getrows(x_idx, end)
		def getlongest(seqs):
			longest = 0
			for i in seqs:
				if isinstance(i, (list, tuple)):
					res = getlongest(i)
				else:
					res = len(str(i))
				if res > longest:
					longest = res
			return longest
		l_elem = getlongest(outdat)
		l_elem2 = getlongest(mapdict.keys())
		if l_elem2 > l_elem: l_elem = l_elem2
		frmtstr = "{:<{ml}}"
		print("|".join(frmtstr.format(i, ml = l_elem)
			for i in mapdict.keys()))
		print("-" * (l_elem + 1) * len(mapdict.keys()))
		for row in outdat:
			print("|".join(frmtstr.format(i, ml = l_elem) for i in row))

	def remframe(self):
		if len(self.mfl.frames) <= 7:
			print("Cannot remove this many frames from example!"); return
		self.mfl.removeframes(1)

	def remrow(self):
		if self.mfl.length == 0:
			print("List is empty already!"); return
		if self.mfl.getselectedcell()[1] is None:
			print("Select a row to delete!"); return
		self.mfl.removerow(self.mfl.getselectedcell()[1])

	def swap(self, first, second):
		_tmp = self.mfl.getcolumns()
		f_frm = _tmp[first]
		s_frm = _tmp[second]
		self.mfl.assigncolumn(first, None)
		self.mfl.assigncolumn(second, f_frm)
		self.mfl.assigncolumn(first, s_frm)

	def swap01(self):
		c_a, c_b = 1, 0
		if self.mfl.getcolumns()[0] == 0:
			c_a, c_b = 0, 1
		self.swap(c_a, c_b)

	def swaprand(self):
		l = self.mfl.getcolumns().keys()
		s_res = sample(l, 2)
		print("Swapping {}".format(" with ".join([str(i) for i in s_res])))
		self.swap(*s_res)

def run_demo():
	demo = Demo()
	demo.root.mainloop()
