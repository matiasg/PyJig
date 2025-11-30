import random
import json
from pathlib import Path
from sys import breakpointhook
from pyjigsaw.jigsawfactory import Cut, Jigsaw
from io import StringIO
from svgpathtools import svg2paths
from tempfile import TemporaryDirectory


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


def _oneline(lines_j: str) -> str:
    lines = [line.strip() for line in lines_j.split("\n")]
    return " ".join(line for line in lines if line)


def test_jigsaw():
    random.seed(42)
    cut = Cut(pieces_height=5, pieces_width=4, abs_height=10, abs_width=20)
    cut.update_cut_template()
    myjig = Jigsaw(cut, image=None)
    expected = {
        0: """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0.0 0.0 5.5625 2.2249999999999996" width="5.5625" height="2.2249999999999996">
        <path d="M 0.0,0.0 L 5.0,0.0 C 5.0,0.0 4.25,1.0 5.0,0.8 C 5.75,0.6000000000000001 5.75,1.4 5.0,1.2 C 4.25,1.0 5.0,2.0 5.0,2.0 C 5.0,2.0 2.5,1.7 3.0,2.0 C 3.5,2.3 1.5,2.3 2.0,2.0 C 2.5,1.7000000000000002 0.0,2.0 0.0,2.0 L 0.0,0.0" stroke="black" fill="white"/>
        </svg>""",
        1: """<svg xmlns="http://www.w3.org/2000/svg" viewBox="4.666666666666667 0.0 5.895833333333333 2.2249999999999996" width="5.895833333333333" height="2.2249999999999996">
            <path d="M 5.0,0.0 L 10.0,0.0 C 10.0,0.0 9.25,1.0 10.0,0.8 C 10.75,0.6000000000000001 10.75,1.4 10.0,1.2 C 9.25,1.0 10.0,2.0 10.0,2.0 C 10.0,2.0 7.5,1.7 8.0,2.0 C 8.5,2.3 6.5,2.3 7.0,2.0 C 7.5,1.7000000000000002 5.0,2.0 5.0,2.0 C 5.0,2.0 4.25,1.0 5.0,1.2 C 5.75,1.4 5.75,0.6 5.0,0.8 C 4.25,1.0 5.0,0.0 5.0,0.0" stroke="black" fill="white"/>
        </svg>""",
        5: """<svg xmlns="http://www.w3.org/2000/svg" viewBox="4.4375 1.8666666666666667 6.125 2.3583333333333347" width="6.125" height="2.3583333333333347">
        <path d="M 5.0,2.0 C 5.0,2.0 7.5,1.7 7.0,2.0 C 6.5,2.3 8.5,2.3 8.0,2.0 C 7.5,1.7000000000000002 10.0,2.0 10.0,2.0 C 10.0,2.0 9.25,3.0 10.0,2.8 C 10.75,2.5999999999999996 10.75,3.4 10.0,3.2 C 9.25,3.0000000000000004 10.0,4.0 10.0,4.0 C 10.0,4.0 7.5,3.7 8.0,4.0 C 8.5,4.3 6.5,4.3 7.0,4.0 C 7.5,3.7 5.0,4.0 5.0,4.0 C 5.0,4.0 5.75,3.0 5.0,3.2 C 4.25,3.4000000000000004 4.25,2.6 5.0,2.8 C 5.75,2.9999999999999996 5.0,2.0 5.0,2.0" stroke="black" fill="white"/>
        </svg>""",
        19: """<svg xmlns="http://www.w3.org/2000/svg" viewBox="14.4375 7.866666666666664 5.5625 2.1333333333333364" width="5.5625" height="2.1333333333333364">
        <path d="M 15.0,8.0 C 15.0,8.0 17.5,7.7 17.0,8.0 C 16.5,8.3 18.5,8.3 18.0,8.0 C 17.5,7.699999999999999 20.0,8.0 20.0,8.0 L 20.0,10.0 L 15.0,10.0 C 15.0,10.0 15.75,9.0 15.0,9.2 C 14.25,9.399999999999999 14.25,8.6 15.0,8.8 C 15.75,9.000000000000002 15.0,8.0 15.0,8.0" stroke="black" fill="white"/>
        </svg>""",
    }
    with TemporaryDirectory() as td:
        myjig.generate_svg_jigsaw(td)
        outfiles = list(Path(td).glob("*.svg"))
        assert len(outfiles) == 20
        for i, content in expected.items():
            with open(Path(td) / f"{i}.svg", "r") as svgf:
                svg_content = svgf.read()
                assert _oneline(svg_content) == _oneline(content)
