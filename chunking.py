from bs4 import BeautifulSoup
import pandas as pd

with open("./data/ugolovnyykodeks04112019.html", "r") as f:
    soup = BeautifulSoup(f, 'lxml')

chunks = []
section_text = ""

for p in soup.find_all("p"):

    if "style" in p.attrs:
        skip = False
        for align in ("right", "center"):
            if f"text-align:{align}" in p["style"]:
                skip = True
        if skip:
            continue

    if p.contents[-1].contents[-1].text == "\xa0":
        continue

    if "ConsPlusTitle" in p["class"]:
        if section_text:
            chunks.append(section_text)
        section_text = "\""
        section_text += p.contents[-1].text
        section_text += "\"\n"

    else:
        section_text += p.contents[-1].text
        section_text += "\n"

if section_text:
    chunks.append(section_text)

pd.DataFrame.from_dict({"chunks": chunks[1:]}).to_csv("./data/chunks.csv", index=False)
