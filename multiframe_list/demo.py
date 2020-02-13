"""
Shoddy demonstration of the MultiframeList.
To run in, call run_demo().
"""

from random import randint, sample
import tkinter as tk

from multiframe_list.multiframe_list import MultiframeList, END

def adddata(mfl):
	mfl.insertrow({col_id: randint(0, 100)
		for col_id in mfl.getcolumns()})
	mfl.format()

def add1col(mfl):
	if "newcol" in mfl.getcolumns():
		if mfl.getcolumns()["newcol"] != 6:
			print("Please return that column to frame 6, it's where it feels at home.")
			return
		mfl.removecolumn("newcol")
	else:
		mfl.addcolumns({"col_id": "newcol", "name": "added @ runtime; wide.",
			"w_width": 35, "minsize": 30, "weight": 3})
		mfl.assigncolumn("newcol", 6)

def getcurrrow(mfl, end = None):
	x_idx = mfl.getselectedcell()[1]
	if x_idx is None:
		print("No row is selected, cannot tell."); return
	outdat, mapdict = mfl.getrows(x_idx, end)
	print(outdat, mapdict)
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
	print("|".join([frmtstr.format(i, ml = l_elem)
		for i in mapdict.keys()]))
	print("-" * (l_elem + 1) * len(mapdict.keys()))
	for row in outdat:
		print("|".join([frmtstr.format(i, ml = l_elem) for i in row]))

def remframe(mfl):
	if len(mfl.frames) <= 7:
		print("Cannot remove this many frames from example!"); return
	mfl.removeframes(1)

def remrow(mfl):
	if mfl.length == 0:
		print("List is empty already!"); return
	if mfl.getselectedcell()[1] is None:
		print("Select a row to delete!"); return
	mfl.removerow(mfl.getselectedcell()[1])

def swap(mfl, first, second):
	_tmp = mfl.getcolumns()
	f_frm = _tmp[first]
	s_frm = _tmp[second]
	mfl.assigncolumn(first, None)
	mfl.assigncolumn(second, f_frm)
	mfl.assigncolumn(first, s_frm)

def swap01(mfl):
	c_a = 1
	c_b = 0
	if mfl.getcolumns()[0] == 0:
		c_a = 0
		c_b = 1
	swap(mfl, c_a, c_b)

def swaprand(mfl):
	l = mfl.getcolumns().keys()
	s_res = sample(l, 2)
	print("Swapping {}".format(" with ".join([str(i) for i in s_res])))
	swap(mfl, *s_res)

def priceconv(data):
	return str(data) + "$"

def run_demo():
	root = tk.Tk()
	mfl = MultiframeList(root, inicolumns=(
		{"name": "Small", "w_width": 10},
		{"name": "Sortercol", "col_id": "sorter"},
		{"name": "Pricecol", "sort": True, "col_id": "sickocol"},
		{"name": "-100", "col_id": "sub_col", "formatter": lambda n: n-100},
		{"name": "Wide col", "w_width": 30},
		{"name": "unconf name", "col_id": "cnfcl"},
	))
	mfl.configcolumn("sickocol", formatter = priceconv)
	mfl.configcolumn("sorter", sort = True)
	mfl.configcolumn("cnfcl", name = "Configured Name", sort = True,
		fallback_type = lambda x: int("0" + str(x)))
	mfl.pack(expand = 1, fill = tk.BOTH)
	mfl.addframes(2)
	mfl.removeframes(1)

	btns = (
		{"text": "+row","command": lambda: adddata(mfl)},
		{"text": "-row", "command": lambda: remrow(mfl)},
		{"text": "---", "command": mfl.clear},
		{"text": "+frame", "fg": "#AA0000", "command":
			lambda: mfl.addframes(1)},
		{"text": "-frame", "command": lambda: remframe(mfl)},
		{"text": "getcolumns", "command": lambda: print(mfl.getcolumns())},
		{"text": "getcurrow", "command": lambda: getcurrrow(mfl)},
		{"text": "get_to_end", "command": lambda: getcurrrow(mfl, END)},
		{"text": "getcurcell", "command":
			lambda: print(mfl.getselectedcell())},
		{"text": "getlength", "command": lambda: print(mfl.getlen())},
		{"text": "addcolumn", "command": lambda: add1col(mfl)},
		{"text": "swp01", "command": lambda: swap01(mfl)},
		{"text": "swprnd", "command": lambda: swaprand(mfl)},
		{"text": "bgstyle", "command": lambda: \
			root.tk.eval("ttk::style configure . -background #{0}{0}{0}".format(
				hex(randint(0, 255))[2:]
			))}
	)

	for b_args in btns:
		tmp_btn = tk.Button(root, **b_args)
		tmp_btn.pack(fill = tk.X, side = tk.LEFT)

	root.mainloop()
