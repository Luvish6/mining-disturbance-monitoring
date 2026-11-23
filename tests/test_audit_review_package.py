import json
import zipfile

import pytest
from scripts.audit_review_package import validate_archive, validate_s2_metadata


def fixture(tmp_path):
    chips = tmp_path / 'chips'; chips.mkdir()
    (chips / 'R12345678.png').write_bytes(b'verified Sentinel render')
    return chips


def write_zip(path, png=b'verified Sentinel render', extra=None, html='<img src="chips10/R12345678.png">'):
    with zipfile.ZipFile(path, 'w') as z:
        for name, value in {'chips10/R12345678.png': png, 'README.txt': 'Sentinel-2',
                            'review_B.html': html, 'review_sheet_B.csv': 'review_id'}.items():
            z.writestr(name, value)
        if extra:
            z.writestr(extra, 'restricted')


def test_package_rejects_extra_raw_asset_and_renamed_pixels(tmp_path):
    chips = fixture(tmp_path); archive = tmp_path / 'review.zip'
    write_zip(archive)
    assert len(validate_archive(archive, chips, ['R12345678'])) == 1
    write_zip(archive, extra='planet.tif')
    with pytest.raises(ValueError): validate_archive(archive, chips, ['R12345678'])
    write_zip(archive, png=b'other image')
    with pytest.raises(ValueError): validate_archive(archive, chips, ['R12345678'])


def test_package_rejects_private_viewer_link(tmp_path):
    chips = fixture(tmp_path); archive = tmp_path / 'review.zip'
    write_zip(archive, html='<img src="http://127.0.0.1:5188/__planet_review__/rgb-0.png">')
    with pytest.raises(ValueError): validate_archive(archive, chips, ['R12345678'])


def test_metadata_requires_all_sentinel_seasons():
    record = {s: {'ids': ['20241101T042931_20241101T043513_T46RCN']} for s in ['before','after','follow']}
    validate_s2_metadata({'R12345678': record}, ['R12345678'])
    record['before']['ids'] = ['20240308_034150_36_24bf']
    with pytest.raises(ValueError): validate_s2_metadata({'R12345678': record}, ['R12345678'])
