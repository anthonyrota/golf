from random import random
import math
from pyglet import gl
from pyglet.math import Vec2
from shapely.geometry import (
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    LinearRing,
)
import pyshaders
from Rectangle import Rectangle
from Tessellator import Tessellator
from IndexedVertices import Buffer, IndexedVertices
from Physics import add_sticky_to_stickies


BUFFER_RESOLUTION = 8
CIRCLE_POINTS = 64


single_color_shader = pyshaders.from_string(
    [
        """attribute vec2 a_vertex_position;
uniform mat4 u_view_matrix;

void main() {
    gl_Position = u_view_matrix * vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform vec3 u_color;
uniform float u_alpha;

void main() {
    gl_FragColor = vec4(u_color, u_alpha);
}"""
    ],
)


stripe_shader = pyshaders.from_string(
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
    float signed_distance_to_line = (
        u_line.x * v_vertex_position.x
        + u_line.y * v_vertex_position.y
        + u_line.z
    );
    if (mod(signed_distance_to_line, u_background_width + u_stripe_width) <= u_stripe_width) {
        gl_FragColor = vec4(u_stripe_color, 1.0);
    } else {
        gl_FragColor = vec4(u_background_color, 1.0);
    }
}"""
    ],
)


faded_dotted_line_shader = pyshaders.from_string(
    [
        """attribute vec2 a_vertex_position;
attribute float a_distance;
uniform mat4 u_view_matrix;
varying float v_distance;

