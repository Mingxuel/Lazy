import time
import os
from rich.console import Console
from rich.table import Table

console = Console()

def FORMAT_NUMBER(num):
    output = ""
    if num >= 0:
        output = "+{:06.2f}".format(num)
    else:
        output =  "{:07.2f}".format(num)
    if output[1] == "0":
        output[1] = " "
    if output[1] == " " and output[2] == "0":
        output[2] = " "
    return output
    
if __name__ == "__main__":
    x = 0.00
    y = -1.10
    print(FORMAT_NUMBER(x))
    print(FORMAT_NUMBER(y))