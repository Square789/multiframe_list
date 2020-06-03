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
# Same effect as if you had put the dict into the inicolumns tuple

item_display.grid(sticky = "nesw")

item_display.setdata({
    "col_items": [t[0] for t in items],
    "col_prices": [t[1] for t in items],
    "col_qty": [t[2] for t in items],
})
item_display.format()
# Required for the price formatter, else the column would display raw values

root.mainloop()

```
Will result in this window:

![<Image> Result of script above](example.PNG)  

## Documentation

Most information can be found in the docstrings of the MultiframeList's class and its methods.  
Other than that:
```
 ~ ### ~ ~
   *#*       
 /  s  \

             ___              _
            /  -]  /|         |
___n____m_-_|___|__||_____---_|__
.             _          .       
   .-.    ~         ___       ' .     
 n_|:|       .    '           __ 
 '-. |_n      _         _______   . 
   | .-'                     __.      
  _|:|___  *             -  [__/     
   | |         ~   ===         
    *  ___     .      - ---
```