void main() {
    v_distance = a_distance;
    gl_Position = u_view_matrix * vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform vec3 u_color;
uniform float u_space_size;
uniform float u_dotted_size;
uniform float u_line_length;
uniform float u_fade_factor;
varying float v_distance;

void main() {
    float fade_distance = max(1.0 - v_distance / u_line_length, 0.0);
    float fade_amount = 1.0 - exp2(-u_fade_factor * fade_distance * fade_distance);
    fade_amount = clamp(fade_amount, 0.0, 1.0);

    if (mod(v_distance, u_space_size + u_dotted_size) > u_dotted_size) {
        discard;
    }

    gl_FragColor = vec4(u_color, fade_amount);
}""",
    ],
)


faded_color_shader = pyshaders.from_string(
    [
        """attribute vec2 a_vertex_position;
attribute float a_distance;
uniform mat4 u_view_matrix;
varying float v_distance;

void main() {
    v_distance = a_distance;
    gl_Position = u_view_matrix * vec4(a_vertex_position, 0.0, 1.0);
}"""
    ],
    [
        """uniform vec3 u_color;
uniform float u_line_length;
uniform float u_fade_factor;
uniform float u_base_alpha;
varying float v_distance;

void main() {
    float fade_distance = max(1.0 - v_distance / u_line_length, 0.0);
    float fade_amount = 1.0 - exp2(-u_fade_factor * fade_distance * fade_distance);
    fade_amount = clamp(fade_amount, 0.0, 1.0);
    gl_FragColor = vec4(u_color, fade_amount * u_base_alpha);
}""",
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
        bg_color,
        pseudo_3d_ground_height,
        pseudo_3d_ground_color,
        unbuffed_platform_color,
        ball_color,
        ball_outline_color,
        ball_outline_size,
        sand_pits,
        sand_pits_color,
        sand_pits_pseudo_3d_ground_color,
        sticky_wall_buffer_distance,
        sticky_wall_outer_buffer_distance,
        sticky_wall_background_color,
        sticky_wall_stripe_color,
        sticky_wall_background_width,
        sticky_wall_stripe_width,
        sticky_wall_stripe_angle,
        preview_sticky_wall_background_color,
        preview_sticky_wall_stripe_color,
        preview_sticky_wall_background_width,
        preview_sticky_wall_stripe_width,
        preview_sticky_wall_stripe_angle,
        max_shot_preview_points,
        shot_preview_lerp_up,
        shot_preview_lerp_down,
        shot_preview_dotted_line_space_size,
        shot_preview_dotted_line_dotted_size,
        shot_preview_dotted_line_color,
        shot_preview_dotted_line_fade_factor,
        shot_preview_polygon_color,
        shot_preview_base_alpha,
        shot_drawback_ring_width,
        shot_drawback_outer_ring_color,
        shot_drawback_outer_ring_alpha,
        shot_drawback_inner_ring_color,
        shot_drawback_inner_ring_alpha,
        num_ball_trail_points,
        ball_trail_color,
        ball_trail_fade_factor,
        ball_trail_base_alpha,
    ):
        self._is_closed_in = exterior_contour is not None
        self._flag_ground_background_color = flag_ground_background_color
        self._flag_ground_stripe_color = flag_ground_stripe_color
        self._flag_ground_background_width = flag_ground_background_width
        self._flag_ground_stripe_width = flag_ground_stripe_width
        self._flag_ground_stripe_angle = flag_ground_stripe_angle
        self._bg_color = bg_color
        self._pseudo_3d_ground_color = pseudo_3d_ground_color
        self._unbuffed_platform_color = unbuffed_platform_color
        self._ball_color = ball_color
        self._ball_outline_color = ball_outline_color
        self._ball_outline_size = ball_outline_size
        self._sand_pits_color = sand_pits_color
        self._sand_pits_pseudo_3d_ground_color = sand_pits_pseudo_3d_ground_color
        self._sticky_wall_buffer_distance = sticky_wall_buffer_distance
        self._sticky_wall_outer_buffer_distance = sticky_wall_outer_buffer_distance
        self._sticky_wall_background_color = sticky_wall_background_color
        self._sticky_wall_stripe_color = sticky_wall_stripe_color
        self._sticky_wall_background_width = sticky_wall_background_width
        self._sticky_wall_stripe_width = sticky_wall_stripe_width
        self._sticky_wall_stripe_angle = sticky_wall_stripe_angle
        self._preview_sticky_wall_background_color = (
            preview_sticky_wall_background_color
        )
        self._preview_sticky_wall_stripe_color = preview_sticky_wall_stripe_color
        self._preview_sticky_wall_background_width = (
            preview_sticky_wall_background_width
        )
        self._preview_sticky_wall_stripe_width = preview_sticky_wall_stripe_width
        self._preview_sticky_wall_stripe_angle = preview_sticky_wall_stripe_angle
        self._shot_preview_dotted_line_space_size = shot_preview_dotted_line_space_size
        self._shot_preview_dotted_line_dotted_size = (
            shot_preview_dotted_line_dotted_size
        )
        self._shot_preview_lerp_up = shot_preview_lerp_up
        self._shot_preview_lerp_down = shot_preview_lerp_down
        self._shot_preview_dotted_line_color = shot_preview_dotted_line_color
        self._shot_preview_fade_factor = shot_preview_dotted_line_fade_factor
        self._shot_preview_polygon_color = shot_preview_polygon_color
        self._shot_preview_base_alpha = shot_preview_base_alpha
        self._shot_drawback_ring_width = shot_drawback_ring_width
        self._shot_drawback_outer_ring_color = shot_drawback_outer_ring_color
        self._shot_drawback_outer_ring_alpha = shot_drawback_outer_ring_alpha
        self._shot_drawback_inner_ring_color = shot_drawback_inner_ring_color
        self._shot_drawback_inner_ring_alpha = shot_drawback_inner_ring_alpha
        self._num_ball_trail_points = num_ball_trail_points
        self._ball_trail_color = ball_trail_color
        self._ball_trail_fade_factor = ball_trail_fade_factor
        self._ball_trail_base_alpha = ball_trail_base_alpha
        self.exterior_rect = None
        self._pseudo_3d_ground_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices = None
        self._buffed_platform_indexed_vertices = None
        self._sand_pits_indexed_vertices = None
        self._sand_pits_3d_ground_indexed_vertices = None
        self._stickies_indexed_vertices = []
        self._start_flat_indexed_vertices = None
        self._flag_flat_indexed_vertices = None
        self._dynamic_wall_indexed_vertices = None
        self._dynamic_shot_preview_dotted_line_vertex_buffers = None
        self._dynamic_shot_preview_dotted_line_distance_buffers = None
        self._dynamic_shot_preview_polygon_vertex_buffer = None
        self._dynamic_shot_preview_polygon_distance_buffer = None
        self._dynamic_drawback_circle_outer_ring_vertex_buffer = None
        self._dynamic_drawback_circle_inner_ring_vertex_buffer = None
        self._dynamic_ball_trail_polygon_vertex_buffer = None
        self._dynamic_ball_trail_polygon_distance_buffer = None
        self._dynamic_ball_outer_vertex_buffer = None
        self._dynamic_ball_inner_vertex_buffer = None
        self.raw_point_shift = None
        self._tess = None
        self._make_static_geometry(
            contours=contours,
            exterior_contour=exterior_contour,
            pseudo_3d_ground_height=pseudo_3d_ground_height,
            start_flat=start_flat,
            flag_flat=flag_flat,
            platform_buffers=platform_buffers,
            sand_pits=sand_pits,
            max_shot_preview_points=max_shot_preview_points,
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
        sand_pits,
        max_shot_preview_points,
    ):
        bounds_buff = (
            max(buff.distance for buff in platform_buffers) + 1
            if exterior_contour
            else 1
        )
        self._tess = Tessellator()

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
                    r, side="left", resolution=BUFFER_RESOLUTION
                )
                if isinstance(shape, LineString):
                    buff_contours.append(shape.coords)
                else:
                    assert isinstance(shape, MultiLineString)
                    # pylint: disable-next=no-member
                    for line in shape.geoms:
                        buff_contours.append(line.coords)
            for i, contour in enumerate(contours[1:] if exterior_contour else contours):
                shape = Polygon(contour).buffer(-r, BUFFER_RESOLUTION)
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

        def make_pseudo_3d_ground_for_contour(vertices, indices, contour, is_inside):
            is_prev_ground = False
            for i, c1 in enumerate(contour):
                c2 = contour[(i + 1) % len(contour)]
                l = c1[0] - c2[0] if exterior_contour and is_inside else c2[0] - c1[0]
                if l >= 0:
                    is_prev_ground = False
                    continue
                c1h = (c1[0], c1[1] + pseudo_3d_ground_height)
                c2h = (c2[0], c2[1] + pseudo_3d_ground_height)
                if not is_prev_ground:
                    vertices.append(c1[0])
                    vertices.append(c1[1])
                    vertices.append(c1h[0])
                    vertices.append(c1h[1])
                num_vertices = len(vertices) // 2
                vertices.append(c2[0])
                vertices.append(c2[1])
                vertices.append(c2h[0])
                vertices.append(c2h[1])
                if exterior_contour and is_inside:
                    a = num_vertices - 1
                    b = num_vertices - 2
                    c = num_vertices
                    d = num_vertices + 1
                else:
                    a = num_vertices - 2
                    b = num_vertices - 1
                    c = num_vertices + 1
                    d = num_vertices
                indices.append(a)
                indices.append(b)
                indices.append(c)
                indices.append(a)
                indices.append(c)
                indices.append(d)
                is_prev_ground = True

        ground_vertices = []
        ground_indices = []
        for i, contour in enumerate(buffs[0]):
            make_pseudo_3d_ground_for_contour(
                ground_vertices, ground_indices, contour, i == 0
            )
        self._pseudo_3d_ground_indexed_vertices = IndexedVertices(
            ground_vertices, ground_indices
        )

        self._unbuffed_platform_indexed_vertices = (
            self._tess.make_indexed_vertices_from_contours(
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
                self._tess.make_indexed_vertices_from_contours(buffs[i] + buffs[i + 1]),
            )
            for i, buff in enumerate(platform_buffers)
        ]

        if sand_pits:
            adjusted_sand_pits = [
                [adjust_point(c) for c in sand_pit] for sand_pit in sand_pits
            ]
            sand_pit_pseudo_vertices = []
            sand_pit_pseudo_indices = []
            for i, sand_pit in enumerate(adjusted_sand_pits):
                make_pseudo_3d_ground_for_contour(
                    sand_pit_pseudo_vertices, sand_pit_pseudo_indices, sand_pit, False
                )
            self._sand_pits_3d_ground_indexed_vertices = IndexedVertices(
                sand_pit_pseudo_vertices, sand_pit_pseudo_indices
            )
            self._sand_pits_indexed_vertices = (
                self._tess.make_indexed_vertices_from_contours(adjusted_sand_pits)
            )

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
                .buffer(r, BUFFER_RESOLUTION)
                .buffer(-2 * r, BUFFER_RESOLUTION)
                .buffer(r, BUFFER_RESOLUTION)
            )
            assert isinstance(shape, Polygon)
            return self._tess.make_indexed_vertices_from_contours(
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
            self._dynamic_wall_indexed_vertices = IndexedVertices(
                [0] * 32, [8] * 24, is_dynamic=True  # Max 4 rectangles
            )

        self._dynamic_shot_preview_dotted_line_vertex_buffers = [
            Buffer([0] * max_shot_preview_points * 2, 2, "float", is_dynamic=True)
            for _ in range(2)
        ]
        self._dynamic_shot_preview_dotted_line_distance_buffers = [
            Buffer([0] * max_shot_preview_points, 1, "float", is_dynamic=True)
            for _ in range(2)
        ]
        self._dynamic_shot_preview_polygon_vertex_buffer = Buffer(
            [0] * max_shot_preview_points * 4, 2, "float", is_dynamic=True
        )
        self._dynamic_shot_preview_polygon_distance_buffer = Buffer(
            [0] * max_shot_preview_points * 2, 1, "float", is_dynamic=True
        )
        self._dynamic_drawback_circle_outer_ring_vertex_buffer = Buffer(
            [0] * (CIRCLE_POINTS + 1) * 4, 2, "float", is_dynamic=True
        )
        self._dynamic_drawback_circle_inner_ring_vertex_buffer = Buffer(
            [0] * (CIRCLE_POINTS + 1) * 4, 2, "float", is_dynamic=True
        )
        self._dynamic_ball_trail_polygon_vertex_buffer = Buffer(
            [0] * self._num_ball_trail_points * 4, 2, "float", is_dynamic=True
        )
        self._dynamic_ball_trail_polygon_distance_buffer = Buffer(
            [0] * self._num_ball_trail_points * 2, 1, "float", is_dynamic=True
        )
        self._dynamic_ball_outer_vertex_buffer = Buffer(
            [0] * (CIRCLE_POINTS + 1) * 4, 2, "float", is_dynamic=True
        )
        self._dynamic_ball_inner_vertex_buffer = Buffer(
            [0] * CIRCLE_POINTS * 2, 2, "float", is_dynamic=True
        )

    def _make_sticky_indexed_vertices(self, sticky):
        r = self._sticky_wall_buffer_distance / 2.1
        shape = (
            LineString(sticky.wall)
            .buffer(
                -self._sticky_wall_buffer_distance
                if sticky.is_exterior
                else self._sticky_wall_buffer_distance,
                single_sided=True,
                resolution=BUFFER_RESOLUTION,
            )
            .buffer(r, BUFFER_RESOLUTION)
            .buffer(-2 * r, BUFFER_RESOLUTION)
            .buffer(r, BUFFER_RESOLUTION)
        )
        if not sticky.is_exterior:
            shape = shape.intersection(Polygon(sticky.contour))
        shape = shape.buffer(
            self._sticky_wall_outer_buffer_distance, resolution=BUFFER_RESOLUTION
        )
        assert not shape.is_empty
        contours = []
        if isinstance(shape, Polygon):
            contours.append(shape.exterior.coords)
            if len(shape.interiors) > 0:
                for interior in shape.interiors:
                    contours.append(interior.coords)
        elif isinstance(shape, MultiPolygon):
            assert isinstance(shape, MultiPolygon)
            # pylint: disable-next=no-member
            for poly in shape.geoms:
                assert isinstance(poly, Polygon)
                contours.append(poly.exterior.coords)
                if len(poly.interiors) > 0:
                    for interior in poly.interiors:
                        contours.append(interior.coords)
        return self._tess.make_indexed_vertices_from_contours(contours)

    def add_sticky(self, sticky):
        self._stickies_indexed_vertices.append(
            (sticky, self._make_sticky_indexed_vertices(sticky))
        )

    def remove_sticky(self, sticky):
        for i, (existing_sticky, existing_sticky_indexed_vertices) in enumerate(
            self._stickies_indexed_vertices
        ):
            if sticky == existing_sticky:
                self._stickies_indexed_vertices.pop(i)
                existing_sticky_indexed_vertices.dispose()
                break
        else:
            raise Exception("Tried removing a sticky that does not exist.")

    def render(self, camera, physics):
        bg_color = normalize_color(self._bg_color)
        gl.glClearColor(bg_color[0], bg_color[1], bg_color[2], 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glLoadIdentity()
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        camera_matrix = camera.get_matrix()
        view_matrix = [camera_matrix.column(i) for i in range(4)]

        single_color_shader.use()
        # pylint: disable=assigning-non-slot
        single_color_shader.uniforms.u_view_matrix = view_matrix
        single_color_shader.uniforms.u_alpha = 1
        single_color_shader.uniforms.u_color = normalize_color(
            self._pseudo_3d_ground_color
        )
        # pylint: enable=assigning-non-slot
        self._pseudo_3d_ground_indexed_vertices.render(
            single_color_shader.attributes.a_vertex_position
        )
        if self._sand_pits_indexed_vertices:
            # pylint: disable-next=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(
                self._sand_pits_pseudo_3d_ground_color
            )
            self._sand_pits_3d_ground_indexed_vertices.render(
                single_color_shader.attributes.a_vertex_position
            )
            # pylint: disable-next=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(
                self._sand_pits_color
            )
            self._sand_pits_indexed_vertices.render(
                single_color_shader.attributes.a_vertex_position
            )
        # pylint: disable-next=assigning-non-slot
        single_color_shader.uniforms.u_color = normalize_color(
            self._unbuffed_platform_color
        )
        self._unbuffed_platform_indexed_vertices.render(
            single_color_shader.attributes.a_vertex_position
        )
        for buff, indexed_vertices in self._buffed_platform_indexed_vertices:
            assert isinstance(buff, ColoredPlatformBuffer)
            # pylint: disable-next=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(buff.color)
            indexed_vertices.render(single_color_shader.attributes.a_vertex_position)
        if self._is_closed_in:
            rectangles = list(camera.get_view_rect().subtract(self.exterior_rect))
            if len(rectangles) > 0:
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
            # pylint: disable-next=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(
                self._unbuffed_platform_color
            )
            self._dynamic_wall_indexed_vertices.render(
                single_color_shader.attributes.a_vertex_position,
                num_triangles=len(rectangles) * 2,
            )
        single_color_shader.clear()

        def make_stripe_line(angle):
            return (math.sin(angle), -math.cos(angle), 0)

        stripe_shader.use()
        # pylint: disable=assigning-non-slot
        stripe_shader.uniforms.u_view_matrix = view_matrix
        stripe_shader.uniforms.u_line = make_stripe_line(self._flag_ground_stripe_angle)
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
        sticky = physics.get_preview_sticky()
        if sticky:
            joined_sticky = add_sticky_to_stickies(physics.existing_stickies, sticky)[1]
            indexed_vertices = self._make_sticky_indexed_vertices(joined_sticky)
            # pylint: disable=assigning-non-slot
            stripe_shader.uniforms.u_view_matrix = view_matrix
            stripe_shader.uniforms.u_line = make_stripe_line(
                self._preview_sticky_wall_stripe_angle
            )
            stripe_shader.uniforms.u_background_color = normalize_color(
                self._preview_sticky_wall_background_color
            )
            stripe_shader.uniforms.u_stripe_color = normalize_color(
                self._preview_sticky_wall_stripe_color
            )
            stripe_shader.uniforms.u_background_width = (
                self._preview_sticky_wall_background_width
            )
            stripe_shader.uniforms.u_stripe_width = (
                self._preview_sticky_wall_stripe_width
            )
            # pylint: enable=assigning-non-slot
            indexed_vertices.render(stripe_shader.attributes.a_vertex_position)
            indexed_vertices.dispose()
        for _, sticky_indexed_vertices in self._stickies_indexed_vertices:
            # pylint: disable=assigning-non-slot
            stripe_shader.uniforms.u_view_matrix = view_matrix
            stripe_shader.uniforms.u_line = make_stripe_line(
                self._sticky_wall_stripe_angle
            )
            stripe_shader.uniforms.u_background_color = normalize_color(
                self._sticky_wall_background_color
            )
            stripe_shader.uniforms.u_stripe_color = normalize_color(
                self._sticky_wall_stripe_color
            )
            stripe_shader.uniforms.u_background_width = (
                self._sticky_wall_background_width
            )
            stripe_shader.uniforms.u_stripe_width = self._sticky_wall_stripe_width
            # pylint: enable=assigning-non-slot
            sticky_indexed_vertices.render(stripe_shader.attributes.a_vertex_position)
        stripe_shader.clear()

        def update_dynamic_shot_preview_dotted_line_buffers(num_buffer, path):
            vertices = []
            distances = []
            distance = 0
            prev_c = None
            scale = camera.get_scale()
            for c in path:
                vertices.append(c[0])
                vertices.append(c[1])
                if prev_c:
                    distance += c.distance(prev_c) * scale
                distances.append(distance)
                prev_c = c
            self._dynamic_shot_preview_dotted_line_vertex_buffers[
                num_buffer
            ].update_part(vertices, 0)
            self._dynamic_shot_preview_dotted_line_distance_buffers[
                num_buffer
            ].update_part(distances, 0)
            return vertices, distances, distance

        def make_circle(centre, radius, num_points):
            points = []
            for i in range(num_points):
                angle = i / num_points * 2 * math.pi
                points.append(
                    (
                        centre[0] + radius * math.cos(angle),
                        centre[1] + radius * math.sin(angle),
                    )
                )
            return points

        def make_ring_vertices_from_circles(inner_circle, outer_circle):
            vertices = []
            for inner_point, outer_point in zip(inner_circle, outer_circle):
                vertices.append(inner_point[0])
                vertices.append(inner_point[1])
                vertices.append(outer_point[0])
                vertices.append(outer_point[1])
            vertices.append(inner_circle[0][0])
            vertices.append(inner_circle[0][1])
            vertices.append(outer_circle[0][0])
            vertices.append(outer_circle[0][1])
            return vertices

        if physics.is_dragging:
            drag_velocity = physics.get_drag_velocity()
            vel_y_sign = 1 if drag_velocity.y > 0 else -1
            vel1 = Vec2(
                drag_velocity.x,
                drag_velocity.y * (1 + vel_y_sign * self._shot_preview_lerp_up),
            )
            vel2 = Vec2(
                drag_velocity.x,
                drag_velocity.y * (1 - vel_y_sign * self._shot_preview_lerp_down),
            )
            path1 = physics.simulate_ball_path_from_position_with_velocity(
                physics.ball_position + Vec2(0, physics.ball_radius), vel1
            )
            path2 = physics.simulate_ball_path_from_position_with_velocity(
                physics.ball_position - Vec2(0, physics.ball_radius), vel2
            )
            verts1, dists1, dist1 = update_dynamic_shot_preview_dotted_line_buffers(
                0, path1
            )
            verts2, dists2, dist2 = update_dynamic_shot_preview_dotted_line_buffers(
                1, path2
            )
            dist = min(dist1, dist2)
            polygon_verts = []
            polygon_dists = []
            for i, (d1, d2) in enumerate(zip(dists1, dists2)):
                polygon_verts.append(verts1[i * 2])
                polygon_verts.append(verts1[i * 2 + 1])
                polygon_verts.append(verts2[i * 2])
                polygon_verts.append(verts2[i * 2 + 1])
                polygon_dists.append(d1)
                polygon_dists.append(d2)
            drag_start = camera.screen_position_to_world_position(
                physics.get_drag_start()
            )
            drag_current = camera.screen_position_to_world_position(
                physics.get_drag_current()
            )
            inner_radius = abs(drag_current - drag_start)
            circle_a = make_circle(drag_start, inner_radius, CIRCLE_POINTS)
            circle_b = make_circle(
                drag_start,
                inner_radius + self._shot_drawback_ring_width,
                CIRCLE_POINTS,
            )
            circle_c = make_circle(
                drag_start,
                inner_radius + 2 * self._shot_drawback_ring_width,
                CIRCLE_POINTS,
            )
            inner_ring_vertices = make_ring_vertices_from_circles(circle_a, circle_b)
            outer_ring_vertices = make_ring_vertices_from_circles(circle_b, circle_c)
            self._dynamic_shot_preview_polygon_vertex_buffer.update_part(
                polygon_verts, 0
            )
            self._dynamic_shot_preview_polygon_distance_buffer.update_part(
                polygon_dists, 0
            )
            self._dynamic_drawback_circle_inner_ring_vertex_buffer.update_part(
                inner_ring_vertices, 0
            )
            self._dynamic_drawback_circle_outer_ring_vertex_buffer.update_part(
                outer_ring_vertices, 0
            )

            faded_dotted_line_shader.use()
            # pylint: disable=assigning-non-slot
            faded_dotted_line_shader.uniforms.u_view_matrix = view_matrix
            faded_dotted_line_shader.uniforms.u_color = normalize_color(
                self._shot_preview_dotted_line_color
            )
            faded_dotted_line_shader.uniforms.u_fade_factor = (
                self._shot_preview_fade_factor
            )
            faded_dotted_line_shader.uniforms.u_space_size = (
                self._shot_preview_dotted_line_space_size
            )
            faded_dotted_line_shader.uniforms.u_dotted_size = (
                self._shot_preview_dotted_line_dotted_size
            )
            faded_dotted_line_shader.uniforms.u_line_length = dist
            # pylint: enable=assigning-non-slot
            for path, vert_buf, dist_buf in zip(
                (path1, path2),
                self._dynamic_shot_preview_dotted_line_vertex_buffers,
                self._dynamic_shot_preview_dotted_line_distance_buffers,
            ):
                vert_buf.bind_to_attrib(
                    faded_dotted_line_shader.attributes.a_vertex_position
                )
                dist_buf.bind_to_attrib(faded_dotted_line_shader.attributes.a_distance)
                gl.glDrawArrays(gl.GL_LINE_STRIP, 0, len(path))
            faded_dotted_line_shader.clear()

            faded_color_shader.use()
            # pylint: disable=assigning-non-slot
            faded_color_shader.uniforms.u_view_matrix = view_matrix
            faded_color_shader.uniforms.u_color = normalize_color(
                self._shot_preview_polygon_color
            )
            faded_color_shader.uniforms.u_fade_factor = self._shot_preview_fade_factor
            faded_color_shader.uniforms.u_base_alpha = self._shot_preview_base_alpha
            faded_color_shader.uniforms.u_line_length = dist
            # pylint: enable=assigning-non-slot
            self._dynamic_shot_preview_polygon_vertex_buffer.bind_to_attrib(
                faded_color_shader.attributes.a_vertex_position
            )
            self._dynamic_shot_preview_polygon_distance_buffer.bind_to_attrib(
                faded_color_shader.attributes.a_distance
            )
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, len(path1) * 2)
            faded_color_shader.clear()

            single_color_shader.use()
            # pylint: disable=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(
                self._shot_drawback_outer_ring_color
            )
            single_color_shader.uniforms.u_alpha = self._shot_drawback_outer_ring_alpha
            # pylint: enable=assigning-non-slot
            self._dynamic_drawback_circle_outer_ring_vertex_buffer.bind_to_attrib(
                single_color_shader.attributes.a_vertex_position
            )
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, (CIRCLE_POINTS + 1) * 2)
            # pylint: disable=assigning-non-slot
            single_color_shader.uniforms.u_color = normalize_color(
                self._shot_drawback_inner_ring_color
            )
            single_color_shader.uniforms.u_alpha = self._shot_drawback_inner_ring_alpha
            # pylint: enable=assigning-non-slot
            self._dynamic_drawback_circle_inner_ring_vertex_buffer.bind_to_attrib(
                single_color_shader.attributes.a_vertex_position
            )
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, (CIRCLE_POINTS + 1) * 2)
            single_color_shader.clear()

        trail = physics.get_ball_trail()
        if len(trail) > 1:
            ball_trail_verts = []
            ball_trail_dists = []
            for i, (v1, v2) in enumerate(trail):
                ball_trail_verts.append(v1[0])
                ball_trail_verts.append(v1[1])
                ball_trail_verts.append(v2[0])
                ball_trail_verts.append(v2[1])
                ball_trail_dists.append(1 - i / (len(trail) - 1))
                ball_trail_dists.append(1 - i / (len(trail) - 1))
            self._dynamic_ball_trail_polygon_vertex_buffer.update_part(
                ball_trail_verts, 0
            )
            self._dynamic_ball_trail_polygon_distance_buffer.update_part(
                ball_trail_dists, 0
            )
            faded_color_shader.use()
            # pylint: disable=assigning-non-slot
            faded_color_shader.uniforms.u_view_matrix = view_matrix
            faded_color_shader.uniforms.u_color = normalize_color(
                self._ball_trail_color
            )
            faded_color_shader.uniforms.u_fade_factor = self._ball_trail_fade_factor
            faded_color_shader.uniforms.u_base_alpha = self._ball_trail_base_alpha
            faded_color_shader.uniforms.u_line_length = 1.0
            # pylint: enable=assigning-non-slot
            self._dynamic_ball_trail_polygon_vertex_buffer.bind_to_attrib(
                faded_color_shader.attributes.a_vertex_position
            )
            self._dynamic_ball_trail_polygon_distance_buffer.bind_to_attrib(
                faded_color_shader.attributes.a_distance
            )
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, len(trail) * 2)
            faded_color_shader.clear()

        assert physics.ball_radius > self._ball_outline_size
        ball_outer_circle = make_circle(
            physics.ball_position, physics.ball_radius, CIRCLE_POINTS
        )
        ball_inner_circle = make_circle(
            physics.ball_position,
            physics.ball_radius - self._ball_outline_size,
            CIRCLE_POINTS,
        )
        ball_ring_vertices = make_ring_vertices_from_circles(
            ball_outer_circle, ball_inner_circle
        )
        ball_inner_vertices = []
        for x, y in ball_inner_circle:
            ball_inner_vertices.append(x)
            ball_inner_vertices.append(y)
        single_color_shader.use()
        self._dynamic_ball_outer_vertex_buffer.update_part(ball_ring_vertices, 0)
        self._dynamic_ball_inner_vertex_buffer.update_part(ball_inner_vertices, 0)
        # pylint: disable=assigning-non-slot
        single_color_shader.uniforms.u_alpha = 1
        single_color_shader.uniforms.u_color = normalize_color(self._ball_outline_color)
        # pylint: enable=assigning-non-slot
        self._dynamic_ball_outer_vertex_buffer.bind_to_attrib(
            single_color_shader.attributes.a_vertex_position
        )
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, (CIRCLE_POINTS + 1) * 2)
        # pylint: disable-next=assigning-non-slot
        single_color_shader.uniforms.u_color = normalize_color(self._ball_color)
        self._dynamic_ball_inner_vertex_buffer.bind_to_attrib(
            single_color_shader.attributes.a_vertex_position
        )
        gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, CIRCLE_POINTS)
        single_color_shader.clear()

    def dispose(self):
        self._pseudo_3d_ground_indexed_vertices.dispose()
        self._pseudo_3d_ground_indexed_vertices = None
        self._unbuffed_platform_indexed_vertices.dispose()
        self._unbuffed_platform_indexed_vertices = None
        for (_, indexed_vertices) in self._buffed_platform_indexed_vertices:
            indexed_vertices.dispose()
        self._buffed_platform_indexed_vertices = None
        self._start_flat_indexed_vertices.dispose()
        self._start_flat_indexed_vertices = None
        self._flag_flat_indexed_vertices.dispose()
        self._flag_flat_indexed_vertices = None
        if self._is_closed_in:
            self._dynamic_wall_indexed_vertices.dispose()
            self._dynamic_wall_indexed_vertices = None
        self._dynamic_shot_preview_dotted_line_vertex_buffers[0].dispose()
        self._dynamic_shot_preview_dotted_line_vertex_buffers[1].dispose()
        self._dynamic_shot_preview_dotted_line_vertex_buffers = None
        self._dynamic_shot_preview_dotted_line_distance_buffers[0].dispose()
        self._dynamic_shot_preview_dotted_line_distance_buffers[1].dispose()
        self._dynamic_shot_preview_dotted_line_distance_buffers = None
        self._dynamic_shot_preview_polygon_vertex_buffer.dispose()
        self._dynamic_shot_preview_polygon_distance_buffer.dispose()
        self._dynamic_drawback_circle_outer_ring_vertex_buffer.dispose()
        self._dynamic_drawback_circle_outer_ring_vertex_buffer = None
        self._dynamic_drawback_circle_inner_ring_vertex_buffer.dispose()
        self._dynamic_drawback_circle_inner_ring_vertex_buffer = None
        for _, indexed_vertices in self._stickies_indexed_vertices:
            indexed_vertices.dispose()
        self._stickies_indexed_vertices = None
        self._dynamic_ball_trail_polygon_vertex_buffer.dispose()
        self._dynamic_ball_trail_polygon_vertex_buffer = None
        self._dynamic_ball_trail_polygon_distance_buffer.dispose()
        self._dynamic_ball_trail_polygon_distance_buffer = None
        self._dynamic_ball_outer_vertex_buffer.dispose()
        self._dynamic_ball_inner_vertex_buffer.dispose()
        if self._sand_pits_indexed_vertices:
            self._sand_pits_3d_ground_indexed_vertices.dispose()
            self._sand_pits_3d_ground_indexed_vertices = None
            self._sand_pits_indexed_vertices.dispose()
            self._sand_pits_indexed_vertices = None
        self._tess.dispose()
        self._tess = None
