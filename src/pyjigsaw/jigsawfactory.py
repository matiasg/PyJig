import base64
import logging
import os
import random
from io import StringIO
from math import ceil
from typing import Callable

from PIL import Image
from svgpathtools import svg2paths

logger = logging.getLogger(__name__)


class Cut:
    def __init__(
        self,
        pieces_height: int,
        pieces_width: int,
        abs_height: int | None = None,
        abs_width: int | None = None,
        image: str | None = None,
        stroke_color: str = "black",
        fill_color: str = "white",
        cmap: Callable[[complex], complex] = lambda z: z,
    ):
        self.pieces_height = pieces_height
        self.pieces_width = pieces_width
        self.abs_height: int
        self.abs_width: int
        self.image = image
        self.stroke_color = stroke_color
        self.fill_color = fill_color
        self.use_image = image is not None
        self.cmap = cmap

        if self.image is None:
            assert abs_height is not None and abs_width is not None, (
                "Please either set a height and width or pass an image in your function call"
            )
            self.abs_height = abs_height
            self.abs_width = abs_width
        else:
            if abs_height is not None or abs_width is not None:
                logger.warning(
                    "abs_height and abs_width parameters are ignored when an image is provided"
                )
            self.abs_width, self.abs_height = Image.open(self.image).size

        self.update_cut_template()

    def xy(self, z: complex) -> str:
        z = self.cmap(z)
        return f"{z.real:g},{z.imag:g}"

    def make_sides(
        self,
        start: complex,
        end: complex,
        notch_ratio: float,
        bend: float,
        perpendicular_side: complex,
    ):
        """Makes a side with a notch by using Bezier curves.

        It returns the side from start to end and also the same side from end to start.
        The backwards side is needed for the contiguous piece.

        The notch_ratio measures the size of the notch w.r.t end-start.
        The bend parameter controls how much the notch bends outwards or inwards.
        The direction the notch is bent depends on bend being >1 or <1 and perpendicular_side.
        """
        # control points
        mid_p = (start + end) / 2
        notch = (end - start) * notch_ratio
        bent_perp = perpendicular_side * (bend - 1)
        cp1 = mid_p + bent_perp
        cp2 = mid_p - notch / 2
        cp3 = mid_p - bent_perp - notch
        cp4 = mid_p - bent_perp + notch
        cp5 = mid_p + notch / 2
        # forward curve
        side = (
            f"C {self.xy(start)} {self.xy(cp1)} {self.xy(cp2)} "
            f"C {self.xy(cp3)} {self.xy(cp4)} {self.xy(cp5)} "
            f"C {self.xy(cp1)} {self.xy(end)} {self.xy(end)}"
        )
        # backwards curve
        inverted_side = (
            f"C {self.xy(end)} {self.xy(cp1)} {self.xy(cp5)} "
            f"C {self.xy(cp4)} {self.xy(cp3)} {self.xy(cp2)} "
            f"C {self.xy(cp1)} {self.xy(start)} {self.xy(start)}"
        )
        return side, inverted_side

    def update_cut_template(self, notch_size=0.2):
        piece_width = self.abs_width // self.pieces_width
        piece_height = (self.abs_height // self.pieces_height) * 1j
        piece_end = piece_width + piece_height
        number_of_pieces = self.pieces_height * self.pieces_width
        col = 0
        paths = []
        all_commands = {}
        metadata = {
            "PiecesCount": number_of_pieces,
            "Rows": self.pieces_height,
            "Cols": self.pieces_width,
            "TotalWidth": self.abs_width,
            "TotalHeight": self.abs_height,
            "PieceWidth": piece_width,
            "PieceHeight": piece_height.imag,
            "Pieces": [],
        }

        # Create svg path for each piece
        for i in range(number_of_pieces):
            row, col = i // self.pieces_width, i % self.pieces_width

            metadata["Pieces"].append(
                {
                    "PieceNumber": i,
                    "UpperEdge": row == 0,
                    "LowerEdge": row == self.pieces_height - 1,
                    "LeftEdge": col == 0,
                    "RightEdge": col == self.pieces_width - 1,
                }
            )

            # Set piece vertices
            v_00 = col * piece_width + row * piece_height
            v_11 = v_00 + piece_end
            v_10 = v_00 + piece_width
            v_01 = v_00 + piece_height

            # Control points for the puzzle notch curve, randomise direction
            curve_bend = 0.15
            bend = random.choice([1 - curve_bend, 1 + curve_bend])

            # Start command dictionary for storing commands for reuse on adjacent Pieces
            commands = []
            commands.append(f"M {self.xy(v_00)}")

            # Top section
            if row > 0:
                # Use inverted command from adjacent piece
                t = all_commands[f"{row}-{col}-t"]
            else:
                # Edge piece
                t = f"L {self.xy(v_10)}"
                all_commands[f"{row}-{col}-t"] = t
            commands.append(t)

            # Right section
            if col < self.pieces_width - 1:
                r, r_inverted = self.make_sides(
                    v_10, v_11, notch_size, bend, v_10 - v_00
                )
                all_commands[f"{row}-{col + 1}-l"] = r_inverted
            else:
                # Edge piece
                r = f"L {self.xy(v_11)}"

            commands.append(r)

            # Bottom section
            if row < self.pieces_height - 1:
                b, b_inverted = self.make_sides(
                    v_11, v_01, notch_size, bend, v_01 - v_00
                )
                all_commands[f"{row + 1}-{col}-t"] = b_inverted
            else:
                # Edge piece
                b = f"L {self.xy(v_01)}"

            commands.append(b)

            # Left section
            if col > 0:
                left_command = all_commands[f"{row}-{col}-l"]
                commands.append(left_command)

            # Close path (including straight line if Left edge piece)
            commands.append("z")

            # Construct path element
            d = "\n\t".join(commands)
            path = f'<path stroke="{self.stroke_color}" fill="{self.fill_color}" d="{d}" />'
            paths.append(path)

        paths = "\n\t".join(paths)
        self.svg_template = f"""\
            <svg width="{self.abs_width}" height="{self.abs_height}">
                {paths}
            </svg>
        """
        self.metadata = metadata
        logger.info("Puzzle template update complete")

    def to_svg(self, filepath):
        self.update_cut_template()
        with open(filepath, "w") as svg_file:
            svg_file.write(self.svg_template)
        logger.info("Puzzle cut template created %s", filepath)


def image_encode(original_image):
    ext = original_image.split(".")[1]
    ext = "jpeg" if ext == "jpg" else ext
    with open(original_image, "rb") as image:
        encoded_string = base64.b64encode(image.read()).decode("utf-8")
    return (ext, encoded_string)


class Jigsaw:
    IMAGE_SVG = """\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin:g} {ymin:g} {w:g} {h:g}" width="{w:g}" height="{h:g}">
        <defs>
            <path id="cropPath" d="{d}" />
            <clipPath id="crop">
                <use href="#cropPath" />
            </clipPath>
        </defs>
        <image href="data:image/{ext};base64,{encoded}" clip-path="url(#crop)"/>
    </svg>
    """
    NO_IMAGE_SVG = """\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin:g} {ymin:g} {w:g} {h:g}" width="{w:g}" height="{h:g}">
        <path d="{d}" stroke="black" fill="white"/>
    </svg>
    """

    def __init__(self, cut: Cut, image=None):
        self.cut = cut
        self.image = image

    def generate_svg_jigsaw(self, outdirectory):
        # Create output directory if it doesn't exist
        os.makedirs(outdirectory, exist_ok=True)

        if self.image:
            ext, encoded = image_encode(self.image)
        else:
            ext, encoded = None, None

        paths_ = svg2paths(StringIO(self.cut.svg_template))
        assert len(paths_) == 2
        paths, _ = paths_

        # Apply bounding box for each path and generate svg from template
        for p, path in enumerate(paths):
            # Get bounding box from svgpathtools - format is (xmin, xmax, ymin, ymax)
            xmin, xmax, ymin, ymax = path.bbox()
            width = xmax - xmin
            height = ymax - ymin

            if self.image and ext and encoded:
                # SVG with image
                svg = self.IMAGE_SVG.format(
                    xmin=xmin,
                    ymin=ymin,
                    w=width,
                    h=height,
                    d=path.d(),
                    ext=ext,
                    encoded=encoded,
                )
            else:
                # SVG without image (just the path shape)
                svg = self.NO_IMAGE_SVG.format(
                    xmin=xmin, ymin=ymin, w=width, h=height, d=path.d()
                )
            with open(os.path.join(outdirectory, f"{p}.svg"), "w") as file:
                file.write(svg)

        logger.info(
            "Svg puzzle set generated: %s (%d Pieces) Directory: %s",
            self.image,
            len(paths),
            outdirectory,
        )
