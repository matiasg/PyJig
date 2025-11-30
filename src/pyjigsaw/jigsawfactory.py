import base64
import logging
import os
import random
from io import StringIO
from math import ceil

from PIL import Image
from svgpathtools import svg2paths

logger = logging.getLogger(__name__)


def xy(z: complex) -> str:
    return f"{z.real:g},{z.imag:g}"


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
    ):
        self.pieces_height = pieces_height
        self.pieces_width = pieces_width
        self.abs_height: int
        self.abs_width: int
        self.image = image
        self.stroke_color = stroke_color
        self.fill_color = fill_color
        self.use_image = image is not None

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

    def update_cut_template(self, notch_size=0.2):
        piece_width = self.abs_width // self.pieces_width
        piece_height = (self.abs_height // self.pieces_height) * 1j
        piece_end = piece_width + piece_height
        half_piece_end = piece_end / 2
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
        for i in range(1, number_of_pieces + 1):
            # Find grid position
            row = ceil(i / self.pieces_width)
            col = col + 1 if col < self.pieces_width else 1

            metadata["Pieces"].append(
                {
                    "PieceNumber": i,
                    "UpperEdge": row == 1,
                    "LowerEdge": row == self.pieces_height,
                    "LeftEdge": col == 1,
                    "RightEdge": col == self.pieces_width,
                }
            )

            # Set piece vertices
            v_00 = (col - 1) * piece_width + (row - 1) * piece_height
            v_11 = v_00 + piece_end
            v_10 = v_00 + piece_width
            v_01 = v_00 + piece_height

            # Notch and notch_start should actually live in R^2 but at this point it is easier to make them in C
            notch_start = piece_end * (1 - notch_size) / 2
            notch = piece_end * notch_size

            # Control points for the puzzle notch curve, randomise direction
            curve_bend = 0.15
            side = random.choice([-curve_bend, curve_bend])
            bend_p, bend_m = 1 + side, 1 - side

            # Start command dictionary for storing commands for reuse on adjacent Pieces
            commands = []
            commands.append(f"M {xy(v_00)}")

            # Top section
            if row > 1:
                # Use inverted command from adjacent piece
                t = all_commands[f"{row}-{col}-t"]
            else:
                # Edge piece
                t = f"L {xy(v_10)}"
                all_commands[f"{row}-{col}-t"] = t
            commands.append(t)

            # Right section
            if col < self.pieces_width:
                # Generate curve
                control_point_1 = v_00 + piece_width * bend_p + piece_height * 0.5
                control_point_2 = v_10 + notch_start.imag * 1j
                control_point_3 = (
                    v_00 + piece_width * bend_m + piece_height * (0.5 + notch_size)
                )
                control_point_4 = v_10 + (notch_start + notch).imag * 1j
                r = (
                    f"C {xy(v_10)} {xy(control_point_1)} {xy(control_point_2)} "
                    f"S {xy(control_point_3)} {xy(control_point_4)} "
                    f"S {xy(v_11)} {xy(v_11)}"
                )

                # Create an inverted version for replicating the Left side of the adjacent piece
                control_point_5 = control_point_2 + notch.imag * 1j
                control_point_7 = control_point_4 - notch.imag * 1j
                control_point_6 = (
                    v_00
                    + piece_width * bend_m
                    + piece_height * 1.5
                    - (notch_start + notch).imag * 2 * 1j
                )
                r_inverted = (
                    f"C {xy(v_11)} {xy(control_point_1)} {xy(control_point_5)} "
                    f"S {xy(control_point_6)} {xy(control_point_7)} "
                    f"S {xy(v_10)} {xy(v_10)}"
                )
                all_commands[f"{row}-{col + 1}-l"] = r_inverted
            else:
                # Edge piece
                r = f"L {xy(v_11)}"

            commands.append(r)

            # Bottom section
            if row < self.pieces_height:
                control_point_1 = (
                    v_00
                    + half_piece_end
                    - half_piece_end.imag * 1j
                    + piece_height * bend_p
                )
                control_point_2 = v_01 + (notch + notch_start).real
                control_point_3 = (
                    v_00
                    + piece_width * 1.5
                    - notch_start.real * 2
                    - notch.real * 2
                    + piece_height * bend_m
                )
                control_point_4 = v_01 + notch_start.real
                control_point_5 = v_00 + piece_height

                # Generate curve
                b = (
                    f"C {xy(v_11)} {xy(control_point_1)} {xy(control_point_2)} "
                    f"S {xy(control_point_3)} {xy(control_point_4)} "
                    f"S {xy(control_point_5)} {xy(control_point_5)}"
                )

                # Create an inverted version for replicating the Left side of the adjacent piece
                control_point_6 = control_point_2 - notch.real
                control_point_7 = (
                    v_00
                    - piece_width * 0.5
                    + notch_start.real * 2
                    + notch.real * 2
                    + piece_height * bend_m
                )
                control_point_8 = control_point_4 + notch.real
                b_inverted = (
                    f"C {xy(control_point_5)} {xy(control_point_1)} {xy(control_point_6)} "
                    f"S {xy(control_point_7)} {xy(control_point_8)} "
                    f"S {xy(v_11)} {xy(v_11)}"
                )
                all_commands[f"{row + 1}-{col}-t"] = b_inverted
            else:
                # Edge piece
                b = f"L {xy(v_01)}"

            commands.append(b)

            if col > 1:
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
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="{} {} {w} {h}" width="{w}" height="{h}">
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
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="{} {} {w} {h}" width="{w}" height="{h}">
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
                    xmin, ymin, w=width, h=height, d=path.d(), ext=ext, encoded=encoded
                )
            else:
                # SVG without image (just the path shape)
                svg = self.NO_IMAGE_SVG.format(
                    xmin, ymin, w=width, h=height, d=path.d()
                )
            with open(os.path.join(outdirectory, f"{p}.svg"), "w") as file:
                file.write(svg)

        logger.info(
            "Svg puzzle set generated: %s (%d Pieces) Directory: %s",
            self.image,
            len(paths),
            outdirectory,
        )
