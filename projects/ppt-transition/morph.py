#!/usr/bin/env python3
"""deck-morph engine: pair components across consecutive slides and wire up PowerPoint Morph.

  morph.py plan  deck.pptx                 analyse only, write the match report
  morph.py apply deck.pptx -o out.pptx     name matched components, add ghosts, set Morph
  morph.py strip deck.pptx -o clean.pptx   undo a previous apply
  morph.py storyboard report.json --images 'slide-*.jpg' --out story
  morph.py compare 'before-*.jpg' 'after-*.jpg'   check the visible slides did not change
"""
import argparse, copy, glob, hashlib, json, math, posixpath, re, sys, zipfile
from difflib import SequenceMatcher
from lxml import etree

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
      "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
      "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main"}
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
DEC_URI = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"
DEC_NS = "http://schemas.microsoft.com/office/drawing/2017/decorative"
PARSER = etree.XMLParser(resolve_entities=False, no_network=True)
SHAPES = ("sp", "pic", "grpSp", "graphicFrame", "cxnSp")
FOOTERS = ("ftr", "sldNum", "dt")
OURS = re.compile(r"^!!m\d+ (.*)$", re.S)
AUTO_NAME = re.compile(r".*\d\s*$", re.S)
CLONABLE_RELS = ("image", "hyperlink", "slide")


def q(tag):
    pfx, name = tag.split(":")
    return "{%s}%s" % (NS[pfx], name)


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


# ---------------------------------------------------------------- package ---
class Pkg:
    def __init__(self, path):
        with zipfile.ZipFile(path) as z:
            self.order = z.namelist()
            self.ctype = {n: z.getinfo(n).compress_type for n in self.order}
            self.raw = {n: z.read(n) for n in self.order}
        self.trees, self.dirty = {}, set()
        self.pres = next(t for (ty, t, _) in self.rels("").values() if ty.endswith("/officeDocument"))
        prels = self.rels(self.pres)
        root = self.xml(self.pres)
        self.slides = [prels[s.get(q("r:id"))][1] for s in root.findall("p:sldIdLst/p:sldId", NS)]
        sz = root.find("p:sldSz", NS)
        self.W, self.H = int(sz.get("cx")), int(sz.get("cy"))

    def xml(self, part):
        if part not in self.trees:
            self.trees[part] = etree.fromstring(self.raw[part], PARSER)
        return self.trees[part]

    @staticmethod
    def rels_name(part):
        d, f = posixpath.split(part)
        return posixpath.join(d, "_rels", f + ".rels")

    def rels(self, part):
        """{rId: (type, resolved target, mode)} for a part ('' = package root)."""
        rn, out = self.rels_name(part), {}
        if rn not in self.raw:
            return out
        for r in self.xml(rn):
            if not isinstance(r.tag, str):
                continue
            mode, t = r.get("TargetMode", "Internal"), r.get("Target", "")
            if mode == "Internal":
                t = t[1:] if t.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(part), t))
            out[r.get("Id")] = (r.get("Type", ""), t, mode)
        return out

    def add_rel(self, part, rtype, target, mode):
        for rid, rel in self.rels(part).items():
            if rel == (rtype, target, mode):
                return rid
        rn = self.rels_name(part)
        root, n = self.xml(rn), 1
        used = {r.get("Id") for r in root if isinstance(r.tag, str)}
        while "rId%d" % n in used:
            n += 1
        el = etree.SubElement(root, "{%s}Relationship" % PKG_REL)
        el.set("Id", "rId%d" % n)
        el.set("Type", rtype)
        el.set("Target", posixpath.relpath(target, posixpath.dirname(part)) if mode == "Internal" else target)
        if mode != "Internal":
            el.set("TargetMode", mode)
        self.dirty.add(rn)
        return "rId%d" % n

    def layout_of(self, part):
        """The part a slide (or layout) inherits placeholders from."""
        want = {"sld": "/slideLayout", "sldLayout": "/slideMaster"}.get(local(self.xml(part)))
        return next((t for (ty, t, _) in self.rels(part).values() if want and ty.endswith(want)), None)

    def save(self, path):
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self.order:
                data = self.raw[n]
                if n in self.dirty:
                    data = etree.tostring(self.trees[n], xml_declaration=True, encoding="UTF-8", standalone=True)
                z.writestr(zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)), data, compress_type=self.ctype[n])


# ------------------------------------------------------------- components ---
def cnv_of(el):
    return el[0].find("p:cNvPr", NS) if len(el) else None


def xfrm_of(el):
    path = {"grpSp": "p:grpSpPr/a:xfrm", "graphicFrame": "p:xfrm"}.get(local(el), "p:spPr/a:xfrm")
    return el.find(path, NS)


def read_box(xf):
    if xf is None or xf.find("a:off", NS) is None or xf.find("a:ext", NS) is None:
        return None
    o, e = xf.find("a:off", NS), xf.find("a:ext", NS)
    return [int(o.get("x")), int(o.get("y")), int(e.get("cx")), int(e.get("cy")), int(xf.get("rot", 0))]


