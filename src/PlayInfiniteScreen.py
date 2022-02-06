from random import random
from itertools import chain
import ctypes
from pyglet import gl
from shapely.geometry import (
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    LinearRing,
)
from GameScreen import GameScreen
from cave_gen import make_cave

glBeginFuncType = ctypes.CFUNCTYPE(None, gl.GLenum)
glEndFuncType = ctypes.CFUNCTYPE(None)
glVertex2dvFuncType = ctypes.CFUNCTYPE(None, ctypes.POINTER(gl.GLdouble))
glTessErrorFuncType = ctypes.CFUNCTYPE(None, gl.GLenum)


class IndexedVertices:
    def __init__(self, vertex_buffer, index_buffer, num_indices):
        self.vertex_buffer = vertex_buffer
        self.index_buffer = index_buffer
        self.num_indices = num_indices


def make_indexed_vertices(vertices, indices):
    num_indices = len(indices)
    vertex_data = (gl.GLdouble * len(vertices))(*vertices)
    index_data = (gl.GLuint * num_indices)(*indices)

    vertex_buffer = gl.GLuint()
    gl.glGenBuffers(1, ctypes.pointer(vertex_buffer))
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
    gl.glBufferData(
        gl.GL_ARRAY_BUFFER, ctypes.sizeof(vertex_data), vertex_data, gl.GL_STATIC_DRAW
    )

    index_buffer = gl.GLuint()
    gl.glGenBuffers(1, ctypes.pointer(index_buffer))
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
    gl.glBufferData(
        gl.GL_ELEMENT_ARRAY_BUFFER,
        ctypes.sizeof(index_data),
        index_data,
        gl.GL_STATIC_DRAW,
    )

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

    return IndexedVertices(vertex_buffer, index_buffer, num_indices)


class Tessellator:
    def __init__(self):
        self._tess = gl.gluNewTess()
        self._mode = None
        self._mode_vertices = None
        self._vertices = None
        self._indices = None

        self._tess_begin_cb = ctypes.cast(
            glBeginFuncType(self._on_tess_begin), ctypes.CFUNCTYPE(None)
        )
        self._tess_vertex_cb = ctypes.cast(
            glVertex2dvFuncType(self._on_tess_vertex), ctypes.CFUNCTYPE(None)
        )
        self._tess_end_cb = ctypes.cast(
            glEndFuncType(self._on_tess_end), ctypes.CFUNCTYPE(None)
        )
        self._tess_error_cb = ctypes.cast(
            glTessErrorFuncType(self._on_tess_error), ctypes.CFUNCTYPE(None)
        )

        gl.gluTessProperty(
            self._tess, gl.GLU_TESS_WINDING_RULE, gl.GLU_TESS_WINDING_ODD
        )
        gl.gluTessCallback(
            self._tess,
            gl.GLU_TESS_VERTEX,
            self._tess_vertex_cb,
        )
        gl.gluTessCallback(
            self._tess,
            gl.GLU_TESS_BEGIN,
            self._tess_begin_cb,
        )
        gl.gluTessCallback(self._tess, gl.GLU_TESS_END, self._tess_end_cb)
        gl.gluTessCallback(
            self._tess,
            gl.GLU_TESS_ERROR,
            self._tess_error_cb,
        )

    def make_indexed_vertices_from_contours(self, contours):
        self._vertices = []
        self._indices = []
        data = [(gl.GLdouble * 3 * len(contour))(*contour) for contour in contours]

        gl.gluTessBeginPolygon(self._tess, None)
        for contour in data:
            gl.gluTessBeginContour(self._tess)
            for vertex in contour:
                gl.gluTessVertex(self._tess, vertex, vertex)
            gl.gluTessEndContour(self._tess)
        gl.gluTessEndPolygon(self._tess)

        indexed_vertices = make_indexed_vertices(self._vertices, self._indices)
        self._vertices = None
        self._indices = None
        return indexed_vertices

    def dispose(self):
        gl.gluDeleteTess(self._tess)
        self._tess = None
        self._tess_begin_cb = None
        self._tess_vertex_cb = None
        self._tess_end_cb = None
        self._tess_error_cb = None

    def _on_tess_begin(self, mode):
        self._mode = mode
        self._mode_vertices = []

    def _on_tess_vertex(self, vertex):
        self._mode_vertices.append((vertex[0], vertex[1]))

    def _on_tess_end(self):
        num_vertices = len(self._mode_vertices)
        first_index = len(self._vertices) // 2
        for vertex in self._mode_vertices:
            self._vertices.append(vertex[0])
            self._vertices.append(vertex[1])
        if self._mode == gl.GL_TRIANGLES:
            for i in range(num_vertices):
                self._indices.append(first_index + i)
        elif self._mode == gl.GL_TRIANGLE_FAN:
            for i in range(num_vertices - 2):
                self._indices.append(first_index)
                self._indices.append(first_index + i + 1)
                self._indices.append(first_index + i + 2)
        elif self._mode == gl.GL_TRIANGLE_STRIP:
            for i in range(num_vertices - 2):
                self._indices.append(first_index + i)
                if i & 1:
                    self._indices.append(first_index + i + 1)
                    self._indices.append(first_index + i + 2)
                else:
                    self._indices.append(first_index + i + 2)
                    self._indices.append(first_index + i + 1)
        else:
            raise Exception("Unexpected tessellation mode", self._mode)

        self._mode = None
        self._mode_vertices = None

    def _on_tess_error(self, error_code):
        print(
            "Tessellation Error",
            ctypes.cast(gl.gluErrorString(error_code), ctypes.c_char_p).value,
        )


