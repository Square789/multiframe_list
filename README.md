# multiframe_list.py
Compact raw python module that brings the MultiframeList class with it.
It is a tkinter widget that can be used to display data split up over multiple columns.

## Installation
Get it by running `pip install multiframe_list`

## Example script:

```python
import tkinter as tk
from multiframe_list import MultiframeList

def format_price(raw):
    cents = raw % 100
    dollars = raw // 100
    return "${}.{:0>2}".format(dollars, cents)

items = (
    ("Apple", 79, 42),
    ("Pear", 79, 58),
    ("Egg", 29, 24),
    ("HL3", 99999999903, 1),
)

root = tk.Tk()

item_display = MultiframeList(root, inicolumns = (
        {"name": "Items", "col_id": "col_items",
         "sort": False},
        {"name": "Price", "col_id": "col_prices",
         "sort": True, "formatter": format_price}
    )
)

item_display.addframes(1)
item_display.addcolumns(
    {"name": "Stock", "col_id": "col_qty",
     "sort": False}
)
item_display.assigncolumn("col_qty", 2)
# Manually create a frame, a column and then display the
# new column in the freshly created third frame

item_display.grid(sticky = "nesw")

item_display.setdata({
    "col_items": [t[0] for t in items],
    "col_prices": [t[1] for t in items],
    "col_qty": [t[2] for t in items],
})
item_display.format() # In order to apply the price formatter

root.mainloop()

```
