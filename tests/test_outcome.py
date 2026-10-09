from app.actions import check_values, outcome


def floor(score):
    return {"score": score}


STEADY_LOW = [60, 60, 60, 60, 60]
STEADY_HIGH = [80, 80, 80, 80, 80]
NOISY = [0, 100, 0, 100, 50, 100, 0]


def test_clear_change_is_reported():
    assert outcome(floor(80), floor(60), STEADY_HIGH, STEADY_LOW)["status"] == "improved"
    assert outcome(floor(60), floor(80), STEADY_LOW, STEADY_HIGH)["status"] == "worse"


def test_small_move_is_not_a_change():
    result = outcome(floor(64), floor(60), [64] * 5, [60] * 5)
    assert result["status"] == "no_clear_change" and result["delta"] == 4.0


def test_noisy_weeks_do_not_claim_a_change():
    # A 20-point drop is within chance when daily checks swing between 0 and 100.
    assert outcome(floor(50), floor(70), NOISY, NOISY)["status"] == "no_clear_change"


def test_too_few_checks_is_explicit():
    assert outcome(floor(80), floor(60), [80, 80], STEADY_LOW)["status"] == "too_few_checks"


def test_no_baseline_when_last_week_missing():
    assert outcome(floor(70), None, STEADY_HIGH)["status"] == "no_baseline"
    assert outcome(floor(70), floor(None), STEADY_HIGH)["status"] == "no_baseline"


def test_no_claim_without_current_score():
    assert outcome(floor(None), floor(60))["status"] == "insufficient_data"


def test_check_values_use_only_checks_with_both_bins_seen():
    rows = [{"bio": "clean", "nonbio": "unseen"}, {"bio": "unseen", "nonbio": "unseen"}, {"bio": "few", "nonbio": "mixed"}]
    assert check_values(rows) == [25]


def test_one_bin_checks_never_produce_a_claim():
    # Codex's counterexample: both weeks show a floor score of 50, but from different bins.
    week_a = [{"bio": "clean", "nonbio": "unseen"}] + [{"bio": "unseen", "nonbio": "mixed"}] * 3
    week_b = [{"bio": "clean", "nonbio": "unseen"}] * 3 + [{"bio": "unseen", "nonbio": "mixed"}]
    result = outcome(floor(50), floor(50), check_values(week_b), check_values(week_a))
    assert result["status"] == "too_few_checks" and result["compared_checks"] == [0, 0]


def test_judgement_and_noise_use_the_same_values():
    result = outcome(floor(70), floor(60), STEADY_HIGH, STEADY_LOW)
    assert result["change"] == 20.0 and result["noise"] == 0.0 and result["delta"] == 10.0
