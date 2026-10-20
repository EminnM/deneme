from kaldirim.geometry import CountRule, ground_point, point_in_polygon, segments_cross


def test_segments_cross():
    assert segments_cross((0, 0), (2, 2), (0, 2), (2, 0))
    assert not segments_cross((0, 0), (1, 1), (2, 2), (3, 3))
    assert segments_cross((0, 0), (2, 0), (1, -1), (1, 1))


def test_point_in_polygon():
    sq = [(0, 0), (4, 0), (4, 4), (0, 4)]
    assert point_in_polygon((2, 2), sq)
    assert not point_in_polygon((5, 2), sq)


def test_ground_point():
    assert ground_point((10, 20, 30, 60)) == (20, 60)


def test_gate_counts_once_per_crossing():
    r = CountRule("gate", gate=[(0, 10), (100, 10)], cooldown_s=2.0)
    pts = [(50, 0), (50, 5), (50, 12), (50, 20), (50, 30)]
    hits = [r.update(7, p, t) for t, p in enumerate(pts)]
    assert hits == [None, None, "gate", None, None]


def test_gate_recounts_after_cooldown_for_new_crossing():
    r = CountRule("gate", gate=[(0, 10), (100, 10)], cooldown_s=1.0)
    assert r.update(1, (50, 0), 0.0) is None
    assert r.update(1, (50, 20), 0.5) == "gate"
    assert r.update(1, (50, 0), 0.9) is None      # inside cooldown, ignored
    assert r.update(1, (50, 20), 5.0) == "gate"   # a genuine second crossing later


def test_zone_needs_consecutive_frames():
    z = [(0, 0), (10, 0), (10, 10), (0, 10)]
    r = CountRule("zone", zone=z, min_frames=3)
    seq = [(5, 5), (5, 5), (20, 20), (5, 5), (5, 5), (5, 5), (5, 5)]
    hits = [r.update(3, p, t) for t, p in enumerate(seq)]
    assert hits == [None, None, None, None, None, "zone", None]


def test_low_fps_crossing_still_detected():
    # at 2 fps a rider jumps 30 px between frames; the segment still crosses the gate
    r = CountRule("gate", gate=[(0, 100), (640, 90)])
    assert r.update(9, (300, 70), 0.0) is None
    assert r.update(9, (320, 130), 0.5) == "gate"


def test_auto_crop_clamps_to_frame():
    from kaldirim.geometry import auto_crop
    assert auto_crop([(100, 400), (500, 380)], 1600, 1200, 160) == (0, 220, 660, 340)
    assert auto_crop([(1500, 1100), (1590, 1190)], 1600, 1200, 160) == (1340, 940, 260, 260)


def test_named_gates_report_which_one():
    r = CountRule("gate", gates=[{"name": "far", "points": [(0, 100), (200, 100)]},
                                 {"name": "near", "points": [(0, 500), (200, 500)]}])
    assert r.update(1, (50, 90), 0.0) is None and r.update(1, (50, 110), 0.5) == "far"
    assert r.update(2, (50, 490), 0.0) is None and r.update(2, (50, 510), 0.5) == "near"
    assert sorted(r.all_points()) == [(0, 100), (0, 500), (200, 100), (200, 500)]
