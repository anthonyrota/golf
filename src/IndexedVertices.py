import ctypes
from pyglet import gl


class IndexedVertices:
    def __init__(self, vertex_buffer, index_buffer, num_indices):
        self.vertex_buffer = vertex_buffer
        self.index_buffer = index_buffer
        self.num_indices = num_indices

    def render_in_single_color(self, color):
        r, g, b = color
        gl.glColor3d(r / 255, g / 255, b / 255)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glVertexPointer(2, gl.GL_DOUBLE, 0, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        gl.glDrawElements(gl.GL_TRIANGLES, self.num_indices, gl.GL_UNSIGNED_INT, 0)


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