def top_shapes(tree):
    """Yield (shape element, wrapper or None, twin elements) for each child of a shape tree."""
    for ch in tree:
        if local(ch) in SHAPES and ch.tag.startswith("{%s}" % NS["p"]):
            yield ch, None, []
        elif ch.tag == q("mc:AlternateContent"):
            found = [e for e in ch.iter() if local(e) in SHAPES and local(e.getparent()) in ("Choice", "Fallback")]
            if found:
                yield found[0], ch, found[1:]


def ph_of(el):
    return el[0].find("p:nvPr/p:ph", NS) if len(el) else None


def fam(ptype):
    return "title" if ptype in ("title", "ctrTitle") else "body" if ptype in ("body", "subTitle", "obj") else ptype


def inherited_box(pkg, part, ph, depth=0):
    """Position of a placeholder that carries none of its own: look at the layout, then the master."""
    parent = pkg.layout_of(part)
    if parent is None or depth > 2:
        return None
    ptype, idx, by_idx, by_type = ph.get("type", "obj"), ph.get("idx"), None, None
    for sp in pkg.xml(parent).iter(q("p:sp"), q("p:pic"), q("p:graphicFrame")):
        cand = ph_of(sp)
        if cand is None:
            continue
        if idx is not None and cand.get("idx") == idx and by_idx is None:
            by_idx = (sp, cand)
        if fam(cand.get("type", "obj")) == fam(ptype) and by_type is None:
            by_type = (sp, cand)
    hit = (by_type or by_idx) if depth else (by_idx or by_type)   # layouts key on idx, masters on type
    if hit is None:
        return inherited_box(pkg, parent, ph, depth + 1)
    return read_box(xfrm_of(hit[0])) or inherited_box(pkg, parent, hit[1], depth + 1)


class Comp:
    """One component (shape, picture, group, table, chart, connector) on a slide."""

    def __init__(self, pkg, part, num, el, wrapper=None, twins=(), parent=None):
        self.part, self.num, self.el, self.wrapper, self.twins, self.parent = part, num, el, wrapper, list(twins), parent
        self.tag = local(el)
        cnv = cnv_of(el)
        self.id = cnv.get("id") if cnv is not None else "?"
        self.name = cnv.get("name", "") if cnv is not None else ""
        self.ref = "%d:%s" % (num, self.id)
        self.user_bang = self.name.startswith("!!")
        ph = ph_of(el)
        self.ph = None if ph is None else {"ctrTitle": "title"}.get(ph.get("type", "obj"), ph.get("type", "obj"))
        self.ph_idx = None if ph is None else ph.get("idx")
        self.kind = self.tag
        if self.tag == "graphicFrame":
            uri = (el.find(".//a:graphicData", NS).get("uri", "") if el.find(".//a:graphicData", NS) is not None else "")
            self.kind = next((k for k in ("table", "chart", "diagram") if k in uri), "object")
        elif self.tag == "pic" and (el.find(".//a:videoFile", NS) is not None or el.find(".//a:audioFile", NS) is not None):
            self.kind = "media"
        paras = ["".join(t.text or "" for t in p.iter(q("a:t"))) for p in el.iter(q("a:p"))]
        self.text = re.sub(r"[ \t]+", " ", "\n".join(s.strip() for s in paras if s.strip())).strip()
        rels = pkg.rels(part)
        hashes = []
        for blip in el.iter(q("a:blip")):
            rel = rels.get(blip.get(q("r:embed"), ""))
            if rel and rel[1] in pkg.raw:
                hashes.append(hashlib.sha1(pkg.raw[rel[1]]).hexdigest()[:12])
        self.img = "+".join(sorted(hashes))
        sppr = el.find("p:spPr", NS)
        self.geom, self.fill = "", ""
        if sppr is not None:
            prst, cust = sppr.find("a:prstGeom", NS), sppr.find("a:custGeom", NS)
            self.geom = prst.get("prst", "") if prst is not None else ("cust:" + hashlib.sha1(etree.tostring(cust)).hexdigest()[:8] if cust is not None else "")
            for f in sppr:
                if local(f) in ("solidFill", "noFill", "gradFill", "blipFill", "pattFill"):
                    self.fill = local(f) + ":" + "".join("%s=%s" % (local(c), c.get("val", "")) for c in f if isinstance(c.tag, str))
                    break
        self.box = read_box(xfrm_of(el)) or (inherited_box(pkg, part, ph) if ph is not None else None)
        self.inert = ph is not None and not self.text and not self.img and self.tag == "sp"   # empty placeholder: not shown
        self.children = []
        if self.tag == "grpSp":
            self.children = [Comp(pkg, part, num, e, w, t, self) for e, w, t in top_shapes(el)]
        self.label = self.name
        self.chain = self     # union-find parent
        self.new_name = None

    def root(self):
        c = self
        while c.chain is not c:
            c.chain = c.chain.chain
            c = c.chain
        return c

    def brief(self):
        d = {"ref": self.ref, "name": self.label, "kind": self.kind}
        if self.text:
            d["text"] = self.text[:60].replace("\n", " / ")
        if self.box:
            d["box"] = self.box[:4]
        return d


