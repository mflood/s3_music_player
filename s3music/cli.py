"""Command line interface: ``scan``, ``buckets`` and ``play``.

The scanning half runs anywhere. ``play`` needs PyQt6, so that import is
deferred -- installing without the GUI extra still gives you a working
scanner rather than an ImportError at startup.
"""

import argparse
import json
import sys
from pathlib import Path

import boto3

from .errors import S3MusicError
from .scanner import S3MusicScanner

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "s3music"


def make_client(profile=None, region=None):
    session = boto3.session.Session(profile_name=profile, region_name=region)
    return session.client("s3")


def format_text(tracks):
    return "\n".join(track.uri for track in tracks)


def format_json(tracks):
    return json.dumps(
        [
            {
                "uri": t.uri,
                "bucket": t.bucket,
                "key": t.key,
                "title": t.title,
                "size": t.size,
                "etag": t.etag,
            }
            for t in tracks
        ],
        indent=2,
    )


def format_m3u(tracks):
    """An extended M3U playlist, which most players will open directly."""
    lines = ["#EXTM3U"]
    for track in tracks:
        lines.append("#EXTINF:-1,%s" % track.title)
        lines.append(track.uri)
    return "\n".join(lines)


FORMATTERS = {"text": format_text, "json": format_json, "m3u": format_m3u}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="s3music", description="Find and play music stored in S3."
    )
    parser.add_argument("--profile", help="AWS profile name")
    parser.add_argument("--region", help="AWS region")
    subparsers = parser.add_subparsers(dest="command", required=True)

    buckets = subparsers.add_parser("buckets", help="list visible buckets")
    buckets.set_defaults(handler=command_buckets)

    scan = subparsers.add_parser("scan", help="list audio files in a bucket")
    scan.add_argument("location", help="bucket name or s3://bucket/prefix")
    scan.add_argument("--prefix", default="", help="restrict to a key prefix")
    scan.add_argument(
        "--format", choices=sorted(FORMATTERS), default="text", help="output format"
    )
    scan.add_argument("--limit", type=int, help="stop after N tracks")
    scan.set_defaults(handler=command_scan)

    play = subparsers.add_parser("play", help="open the player window")
    play.add_argument("location", nargs="?", default="", help="bucket to preload")
    play.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR), help="where downloads are kept"
    )
    play.set_defaults(handler=command_play)

    return parser


def command_buckets(args, client):
    for name in S3MusicScanner(client).list_buckets():
        print(name)
    return 0


def command_scan(args, client):
    scanner = S3MusicScanner(client)
    tracks = []
    for track in scanner.scan(args.location, prefix=args.prefix):
        tracks.append(track)
        if args.limit is not None and len(tracks) >= args.limit:
            break

    if not tracks:
        print("no audio files found", file=sys.stderr)
        return 1

    print(FORMATTERS[args.format](tracks))
    return 0


def command_play(args, client):
    try:
        from .qt.app import run
    except ImportError as exc:
        print(
            "error: the player needs PyQt6 (pip install -r requirements-gui.txt): %s"
            % (exc,),
            file=sys.stderr,
        )
        return 1
    return run(client, args.cache_dir, args.location)


def main(argv=None, client_factory=make_client):
    args = build_parser().parse_args(argv)
    try:
        client = client_factory(profile=args.profile, region=args.region)
        return args.handler(args, client)
    except S3MusicError as exc:
        print("error: %s" % (exc,), file=sys.stderr)
        return 1
