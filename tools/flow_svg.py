"""產生「網格開單流程」頁面上方的流程圖 SVG，寫回 grid-flow.html 與 flow.html。
用法：python tools/flow_svg.py <grid-flow.html> [flow.html ...]
"""
import re, sys

def badge(cx, cy, n, r=12):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="bd"/><text x="{cx}" y="{cy+4.5}" class="t-bd">{n}</text>'

def texts(cx, cy, lines):
    out, n = '', len(lines)
    for i, (t, c) in enumerate(lines):
        out += f'<text x="{cx}" y="{cy+(i-(n-1)/2)*17+5:.1f}" class="{c}">{t}</text>'
    return out

def node(x, y, w, h, cls, lines, nums=()):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>'
    cy = y + h / 2
    if nums:
        bx = x + 22
        for i, n in enumerate(nums):
            out += badge(bx + i * 27, cy, n)
        left = bx + (len(nums) - 1) * 27 + 16
        out += texts((left + x + w) / 2 - 4, cy, lines)
    else:
        out += texts(x + w / 2, cy, lines)
    return out

def hexa(cx, y, w, h, lines, num):
    pts = [(cx-w/2, y+h/2), (cx-w/2+22, y), (cx+w/2-22, y), (cx+w/2, y+h/2), (cx+w/2-22, y+h), (cx-w/2+22, y+h)]
    out = '<polygon points="' + ' '.join(f'{a:.0f},{b:.0f}' for a, b in pts) + '" class="n-dec"/>'
    bx = cx - w/2 + 40
    out += badge(bx, y + h/2, num)
    out += texts((bx + 16 + cx + w/2 - 22) / 2, y + h/2, lines)
    return out

def ln(pts, cls="ed", arrow=True):
    d = 'M' + ' L'.join(f'{a},{b}' for a, b in pts)
    return f'<path d="{d}" class="{cls}"' + (' marker-end="url(#ar)"' if arrow else '') + '/>'

def svg():
    C, g = 180, []
    g.append(node(55, 0, 250, 42, 'n-step', [('選週期：日線為主', 't-b')], ('0',)))
    g.append(ln([(C, 42), (C, 56)]))
    g.append(node(30, 58, 300, 54, 'n-step', [('頁面 1 粗篩', 't-b'), ('交易量・波動率・ER', 't-s')], ('1', '2', '3')))
    g.append(ln([(C, 112), (C, 126)]))
    g.append(hexa(C, 128, 240, 58, [('判斷市況', 't-b'), ('ER ＋ ADX', 't-s')], '4'))
    g.append(ln([(C, 186), (C, 200)], arrow=False)); g.append(ln([(62, 200), (298, 200)], arrow=False))
    for x in (62, C, 298): g.append(ln([(x, 200), (x, 216)]))
    g.append(node(8, 218, 108, 58, 'n-bad', [('強趨勢', 't-bad'), ('先觀望', 't-s')]))
    g.append(node(126, 218, 108, 58, 'n-good', [('有方向／震盪', 't-good'), ('往下走', 't-s')]))
    g.append(node(244, 218, 108, 58, 'n-warn', [('兩指標分歧', 't-warn'), ('品質較低', 't-s')]))
    g.append(ln([(C, 276), (C, 302)]))
    g.append(ln([(298, 276), (298, 290), (C+14, 290), (C+14, 302)], cls="ed dash"))
    g.append(node(55, 304, 250, 42, 'n-step', [('看線圖定多空', 't-b')], ('5',)))
    g.append(ln([(C, 346), (C, 360)]))
    g.append(hexa(C, 362, 240, 52, [('依方向選擇網格', 't-b')], '6'))
    g.append(ln([(C, 414), (C, 428)], arrow=False)); g.append(ln([(62, 428), (298, 428)], arrow=False))
    for x in (62, C, 298): g.append(ln([(x, 428), (x, 444)]))
    g.append(node(8, 446, 108, 74, 'n-good', [('看多', 't-good'), ('現貨網格', 't-s'), ('或做多合約網格', 't-s')]))
    g.append(node(126, 446, 108, 74, 'n-good', [('看空', 't-good'), ('做空合約網格', 't-s')]))
    g.append(node(244, 446, 108, 74, 'n-warn', [('震盪', 't-warn'), ('現貨網格', 't-s'), ('或中性合約網格', 't-s')]))
    for x in (62, C, 298): g.append(ln([(x, 520), (x, 534)], arrow=False))
    g.append(ln([(62, 534), (298, 534)], arrow=False)); g.append(ln([(C, 534), (C, 550)]))
    g.append(node(55, 552, 250, 42, 'n-step', [('開單前確認（頁面 3）', 't-b')], ('7',)))
    g.append(ln([(C, 594), (C, 608)]))
    g.append(f'<rect x="120" y="610" width="120" height="38" rx="19" class="n-end"/><text x="{C}" y="634" class="t-end">開單</text>')
    return ('<svg viewBox="0 0 360 652" role="img" aria-label="網格開單流程圖：選週期、粗篩、判斷市況、看線圖定多空、選擇網格、開單前確認">'
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="ar"/></marker></defs>'
            + ''.join(g) + '</svg>')

if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = open(p, encoding='utf-8').read()
        s, n = re.subn(r'<div class="fc"><svg.*?</svg></div>', lambda m: '<div class="fc">' + svg() + '</div>', s, flags=re.S)
        assert n == 1, p
        open(p, 'w', encoding='utf-8').write(s)
        print('updated', p)