def walk(cs):
    for c in cs:
        yield c
        yield from walk(c.children)


def slide_comps(pkg, part, num):
    tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
    out, seen = [Comp(pkg, part, num, e, w, t) for e, w, t in top_shapes(tree)], {}
    for c in walk(out):                           # some generators reuse shape ids on a slide
        seen[c.ref] = seen.get(c.ref, 0) + 1
        if seen[c.ref] > 1:
            c.ref += "#%d" % seen[c.ref]
    return out


# --------------------------------------------------------------- matching ---
def ratio(u, v):
    return 1.0 if max(u, v) <= 0 else min(u, v) / max(u, v)


def proximity(a, b, diag):
    (ax, ay, aw, ah), (bx, by, bw, bh) = a.box[:4], b.box[:4]
    d = math.hypot((ax + aw / 2) - (bx + bw / 2), (ay + ah / 2) - (by + bh / 2))
    return max(0.0, 1 - d / (0.35 * diag)), math.sqrt(ratio(aw, bw) * ratio(ah, bh)), d


def score(a, b, diag):
    """How confident are we that b (next slide) is the same component as a? -> (0..1, reason)"""
    if a.kind != b.kind:
        return 0.0, ""
    if a.ph in FOOTERS or b.ph in FOOTERS:
        return (0.9, "same footer placeholder") if a.ph == b.ph else (0.0, "")
    s, why = 0.0, []
    if a.ph and a.ph == b.ph:
        if a.ph == "title":
            s += 0.55
            why.append("both are the slide title")
        else:
            s += 0.4 if a.ph_idx == b.ph_idx else 0.25
            why.append("same %s placeholder" % a.ph)
    if a.text and b.text:
        if a.text == b.text:
            s += 0.6 if len(a.text) >= 3 else 0.3
            why.append("same text")
        else:
            sm = SequenceMatcher(None, a.text[:400], b.text[:400])
            if sm.real_quick_ratio() >= 0.6 and sm.quick_ratio() >= 0.6 and sm.ratio() >= 0.6:
                s += 0.45 * sm.ratio()
                why.append("similar text")
    elif not a.text and not b.text:
        s += 0.05
    if a.img and a.img == b.img:
        s += 0.7
        why.append("same image")
    if a.geom and a.geom == b.geom:
        s += 0.12
    if a.fill and a.fill == b.fill:
        s += 0.08
    if a.name and a.name == b.name:
        s += 0.15 if AUTO_NAME.match(a.name) else 0.35
        why.append("same name")
    if a.box and b.box:
        pos, size, _ = proximity(a, b, diag)
        s += 0.15 * pos + 0.15 * size + 0.1 * pos * size
        if pos > 0.97 and size > 0.97:
            why.append("same place")
        elif size > 0.9 and pos < 0.9:
            why.append("same size, moved")
    return min(s, 1.0), ", ".join(why) or "similar shape, size and position"


def look(c):
    """A signature for 'what it looks like'; None when the look is too plain to mean anything."""
    solid = (c.fill and not c.fill.startswith("noFill")) or c.kind == "cxnSp"
    return (c.kind, c.geom, c.fill) if solid and c.box and not c.inert else None


def match(A, B, ctx):
    """Greedy one-to-one matching between two component lists. -> [(a, b, score, why)]"""
    cand = []
    la, lb = [look(c) for c in A], [look(c) for c in B]
    for a in A:
        for b in B:
            if a.inert or b.inert or a.ref in ctx["ignore"] or b.ref in ctx["ignore"] or (a.ref, b.ref) in ctx["unlink"]:
                continue
            if (a.ref, b.ref) in ctx["link"]:
                if a.kind != b.kind:
                    ctx["warn"].append("override %s -> %s skipped: Morph cannot pair a %s with a %s" % (a.ref, b.ref, a.kind, b.kind))
                    continue
                sc, why = 9.0, "forced by override"
            elif a.user_bang or b.user_bang:
                sc, why = (8.0, "already share a !! name") if a.name == b.name and a.kind == b.kind else (0.0, "")
            else:
                sc, why = score(a, b, ctx["diag"])
                lk = look(a)                      # a one-of-a-kind look, e.g. the logo that shrinks into a corner
                if lk and lk == look(b) and la.count(lk) == 1 and lb.count(lk) == 1 and \
                        (a.kind == "cxnSp" or ratio(a.box[2] * b.box[3], b.box[2] * a.box[3]) > 0.8):
                    sc += 0.35
                    why = ", ".join([w for w in [why] if w and not w.startswith("similar shape")] + ["the only one with that look on both slides"])
            if sc >= ctx["threshold"]:
                dist = proximity(a, b, ctx["diag"])[2] if a.box and b.box else 0
                cand.append((-sc, dist, len(cand), a, b, why))
    used, out = set(), []
    for negsc, _, _, a, b, why in sorted(cand, key=lambda c: c[:3]):
        if id(a) in used or id(b) in used:
            continue
        used |= {id(a), id(b)}
        b.root().chain = a.root()
        out.append((a, b, min(-negsc, 1.0), why))
        if a.children and b.children:
            out[-1] += (match(a.children, b.children, ctx),)
    return out


