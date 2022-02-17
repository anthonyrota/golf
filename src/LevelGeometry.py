from random import random
import math
import pyglet
from pyglet import gl
from pyglet.math import Vec2
from shapely.geometry import (
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    LinearRing,
)
from pyshaders import from_string
from Rectangle import Rectangle
from Tessellator import Tessellator
from IndexedVertices import IndexedVertices


single_color_shader = from_string(
    [
        """attribute vec2 a_vertex_position;
uniform mat4 u_view_matrix;

void main() {
    gl_Position = u_view_matrix * vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform vec3 u_color;

void main() {
    gl_FragColor = vec4(u_color, 1.0);
}"""
    ],
)


stripe_shader = from_string(
    [
        """attribute vec2 a_vertex_position;
uniform mat4 u_view_matrix;
varying vec2 v_vertex_position;

void main() {
    v_vertex_position = a_vertex_position;
    gl_Position = u_view_matrix * vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform vec3 u_line;
uniform vec3 u_background_color;
uniform vec3 u_stripe_color;
uniform float u_background_width;
uniform float u_stripe_width;
varying vec2 v_vertex_position;

void main() {
    float signed_distance_to_line = u_line.x * v_vertex_position.x + u_line.y * v_vertex_position.y + u_line.z;
    if (mod(signed_distance_to_line, u_background_width + u_stripe_width) < u_stripe_width) {
        gl_FragColor = vec4(u_stripe_color, 1.0);
    } else {
        gl_FragColor = vec4(u_background_color, 1.0);
    }
}"""
    ],
)


class PlatformBuffer:
    def __init__(self, distance):
        self.distance = distance


class ColoredPlatformBuffer(PlatformBuffer):
    def __init__(self, distance, color):
        super().__init__(distance)
        self.color = color


def normalize_color(color):
    return (color[0] / 255, color[1] / 255, color[2] / 255)


