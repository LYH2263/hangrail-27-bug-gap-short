from app.services.rail_engine import Segment, first_fit, free_gaps


def test_first_fit_leftmost():
    occ = [Segment(20, 40)]
    p = first_fit(100, occ, 15)
    assert p is not None
    assert p.start_cm == 0
    assert p.end_cm == 15


def test_first_fit_skips_too_small_gap():
    occ = [Segment(0, 10), Segment(18, 50)]
    p = first_fit(100, occ, 10)
    assert p is not None
    assert p.start_cm == 50


def test_no_space():
    occ = [Segment(0, 80)]
    assert first_fit(100, occ, 25) is None


def test_free_gaps_edges():
    gaps = free_gaps(50, [Segment(10, 20), Segment(30, 35)])
    assert gaps == [Segment(0, 10), Segment(20, 30), Segment(35, 50)]


# —— 间隔缓冲 ——


def test_no_buffer_allows_edge_to_edge():
    # 无缓冲：可贴 0 起挂，也可贴满连续空隙（现网行为不变）
    assert first_fit(100, [], 100, buffer_cm=0).start_cm == 0
    p = first_fit(100, [Segment(0, 40)], 60, buffer_cm=0)
    assert p is not None
    assert p.start_cm == 40  # 贴边，无需留白
    assert p.end_cm == 100
    # 两件衣物中间的空隙也可贴边填满
    p = first_fit(100, [Segment(0, 40), Segment(90, 100)], 50, buffer_cm=0)
    assert p is not None
    assert (p.start_cm, p.end_cm) == (40, 90)


def test_buffer_pushes_start_past_prev_end_plus_buffer():
    # 有缓冲：起点至少离开前衣 end + 登记缓冲（不是写死的 1cm）
    p = first_fit(100, [Segment(0, 40)], 50, buffer_cm=5)
    assert p is not None
    assert p.start_cm == 45
    assert p.end_cm == 95


def test_buffer_value_is_honored_not_clipped_to_one_cm():
    # 登记 8cm 就必须真留 8cm
    p = first_fit(100, [Segment(0, 40)], 30, buffer_cm=8)
    assert p is not None
    assert p.start_cm == 48
    assert p.start_cm - 40 == 8


def test_buffer_also_counts_before_next_garment():
    # 两侧都有衣物时，缓冲在两边都计入占用：
    # 空隙 [40,95] 长 55，缓冲 5 时可用长度仅 45。
    occ = [Segment(0, 40), Segment(95, 100)]
    assert first_fit(100, occ, 50, buffer_cm=0) is not None
    assert first_fit(100, occ, 46, buffer_cm=5) is None
    # 恰好 45 可入：落在 [45,90]，与两边各留 5cm
    p = first_fit(100, occ, 45, buffer_cm=5)
    assert p is not None
    assert (p.start_cm, p.end_cm) == (45, 90)


def test_new_garment_never_touches_next_garment():
    # 回归：再挂一件时不得贴死「后一件」，净距必须 ≥ 登记缓冲
    occ = [Segment(0, 40), Segment(90, 100)]  # 空隙 [40,90]
    p = first_fit(100, occ, 40, buffer_cm=5)
    assert p is not None
    assert p.end_cm == 85
    assert 90 - p.end_cm == 5


def test_buffer_not_required_at_rail_ends():
    # 杆端无相邻衣物，不留缓冲：可贴 0 起挂、可顶到杆尾
    p = first_fit(100, [Segment(50, 100)], 45, buffer_cm=5)
    assert p is not None
    assert p.start_cm == 0
    p = first_fit(100, [Segment(0, 50)], 45, buffer_cm=5)
    assert p is not None
    assert p.end_cm == 100


def test_buffer_blocks_exact_fit_gap():
    # 恰好等长的空隙：无缓冲可贴边挂满，有缓冲则失败
    occ = [Segment(0, 40), Segment(90, 100)]  # 空隙 [40,90] 长 50
    assert first_fit(100, occ, 50, buffer_cm=0) is not None
    # 两侧各扣 5cm 后仅剩 40cm：49cm 挂不下
    assert first_fit(100, occ, 49, buffer_cm=5) is None
    # 40cm 恰好挂入，与两侧各留 5cm
    p = first_fit(100, occ, 40, buffer_cm=5)
    assert p is not None
    assert (p.start_cm, p.end_cm) == (45, 85)


def test_buffer_moves_placement_to_later_gap():
    # 种子场景：A 杆缓冲 5，[0,45] [50,85] [115,155]
    occ = [Segment(0, 45), Segment(50, 85), Segment(115, 155)]
    # 无缓冲：30cm 贴边挂入恰好等长的 [85,115]
    p = first_fit(200, occ, 30, buffer_cm=0)
    assert p is not None
    assert p.start_cm == 85
    # 有缓冲：[85,115] 两侧各扣 5 后不可用，改挂杆尾空隙 160 起
    p = first_fit(200, occ, 30, buffer_cm=5)
    assert p is not None
    assert p.start_cm == 160
    assert p.end_cm == 190


def test_release_reopens_gap_with_buffer_rules():
    # 取件释放后，空隙按缓冲规则重新可入
    occ = [Segment(0, 45), Segment(50, 85), Segment(115, 155)]
    assert first_fit(200, occ, 30, buffer_cm=5).start_cm == 160
    released = [Segment(0, 45), Segment(115, 155)]  # 取走 [50,85]
    p = first_fit(200, released, 30, buffer_cm=5)
    assert p is not None
    # 并入后的空隙 [45,115] 两侧均有衣物，各留 5cm：50 起
    assert p.start_cm == 50
    assert p.end_cm == 80


def test_preexisting_short_gap_is_never_reused_below_buffer():
    # 历史数据/改缓冲前已留下的短空档（仅 2cm），新上杆不得贴入；
    # 缓冲规则对释放后的空隙一视同仁。
    occ = [Segment(0, 40), Segment(42, 82)]  # 40 与 42 间只有 2cm
    # 30cm 衣物只能落到后衣之后，且与其留足 5cm
    p = first_fit(100, occ, 10, buffer_cm=5)
    assert p is not None
    assert p.start_cm == 87