# ---------------------------------------------------------- ghosts / xml ----
def extent(box):
    x, y, w, h, rot = box
    if rot % 10800000:
        r = math.hypot(w, h) / 2
        return x + w / 2 - r, y + h / 2 - r, x + w / 2 + r, y + h / 2 + r
    return x, y, x + w, y + h


def offcanvas(box, W, H):
    l, t, r, b = extent(box)
    return r <= 0 or b <= 0 or l >= W or t >= H


def ghost_block(pkg, c, target_part, target_comps):
    """Why this component cannot be cloned onto another slide (None = it can)."""
    if c.wrapper is not None or c.kind in ("chart", "diagram", "object", "media"):
        return "%s cannot be cloned" % ("wrapped object" if c.wrapper is not None else c.kind)
    if c.box is None:
        return "position unknown"
    if c.ph:
        if c.ph in FOOTERS:
            return "footer placeholder"
        layout = pkg.layout_of(target_part)
        slots = [ph_of(sp) for sp in pkg.xml(layout).iter(q("p:sp"), q("p:pic"))] if layout else []
        if pkg.layout_of(c.part) != layout and not any(
                sl is not None and sl.get("idx") == c.ph_idx and fam(sl.get("type", "obj")) == fam(c.ph) for sl in slots):
            return "placeholder the other slide's layout does not have"
        if any(t.ph == c.ph and t.ph_idx == c.ph_idx for t in target_comps):
            return "target slide already uses that placeholder"
    rels = pkg.rels(c.part)
    for e in c.el.iter():
        for k, v in e.attrib.items():
            if k.startswith("{%s}" % NS["r"]) and v and not (v in rels and rels[v][0].rsplit("/", 1)[-1] in CLONABLE_RELS):
                return "linked content cannot be cloned"
    return None


def shifts(comps, W, H, style, flow, sign):
    """Offsets that park each component fully off the slide. sign=+1 entering side, -1 leaving side."""
    pad, out = 0.02 * W, {}
    exts = {id(c): extent(c.box) for c in comps}
    if style == "push" and comps:
        horiz = flow in ("right", "left")
        d = sign * (1 if flow in ("right", "bottom") else -1)
        lo = min(e[0 if horiz else 1] for e in exts.values())
        hi = max(e[2 if horiz else 3] for e in exts.values())
        size = W if horiz else H
        s = (size + pad - min(lo, 0)) if d > 0 else -(max(hi, size) + pad)   # one slide-width, so the block moves as one
        return {id(c): ((s, 0) if horiz else (0, s)) for c in comps}
    for c in comps:
        l, t, r, b = exts[id(c)]
        opts = [(r + pad, (-(r + pad), 0)), (W - l + pad, (W - l + pad, 0)), (b + pad, (0, -(b + pad))), (H - t + pad, (0, H - t + pad))]
        out[id(c)] = min(opts, key=lambda o: o[0])[1]
    return out


def make_ghost(pkg, c, target_part, dx, dy, next_id):
    g = copy.deepcopy(c.el)
    g.tail = None
    cnv = cnv_of(g)
    for k in ("descr", "title"):                  # a parked copy should be silent to screen readers and not clickable
        cnv.attrib.pop(k, None)
    for link in cnv.findall("a:hlinkClick", NS) + cnv.findall("a:hlinkHover", NS):
        cnv.remove(link)
    src_rels = pkg.rels(c.part)
    for e in g.iter():
        if not isinstance(e.tag, str):
            continue
        for k, v in list(e.attrib.items()):
            if k.startswith("{%s}" % NS["r"]) and v:
                e.set(k, pkg.add_rel(target_part, *src_rels[v]))
        if local(e) == "cNvPr":
            e.set("id", str(next_id[0]))
            next_id[0] += 1
    lst = cnv.find("a:extLst", NS)
    if lst is None:
        lst = etree.SubElement(cnv, q("a:extLst"))
    for old in [e for e in lst if e.get("uri") == DEC_URI]:
        lst.remove(old)
    ext = etree.SubElement(lst, q("a:ext"))
    ext.set("uri", DEC_URI)
    etree.SubElement(ext, "{%s}decorative" % DEC_NS, nsmap={"adec": DEC_NS}).set("val", "1")
    xf = xfrm_of(g)
    if xf is None or xf.find("a:off", NS) is None:      # placeholder that inherited its position
        if xf is None:
            xf = etree.Element(q("a:xfrm"))
            g.find("p:spPr", NS).insert(0, xf)
        for name, keys, vals in (("a:off", ("x", "y"), c.box[:2]), ("a:ext", ("cx", "cy"), c.box[2:4])):
            node = etree.SubElement(xf, q(name))
            for kk, vv in zip(keys, vals):
                node.set(kk, str(int(vv)))
    off = xf.find("a:off", NS)
    off.set("x", str(int(c.box[0] + dx)))
    off.set("y", str(int(c.box[1] + dy)))
    return g


