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


class Framebuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.fbo = gl.GLuint()
        gl.glGenFramebuffers(1, ctypes.pointer(self.fbo))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)

        self.tex = gl.GLuint()
        gl.glGenTextures(1, ctypes.pointer(self.tex))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGB,
            width,
            height,
            0,
            gl.GL_RGB,
            gl.GL_UNSIGNED_BYTE,
            None,
        )
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.tex, 0
        )

        if gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) != gl.GL_FRAMEBUFFER_COMPLETE:
            raise Exception("Framebuffer binding failed")

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def resize(self, width, height):
        if self.width == width and self.height == height:
            return
        self.width = width
        self.height = height
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGB,
            width,
            height,
            0,
            gl.GL_RGB,
            gl.GL_UNSIGNED_BYTE,
            None,
        )
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def dispose(self):
        gl.glDeleteFramebuffers(1, ctypes.pointer(self.fbo))
        self.fbo = None
        gl.glDeleteTextures(1, ctypes.pointer(self.tex))
        self.tex = None


def normalize_color(color):
    return (color[0] / 255, color[1] / 255, color[2] / 255)


def clear_gl(color):
    c = normalize_color(color)
    gl.glClearColor(c[0], c[1], c[2], 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    gl.glLoadIdentity()
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)


# From pyglet source code: pyglet buffers textures to the nearest power of two
# for compatibility with older graphics cards.
def nearest_pow2(v):
    # From http://graphics.stanford.edu/~seander/bithacks.html#RoundUpPowerOf2
    # Credit: Sean Anderson
    v -= 1
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    return v + 1