class Geometry:
    def __init__(
        self,
        contours,
        exterior_contour,
        start_flat,
        flag_flat,
        flag_ground_background_color,
        flag_ground_stripe_color,
        flag_ground_background_width,
        flag_ground_stripe_width,
        flag_ground_stripe_angle,
        platform_buffers,
        pseudo_3d_ground_height,
        pseudo_3d_ground_color,
        unbuffed_platform_color,
        ball_image,
    ):
        self._is_closed_in = exterior_contour is not None
        self._flag_ground_background_color = flag_ground_background_color
        self._flag_ground_stripe_color = flag_ground_stripe_color
        self._flag_ground_background_width = flag_ground_background_width
        self._flag_ground_stripe_width = flag_ground_stripe_width
        self._flag_ground_stripe_angle = flag_ground_stripe_angle
        self._pseudo_3d_ground_color = pseudo_3d_ground_color
        self._unbuffed_platform_color = unbuffed_platform_color
        self.exterior_rect = None
        self._pseudo_3d_ground_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices = None
        self._buffed_platform_indexed_vertices = None
        self._start_flat_indexed_vertices = None
        self._flag_flat_indexed_vertices = None
        self._dynamic_wall_indexed_vertices = None
        self._ball_image = ball_image
        self._ball_sprite = pyglet.sprite.Sprite(img=ball_image)
        self.raw_point_shift = None
        self._make_static_geometry(
            contours=contours,
            exterior_contour=exterior_contour,
            pseudo_3d_ground_height=pseudo_3d_ground_height,
            start_flat=start_flat,
            flag_flat=flag_flat,
            platform_buffers=platform_buffers,
        )

    @property
    def frame(self):
        return self.exterior_rect

    def _make_static_geometry(
        self,
        contours,
        exterior_contour,
        pseudo_3d_ground_height,
        start_flat,
        flag_flat,
        platform_buffers,
    ):

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

        self.raw_point_shift = Vec2(
            bounds_buff - exterior_bottom_left[0], bounds_buff - exterior_bottom_left[1]
        )

        def adjust_point(point):
            return (
                point[0] + self.raw_point_shift[0],
                point[1] + self.raw_point_shift[1],
            )

        def adjust_point_and_randomize(point):
            # shapely throws an error and I don't know why, but adding a
            # small random number fixes it.
            return (
                point[0] + self.raw_point_shift[0] + random() / 100,
                point[1] + self.raw_point_shift[1] + random() / 100,
            )

        contours = [
            [adjust_point_and_randomize(c) for c in contour]
            for contour in (
                [exterior_contour] + contours if exterior_contour else contours
            )
        ]

        buffs = [contours]
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

        self.exterior_rect = Rectangle(
            Vec2(),
            exterior_top_right[0] - exterior_bottom_left[0] + 2 * bounds_buff,
            exterior_top_right[1]
            - exterior_bottom_left[1]
            + 2 * bounds_buff
            + (0 if exterior_contour else pseudo_3d_ground_height),
        )

        ground_vertices = []
        ground_indices = []
        for i, contour in enumerate(buffs[0]):
            is_prev_ground = False
            for j, c1 in enumerate(contour):
                c2 = contour[(j + 1) % len(contour)]
                l = c1[0] - c2[0] if exterior_contour and i == 0 else c2[0] - c1[0]
                if l >= 0:
                    is_prev_ground = False
                    continue
                c1h = (c1[0], c1[1] + pseudo_3d_ground_height)
                c2h = (c2[0], c2[1] + pseudo_3d_ground_height)
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

        self._pseudo_3d_ground_indexed_vertices = (
            IndexedVertices.from_vertices_and_indices(ground_vertices, ground_indices)
        )

        self._unbuffed_platform_indexed_vertices = (
            tess.make_indexed_vertices_from_contours(
                [
                    [
                        (self.exterior_rect.pos.x, self.exterior_rect.pos.y),
                        (self.exterior_rect.width, self.exterior_rect.pos.y),
                        (self.exterior_rect.width, self.exterior_rect.height),
                        (self.exterior_rect.pos.x, self.exterior_rect.height),
                    ]
                ]
                + buffs[-1]
                if exterior_contour
                else buffs[-1],
            )
        )
        self._buffed_platform_indexed_vertices = [
            (
                buff,
                tess.make_indexed_vertices_from_contours(buffs[i] + buffs[i + 1]),
            )
            for i, buff in enumerate(platform_buffers)
        ]

        def make_rounded_rectangle_indexed_vertices(rect):
            r = min(rect.width, rect.height) / 4
            shape = (
                Polygon(
                    [
                        (rect.pos[0], rect.pos[1]),
                        (rect.pos[0] + rect.width, rect.pos[1]),
                        (rect.pos[0] + rect.width, rect.pos[1] + rect.height),
                        (rect.pos[0], rect.pos[1] + rect.height),
                    ]
                )
                .buffer(r)
                .buffer(-2 * r)
                .buffer(r)
            )
            assert isinstance(shape, Polygon)
            return tess.make_indexed_vertices_from_contours(
                # pylint: disable-next=no-member
                [list(shape.exterior.coords)]
            )

        start_flat_pos = adjust_point(start_flat.pos)
        self._start_flat_indexed_vertices = make_rounded_rectangle_indexed_vertices(
            Rectangle(
                Vec2(start_flat_pos[0], start_flat_pos[1]),
                start_flat.width,
                pseudo_3d_ground_height,
            ),
        )
        flag_flat_pos = adjust_point(flag_flat.pos)
        self._flag_flat_indexed_vertices = make_rounded_rectangle_indexed_vertices(
            Rectangle(
                Vec2(flag_flat_pos[0], flag_flat_pos[1]),
                flag_flat.width,
                pseudo_3d_ground_height,
            ),
        )

        if self._is_closed_in:
            self._dynamic_wall_indexed_vertices = (
                IndexedVertices.from_vertices_and_indices(
                    [0] * 32, [8] * 24, is_dynamic=True  # Max 4 rectangles
                )
            )

        tess.dispose()

    def render(self, camera, physics):
        if self._is_closed_in:
            rectangles = list(camera.get_view_rect().subtract(self.exterior_rect))
            num_wall_rectangles = len(rectangles)
            if num_wall_rectangles > 0:
                new_vertices = []
                new_indices = []
                for i, rectangle in enumerate(rectangles):
                    new_vertices.append(rectangle.pos.x)
                    new_vertices.append(rectangle.pos.y)
                    new_vertices.append(rectangle.pos.x + rectangle.width)
                    new_vertices.append(rectangle.pos.y)
                    new_vertices.append(rectangle.pos.x + rectangle.width)
                    new_vertices.append(rectangle.pos.y + rectangle.height)
                    new_vertices.append(rectangle.pos.x)
                    new_vertices.append(rectangle.pos.y + rectangle.height)
                    new_indices.append(i * 4)
                    new_indices.append(i * 4 + 1)
                    new_indices.append(i * 4 + 2)
                    new_indices.append(i * 4)
                    new_indices.append(i * 4 + 2)
                    new_indices.append(i * 4 + 3)
                self._dynamic_wall_indexed_vertices.update_part_of_vertex_buffer(
                    new_vertices, 0
                )
                self._dynamic_wall_indexed_vertices.update_part_of_index_buffer(
                    new_indices, 0
                )

        camera_matrix = camera.get_matrix()
        view_matrix = [camera_matrix.column(i) for i in range(4)]

        single_color_shader.use()
        # pylint: disable=assigning-non-slot
        single_color_shader.uniforms.u_color = normalize_color(
            self._pseudo_3d_ground_color
        )
        single_color_shader.uniforms.u_view_matrix = view_matrix
        self._pseudo_3d_ground_indexed_vertices.render(
            single_color_shader.attributes.a_vertex_position
        )
        single_color_shader.clear()

        stripe_shader.use()
        # pylint: disable=assigning-non-slot
        stripe_shader.uniforms.u_view_matrix = view_matrix
        stripe_shader.uniforms.u_line = (
            math.sin(self._flag_ground_stripe_angle),
            -math.cos(self._flag_ground_stripe_angle),
            0,
        )
        stripe_shader.uniforms.u_background_color = normalize_color(
            self._flag_ground_background_color
        )
        stripe_shader.uniforms.u_stripe_color = normalize_color(
            self._flag_ground_stripe_color
        )
        stripe_shader.uniforms.u_background_width = self._flag_ground_background_width
        stripe_shader.uniforms.u_stripe_width = self._flag_ground_stripe_width
        # pylint: enable=assigning-non-slot
        self._start_flat_indexed_vertices.render(
            stripe_shader.attributes.a_vertex_position
        )
        self._flag_flat_indexed_vertices.render(
            stripe_shader.attributes.a_vertex_position
        )
        stripe_shader.clear()

        single_color_shader.use()
        # pylint: disable=assigning-non-slot
        single_color_shader.uniforms.u_color = normalize_color(
            self._unbuffed_platform_color
        )
        # pylint: enable=assigning-non-slot
        self._unbuffed_platform_indexed_vertices.render(
            single_color_shader.attributes.a_vertex_position
        )
        if self._is_closed_in and num_wall_rectangles > 0:
            self._dynamic_wall_indexed_vertices.render(
                single_color_shader.attributes.a_vertex_position,
                num_triangles=num_wall_rectangles * 2,
            )
        for buff, indexed_vertices in self._buffed_platform_indexed_vertices:
            assert isinstance(buff, ColoredPlatformBuffer)
            # pylint: disable-next=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(buff.color)
            indexed_vertices.render(single_color_shader.attributes.a_vertex_position)
        single_color_shader.clear()

        gl.glPushMatrix()
        camera.update_opengl_matrix()
        self._ball_sprite.position = physics.ball_position - Vec2(
            physics.ball_radius, physics.ball_radius
        )
        self._ball_sprite.scale_x = 2 * physics.ball_radius / self._ball_image.width
        self._ball_sprite.scale_y = 2 * physics.ball_radius / self._ball_image.height
        self._ball_sprite.draw()
        gl.glPopMatrix()

    def dispose(self):
        self._pseudo_3d_ground_indexed_vertices.dispose()
        self._pseudo_3d_ground_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices.dispose()
        self._unbuffed_platform_indexed_vertices = None
        for (_, indexed_vertices) in self._buffed_platform_indexed_vertices:
            indexed_vertices.dispose()
        self._buffed_platform_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices.dispose()
        self._unbuffed_platform_indexed_vertices = None
        self._start_flat_indexed_vertices.dispose()
        self._start_flat_indexed_vertices = None
        self._flag_flat_indexed_vertices.dispose()
        self._flag_flat_indexed_vertices = None