def is_ghost(el, W, H):
    cnv = cnv_of(el)
    if cnv is None or not cnv.get("name", "").startswith("!!"):
        return False
    dec = cnv.find("a:extLst/a:ext[@uri='%s']" % DEC_URI, NS)
    box = read_box(xfrm_of(el))
    return dec is not None and box is not None and offcanvas(box, W, H)


def find_transition(root):
    for ch in root:
        if not isinstance(ch.tag, str):
            continue
        tr = ch if ch.tag == q("p:transition") else (ch.find(".//p:transition", NS) if ch.tag == q("mc:AlternateContent") else None)
        if tr is not None:
            kids = [local(k) for k in tr if isinstance(k.tag, str)]
            return ch, tr, (kids[0] if kids else "none")
    return None, None, None


def set_transition(root, dur_ms=None, option=None):
    """Replace the slide transition with Morph (or drop it when dur_ms is None). Returns the old type."""
    holder, tr, old = find_transition(root)
    adv = {}
    if holder is not None:
        adv = {k: tr.get(k) for k in ("advClick", "advTm") if tr.get(k) is not None}
        root.remove(holder)
    anchor = root.find("p:clrMapOvr", NS)
    anchor = anchor if anchor is not None else root.find("p:cSld", NS)
    if dur_ms is None:
        if adv:
            node = etree.Element(q("p:transition"))
            node.attrib.update(adv)
            anchor.addnext(node)
        return old
    ac = etree.SubElement(root, q("mc:AlternateContent"), nsmap={"mc": NS["mc"]})
    choice = etree.SubElement(ac, q("mc:Choice"), nsmap={"p159": NS["p159"]})
    choice.set("Requires", "p159")
    t1 = etree.SubElement(choice, q("p:transition"), nsmap={"p14": NS["p14"]})
    t1.set("spd", "slow")
    t1.set(q("p14:dur"), str(dur_ms))
    etree.SubElement(t1, q("p159:morph")).set("option", option)
    t2 = etree.SubElement(etree.SubElement(ac, q("mc:Fallback")), q("p:transition"))
    t2.set("spd", "slow")
    etree.SubElement(t2, q("p:fade"))
    for t in (t1, t2):
        t.attrib.update(adv)
    anchor.addnext(ac)                            # moves it to its schema position
    return old


def strip(pkg):
    """Undo a previous apply: drop ghosts, restore names, remove Morph transitions. -> count of changes"""
    total = 0
    for part in pkg.slides:
        root, n = pkg.xml(part), 0
        tree = root.find("p:cSld/p:spTree", NS)
        for el, wrapper, _ in list(top_shapes(tree)):
            if wrapper is None and is_ghost(el, pkg.W, pkg.H):
                tree.remove(el)
                n += 1
        for cnv in root.iter(q("p:cNvPr")):
            m = OURS.match(cnv.get("name", ""))
            if m:
                cnv.set("name", m.group(1))
                n += 1
        holder = find_transition(root)[0]
        if holder is not None and holder.find(".//p159:morph", NS) is not None:
            set_transition(root)
            n += 1
        if n:
            pkg.dirty.add(part)
        total += n
    return total


# ------------------------------------------------------------------- run ----
def parse_slides(spec, total):
    out = set()
    for chunk in spec.split(","):
        lo, _, hi = chunk.strip().partition("-")
        out |= set(range(int(lo), int(hi or lo) + 1))
    return {n for n in out if 1 <= n <= total}


