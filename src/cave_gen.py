import math
from random import randint, randrange
from collections import deque
from pyglet.math import Vec2
from shapely.geometry import Polygon
from collision import (
    Vector as CollisionVector,
    Poly,
    Concave_Poly as ConcavePoly,
    collide,
)
from Rectangle import Rectangle


def make_cave_contours(grid, width, height):
    edges = {}

    def add_edge(x, y, p1, p2):
        def coord(x, y, p):
            if p == 1:
                dx = 1
                dy = 2
            if p == 2:
                dx = 2
                dy = 1
            if p == 3:
                dx = 1
                dy = 0
            if p == 4:
                dx = 0
                dy = 1
            return (x * 2 + dx, y * 2 + dy)

        c1 = coord(x, y, p1)
        c2 = coord(x, y, p2)

        edges[c1] = (edges[c1][0], c2) if c1 in edges else (c2, None)
        edges[c2] = (edges[c2][0], c1) if c2 in edges else (c1, None)

    for y in range(height - 1):
        for x in range(width - 1):
            case = (
                grid[y + 1][x]
                + (grid[y + 1][x + 1] << 1)
                + (grid[y][x + 1] << 2)
                + (grid[y][x] << 3)
            )

            if case == 1:
                add_edge(x, y, 1, 4)
            elif case == 2:
                add_edge(x, y, 1, 2)
            elif case == 3:
                add_edge(x, y, 2, 4)
            elif case == 4:
                add_edge(x, y, 2, 3)
            elif case == 5:
                add_edge(x, y, 1, 2)
                add_edge(x, y, 3, 4)
            elif case == 6:
                add_edge(x, y, 1, 3)
            elif case == 7:
                add_edge(x, y, 3, 4)
            elif case == 8:
                add_edge(x, y, 3, 4)
            elif case == 9:
                add_edge(x, y, 1, 3)
            elif case == 10:
                add_edge(x, y, 1, 4)
                add_edge(x, y, 2, 3)
            elif case == 11:
                add_edge(x, y, 2, 3)
            elif case == 12:
                add_edge(x, y, 2, 4)
            elif case == 13:
                add_edge(x, y, 1, 2)
            elif case == 14:
                add_edge(x, y, 1, 4)

    polygons = [[]]
    c1, (c2, _) = next(iter(edges.items()))
    while True:
        polygons[-1].append(c1)
        del edges[c1]
        if c2 in edges:
            c2a, c2b = edges[c2]
            c1, c2 = c2, c2b if c2a == c1 else c2a
        elif len(edges) > 0:
            polygons.append([])
            c1, (c2, _) = next(iter(edges.items()))
        else:
            break

    for polygon in polygons:
        if _get_signed_area_of_polygon(polygon) > 0:
            polygon.reverse()  # make counter-clockwise

    return polygons


def _get_signed_area_of_polygon(polygon):
    double_signed_area = 0
    for i, c1 in enumerate(polygon):
        c2 = polygon[(i + 1) % len(polygon)]
        double_signed_area += (c2[0] - c1[0]) * (c2[1] + c1[1])
    return double_signed_area / 2


class Flat:
    def __init__(self, pos, width):
        self.pos = pos
        self.width = width

    def extend(self, x):
        if x < self.pos.x:
            return Flat(Vec2(x, self.pos.y), (self.pos.x + self.width) - x)
        if x > self.pos.x + self.width:
            return Flat(self.pos, x - self.pos.x)
        return self

    def buffer(self, amount):
        return Flat(Vec2(self.pos.x - amount, self.pos.y), self.width + 2 * amount)

    def make_rect(self, height):
        return Rectangle(self.pos, self.width, height)

    def get_middle(self):
        return Vec2(self.pos.x + self.width / 2, self.pos.y)


def _get_flat_grounds(contours):
    flats = []
    for i, contour in enumerate(contours):
        is_prev_flat = False
        for j, c1 in enumerate(contour):
            c2 = contour[(j + 1) % len(contour)]
            if c1[1] != c2[1]:
                is_prev_flat = False
                continue
            l = c1[0] - c2[0] if i == 0 else c2[0] - c1[0]
            if l >= 0:
                is_prev_flat = False
                continue
            if is_prev_flat:
                flats[-1] = flats[-1].extend(c2[0])
            else:
                flats.append(
                    Flat(pos=Vec2(min(c1[0], c2[0]), c1[1]), width=abs(c2[0] - c1[0]))
                )
            is_prev_flat = True
    return flats


