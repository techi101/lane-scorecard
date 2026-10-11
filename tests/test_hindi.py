import unicodedata

import pytest

from app.guide import build, classify, items_from_text
from test_workflow import client, floor, record  # noqa: F401


@pytest.mark.parametrize('hindi,english', [
    ('दूध', 'milk'), ('केले', 'banana'), ('सैनिटरी पैड', 'sanitary pad'),
    ('बैटरी', 'battery'), ('चायपत्ती', 'tea'), ('अंडे', 'egg'),
    ('प्याज़', 'onion'), ('डेयरी मिल्क चॉकलेट', 'dairy milk chocolate'),
    ('आटा', 'atta'), ('दवाई', 'medicine'), ('साबुन', 'soap'),
])
def test_hindi_names_use_the_same_reviewed_rules(hindi, english):
    expected = classify(english)['parts']
    for form in ('NFC', 'NFD'):
        result = classify(unicodedata.normalize(form, hindi))
        assert result['source'] == 'rule'
        assert result['parts'] == expected


def test_hindi_receipt_amounts_and_word_boundaries():
    names = items_from_text('दूध ५०० मिलीलीटर\nकेले १ किलो\nबैटरी २ पीस\nकुल १००\nजीएसटी ५%')
    assert names == ['दूध', 'केले', 'बैटरी']
    assert build(names)['unknown'] == 0
    assert classify('आमदनी')['source'] == 'unknown'
    assert classify('घीया')['source'] == 'unknown'


def test_hindi_weekly_plan_and_report(client):
    fid = floor(client, name='पुस्तकालय <入口>')
    record(client, fid, bio='mixed', nonbio='clean', issues=['plastic_in_wet'], note='PRIVATE NOTE')
    action = client.get('/api/pilot/dashboard').json()['actions'][0]
    assert 'डिब्बों' in action['title_hi']
    assert 'प्लास्टिक' in action['evidence_hi']
    report = client.get('/api/pilot/report.html?lang=hi').text
    assert '<html lang="hi">' in report
    for text in ('वास्तविक पायलट निरीक्षण', 'परिसर का स्कोर', 'जगह के अनुसार निरीक्षण', action['title_hi'], action['evidence_hi']):
        assert text in report
    assert 'पुस्तकालय &lt;入口&gt;' in report
    assert 'PRIVATE NOTE' not in report
    assert 'Observations by location' not in report
    english = client.get('/api/pilot/report.html?lang=en').text
    assert 'REAL PILOT OBSERVATIONS' in english and action['title'] in english
