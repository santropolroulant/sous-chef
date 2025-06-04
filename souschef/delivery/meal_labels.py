import collections
from dataclasses import dataclass
from typing import Any, Union

from reportlab.graphics import shapes as rl_shapes
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics as rl_pdfmetrics

HORIZ_MARGIN = 9  # distance from edge of label 9/72 = 1/8 inch
NAME_LINE_VERTIC_POS = 11


meal_label_fields = [  # Contents for Meal Labels.
    # field name, default value
    "sortkey",
    "",  # key for sorting
    "route",
    "",  # String : Route name
    "name",
    "",  # String : Last + First abbreviated
    "date",
    "",  # String : Delivery date
    "size",
    "",  # String : Regular or Large
    "main_dish_name",
    "",  # String
    "dish_clashes",
    [],  # List of strings
    "preparations",
    [],  # List of strings
    "sides_clashes",
    [],  # List of strings
    "other_restrictions",
    [],  # List of strings
    "sides",
    [],  # List of strings
    "ingredients",
    [],  # List of strings
]
MealLabel = collections.namedtuple("MealLabel", meal_label_fields[0::2])


@dataclass
class LabelPainter:
    # dimensions are in font points (72 points = 1 inch)
    label: Any
    width: Union[int, float]
    height: Union[int, float]
    vertic_post: int = 0

    def __post_init__(self):
        self.vertic_pos = self.height * 0.85

    def _draw_dish_line(self, data: MealLabel):
        if data.main_dish_name:
            self.label.add(
                rl_shapes.String(
                    HORIZ_MARGIN,
                    self.vertic_pos,
                    data.main_dish_name,
                    fontName="Helvetica-Bold",
                    fontSize=10,
                )
            )
        if data.size:
            self.label.add(
                rl_shapes.String(
                    self.width - HORIZ_MARGIN,
                    self.vertic_pos,
                    data.size,
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textAnchor="end",
                )
            )
        if data.main_dish_name or data.size:
            self.vertic_pos -= 14

    def _draw_sides(self, data: MealLabel):
        if data.sides:
            for line in data.sides:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica",
                        fontSize=9,
                    )
                )
                self.vertic_pos -= 10

    def _draw_side_clashes(self, data: MealLabel):
        if data.sides_clashes:
            # draw prefix
            self.label.add(
                rl_shapes.String(
                    HORIZ_MARGIN,
                    self.vertic_pos,
                    data.sides_clashes[0],
                    fontName="Helvetica",
                    fontSize=9,
                )
            )
            # measure prefix length to offset first line
            offset = rl_pdfmetrics.stringWidth(
                data.sides_clashes[0], fontName="Helvetica", fontSize=9
            )
            for line in data.sides_clashes[1:]:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN + offset,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica-Bold",
                        fontSize=9,
                    )
                )
                offset = 0.0  # Only first line is offset at right of prefix
                self.vertic_pos -= 10

    def _draw_preparations(self, data: MealLabel):
        if data.preparations:
            # draw prefix
            self.label.add(
                rl_shapes.String(
                    HORIZ_MARGIN,
                    self.vertic_pos,
                    data.preparations[0],
                    fontName="Helvetica",
                    fontSize=9,
                )
            )
            # measure prefix length to offset first line
            offset = rl_pdfmetrics.stringWidth(
                data.preparations[0], fontName="Helvetica", fontSize=9
            )
            for line in data.preparations[1:]:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN + offset,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica-Bold",
                        fontSize=9,
                    )
                )
                offset = 0.0  # Only first line is offset at right of prefix
                self.vertic_pos -= 10

    def _draw_dish_clashes(self, data: MealLabel):
        if data.dish_clashes:
            for line in data.dish_clashes:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica",
                        fontSize=9,
                    )
                )
                self.vertic_pos -= 10

    def _draw_other_restrictions(self, data: MealLabel):
        if data.other_restrictions:
            for line in data.other_restrictions:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica",
                        fontSize=9,
                    )
                )
                self.vertic_pos -= 10

    def _draw_ingredients(self, data: MealLabel):
        if data.ingredients:
            for line in data.ingredients:
                self.label.add(
                    rl_shapes.String(
                        HORIZ_MARGIN,
                        self.vertic_pos,
                        line,
                        fontName="Helvetica",
                        fontSize=8,
                    )
                )
                self.vertic_pos -= 9

    def _draw_name_line(self, data: MealLabel):
        # Name is drawn at the bottom of the label
        self.label.add(
            rl_shapes.Rect(
                0,
                NAME_LINE_VERTIC_POS - 13,
                self.width,
                NAME_LINE_VERTIC_POS + 15,
                fillColor=colors.white,
                strokeColor=None,
            )
        )
        if data.name:
            self.label.add(
                rl_shapes.String(
                    HORIZ_MARGIN,
                    NAME_LINE_VERTIC_POS,
                    data.name,
                    fontName="Helvetica-Bold",
                    fontSize=12,
                )
            )

        if data.route:
            self.label.add(
                rl_shapes.String(
                    self.width / 2.0,
                    NAME_LINE_VERTIC_POS,
                    data.route,
                    fontName="Helvetica-Oblique",
                    fontSize=10,
                    textAnchor="middle",
                )
            )

        if data.date:
            self.label.add(
                rl_shapes.String(
                    self.width - HORIZ_MARGIN,
                    NAME_LINE_VERTIC_POS,
                    data.date,
                    fontName="Helvetica",
                    fontSize=10,
                    textAnchor="end",
                )
            )

    def draw(self, data: MealLabel):
        self.vertic_pos -= 14
        self._draw_dish_line(data)
        self._draw_sides(data)
        self._draw_side_clashes(data)
        self._draw_preparations(data)
        self._draw_dish_clashes(data)
        self._draw_other_restrictions(data)
        self._draw_ingredients(data)
        self._draw_name_line(data)


def draw_label(label, width: float, height: float, data: MealLabel):
    """Draw a single Meal Label on the sheet.

    Callback function that is used by the labels generator.

    Args:
        label: Object passed by pylabels.
        width: Single label width in font points.
        height: Single label height in font points.
        data: A MealLabel namedtuple.
    """
    painter = LabelPainter(label=label, width=width, height=height)
    painter.draw(data)
