from random import random
import ctypes
from pyglet import gl
from pyglet.math import Vec2
from shapely.geometry import (
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    LinearRing,
)
from Rectangle import Rectangle
from Tessellator import Tessellator
from IndexedVertices import make_indexed_vertices


class PlatformBuffer:
    def __init__(self, distance):
        self.distance = distance


class ColoredPlatformBuffer(PlatformBuffer):
    def __init__(self, distance, color):
        super().__init__(distance)
        self.color = color


class LevelGeometry:
    def __init__(
        self,
        contours,
        exterior_contour,
        platform_buffers,
        pseudo_3d_ground_height,
        pseudo_3d_ground_color,
        unbuffed_platform_color,
    ):
        self._is_closed_in = exterior_contour is not None
        self._pseudo_3d_ground_height = pseudo_3d_ground_height
        self._pseudo_3d_ground_color = pseudo_3d_ground_color
        self._unbuffed_platform_color = unbuffed_platform_color
        self._exterior_rect = None
        self._pseudo_3d_ground_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices = None
        self._buffed_platform_indexed_vertices = None
        self._make_static_geometry(contours, exterior_contour, platform_buffers)

    @property
    def frame(self):
        return self._exterior_rect

    def _make_static_geometry(self, contours, exterior_contour, platform_buffers):
        bounds_buff = (
            max(buff.distance for buff in platform_buffers) + 1
            if exterior_contour
            else 1
        )
        tess = Tessellator()

        exterior = list(
            # pylint: disable-next=no-member
            (
                LineString(exterior_contour)
                if exterior_contour
                else MultiLineString(contours)
            ).envelope.exterior.coords
        )[:-1]
        exterior_bottom_left = (exterior[0][0], exterior[0][1])
        exterior_top_right = (exterior[2][0], exterior[2][1])

        contours = [
            [
                (
                    # shapely throws an error and I don't know why, but adding a
                    # small random number fixes it.
                    c[0] - exterior_bottom_left[0] + bounds_buff + random() / 100,
                    c[1] - exterior_bottom_left[1] + bounds_buff + random() / 100,
                )
                for c in contour
            ]
            for contour in (
                [exterior_contour] + contours if exterior_contour else contours
            )
        ]

        buffs = [[]]
        for contour in contours:  # TODO: find a better way to do this
            shape = Polygon(contour).buffer(1).buffer(-2).buffer(1)
            if isinstance(shape, Polygon):
                buffs[0].append(shape.exterior.coords)
            else:  # TODO: why?
                assert isinstance(shape, MultiPolygon)
                # pylint: disable-next=no-member
                for poly in shape.geoms:
                    assert isinstance(poly, Polygon)
                    buffs[0].append(poly.exterior.coords)
        for buff in platform_buffers:
            r = buff.distance
            buff_contours = []
            if exterior_contour:
                shape = LinearRing(reversed(contours[0])).parallel_offset(
                    r, side="left"
                )
                if isinstance(shape, LineString):
                    buff_contours.append(shape.coords)
                else:
                    assert isinstance(shape, MultiLineString)
                    # pylint: disable-next=no-member
                    for line in shape.geoms:
                        buff_contours.append(line.coords)
            for i, contour in enumerate(contours[1:] if exterior_contour else contours):
                shape = Polygon(contour).buffer(-r)
                if shape.is_empty:
                    continue
                if isinstance(shape, Polygon):
                    buff_contours.append(shape.exterior.coords)
                else:
                    assert isinstance(shape, MultiPolygon)
                    # pylint: disable-next=no-member
                    for poly in shape.geoms:
                        assert isinstance(poly, Polygon)
                        buff_contours.append(poly.exterior.coords)
            buffs.append(buff_contours)

        self._exterior_rect = Rectangle(
            Vec2(),
            exterior_top_right[0] - exterior_bottom_left[0] + 2 * bounds_buff,
            exterior_top_right[1]
            - exterior_bottom_left[1]
            + 2 * bounds_buff
            + (0 if exterior_contour else self._pseudo_3d_ground_height),
        )

        ground_vertices = []
        ground_indices = []
        for i, contour in enumerate(buffs[0]):
            is_prev_ground = False
            for j, c1 in enumerate(contour):
                c2 = contour[(j + 1) % len(contour)]
                l = c1[0] - c2[0] if exterior_contour and i == 0 else c2[0] - c1[0]
                if l <= 0:
                    is_prev_ground = False
                    continue
                c1h = (c1[0], c1[1] + self._pseudo_3d_ground_height)
                c2h = (c2[0], c2[1] + self._pseudo_3d_ground_height)
                if not is_prev_ground:
                    ground_vertices.append(c1[0])
                    ground_vertices.append(c1[1])
                    ground_vertices.append(c1h[0])
                    ground_vertices.append(c1h[1])
                num_vertices = len(ground_vertices) // 2
                ground_vertices.append(c2[0])
                ground_vertices.append(c2[1])
                ground_vertices.append(c2h[0])
                ground_vertices.append(c2h[1])
                if exterior_contour and i == 0:
                    a = num_vertices - 1
                    b = num_vertices - 2
                    c = num_vertices
                    d = num_vertices + 1
                else:
                    a = num_vertices - 2
                    b = num_vertices - 1
                    c = num_vertices + 1
                    d = num_vertices
                ground_indices.append(a)
                ground_indices.append(b)
                ground_indices.append(c)
                ground_indices.append(a)
                ground_indices.append(c)
                ground_indices.append(d)
                is_prev_ground = True

        self._pseudo_3d_ground_indexed_vertices = make_indexed_vertices(
            ground_vertices, ground_indices
        )
        self._unbuffed_platform_indexed_vertices = (
            tess.make_indexed_vertices_from_contours(
                [
                    [
                        (self._exterior_rect.pos.x, self._exterior_rect.pos.y),
                        (self._exterior_rect.width, self._exterior_rect.pos.y),
                        (self._exterior_rect.width, self._exterior_rect.height),
                        (self._exterior_rect.pos.x, self._exterior_rect.height),
                    ]
                ]
                + buffs[-1]
                if exterior_contour
                else buffs[-1]
            )
        )
        self._buffed_platform_indexed_vertices = [
            (buff, tess.make_indexed_vertices_from_contours(buffs[i] + buffs[i + 1]))
            for i, buff in enumerate(platform_buffers)
        ]

        tess.dispose()

    def render(self, camera):
        self._pseudo_3d_ground_indexed_vertices.render_in_single_color(
            self._pseudo_3d_ground_color
        )
        self._unbuffed_platform_indexed_vertices.render_in_single_color(
            self._unbuffed_platform_color
        )
        for buff, indexed_vertices in self._buffed_platform_indexed_vertices:
            assert isinstance(buff, ColoredPlatformBuffer)
            indexed_vertices.render_in_single_color(buff.color)
        if self._is_closed_in:
            for wall_rect in camera.get_view_rect().subtract(self._exterior_rect):
                r, g, b = self._unbuffed_platform_color
                gl.glColor3d(r / 255, g / 255, b / 255)
                gl.glRectd(
                    wall_rect.pos.x, wall_rect.pos.y, wall_rect.right, wall_rect.top
                )

    def dispose(self):
        gl.glDeleteBuffers(
            1, ctypes.pointer(self._pseudo_3d_ground_indexed_vertices.vertex_buffer)
        )
        gl.glDeleteBuffers(
            1, ctypes.pointer(self._pseudo_3d_ground_indexed_vertices.index_buffer)
        )
        self._pseudo_3d_ground_indexed_vertices = None
        gl.glDeleteBuffers(
            1, ctypes.pointer(self._unbuffed_platform_indexed_vertices.vertex_buffer)
        )
        gl.glDeleteBuffers(
            1, ctypes.pointer(self._unbuffed_platform_indexed_vertices.index_buffer)
        )
        self._unbuffed_platform_indexed_vertices = None
        for (_, indexed_vertices) in self._buffed_platform_indexed_vertices:
            gl.glDeleteBuffers(1, ctypes.pointer(indexed_vertices.vertex_buffer))
            gl.glDeleteBuffers(1, ctypes.pointer(indexed_vertices.index_buffer))
        self._buffed_platform_indexed_vertices = None
