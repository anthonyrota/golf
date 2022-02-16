import ctypes
from pyglet import gl
from IndexedVertices import IndexedVertices


glBeginFuncType = ctypes.CFUNCTYPE(None, gl.GLenum)
glEndFuncType = ctypes.CFUNCTYPE(None)
glVertex2dvFuncType = ctypes.CFUNCTYPE(None, ctypes.POINTER(gl.GLdouble))
glTessErrorFuncType = ctypes.CFUNCTYPE(None, gl.GLenum)


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

        indexed_vertices = IndexedVertices.from_vertices_and_indices(
            self._vertices, self._indices
        )
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