class PlayInfiniteScreen(GameScreen):
    def __init__(self):
        self._game = None
        self._colors = [
            (79, 251, 22),
            (72, 137, 62),
            (86, 77, 64),
            (66, 61, 54),
        ]
        self._indexed_vertices = None

    def bind(self, game):
        self._game = game

        N = [2, 5]
        bounds_buff = max(N) + 1

        tess = Tessellator()

        contours = make_cave(60, 60)

        scale = 10  # temp
        contours = [
            [(c[0] * scale, c[1] * scale) for c in contour] for contour in contours
        ]  # temp
        N = [r * scale for r in N]  # temp
        bounds_buff = (bounds_buff - 1) * scale + 1  # temp

        # pylint: disable-next=no-member
        exterior = list(Polygon(contours[0]).envelope.exterior.coords)[:-1]

        contours = [
            [
                (
                    # shapely throws an error and I don't know why, but adding a
                    # small random number fixes it.
                    c[0] - exterior[0][0] + bounds_buff + random() / 100,
                    c[1] - exterior[0][1] + bounds_buff + random() / 100,
                )
                for c in contour
            ]
            for contour in contours
        ]

        buffs = [[]]
        for contour in contours:  # TODO: find a better way to do this
            shape = (
                Polygon(contour)
                .buffer(1 * scale)  # temp
                .buffer(-2 * scale)  # temp
                .buffer(1 * scale)  # temp
            )
            assert isinstance(shape, Polygon)
            # pylint: disable-next=no-member
            buffs[0].append(shape.exterior.coords)
        for r in N:
            buff_contours = []
            shape = LinearRing(reversed(contours[0])).parallel_offset(r, side="left")
            if isinstance(shape, LineString):
                buff_contours.append(shape.coords)
            else:
                assert isinstance(shape, MultiLineString)
                # pylint: disable-next=no-member
                for line in shape.geoms:
                    buff_contours.append(line.coords)
            for i, contour in enumerate(contours[1:]):
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

        buff_tess_contours = [
            [
                [
                    (0, 0),
                    (
                        exterior[1][0] - exterior[0][0] + 2 * bounds_buff,
                        exterior[1][1] - exterior[0][1],
                    ),
                    (
                        exterior[2][0] - exterior[0][0] + 2 * bounds_buff,
                        exterior[2][1] - exterior[0][1] + 2 * bounds_buff,
                    ),
                    (
                        exterior[3][0] - exterior[0][0],
                        exterior[3][1] - exterior[0][1] + 2 * bounds_buff,
                    ),
                ]
            ]
            + buffs[-1]
        ] + [buffs[i] + buffs[i + 1] for i in range(len(N))]

        ground_vertices = []
        ground_indices = []
        s = 1 * scale  # temp
        for i, contour in enumerate(buffs[0]):
            is_prev_ground = False
            for j, c1 in enumerate(contour):
                c2 = contour[(j + 1) % len(contour)]
                l = c1[0] - c2[0] if i == 0 else c2[0] - c1[0]
                if l <= 0:
                    is_prev_ground = False
                    continue
                c1h = (c1[0], c1[1] + s)
                c2h = (c2[0], c2[1] + s)
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
                if i == 0:
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

        self._indexed_vertices = [
            make_indexed_vertices(ground_vertices, ground_indices)
        ] + [
            tess.make_indexed_vertices_from_contours(contours)
            for contours in buff_tess_contours
        ]

        tess.dispose()

    def render(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glLoadIdentity()

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        for (r, g, b), buffs in zip(
            chain([self._colors[0], self._colors[-1]], self._colors[1:-1]),
            self._indexed_vertices,
        ):
            gl.glColor3d(r / 255, g / 255, b / 255)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, buffs.vertex_buffer)
            gl.glVertexPointer(2, gl.GL_DOUBLE, 0, 0)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, buffs.index_buffer)
            gl.glDrawElements(gl.GL_TRIANGLES, buffs.num_indices, gl.GL_UNSIGNED_INT, 0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)

    def update(self, dt):
        pass

    def unbind(self):
        self._game = None
        for buffs in self._indexed_vertices:
            gl.glDeleteBuffers(1, ctypes.pointer(buffs.vertex_buffer))
            gl.glDeleteBuffers(1, ctypes.pointer(buffs.index_buffer))
        self._indexed_vertices = None