# https://github.com/bsharvari/A-Star-Search
def _min_path_length(grid, start, end):
    path = []
    val = 1

    visited = [[0 for _ in range(len(grid[0]))] for _ in range(len(grid))]
    visited[start[0]][start[1]] = 1

    heuristic = lambda x, y: abs(end[0] - x) + abs(end[1] - y)

    x = start[0]
    y = start[1]
    g = 0
    f = g + heuristic(x, y)

    minList = [f, g, x, y]

    delta = [[-1, 0], [0, -1], [1, 0], [0, 1]]

    while minList[2:] != end:
        # pylint: disable-next=consider-using-enumerate
        for i in range(len(delta)):
            x2 = x + delta[i][0]
            y2 = y + delta[i][1]
            if 0 <= x2 < len(grid) and 0 <= y2 < len(grid[0]):
                if visited[x2][y2] == 0 and grid[x2][y2] == 0:
                    g2 = g + 1
                    f2 = g2 + heuristic(x2, y2)
                    path.append([f2, g2, x2, y2])
                    visited[x2][y2] = 1

        if not path:
            raise Exception("No path")

        del minList[:]
        minList = min(path)
        path.remove(minList)
        x = minList[2]
        y = minList[3]
        g = minList[1]
        val += 1

    return minList[1]


def place_start_flat_and_flag_flat(contours, grid):
    flat_grounds = [flat.buffer(-0.25) for flat in _get_flat_grounds(contours)]

    def flat_to_grid_coords(flat):
        mid = flat.get_middle()
        return [int(mid.y / 2) + 1, int(mid.x / 2)]

    def get_score(start_flat, flag_flat):
        return flag_flat.width + _min_path_length(
            grid, flat_to_grid_coords(start_flat), flat_to_grid_coords(flag_flat)
        )

    i, j, _ = max(
        (
            (i, j, get_score(a, b))
            for i, a in enumerate(flat_grounds)
            for j, b in enumerate(flat_grounds)
            if i != j
        ),
        key=lambda t: t[2],
    )

    return flat_grounds[i], flat_grounds[j]


def make_sand_pits(
    contours,
    min_sand_pit_area,
    max_sand_pit_area,
    max_sand_pits,
    avoid_rects,
    ball_radius,
):
    avoid_polys = [
        ConcavePoly(
            CollisionVector(0, 0), [CollisionVector(v[0], v[1]) for v in inner_contour]
        )
        for inner_contour in contours[1:]
    ] + [
        Poly(
            CollisionVector(0, 0),
            [
                CollisionVector(rect.pos.x, rect.pos.y),
                CollisionVector(rect.right, rect.pos.y),
                CollisionVector(rect.right, rect.top),
                CollisionVector(rect.pos.x, rect.top),
            ],
        )
        for rect in avoid_rects
    ]

    def sand_pit_to_poly(sand_pit):
        shape = Polygon(sand_pit).buffer(ball_radius, 4)
        assert isinstance(shape, Polygon)
        return ConcavePoly(
            CollisionVector(0, 0),
            # pylint: disable-next=no-member
            [CollisionVector(v[0], v[1]) for v in shape.exterior.coords][:-1],
        )

    sand_pits = []
    sand_pit_starts = []
    outer_contour = contours[0]
    for i, (v1, v2) in enumerate(zip(outer_contour, outer_contour[1:])):
        if v2[1] < v1[1]:
            sand_pit_starts.append(i)
        elif v2[1] > v1[1]:
            start_index = None
            while len(sand_pit_starts) > 0:
                start_index_ = sand_pit_starts[-1]
                start_v = outer_contour[start_index_]
                if v2[1] >= start_v[1]:
                    start_index = start_index_
                    sand_pit_starts.pop()
                else:
                    break
            if start_index is not None:
                sand_pit = outer_contour[start_index : i + 2]
                sand_pit_poly = sand_pit_to_poly(sand_pit)
                if (
                    len(sand_pit) >= 4
                    # Compare signed area, not absolute area, to also check winding
                    # is counter-clockwise, i.e. the sand pit is not inside the cave
                    # wall (in which case the winding would be clockwise)
                    and (
                        min_sand_pit_area
                        <= -_get_signed_area_of_polygon(sand_pit)
                        <= max_sand_pit_area
                    )
                    and not any(
                        collide(sand_pit_poly, avoid_poly) for avoid_poly in avoid_polys
                    )
                ):
                    sand_pits.append(sand_pit)

    sand_pit_polys = [sand_pit_to_poly(sand_pit) for sand_pit in sand_pits]
    selected_sand_pits = []
    selected_sand_pit_polys = []
    while len(sand_pits) > 0 and len(selected_sand_pits) < max_sand_pits:
        i = randrange(len(sand_pits))
        sand_pit = sand_pits.pop(i)
        sand_pit_poly = sand_pit_polys.pop(i)
        if any(
            collide(sand_pit_poly, selected_sand_pit_poly)
            for selected_sand_pit_poly in selected_sand_pit_polys
        ):
            continue
        selected_sand_pits.append(sand_pit)
        selected_sand_pit_polys.append(sand_pit_poly)

    for sand_pit in selected_sand_pits:
        top_left = sand_pit[0]
        top_right = sand_pit[-1]
        step = 0.25
        x = top_right[0] - step
        while x > top_left[0]:
            dx = x - top_left[0]
            sand_pit.append((x, top_left[1] + math.sin(dx) / 10))
            x -= step

    return selected_sand_pits