def run(args, write):
    pkg = Pkg(args.deck)
    W, H = pkg.W, pkg.H
    prior = strip(pkg)
    ov = json.load(open(args.overrides)) if args.overrides else {}
    ctx = {"diag": math.hypot(W, H), "threshold": args.threshold, "warn": [],
           "link": {tuple(p) for p in ov.get("link", [])}, "unlink": {tuple(p) for p in ov.get("unlink", [])},
           "ignore": set(ov.get("ignore", []))}
    if prior:
        ctx["warn"].append("input had already been processed; rebuilt from scratch (%d earlier changes undone)" % prior)
    comps = {n: slide_comps(pkg, part, n) for n, part in enumerate(pkg.slides, 1)}
    had_dup_ids = {n for n in comps if len({c.id for c in walk(comps[n])}) < sum(1 for _ in walk(comps[n]))}
    visible = [n for n, part in enumerate(pkg.slides, 1) if pkg.xml(part).get("show", "1") not in ("0", "false")]
    wanted = parse_slides(args.slides, len(pkg.slides)) if args.slides else set(visible)
    wanted -= set(ov.get("no_morph_slides", []))
    pairs = [(a, b) for a, b in zip(visible, visible[1:]) if b in wanted]
    text_modes = {int(k): v for k, v in ov.get("text_mode", {}).items()}
    report = {"deck": args.deck, "slide_size": [W, H], "style": args.style, "visible_slides": visible, "pairs": []}
    plans = []                                    # (a, b, matches, entering on b, leaving from a)
    for a, b in pairs:
        ms = match(comps[a], comps[b], ctx)
        ma, mb = {id(m[0]) for m in ms}, {id(m[1]) for m in ms}
        live = lambda cs, done: [c for c in cs if id(c) not in done and not c.inert]
        plans.append((a, b, ms, live(comps[b], mb), live(comps[a], ma)))
        for sn in (a, b):
            n_empty = sum(c.inert for c in comps[sn])
            msg = "slide %d has %d empty placeholder(s); delete them in PowerPoint if Morph misbehaves there" % (sn, n_empty)
            if n_empty and msg not in ctx["warn"]:
                ctx["warn"].append(msg)

    # decide ghosts, then name every chain that needs a name
    ghosts = []                                   # (component, target slide number, dx, dy)
    for a, b, ms, enter, leave in plans:
        entry = {"from": a, "to": b, "matches": [], "enter": [], "leave": []}
        for m in ms:
            x, y, sc, why = m[:4]
            item = {"from": x.brief(), "to": y.brief(), "score": round(sc, 2), "why": why,
                    "confidence": "strong" if sc >= 0.8 else "likely" if sc >= 0.6 else "weak"}
            if len(m) > 4:
                item["inside_group"] = len(m[4])
            entry["matches"].append(item)
        for group, dst, key, sign in ((enter, a, "enter", 1), (leave, b, "leave", -1)):
            ok = []
            for c in group:
                why_not = "style is fade" if args.style == "fade" else "ignored by override" if c.ref in ctx["ignore"] else ghost_block(pkg, c, pkg.slides[dst - 1], comps[dst])
                entry[key].append(dict(c.brief(), motion="fade" if why_not else "glide", **({"note": why_not} if why_not and args.style != "fade" else {})))
                if not why_not:
                    ok.append(c)
            off = shifts(ok, W, H, args.style, args.flow, sign)
            for c, item in zip(ok, [i for i in entry[key] if i["motion"] == "glide"]):
                ghosts.append((c, dst, off[id(c)][0], off[id(c)][1]))
                item["parked_at_offset"] = [round(off[id(c)][0] / W, 2), round(off[id(c)][1] / H, 2)]   # in slide widths / heights
        report["pairs"].append(entry)

    members, counter = {}, [0]
    involved = {n for a, b in pairs for n in (a, b)}
    for n in sorted(comps):
        for c in walk(comps[n]):
            members.setdefault(id(c.root()), []).append(c)
    ghosted = {id(g[0].root()) for g in ghosts}
    for n in sorted(comps):
        for c in walk(comps[n]):
            chain = members[id(c.root())]
            alone = len(chain) == 1 and id(c.root()) not in ghosted
            isolate = args.isolate and n in involved and c.parent is None and not c.inert and not c.user_bang
            if c.new_name or (alone and not isolate):
                continue
            name = next((m.name for m in chain if m.user_bang), None)     # a name the user set by hand wins
            if name is None:
                counter[0] += 1
                name = "!!m%d %s" % (counter[0], (chain[0].name or chain[0].kind)[:48])
            for mbr in chain:
                mbr.new_name = name
    by_ref = {c.ref: c for n in comps for c in walk(comps[n])}
    for entry in report["pairs"]:
        for m in entry["matches"]:
            m["morph_name"] = by_ref[m["from"]["ref"]].new_name

    stats = {"transitions": len(pairs), "matched": sum(len(e["matches"]) for e in report["pairs"]),
             "glide": len(ghosts), "fade": sum(i["motion"] == "fade" for e in report["pairs"] for i in e["enter"] + e["leave"]),
             "weak": sum(m["confidence"] == "weak" for e in report["pairs"] for m in e["matches"])}
    report.update(summary=stats, warnings=ctx["warn"], hidden_slides=[n for n in comps if n not in visible])

    if write:
        for n in sorted(comps):
            for c in walk(comps[n]):
                if c.new_name and c.new_name != c.name:
                    for el in [c.el] + c.twins:
                        if cnv_of(el) is not None:
                            cnv_of(el).set("name", c.new_name)
                    pkg.dirty.add(c.part)
        next_id = {}
        for n, part in enumerate(pkg.slides, 1):
            ids = [int(e.get("id")) for e in pkg.xml(part).iter(q("p:cNvPr")) if (e.get("id") or "").isdigit()]
            next_id[n] = [max(ids + [1]) + 1]
        twin = {}                                 # (id(source comp), target slide) -> element on target slide
        for a, b, ms, _, _ in plans:
            for m in ms:
                twin[(id(m[0]), b)], twin[(id(m[1]), a)] = m[1].wrapper if m[1].wrapper is not None else m[1].el, m[0].wrapper if m[0].wrapper is not None else m[0].el
        for c, dst, dx, dy in ghosts:
            part = pkg.slides[dst - 1]
            g = make_ghost(pkg, c, part, dx, dy, next_id[dst])
            tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
            sibs = comps[c.num]
            before = [twin.get((id(s), dst)) for s in sibs[:sibs.index(c)]]
            before = [e for e in before if e is not None]
            if before:
                before[-1].addnext(g)             # keep the stacking order of the source slide
            else:
                tree.find("p:grpSpPr", NS).addnext(g)
            twin[(id(c), dst)] = g
            pkg.dirty.add(part)
        for a, b in pairs:
            root = pkg.xml(pkg.slides[b - 1])
            mode = {"object": "byObject", "word": "byWord", "char": "byChar"}[text_modes.get(b, args.text_mode)]
            old = set_transition(root, int(args.duration * 1000), mode)
            if old not in (None, "none", "morph"):
                ctx["warn"].append("slide %d: replaced its existing '%s' transition with Morph" % (b, old))
            if root.find("p:timing", NS) is not None and root.find("p:timing", NS).find(".//p:cTn[@presetClass]", NS) is not None:
                ctx["warn"].append("slide %d has its own click/entrance animations; they still run after the Morph" % b)
            pkg.dirty.add(pkg.slides[b - 1])
        pkg.save(args.output)
        problems = self_check(args.output, had_dup_ids)
        report["self_check"] = problems or "passed"
        report["output"] = args.output
    json.dump(report, open(args.report, "w"), indent=1, ensure_ascii=False)
    print_summary(report, write)
    return 1 if write and report["self_check"] != "passed" else 0


