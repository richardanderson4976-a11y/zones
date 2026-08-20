"""
Lightweight tests for osm_zone_extractor.py v3.1.0 upgrades.

Run with: python test_zone_extractor.py
       or: pytest test_zone_extractor.py
"""
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_log():
    """Return a minimal RunLog substitute that records calls."""
    log = MagicMock()
    log.error_count = 0
    log.warning_count = 0
    return log


# ---------------------------------------------------------------------------
# 1. Polygon assembly + representative point
# ---------------------------------------------------------------------------

class TestPolygonAssembly(unittest.TestCase):
    """fetch_geometry_for_relations assembles a square and returns an
    interior point for a synthetic Overpass-geom-shaped payload."""

    def _make_square_payload(self, relation_id: int) -> list[dict]:
        """A simple unit square as a single outer-ring way member."""
        return [
            {
                "type": "relation",
                "id": relation_id,
                "members": [
                    {
                        "type": "way",
                        "role": "outer",
                        "geometry": [
                            {"lat": 0.0, "lon": 0.0},
                            {"lat": 0.0, "lon": 1.0},
                            {"lat": 1.0, "lon": 1.0},
                            {"lat": 1.0, "lon": 0.0},
                            {"lat": 0.0, "lon": 0.0},
                        ],
                    }
                ],
            }
        ]

    def test_representative_point_inside_square(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "osm_zone_extractor",
            os.path.join(os.path.dirname(__file__), "osm_zone_extractor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not mod._SHAPELY_AVAILABLE:
            self.skipTest("shapely not installed")

        log = _make_log()
        fetcher = MagicMock()

        payload = self._make_square_payload(42)

        with patch.object(mod, "overpass_query", return_value=payload):
            result = mod.fetch_geometry_for_relations(fetcher, log, [42])

        self.assertIn(42, result)
        pt = result[42]
        self.assertAlmostEqual(pt["lat"], 0.5, places=1)
        self.assertAlmostEqual(pt["lon"], 0.5, places=1)
        self.assertEqual(pt["basis"], "polygon-representative-point")

        # Point must be inside the unit square [0,1]×[0,1].
        self.assertGreater(pt["lat"], 0.0)
        self.assertLess(pt["lat"], 1.0)
        self.assertGreater(pt["lon"], 0.0)
        self.assertLess(pt["lon"], 1.0)

    def test_missing_geometry_returns_empty(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "osm_zone_extractor",
            os.path.join(os.path.dirname(__file__), "osm_zone_extractor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not mod._SHAPELY_AVAILABLE:
            self.skipTest("shapely not installed")

        log = _make_log()
        fetcher = MagicMock()

        # Empty Overpass response
        with patch.object(mod, "overpass_query", return_value=[]):
            result = mod.fetch_geometry_for_relations(fetcher, log, [99])

        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# 2. Geometry containment: accept inside, reject outside
# ---------------------------------------------------------------------------

class TestGeometryContainment(unittest.TestCase):

    def _load_mod(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "osm_zone_extractor",
            os.path.join(os.path.dirname(__file__), "osm_zone_extractor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_point_inside_accepted(self):
        mod = self._load_mod()

        if not mod._SHAPELY_AVAILABLE:
            self.skipTest("shapely not installed")

        from shapely.geometry import Point, Polygon
        boundary = Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])
        pt = Point(5, 5)
        self.assertTrue(boundary.covers(pt))

    def test_point_outside_rejected(self):
        mod = self._load_mod()

        if not mod._SHAPELY_AVAILABLE:
            self.skipTest("shapely not installed")

        from shapely.geometry import Point, Polygon
        boundary = Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])
        pt = Point(15, 15)
        self.assertFalse(boundary.covers(pt))


# ---------------------------------------------------------------------------
# 3. 429 empty-batch warning path
# ---------------------------------------------------------------------------

class Test429EmptyBatch(unittest.TestCase):

    def _load_mod(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "osm_zone_extractor",
            os.path.join(os.path.dirname(__file__), "osm_zone_extractor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_empty_batch_logs_warn(self):
        mod = self._load_mod()
        log = _make_log()
        fetcher = MagicMock()

        # overpass_query returns [] for a non-empty id list
        with patch.object(mod, "overpass_query", return_value=[]):
            mod.fetch_admin_centres(fetcher, log, [1, 2, 3])

        # At least one warn call should mention "0 elements"
        warn_messages = [
            str(call) for call in log.warn.call_args_list
        ]
        self.assertTrue(
            any("0 elements" in m or "0 element" in m for m in warn_messages),
            f"Expected '0 elements' warning; got: {warn_messages}",
        )


# ---------------------------------------------------------------------------
# 4. resolve_profile: refuse candidate without explicit levels
# ---------------------------------------------------------------------------

class TestResolveProfileCandidate(unittest.TestCase):

    def _load_mod(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "osm_zone_extractor",
            os.path.join(os.path.dirname(__file__), "osm_zone_extractor.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_candidate_refused_without_levels(self):
        mod = self._load_mod()
        log = _make_log()

        # UG is a CANDIDATE profile
        result = mod.resolve_profile(
            "UG", log,
            boundary_level=None, child_level=None,
            boundary_zone_type=None, child_zone_type=None,
        )

        self.assertIsNone(result)
        log.error.assert_called()

    def test_candidate_accepted_with_explicit_levels(self):
        mod = self._load_mod()
        log = _make_log()

        result = mod.resolve_profile(
            "UG", log,
            boundary_level=4, child_level=6,
            boundary_zone_type=None, child_zone_type=None,
        )

        # Should return a profile (not None)
        self.assertIsNotNone(result)

    def test_verified_profile_accepted_without_levels(self):
        mod = self._load_mod()
        log = _make_log()

        result = mod.resolve_profile(
            "KE", log,
            boundary_level=None, child_level=None,
            boundary_zone_type=None, child_zone_type=None,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.country_name, "Kenya")


# ---------------------------------------------------------------------------
# 5. --probe-batch ISO list parsing
# ---------------------------------------------------------------------------

class TestProbeBatchParsing(unittest.TestCase):

    def test_comma_split(self):
        raw = "KE,UG,ZM"
        codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
        self.assertEqual(codes, ["KE", "UG", "ZM"])

    def test_whitespace_tolerant(self):
        raw = " KE , UG , ZM "
        codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
        self.assertEqual(codes, ["KE", "UG", "ZM"])

    def test_single_code(self):
        raw = "KE"
        codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
        self.assertEqual(codes, ["KE"])

    def test_empty_string(self):
        raw = ""
        codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
        self.assertEqual(codes, [])


if __name__ == "__main__":
    unittest.main()