def make_cave_grid(
    width,
    height,
    wall_chance,
    min_surrounding_walls,
    iterations,
    pillar_iterations,
    min_open_percent,
):
    def do_cellular_automata(grid, make_pillars):
        updated_grid = [row[:] for row in grid]

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                count = (
                    grid[y - 1][x - 1]
                    + grid[y - 1][x]
                    + grid[y - 1][x + 1]
                    + grid[y][x - 1]
                    + grid[y][x]
                    + grid[y][x + 1]
                    + grid[y + 1][x - 1]
                    + grid[y + 1][x]
                    + grid[y + 1][x + 1]
                )
                is_wall = count >= min_surrounding_walls or (
                    make_pillars and count == 0
                )
                updated_grid[y][x] = 1 if is_wall else 0

        return updated_grid

    def copy_largest_open_space_into_new_grid(grid):
        def copy_open_space_into_new_grid(start_x, start_y):
            grid_with_single_open_space = [
                [1 for _ in range(width)] for _ in range(height)
            ]
            grid_with_single_open_space[start_y][start_x] = 0
            cell_coordinates_to_visit = deque([(start_x, start_y)])
            open_count = 1

            def check_empty(x, y):
                nonlocal open_count
                if grid[y][x] == 0 and grid_with_single_open_space[y][x] == 1:
                    grid_with_single_open_space[y][x] = 0
                    cell_coordinates_to_visit.append((x, y))
                    open_count += 1

            while len(cell_coordinates_to_visit) > 0:
                x, y = cell_coordinates_to_visit.popleft()
                grid_with_single_open_space[y][x] = 0
                check_empty(x - 1, y)
                check_empty(x + 1, y)
                check_empty(x, y - 1)
                check_empty(x, y + 1)

            return (grid_with_single_open_space, open_count)

        isolated_open_space_grids = []

        for start_y in range(1, height - 1):
            for start_x in range(1, width - 1):
                if grid[start_y][start_x] == 0 and all(
                    t[0][start_y][start_x] == 1 for t in isolated_open_space_grids
                ):
                    isolated_open_space_grids.append(
                        copy_open_space_into_new_grid(start_x, start_y)
                    )

        return max(isolated_open_space_grids, key=lambda t: t[1])

    while True:
        grid = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                if (
                    x == 0
                    or y == 0
                    or x == width - 1
                    or y == height - 1
                    or randint(0, 100) <= wall_chance
                ):
                    grid[y][x] = 1

        for _ in range(pillar_iterations):
            grid = do_cellular_automata(grid, make_pillars=True)

        for _ in range(iterations):
            grid = do_cellular_automata(grid, make_pillars=False)

        found_open = False
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if grid[y][x] == 0:
                    found_open = True
                    break
            if found_open:
                break
        if not found_open:
            continue

        (
            grid_with_single_open_space,
            open_count,
        ) = copy_largest_open_space_into_new_grid(grid)
        if open_count >= min_open_percent * width * height:
            return grid_with_single_open_space