def self_check(path, had_dup_ids=()):
    """Re-open the written deck and look for anything PowerPoint would choke on."""
    bad = []
    try:
        pkg = Pkg(path)
    except Exception as e:                        # noqa: BLE001
        return ["cannot re-open output: %s" % e]
    for n, part in enumerate(pkg.slides, 1):
        root, rels = pkg.xml(part), pkg.rels(part)
        real = [e for e in root.iter(q("p:cNvPr")) if not any(a.tag == q("mc:Fallback") for a in e.iterancestors())]
        ids = [e.get("id") for e in real]
        names = [e.get("name") for e in real if OURS.match(e.get("name", ""))]
        if len(ids) != len(set(ids)) and n not in had_dup_ids:
            bad.append("slide %d: duplicate shape ids" % n)
        if len(names) != len(set(names)):
            bad.append("slide %d: a morph name is used twice" % n)
        for e in root.iter():
            if isinstance(e.tag, str):
                bad += ["slide %d: dangling relationship %s" % (n, v) for k, v in e.attrib.items() if k.startswith("{%s}" % NS["r"]) and v and v not in rels]
        holder = find_transition(root)[0]
        if holder is not None:
            kids = list(root)
            before = [k for k in kids[:kids.index(holder)] if isinstance(k.tag, str)]
            after = [k for k in kids[kids.index(holder) + 1:] if isinstance(k.tag, str)]
            if any(local(k) in ("timing", "extLst") for k in before) or any(local(k) in ("cSld", "clrMapOvr") for k in after):
                bad.append("slide %d: transition is in the wrong place" % n)
    return bad


def print_summary(report, wrote):
    s = report["summary"]
    print("%s  |  %d transitions  |  %d components morph, %d glide in/out, %d fade" % (
        "APPLIED -> " + report["output"] if wrote else "PLAN (nothing written)", s["transitions"], s["matched"], s["glide"], s["fade"]))
    for e in report["pairs"]:
        g = sum(i["motion"] == "glide" for i in e["enter"] + e["leave"])
        f = len(e["enter"]) + len(e["leave"]) - g
        print("  slide %d -> %d: %d morph, %d glide, %d fade" % (e["from"], e["to"], len(e["matches"]), g, f))
        for m in e["matches"]:
            if m["confidence"] == "weak":
                print("      weak (%.2f): %s [%s] -> %s [%s]  (%s)" % (m["score"], m["from"]["name"], m["from"]["ref"], m["to"]["name"], m["to"]["ref"], m["why"]))
    for w in report["warnings"]:
        print("  note: " + w)
    if wrote:
        print("  self-check: " + (report["self_check"] if isinstance(report["self_check"], str) else "; ".join(report["self_check"])))


