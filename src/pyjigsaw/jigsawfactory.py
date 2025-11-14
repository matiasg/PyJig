import base64
import logging
import os
import random
from io import StringIO
from math import ceil

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
        notch_start = (1 - notch_size) / 2
        piece_width = self.abs_width // self.pieces_width
        piece_height = self.abs_height // self.pieces_height
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
            "PieceHeight": piece_height,
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

            # Set pixel start and end positions
            origin_x = (col - 1) * piece_width
            origin_y = (row - 1) * piece_height
            end_x = origin_x + piece_width
            end_y = origin_y + piece_height

            # Calculate distance to the start of the notch
            to_x_notch = piece_width * notch_start
            to_y_notch = piece_height * notch_start
            x_notch = piece_width * notch_size
            y_notch = piece_height * notch_size

            # Control points for the puzzle notch curve, randomise direction
            curve_multiplier_1, curve_multiplier_2 = random.sample([0.85, 1.15], 2)

            # Start command dictionary for storing commands for reuse on adjacent Pieces
            commands = []
            commands.append("M {},{}".format(origin_x, origin_y))

            # Top section
            if row > 1:
                # Use inverted command from adjacent piece
                t = all_commands["{}-{}-t".format(row, col)]
            else:
                # Edge piece
                t = "L {},{}".format(str(end_x), str(origin_y))
                all_commands["{}-{}-t".format(row, col)] = t
            commands.append(t)

            # Right section
            if col < self.pieces_width:
                # Generate curve
                r = (
                    "C {x:g},{origin_h:g} {w_curve_1:g},{half_piece_h:g} {x:g},{to_notch_start:g} "
                    "S {w_curve_2:g},{control_point:g} {x:g},{to_notch_end:g} S {x:g},{y:g} {x:g},{y:g}"
                ).format(
                    x=end_x,
                    y=end_y,
                    origin_h=origin_y,
                    half_piece_h=origin_y + (piece_height * 0.5),
                    w_curve_1=origin_x + (piece_width * curve_multiplier_1),
                    w_curve_2=origin_x + (piece_width * curve_multiplier_2),
                    to_notch_start=origin_y + to_y_notch,
                    to_notch_end=origin_y + to_y_notch + y_notch,
                    control_point=origin_y
                    + (piece_height * 0.5)
                    + ((to_y_notch + y_notch) - (piece_height * 0.5)) * 2,
                )

                # Create an inverted version for replicating the Left side of the adjacent piece
                r_inverted = (
                    "C {x:g},{y:g} {w_curve_1:g},{half_piece_h:g} {x:g},{to_notch_start:g} "
                    "S {w_curve_2:g},{control_point:g} {x:g},{to_notch_end:g} S {x:g},{origin_h:g} {x:g},{origin_h:g}"
                ).format(
                    x=end_x,
                    y=end_y,
                    origin_h=origin_y,
                    half_piece_h=origin_y + (piece_height * 0.5),
                    w_curve_1=origin_x + (piece_width * curve_multiplier_1),
                    w_curve_2=origin_x + (piece_width * curve_multiplier_2),
                    to_notch_start=origin_y + to_y_notch + y_notch,
                    to_notch_end=origin_y + to_y_notch,
                    control_point=origin_y
                    + (piece_height * 0.5)
                    - ((to_y_notch + y_notch) - (piece_height * 0.5)) * 2,
                )
                all_commands["{}-{}-l".format(row, col + 1)] = r_inverted
            else:
                # Edge piece
                r = "L {},{}".format(end_x, end_y)

            commands.append(r)

            # Bottom section
            if row < self.pieces_height:
                # Generate curve
                b = "C {x:g},{y:g} {half_piece_w:g},{w_curve_1:g} {to_notch_start:g},{y:g} S {control_point:g},{w_curve_2:g} {to_notch_end:g},{y:g} S {origin_w:g},{y:g} {origin_w:g},{y:g}".format(
                    x=end_x,
                    y=end_y,
                    origin_w=origin_x,
                    half_piece_w=origin_x + (piece_width * 0.5),
                    w_curve_1=origin_y + (piece_height * curve_multiplier_1),
                    w_curve_2=origin_y + (piece_height * curve_multiplier_2),
                    to_notch_start=origin_x + to_x_notch + x_notch,
                    to_notch_end=origin_x + to_x_notch,
                    control_point=origin_x
                    + (piece_width * 0.5)
                    - ((to_x_notch + x_notch) - (piece_width * 0.5)) * 2,
                )

                # Create an inverted version for replicating the Left side of the adjacent piece
                b_inverted = "C {origin_w:g},{y:g} {half_piece_w:g},{w_curve_1:g} {to_notch_start:g},{y:g} S {control_point:g},{w_curve_2:g} {to_notch_end:g},{y:g} S {x:g},{y:g} {x:g},{y:g}".format(
                    x=end_x,
                    y=end_y,
                    origin_w=origin_x,
                    half_piece_w=origin_x + (piece_width * 0.5),
                    w_curve_1=origin_y + (piece_height * curve_multiplier_1),
                    w_curve_2=origin_y + (piece_height * curve_multiplier_2),
                    to_notch_start=origin_x + to_x_notch,
                    to_notch_end=origin_x + to_x_notch + x_notch,
                    control_point=origin_x
                    + (piece_width * 0.5)
                    + ((to_x_notch + x_notch) - (piece_width * 0.5)) * 2,
                )
                all_commands["{}-{}-t".format(row + 1, col)] = b_inverted
            else:
                # Edge piece
                b = "L {},{}".format(origin_x, end_y)

            commands.append(b)

            if col > 1:
                left_command = all_commands["{}-{}-l".format(row, col)]
                commands.append(left_command)

            # Close path (including straight line if Left edge piece)
            commands.append("z")

            # Construct path element
            d = "\n\t".join(commands)
            path = '<path stroke="{}" fill="{}" d="{}" />'.format(
                self.stroke_color, self.fill_color, d
            )
            paths.append(path)

        paths = "\n\t".join(paths)
        self.svg_template = """\
    <svg width="{}" height="{}">
        {}
    </svg>
        """.format(self.abs_width, self.abs_height, paths)

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
            with open(os.path.join(outdirectory, "{}.svg".format(p)), "w") as file:
                file.write(svg)

        logger.info(
            "Svg puzzle set generated: %s (%d Pieces) Directory: %s",
            self.image,
            len(paths),
            outdirectory,
        )
