from argparse import ArgumentParser
from pathlib import Path

from pyjigsaw import jigsawfactory


def main(image: Path, outdir: Path, rows: int, cols: int):
    mycut = jigsawfactory.Cut(rows, cols, 500, 500)
    myjig = jigsawfactory.Jigsaw(mycut, str(image))
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
