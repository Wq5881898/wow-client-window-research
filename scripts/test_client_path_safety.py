"""Counterexamples for the retreat path of 2026-11-13.

The batch run died because the recovery reversed the whole recorded trail.
The trail holds the out-and-back leg of the road survey and the jump that
follows a revive, so the reversed list walked back through the place where
the character had just been attacked.

The fixtures below use the coordinates of that run: the road chain
initial..road6, the return leg, the fight at the road6 area, the death
further south and the revive that brought the character back.
"""
import json
import math
import unittest
from pathlib import Path

from client_path_safety import (NoSafePath, analyse, classify_edges,
                                 danger_points_from_report, legacy_reversed_trail_path,
                                 mark_danger, point_segment_distance,
                                 safe_back_path)

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'desktop-check'

ANCHOR = (0.4457770656900893, 0.6245517662317845)
ROAD = [(0.4467, 0.6137), (0.4505, 0.6009), (0.4554, 0.5918),
        (0.4696, 0.5916), (0.4803, 0.5900), (0.4859, 0.5848)]
RETURN_LEG = [(0.4830, 0.5870), (0.4810, 0.5900), (0.4780, 0.5910)]
FIGHT = (0.4860, 0.5849)
SOUTH = [(0.4950, 0.5830), (0.4950, 0.5950), (0.4950, 0.6060)]
DEATH = (0.3930, 0.6048)
BYPASS = [(0.4880, 0.6070), (0.4780, 0.6080), (0.4680, 0.6090),
          (0.4580, 0.6100), (0.4480, 0.6110), (0.4400, 0.6180)]
ROAD6_INDEX = len(ROAD)


def make_trail(points, *, start=0.0, step=0.3):
    """A sampled trail with the shape of a walked path."""
    trail = []
    time = start
    for index, point in enumerate(points):
        trail.append({'pos': [point[0], point[1]], 'map': 0, 'time': time, 'seq': index})
        time += step
    return trail


def road_trail(*, with_bypass=False, gap_seconds=577.0):
    """The trail of the run: out along the road, back again, then south."""
    points = [ANCHOR] + ROAD + RETURN_LEG
    trail = make_trail(points)
    index = len(trail)
    trail.append({'pos': [FIGHT[0], FIGHT[1]], 'map': 0,
                  'time': trail[-1]['time'] + gap_seconds, 'seq': index})
    trail.extend(make_trail(SOUTH, start=trail[-1]['time'] + 0.3, step=0.3))
    if with_bypass:
        trail.extend(make_trail(BYPASS, start=trail[-1]['time'] + 0.3, step=0.3))
        trail.append({'pos': [ANCHOR[0], ANCHOR[1]], 'map': 0,
                      'time': trail[-1]['time'] + 0.3, 'seq': len(trail)})
    return trail


def threats():
    return [{'pos': FIGHT, 'kind': 'fight'}, {'pos': DEATH, 'kind': 'death'}]


