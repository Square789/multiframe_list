import tkinter as tk

from multiframe_list.multiframe_list import MultiframeList

def main():
	root = tk.Tk()
	mfl = MultiframeList(root, inicolumns =
		({"name": "aaaa"}, {"name": "bbbb"}),
		resizable = True, reorderable = True
	)
	mfl.pack(fill = tk.BOTH, expand = 1)
	root.mainloop()

if __name__ == "__main__":
	main()