def storyboard(args):
    from PIL import Image, ImageDraw, ImageFont
    rep = json.load(open(args.report))
    W, H = rep["slide_size"]
    nat = lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
    files = sorted(glob.glob(args.images), key=nat)
    img_of = dict(zip(rep["visible_slides"], files))
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()
    palette = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080", "#9a6324", "#800000", "#000075", "#f032e6", "#808000", "#469990"]
    pw = 900
    ph = int(pw * H / W)
    made = []
    for e in rep["pairs"]:
        if e["from"] not in img_of or e["to"] not in img_of:
            continue
        sheet = Image.new("RGB", (pw * 2 + 60, ph + 110), "white")
        d = ImageDraw.Draw(sheet)
        for i, key in enumerate(("from", "to")):
            x0 = 20 + i * (pw + 20)
            sheet.paste(Image.open(img_of[e[key]]).convert("RGB").resize((pw, ph)), (x0, 50))
            d.rectangle([x0, 50, x0 + pw, 50 + ph], outline="#888888")
            d.text((x0, 16), "Slide %d" % e[key], fill="black", font=font)

            def rect(box, colour, tag, width=4, x0=x0):
                x, y, w, h = [v * pw / W for v in box]
                d.rectangle([x0 + x, 50 + y, x0 + x + max(w, 3), 50 + y + max(h, 3)], outline=colour, width=width)
                ty = 50 + y - 24 if y >= 24 else 50 + y
                d.rectangle([x0 + x, ty, x0 + x + 12 * len(tag) + 8, ty + 24], fill=colour)
                d.text((x0 + x + 4, ty + 2), tag, fill="white", font=font)
            for k, m in enumerate(e["matches"], 1):
                if "box" in m[key]:
                    rect(m[key]["box"], palette[(k - 1) % len(palette)], str(k) + ("?" if m["confidence"] == "weak" else ""))
            for item in e["leave" if key == "from" else "enter"]:
                if "box" in item:
                    rect(item["box"], "#111111" if item["motion"] == "glide" else "#999999", "out" if key == "from" else "in", 2)
        d.text((20, ph + 62), "numbered = same component, morphs between slides ('?' = weak match, check it)   "
               "black in/out = glides on or off   grey in/out = fades", fill="black", font=font)
        out = "%s-%d-%d.png" % (args.out, e["from"], e["to"])
        sheet.save(out)
        made.append(out)
    print("\n".join(made) if made else "no storyboard pages written (check --images)")


def compare(args):
    from PIL import Image, ImageChops
    nat = lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
    before, after = (sorted(glob.glob(g), key=nat) for g in (args.before, args.after))
    if not before or len(before) != len(after):
        print("cannot compare: %d images before, %d after" % (len(before), len(after)))
        return 1
    changed = []
    for i, (x, y) in enumerate(zip(before, after), 1):
        a, b = Image.open(x).convert("RGB"), Image.open(y).convert("RGB")
        if a.size != b.size or max(band.getextrema()[1] for band in ImageChops.difference(a, b).split()) > args.tolerance:
            changed.append(i)
    print("all %d slides look identical before and after" % len(before) if not changed else
          "slides that look different (by position among rendered slides): %s" % changed)
    return 1 if changed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "apply"):
        sp = sub.add_parser(name)
        sp.add_argument("deck")
        sp.add_argument("-o", "--output", required=(name == "apply"))
        sp.add_argument("--style", choices=("push", "assemble", "fade"), default="push",
                        help="what unmatched components do: push = glide as one block, assemble = each from its nearest edge, fade = plain Morph")
        sp.add_argument("--enter-from", dest="flow", choices=("right", "left", "top", "bottom"), default="right", help="side new content arrives from (push style)")
        sp.add_argument("--duration", type=float, default=1.5, help="seconds per transition")
        sp.add_argument("--text-mode", choices=("object", "word", "char"), default="object")
        sp.add_argument("--threshold", type=float, default=0.5, help="minimum match confidence")
        sp.add_argument("--slides", help="destination slides to animate into, e.g. 2-6,9 (default: all)")
        sp.add_argument("--overrides", help="JSON file with link / unlink / ignore / no_morph_slides / text_mode")
        sp.add_argument("--no-isolate", dest="isolate", action="store_false", help="leave unmatched components to PowerPoint's own guessing")
        sp.add_argument("--report", default="morph_report.json")
    sp = sub.add_parser("strip")
    sp.add_argument("deck")
    sp.add_argument("-o", "--output", required=True)
    sp = sub.add_parser("storyboard")
    sp.add_argument("report")
    sp.add_argument("--images", required=True, help="glob of rendered slide images, in slide order")
    sp.add_argument("--out", default="storyboard")
    sp = sub.add_parser("compare")
    sp.add_argument("before", help="glob of slide images rendered from the original deck")
    sp.add_argument("after", help="glob of slide images rendered from the morphed deck")
    sp.add_argument("--tolerance", type=int, default=8)
    args = ap.parse_args()
    if args.cmd == "storyboard":
        return storyboard(args)
    if args.cmd == "compare":
        return compare(args)
    try:
        if args.cmd == "strip":
            pkg = Pkg(args.deck)
            n = strip(pkg)
            pkg.save(args.output)
            print("removed %d morph changes -> %s" % (n, args.output))
            return 0
        return run(args, write=(args.cmd == "apply"))
    except zipfile.BadZipFile:
        print("Not a readable .pptx: an old .ppt or a password-protected file has to be re-saved as plain .pptx first.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
