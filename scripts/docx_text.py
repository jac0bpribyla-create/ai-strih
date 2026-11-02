"""Text ze scénáře ve Wordu (.docx) bez dalších programů – na Macu i na Windows.

Použití: scripts/py docx_text.py scenar.docx
"""
import re
import sys
import zipfile
from html import unescape

xml = zipfile.ZipFile(sys.argv[1]).read("word/document.xml").decode("utf-8")
for odstavec in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
    text = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", odstavec))
    print(unescape(text))
