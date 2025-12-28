import math
from argparse import ArgumentParser
from pathlib import Path
from typing import Callable

from pyjigsaw import jigsawfactory


def at_unit_square(f: Callable[[complex], complex]):
    def g(z: complex, width: float, height: float) -> complex:
        c = width / 2 + (height / 2) * 1j
        m = max(width, height) / 2
        w = (z - c) / m
        z = f(w)
        return (z * m) + c

    return g


@at_unit_square
def zsq(z: complex) -> complex:
    z += 1 + 1j
    return z * z


@at_unit_square
def rrot(z: complex) -> complex:
    r = abs(z)
    if r < 0.5:
        t = math.e ** (1j * math.pi * (0.5 - r))
        z *= t
    return z


@at_unit_square
def rgrw(z: complex) -> complex:
    r = abs(z)
    if r < 1:
        return z * (r + 1) / 2
    else:
        return z


def idz(z: complex, width: float, height: float) -> complex:
    return z


def main(image: Path, outdir: Path, rows: int, cols: int):
    mycut = jigsawfactory.Cut(rows, cols, image=image, cmap=rrot)
    myjig = jigsawfactory.Jigsaw(mycut, image)
    myjig.generate_svg_jigsaw(outdir)


def parse():
    parser = ArgumentParser()
    parser.add_argument("image", type=Path, help="path to image")
    parser.add_argument("outdir", type=Path, help="path to output directory")
    parser.add_argument("--rows", type=int, default=5)
    parser.add_argument("--cols", type=int, default=8)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse()
    main(args.image, args.outdir, args.rows, args.cols)
