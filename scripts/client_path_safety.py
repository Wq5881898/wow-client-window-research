"""Loop-free and danger-aware retreat paths over a sampled client trail.

Why this module exists
----------------------
The batch owner of 2026-11-13 walked the character back by reversing the whole
recorded trail.  The trail is not a single walk: it holds the out-and-back leg
of the road survey and, after a revive, the jump from the corpse to the
graveyard.  Reversing that list re-entered the place where the character had
just been attacked and the retreat died there.

The module therefore works on the sampled geometry itself:

* only edges that were really walked may be used for a route,
* an edge that runs through a known threat area is refused,
* a route without a safe variant is refused instead of guessed.

Nothing in here talks to the game.  The caller owns the input and the
recovery, this module only answers which waypoints may be walked and which
waypoints are forbidden.  Positions are the normalised map coordinates that
the probe reports.
"""
import heapq
import math

WALK = 'walk'
TELEPORT = 'teleport'


class NoSafePath(ValueError):
    """Raised when no route avoids the recorded threat areas.

    The caller must treat this as a blocked branch and keep control; it must
    not fall back to a route through the threat area.
    """


def quantize(pos, digits=3):
    """The node key of a position."""
    return (round(float(pos[0]), digits), round(float(pos[1]), digits))


def point_segment_distance(point, a, b):
    """The distance of a point to a segment."""
    px, py = float(point[0]), float(point[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def classify_edges(trail, *, jump_distance=0.02, jump_seconds=60.0,
                   station_distance=0.001):
    """Split the sampled trail into edges and mark the ones that were not walked.

    A position jump and a long gap in the sampling are both evidence that the
    two samples are not connected by a walk: the character was revived, it
    was teleported or the recording was interrupted.  Such an edge must never
    become a waypoint of a route.

    A long gap between two samples at the same place is not such an edge: the
    character stood still and continued from there.  Cutting it would isolate
    the place where the character waited, for example the first certified
    point of a run.
    """
    edges = []
    for index in range(len(trail) - 1):
        first, second = trail[index], trail[index + 1]
        a = (float(first['pos'][0]), float(first['pos'][1]))
        b = (float(second['pos'][0]), float(second['pos'][1]))
        distance = math.dist(a, b)
        duration = float(second.get('time', 0)) - float(first.get('time', 0))
        kind, reason = WALK, ''
        if distance > jump_distance:
            kind, reason = TELEPORT, 'position_jump'
        elif duration > jump_seconds:
            if distance > station_distance:
                kind, reason = TELEPORT, 'sampled_gap'
            else:
                reason = 'stationary_pause'
        edges.append({'index': index, 'a': quantize(a), 'b': quantize(b),
                      'pa': a, 'pb': b, 'distance': distance,
                      'duration': duration, 'kind': kind, 'reason': reason,
                      'danger': False, 'danger_reason': ''})
    return edges


def mark_danger(edges, danger_points, *, danger_radius=0.004, occupied_from=None,
                occupied_zones=()):
    """Flag every edge that runs through a recorded threat area.

    The test is the distance of the threat to the edge, not to its end points,
    because a straight leg can pass close to a threat without ending on it.

    A zone that already holds the character does not forbid anything: the
    character is inside it and has to be able to leave.  The caller may name
    further zones as occupied, for example the place of the fight the
    character is just leaving; a zone that separates the character from the
    road it came from would otherwise trap it.
    """
    exempt = {id(threat) for threat in occupied_zones}
    for edge in edges:
        edge['danger'] = False
        edge['danger_reason'] = ''
        edge['danger_zone'] = None
    for edge in edges:
        for threat in danger_points:
            radius = float(threat.get('radius', danger_radius))
            if point_segment_distance(threat['pos'], edge['pa'], edge['pb']) > radius:
                continue
            if id(threat) in exempt:
                continue
            edge['danger'] = True
            edge['danger_reason'] = threat.get('kind', 'threat')
            edge['danger_zone'] = threat
            break
    if occupied_from is not None:
        for threat in danger_points:
            radius = float(threat.get('radius', danger_radius))
            if math.dist(threat['pos'], occupied_from) <= radius:
                exempt.add(id(threat))
        if exempt:
            for edge in edges:
                if edge['danger'] and id(edge['danger_zone']) in exempt:
                    edge['danger'] = False
                    edge['danger_reason'] = ''
                    edge['danger_zone'] = None
    return edges


def build_graph(edges, *, allow_danger=False):
    """The graph of the walked edges, without the forbidden ones."""
    graph = {}
    for edge in edges:
        if edge['kind'] != WALK:
            continue
        if edge['danger'] and not allow_danger:
            continue
        graph.setdefault(edge['a'], []).append((edge['b'], edge))
        graph.setdefault(edge['b'], []).append((edge['a'], edge))
    return graph


def node_positions(edges):
    """One representative position per node."""
    positions = {}
    for edge in edges:
        positions.setdefault(edge['a'], edge['pa'])
        positions.setdefault(edge['b'], edge['pb'])
    return positions


def nearest_node(graph, pos, tolerance=0.006):
    """The node closest to a position, within the tolerance."""
    best, best_distance = None, tolerance
    for node in graph:
        distance = math.dist(node, pos)
        if distance <= best_distance:
            best, best_distance = node, distance
    return best


def shortest_path(graph, start, target):
    """The cheapest path between two nodes of the graph.

    The path is simple: a node never appears twice, so the route cannot walk
    a loop.
    """
    if start == target:
        return []
    if start not in graph or target not in graph:
        raise NoSafePath('node_missing')
    distance = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    settled = set()
    while queue:
        cost, node = heapq.heappop(queue)
        if node in settled:
            continue
        settled.add(node)
        if node == target:
            break
        for neighbour, edge in graph.get(node, ()):
            candidate = cost + edge['distance']
            if candidate < distance.get(neighbour, math.inf):
                distance[neighbour] = candidate
                previous[neighbour] = (node, edge)
                heapq.heappush(queue, (candidate, neighbour))
    if target not in distance:
        raise NoSafePath('no_safe_route')
    legs = []
    node = target
    while node != start:
        parent, edge = previous[node]
        legs.append((node, edge))
        node = parent
    legs.reverse()
    return legs


def safe_back_path(trail, start_pos, target_pos, *, danger_points=(),
                   danger_radius=0.004, jump_distance=0.02, jump_seconds=60.0,
                   allow_danger=False, attach_tolerance=0.006, occupied_zones=()):
    """The waypoints from a position back to a target, without the threat areas.

    Raises NoSafePath when the target cannot be reached without walking a
    forbidden edge.  The caller must not route in that case.
    """
    edges = classify_edges(trail, jump_distance=jump_distance,
                           jump_seconds=jump_seconds)
    mark_danger(edges, danger_points, danger_radius=danger_radius,
                occupied_from=start_pos, occupied_zones=occupied_zones)
    graph = build_graph(edges, allow_danger=allow_danger)
    positions = node_positions(edges)
    start = nearest_node(graph, start_pos, attach_tolerance)
    target = nearest_node(graph, target_pos, attach_tolerance)
    if start is None:
        raise NoSafePath('start_not_on_walked_trail')
    if target is None:
        raise NoSafePath('target_not_on_walked_trail')
    legs = shortest_path(graph, start, target)
    waypoints = [positions[leg[0]] for leg in legs]
    used = [leg[1] for leg in legs]
    return {'waypoints': waypoints, 'edges': used,
            'length': sum(edge['distance'] for edge in used),
            'nodes': [leg[0] for leg in legs]}


def legacy_reversed_trail_path(trail, target_index, target_pos):
    """The retired behaviour, kept only to prove the counterexample.

    The owner of 2026-11-13 reversed the sampled trail from the index of the
    target and appended the target position.  That list contains the
    out-and-back leg of the survey and the jump that follows a revive.
    """
    out = []
    for sample in reversed(trail[target_index + 1:]):
        if not out or math.dist(sample['pos'], out[-1]) > 0.0006:
            out.append(list(sample['pos']))
    out.append(list(target_pos))
    return out


def path_report(path, edges, danger_points=(), danger_radius=0.004):
    """How a waypoint list touches the classified edges.

    A leg of the path that matches no sampled edge was invented by the
    path itself: it cuts a straight chord over the terrain.  Such a leg is
    counted separately, and it is checked against the threat areas because
    that is where it can lead.
    """
    danger_hits, teleport_hits, invented = 0, 0, 0
    length = 0.0
    for first, second in zip(path, path[1:]):
        length += math.dist(first, second)
        qa, qb = quantize(first), quantize(second)
        matched = None
        for edge in edges:
            if (edge['a'] == qa and edge['b'] == qb) or \
               (edge['a'] == qb and edge['b'] == qa):
                matched = edge
                break
        if matched is None:
            invented += 1
            for threat in danger_points:
                radius = float(threat.get('radius', danger_radius))
                if point_segment_distance(threat['pos'], first, second) <= radius:
                    danger_hits += 1
                    break
            continue
        if matched['danger']:
            danger_hits += 1
        if matched['kind'] != WALK:
            teleport_hits += 1
    nodes = [quantize(p) for p in path]
    return {'waypoints': len(path), 'length': length, 'danger_hits': danger_hits,
            'teleport_hits': teleport_hits, 'invented_legs': invented,
            'repeated_nodes': len(nodes) - len(set(nodes))}


def cluster_points(points, *, radius=0.002):
    """Merge the threat positions that belong to the same place.

    A dead character reports a slightly different position in every sample,
    and the ghost walks while it is dead.  Without clustering one incident
    would produce dozens of threat points and flag unrelated edges.
    """
    zones = []
    for point in points:
        target = None
        for zone in zones:
            if math.dist(zone['pos'], point['pos']) <= radius:
                target = zone
                break
        if target is None:
            zones.append({'pos': point['pos'], 'kind': point['kind'], 'spread': 0.0})
            continue
        target['spread'] = max(target['spread'], math.dist(target['pos'], point['pos']))
        if severity_of(point['kind']) > severity_of(target['kind']):
            target['kind'] = point['kind']
    for zone in zones:
        if zone['spread'] > 0:
            zone['radius'] = radius + zone['spread']
    return zones


def severity_of(kind):
    """The order of the threat kinds: a death is worse than a fight."""
    return {'combat': 0, 'fight': 1, 'death': 2}.get(kind, 0)


def danger_points_from_report(report, *, kinds=('fight', 'combat', 'death'),
                               cluster_radius=0.002):
    """The threat areas of a run report."""
    points = []
    index = {}
    severity = severity_of
    death_recorded = False

    def add(pos, kind):
        if kind not in kinds:
            return
        key = quantize(pos)
        if key in index:
            if severity(kind) <= severity(points[index[key]]['kind']):
                return
            points[index[key]]['kind'] = kind
            return
        index[key] = len(points)
        points.append({'pos': (float(pos[0]), float(pos[1])), 'kind': kind})

    def scan(sample, kind):
        if isinstance(sample, dict) and 'pos_x' in sample and 'pos_y' in sample:
            add((sample['pos_x'], sample['pos_y']), kind)

    for fight in report.get('fights', []) or []:
        scan(fight.get('before'), 'fight')
        for sample in fight.get('samples', []) or []:
            scan(sample, 'fight')
    for sample in report.get('samples', []) or []:
        if not isinstance(sample, dict):
            continue
        if sample.get('dead'):
            if death_recorded:
                continue
            death_recorded = True
            scan(sample, 'death')
        elif sample.get('combat'):
            scan(sample, 'combat')
    return cluster_points(points, radius=cluster_radius)


def analyse(trail, start_pos, target_pos, danger_points=(), **options):
    """Compare the retired path with the safe path and report both.

    The report separates what was observed from what the new rule produces:
    the legacy numbers describe the run of 2026-11-13, the safe numbers are
    the offline result of the new rule.
    """
    edges = classify_edges(trail, jump_distance=options.get('jump_distance', 0.02),
                           jump_seconds=options.get('jump_seconds', 60.0))
    mark_danger(edges, danger_points, danger_radius=options.get('danger_radius', 0.004))
    legacy = legacy_reversed_trail_path(trail, options.get('target_index', 0),
                                        target_pos)
    legacy_report = path_report(legacy, edges, danger_points,
                                options.get('danger_radius', 0.004))
    route_options = {key: value for key, value in options.items()
                     if key in ('danger_radius', 'jump_distance', 'jump_seconds',
                                'allow_danger', 'attach_tolerance', 'occupied_zones')}
    try:
        safe = safe_back_path(trail, start_pos, target_pos,
                               danger_points=danger_points, **route_options)
    except NoSafePath as exc:
        safe = {'refused': True, 'reason': str(exc), 'waypoints': 0,
                'length': 0.0, 'danger_hits': 0, 'teleport_hits': 0,
                'repeated_nodes': 0, 'nodes': []}
    else:
        safe = dict(safe, refused=False, reason='ok')
        safe.update(path_report(safe['waypoints'], edges, danger_points,
                                options.get('danger_radius', 0.004)))
    return {
        'trail_points': len(trail),
        'walk_edges': sum(1 for edge in edges if edge['kind'] == WALK),
        'teleport_edges': sum(1 for edge in edges if edge['kind'] != WALK),
        'danger_edges': sum(1 for edge in edges if edge['danger']),
        'danger_points': [{'pos': list(point['pos']), 'kind': point['kind']}
                          for point in danger_points],
        'legacy': legacy_report,
        'safe': safe,
    }


def main(argv=None):
    """Offline analysis of a recorded trail."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trail', required=True)
    parser.add_argument('--report', action='append', default=[],
                        help='run report with fights and samples, repeatable')
    parser.add_argument('--target', required=True, help='x,y of the target')
    parser.add_argument('--start', help='x,y of the current position')
    parser.add_argument('--target-index', type=int, default=0)
    parser.add_argument('--danger-radius', type=float, default=0.004)
    parser.add_argument('--out')
    options = parser.parse_args(argv)

    trail = json.loads(Path(options.trail).read_text(encoding='utf-8'))
    danger_points = []
    for name in options.report:
        report = json.loads(Path(name).read_text(encoding='utf-8'))
        danger_points.extend(danger_points_from_report(report))
    target = [float(value) for value in options.target.split(',')]
    start = ([float(value) for value in options.start.split(',')]
             if options.start else list(trail[-1]['pos']))
    summary = analyse(trail, start, target, danger_points,
                      target_index=options.target_index,
                      danger_radius=options.danger_radius)
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if options.out:
        Path(options.out).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
