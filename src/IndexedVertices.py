import ctypes
from pyglet import gl


class IndexedVertices:
    @classmethod
    def from_vertices_and_indices(cls, vertices, indices, is_dynamic=False):
        num_indices = len(indices)
        vertex_data = (gl.GLdouble * len(vertices))(*vertices)
        index_data = (gl.GLuint * num_indices)(*indices)

        vertex_buffer = gl.GLuint()
        gl.glGenBuffers(1, ctypes.pointer(vertex_buffer))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vertex_buffer)
        gl.glBufferData(
            gl.GL_ARRAY_BUFFER,
            ctypes.sizeof(vertex_data),
            vertex_data,
            gl.GL_STATIC_DRAW,
        )

        index_buffer = gl.GLuint()
        gl.glGenBuffers(1, ctypes.pointer(index_buffer))
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, index_buffer)
        gl.glBufferData(
            gl.GL_ELEMENT_ARRAY_BUFFER,
            ctypes.sizeof(index_data),
            index_data,
            gl.GL_DYNAMIC_DRAW if is_dynamic else gl.GL_STATIC_DRAW,
        )

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0)

        return cls(vertex_buffer, index_buffer, num_indices)

    def __init__(self, vertex_buffer, index_buffer, num_indices):
        self.vertex_buffer = vertex_buffer
        self.index_buffer = index_buffer
        self.num_indices = num_indices

    def update_part_of_vertex_buffer(self, vertices, offset):
        vertex_data = (gl.GLdouble * len(vertices))(*vertices)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferSubData(
            gl.GL_ARRAY_BUFFER, offset, ctypes.sizeof(vertex_data), vertex_data
        )

    def update_part_of_index_buffer(self, indices, offset):
        index_data = (gl.GLuint * len(indices))(*indices)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        gl.glBufferSubData(
            gl.GL_ELEMENT_ARRAY_BUFFER, offset, ctypes.sizeof(index_data), index_data
        )

    def render(self, vertex_attrib, num_triangles=None):
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        vertex_attrib.point_to(0, gl.GL_DOUBLE, 2, False, 0)
        vertex_attrib.enable()
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        gl.glDrawElements(
            gl.GL_TRIANGLES,
            self.num_indices if num_triangles is None else num_triangles * 3,
            gl.GL_UNSIGNED_INT,
            0,
        )

    def dispose(self):
        gl.glDeleteBuffers(1, ctypes.pointer(self.vertex_buffer))
        gl.glDeleteBuffers(1, ctypes.pointer(self.index_buffer))
