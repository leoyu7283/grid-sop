"""把 data.json 塞進 template.html，產生完整網頁。
用法：python build_html.py [data.json] [輸出.html]"""
import sys
data = sys.argv[1] if len(sys.argv) > 1 else "data.json"
out = sys.argv[2] if len(sys.argv) > 2 else "index.html"
t = open("template.html", encoding="utf-8").read()
d = open(data, encoding="utf-8").read()
assert "/*DATA*/null" in t
open(out, "w", encoding="utf-8").write(t.replace("/*DATA*/null", d))
print("wrote", out)
