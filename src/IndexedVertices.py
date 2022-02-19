import ctypes
from pyglet import gl


class IndexedVertices:
    def __init__(self, vertices, indices, is_dynamic=False):
        self._num_indices = len(indices)
        self._vertex_buffer = Buffer(vertices, 2, "float", is_dynamic=is_dynamic)
        self._index_buffer = Buffer(
            indices, 1, "uint", is_element_buffer=True, is_dynamic=is_dynamic
        )

    def update_part_of_vertex_buffer(self, vertices, offset):
        self._vertex_buffer.update_part(vertices, offset)

    def update_part_of_index_buffer(self, indices, offset):
        self._index_buffer.update_part(indices, offset)

    def render(self, vertex_attrib, num_triangles=None):
        self._vertex_buffer.bind_to_attrib(vertex_attrib)
        self._index_buffer.bind()
        gl.glDrawElements(
            gl.GL_TRIANGLES,
            self._num_indices if num_triangles is None else num_triangles * 3,
            gl.GL_UNSIGNED_INT,
            0,
        )

    def dispose(self):
        self._vertex_buffer.dispose()
        self._index_buffer.dispose()


class Buffer:
    def __init__(
        self, values, value_len, data_type, is_element_buffer=False, is_dynamic=False
    ):
        if data_type == "float":
            self._data_type = gl.GLfloat
            self._gl_type = gl.GL_FLOAT
        elif data_type == "uint":
            self._data_type = gl.GLuint
            self._gl_type = gl.GL_UNSIGNED_INT
        self._value_len = value_len
        data = (self._data_type * len(values))(*values)
        self._buffer = gl.GLuint()
        gl.glGenBuffers(1, ctypes.pointer(self._buffer))
        self._buffer_type = (
            gl.GL_ELEMENT_ARRAY_BUFFER if is_element_buffer else gl.GL_ARRAY_BUFFER
        )
        gl.glBindBuffer(self._buffer_type, self._buffer)
        gl.glBufferData(
            self._buffer_type,
            ctypes.sizeof(data),
            data,
            gl.GL_DYNAMIC_DRAW if is_dynamic else gl.GL_STATIC_DRAW,
        )
        gl.glBindBuffer(self._buffer_type, 0)

    def update_part(self, values, offset):
        data = (self._data_type * len(values))(*values)
        gl.glBindBuffer(self._buffer_type, self._buffer)
        gl.glBufferSubData(
            self._buffer_type, offset * self._value_len, ctypes.sizeof(data), data
        )

    def bind(self):
        gl.glBindBuffer(self._buffer_type, self._buffer)

    def bind_to_attrib(self, vertex_attrib):
        self.bind()
        vertex_attrib.point_to(0, self._gl_type, self._value_len, False, 0)
        vertex_attrib.enable()

    def dispose(self):
        gl.glDeleteBuffers(1, ctypes.pointer(self._buffer))
