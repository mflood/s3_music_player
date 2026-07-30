import json

import pytest

from s3music.cli import main


@pytest.fixture
def run(s3):
    """Run the CLI against the mocked S3 client."""

    def invoke(argv):
        return main(argv, client_factory=lambda profile, region: s3)

    return invoke


def test_buckets_lists_names(run, s3, capsys):
    for name in ("beta", "alpha"):
        s3.create_bucket(Bucket=name)

    assert run(["buckets"]) == 0
    assert capsys.readouterr().out.split() == ["alpha", "beta"]


def test_scan_prints_uris(run, populated_bucket, capsys):
    assert run(["scan", populated_bucket]) == 0
    lines = capsys.readouterr().out.strip().splitlines()

    assert len(lines) == 3
    assert all(line.startswith("s3://music/") for line in lines)


def test_scan_json_carries_metadata(run, populated_bucket, capsys):
    assert run(["scan", populated_bucket, "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(payload) == 3
    assert {"uri", "bucket", "key", "title", "size", "etag"} <= set(payload[0])


def test_scan_m3u_is_a_valid_playlist(run, populated_bucket, capsys):
    assert run(["scan", populated_bucket, "--format", "m3u"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()

    assert lines[0] == "#EXTM3U"
    assert lines[1].startswith("#EXTINF:-1,")
    assert lines[2].startswith("s3://")
    assert len(lines) == 1 + 3 * 2


def test_scan_limit_stops_early(run, populated_bucket, capsys):
    assert run(["scan", populated_bucket, "--limit", "2"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 2


def test_scan_prefix_narrows_results(run, populated_bucket, capsys):
    assert run(["scan", populated_bucket, "--prefix", "albums/nested/"]) == 0
    assert capsys.readouterr().out.strip() == "s3://music/albums/nested/three.M4A"


def test_scan_accepts_an_s3_uri(run, populated_bucket, capsys):
    assert run(["scan", "s3://%s/albums/nested" % populated_bucket]) == 0
    assert "three.M4A" in capsys.readouterr().out


def test_scan_with_no_matches_reports_and_exits_nonzero(run, bucket, capsys):
    assert run(["scan", bucket]) == 1
    assert "no audio files found" in capsys.readouterr().err


def test_scan_of_a_missing_bucket_reports_without_a_traceback(run, capsys):
    assert run(["scan", "nope-not-here"]) == 1
    assert "error:" in capsys.readouterr().err


def test_unknown_format_is_rejected_by_the_parser(run, populated_bucket):
    with pytest.raises(SystemExit):
        run(["scan", populated_bucket, "--format", "xspf"])


def test_a_command_is_required(run):
    with pytest.raises(SystemExit):
        run([])