class PathSafetyTests(unittest.TestCase):
    def test_retired_path_replays_the_out_and_back_leg(self):
        trail = road_trail()
        legacy = legacy_reversed_trail_path(trail, ROAD6_INDEX, ROAD[-1])
        self.assertIn([FIGHT[0], FIGHT[1]], legacy)
        for point in RETURN_LEG:
            self.assertIn([point[0], point[1]], legacy)

    def test_retired_path_touches_the_threat_and_invents_legs(self):
        trail = road_trail()
        summary = analyse(trail, SOUTH[-1], ANCHOR, threats(), target_index=ROAD6_INDEX)
        self.assertGreaterEqual(summary['legacy']['danger_hits'], 1)
        self.assertGreaterEqual(summary['legacy']['invented_legs'], 1)
        self.assertEqual(summary['safe']['refused'], True)

    def test_route_is_refused_when_only_the_threat_leads_back(self):
        trail = road_trail()
        with self.assertRaises(NoSafePath) as caught:
            safe_back_path(trail, SOUTH[-1], ANCHOR, danger_points=threats())
        self.assertEqual(str(caught.exception), 'no_safe_route')

    def test_safe_route_avoids_the_threat_and_stays_loop_free(self):
        trail = road_trail(with_bypass=True)
        result = safe_back_path(trail, SOUTH[-1], ANCHOR, danger_points=threats())
        self.assertTrue(result['waypoints'])
        self.assertEqual(len(result['nodes']), len(set(result['nodes'])))
        for waypoint in result['waypoints']:
            for threat in threats():
                self.assertGreater(math.dist(waypoint, threat['pos']), 0.0005)
        for edge in result['edges']:
            self.assertFalse(edge['danger'])
            self.assertEqual(edge['kind'], 'walk')

    def test_safe_route_is_shorter_than_the_retired_path(self):
        trail = road_trail(with_bypass=True)
        summary = analyse(trail, SOUTH[-1], ANCHOR, threats(), target_index=ROAD6_INDEX)
        self.assertFalse(summary['safe']['refused'])
        self.assertEqual(summary['safe']['danger_hits'], 0)
        self.assertLess(summary['safe']['length'], summary['legacy']['length'])

    def test_the_only_danger_edge_is_refused_and_can_be_forced(self):
        trail = make_trail([(0.40, 0.60), (0.42, 0.60)])
        threat = [{'pos': (0.41, 0.60), 'kind': 'combat'}]
        with self.assertRaises(NoSafePath):
            safe_back_path(trail, (0.42, 0.60), (0.40, 0.60), danger_points=threat)
        forced = safe_back_path(trail, (0.42, 0.60), (0.40, 0.60),
                                danger_points=threat, allow_danger=True)
        self.assertTrue(forced['waypoints'])
        self.assertTrue(any(edge['danger'] for edge in forced['edges']))

    def test_a_zone_the_character_stands_in_does_not_trap_it(self):
        trail = make_trail([(0.40, 0.60), (0.405, 0.60), (0.42, 0.60)])
        threat = [{'pos': (0.405, 0.60), 'kind': 'fight'}]
        inside = safe_back_path(trail, (0.405, 0.60), (0.42, 0.60),
                                danger_points=threat)
        self.assertTrue(inside['waypoints'])
        with self.assertRaises(NoSafePath):
            safe_back_path(trail, (0.42, 0.60), (0.40, 0.60), danger_points=threat)

    def test_a_zone_beside_the_character_does_not_cut_it_off(self):
        trail = make_trail([(0.405, 0.585), (0.405, 0.600), (0.405, 0.615), (0.405, 0.630)])
        threat = [{'pos': (0.405, 0.615), 'kind': 'fight'}]
        # The character stands below the zone, the point it wants is above it.
        with self.assertRaises(NoSafePath):
            safe_back_path(trail, (0.405, 0.600), (0.405, 0.630), danger_points=threat)
        # The caller names the zone of the fight the character is leaving.
        leaving = safe_back_path(trail, (0.405, 0.600), (0.405, 0.630),
                                 danger_points=threat, occupied_zones=threat)
        self.assertTrue(leaving['waypoints'])

    def test_sampled_gap_and_position_jump_are_not_walked_edges(self):
        trail = road_trail()
        edges = classify_edges(trail)
        teleports = [edge for edge in edges if edge['kind'] != 'walk']
        self.assertTrue(teleports)
        for edge in teleports:
            self.assertIn(edge['reason'], ('position_jump', 'sampled_gap'))
        jump = classify_edges(make_trail([ANCHOR, (0.60, 0.70)]))
        self.assertEqual(jump[0]['kind'], 'teleport')
        self.assertEqual(jump[0]['reason'], 'position_jump')

    def test_a_long_pause_at_the_same_place_keeps_the_chain_connected(self):
        trail = [{'pos': [0.40, 0.60], 'time': 0.0},
                 {'pos': [0.40, 0.60], 'time': 300.0},
                 {'pos': [0.42, 0.60], 'time': 300.3}]
        edges = classify_edges(trail)
        self.assertEqual(edges[0]['kind'], 'walk')
        self.assertEqual(edges[0]['reason'], 'stationary_pause')
        result = safe_back_path(trail, (0.42, 0.60), (0.40, 0.60))
        self.assertTrue(result['waypoints'])

    def test_threat_next_to_a_leg_is_found_without_its_end_points(self):
        edges = classify_edges(make_trail([(0.40, 0.60), (0.40, 0.70)]))
        mark_danger(edges, [{'pos': (0.40, 0.65), 'kind': 'combat'}], danger_radius=0.004)
        self.assertTrue(edges[0]['danger'])
        self.assertEqual(edges[0]['danger_reason'], 'combat')

    def test_distance_of_a_point_to_a_segment(self):
        self.assertAlmostEqual(point_segment_distance((0.0, 0.05), (0.0, 0.0), (0.0, 0.1)), 0.0)
        self.assertAlmostEqual(point_segment_distance((0.05, 0.05), (0.0, 0.0), (0.0, 0.1)), 0.05)
        self.assertAlmostEqual(point_segment_distance((0.0, 0.2), (0.0, 0.0), (0.0, 0.1)), 0.1)

    def test_danger_points_of_a_report_are_collected_once(self):
        report = {'fights': [{'before': {'pos_x': 0.1, 'pos_y': 0.2}, 'samples': [
            {'pos_x': 0.1, 'pos_y': 0.2, 'combat': True}]}],
            'samples': [{'pos_x': 0.5, 'pos_y': 0.6, 'dead': True},
                        {'pos_x': 0.3, 'pos_y': 0.4, 'combat': True}]}
        points = danger_points_from_report(report)
        kinds = sorted(point['kind'] for point in points)
        self.assertEqual(kinds, ['combat', 'death', 'fight'])


