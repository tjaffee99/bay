"""Parse an OSM API XML file into ways/nodes with tags; utilities to filter and project."""
import xml.etree.ElementTree as ET, math, json, sys

def load(path):
    t = ET.parse(path).getroot()
    nodes = {}; ntags = {}
    for n in t.iter('node'):
        i = int(n.get('id')); nodes[i] = (float(n.get('lon')), float(n.get('lat')))
        tg = {x.get('k'): x.get('v') for x in n.findall('tag')}
        if tg: ntags[i] = tg
    ways = {}
    for w in t.iter('way'):
        i = int(w.get('id'))
        nds = [int(x.get('ref')) for x in w.findall('nd')]
        tg = {x.get('k'): x.get('v') for x in w.findall('tag')}
        ways[i] = (nds, tg)
    rels = {}
    for r in t.iter('relation'):
        i = int(r.get('id'))
        mem = [(m.get('type'), int(m.get('ref')), m.get('role')) for m in r.findall('member')]
        tg = {x.get('k'): x.get('v') for x in r.findall('tag')}
        rels[i] = (mem, tg)
    return nodes, ntags, ways, rels

def local(anchor, p):
    k = 111320 * math.cos(math.radians(anchor[1]))
    return ((p[0] - anchor[0]) * k, (p[1] - anchor[1]) * 110574)
