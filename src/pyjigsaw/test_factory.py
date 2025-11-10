import random
import json
from pathlib import Path
from pyjigsaw.jigsawfactory import Cut
from io import StringIO
from svgpathtools import svg2paths


def test_cut():
    random.seed(42)
    cut = Cut(pieces_height=5, pieces_width=4, abs_height=10, abs_width=20)
    cut.update_cut_template()
    assert cut.image is None
    cut.update_cut_template()
    assert cut.svg_template is not None
    sio = StringIO(cut.svg_template)
    spaths = svg2paths(sio)
    assert len(spaths) == 2
    s, paths = spaths
    assert len(s) == len(paths) == 20
    md = cut.metadata
    assert md["Rows"] == 5
    assert md["Cols"] == 4
    assert len(md["Pieces"]) == 20

    with open(Path(__file__).parent / "test_paths.json", "r") as o:
        oj = json.load(o)

    assert paths == oj