@unittest.skipUnless((CACHE / 'wolf_v2_trail.json').exists(),
                     'the recorded trail of 2026-11-13 is not available')
class RecordedRunTests(unittest.TestCase):
    """The counterexample of the real run, not only of a synthetic trail."""

    def setUp(self):
        self.trail = json.loads((CACHE / 'wolf_v2_trail.json').read_text(encoding='utf-8'))
        self.points = json.loads((CACHE / 'wolf_v2_points.json').read_text(encoding='utf-8'))
        self.report = json.loads((CACHE / 'wolf_v2_report.json').read_text(encoding='utf-8'))
        self.recovery = json.loads((CACHE / 'wolf_recovery_report.json').read_text(encoding='utf-8'))
        self.road6 = next(point for point in self.points if point['id'] == 'road6')
        self.threats = danger_points_from_report(self.report) + \
            danger_points_from_report(self.recovery)

    def test_retired_path_of_the_real_run_crosses_the_fight_area(self):
        summary = analyse(self.trail, self.trail[-1]['pos'], self.road6['pos'],
                          self.threats, target_index=self.road6['trail_index'])
        self.assertGreaterEqual(summary['legacy']['danger_hits'], 1)
        self.assertGreaterEqual(summary['legacy']['invented_legs'], 1)
        self.assertGreaterEqual(summary['legacy']['repeated_nodes'], 10)

    def test_the_real_run_has_no_safe_route_back_to_the_anchor(self):
        with self.assertRaises(NoSafePath):
            safe_back_path(self.trail, self.trail[-1]['pos'],
                           self.trail[0]['pos'], danger_points=self.threats)

    def test_the_real_death_position_is_recorded_as_a_threat(self):
        kinds = {point['kind'] for point in self.threats}
        self.assertIn('death', kinds)
        self.assertIn('fight', kinds)


if __name__ == '__main__':
    unittest.main()
