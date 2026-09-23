"""Szenario (mhs_scenario.make_scenario): Determinismus, Struktur der Ladeliste, Randfaelle."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mhs_scenario import make_scenario  # noqa: E402


def test_deterministic_for_the_same_seed():
    a, pa = make_scenario(8, 2, 0)
    b, pb = make_scenario(8, 2, 0)
    assert a == b and pa == pb


def test_different_seeds_usually_differ():
    a, _ = make_scenario(8, 2, 0)
    b, _ = make_scenario(8, 2, 1)
    assert a != b


def test_loads_shape_has_n_ports_entries_last_one_empty():
    loads, peak = make_scenario(6, 3, 0)
    assert len(loads) == 6
    assert loads[-1] == []          # letzter Hafen laedt nichts mehr (keine spaeteren Ziele)


def test_each_port_loads_exactly_volume_containers_except_the_last():
    loads, _ = make_scenario(8, 3, 5)
    for p in range(len(loads) - 1):
        assert len(loads[p]) == 3


def test_destinations_are_always_strictly_later_than_the_loading_port():
    loads, _ = make_scenario(10, 4, 2)
    for p, port_loads in enumerate(loads):
        for d in port_loads:
            assert d > p


def test_peak_occupancy_is_at_least_one_port_volume_and_never_exceeds_total_loaded():
    loads, peak = make_scenario(8, 2, 3)
    total_loaded = sum(len(pl) for pl in loads)
    assert 0 < peak <= total_loaded


def test_max_dest_spread_limits_how_far_destinations_reach():
    loads, _ = make_scenario(10, 3, 0, max_dest_spread=2)
    for p, port_loads in enumerate(loads):
        for d in port_loads:
            assert d <= p + 2


def test_minimal_two_port_route_has_one_loading_port_with_only_destination():
    loads, peak = make_scenario(2, 2, 0)
    assert len(loads) == 2 and loads[1] == []
    assert all(d == 1 for d in loads[0])
    assert peak == len(loads[0])


def test_zero_volume_per_port_yields_empty_route():
    loads, peak = make_scenario(6, 0, 0)
    assert all(pl == [] for pl in loads) and peak == 0
