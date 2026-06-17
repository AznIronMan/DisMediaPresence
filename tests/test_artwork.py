from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dis_music_presence.artwork import ArtworkAsset, ArtworkManager, UploadedArtwork
from dis_music_presence.artwork import _best_catalog_result, _resize_apple_artwork_url
from dis_music_presence.artwork import _plex_image_path
from dis_music_presence.artwork import _tmpfiles_direct_url, _tmpfiles_image_url
from dis_music_presence.models import ActivityKind, MediaActivity, MediaType
from dis_music_presence.settings import DEFAULT_SETTINGS, Settings


def _settings(**overrides: str) -> Settings:
    values = dict(DEFAULT_SETTINGS)
    values.update(overrides)
    return Settings(path=Path("dmp.settings"), values=values)


def _activity() -> MediaActivity:
    return MediaActivity(
        kind=ActivityKind.LISTENING,
        source="Apple Music",
        media_type=MediaType.MUSIC,
        title="Song",
        artist="Artist",
        album="Album",
    )


class FakeFilebinClient:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []
        self.deletes: list[UploadedArtwork] = []

    def upload(self, **kwargs: object) -> UploadedArtwork:
        self.uploads.append(kwargs)
        return UploadedArtwork(
            image_url=f"https://filebin.test/{kwargs['bin_name']}/{kwargs['filename']}",
            image_text=str(kwargs["image_text"]),
            bin_name=str(kwargs["bin_name"]),
            filename=str(kwargs["filename"]),
            sha256=str(kwargs["sha256"]),
            delete_bin=bool(kwargs["delete_bin"]),
        )

    def delete(self, upload: UploadedArtwork) -> None:
        self.deletes.append(upload)


class FakeTmpfilesClient:
    def __init__(self) -> None:
        self.uploads: list[dict[str, object]] = []

    def upload(self, **kwargs: object) -> UploadedArtwork:
        self.uploads.append(kwargs)
        return UploadedArtwork(
            image_url=f"https://tmpfiles.test/dl/{kwargs['filename']}",
            image_text=str(kwargs["image_text"]),
            filename=str(kwargs["filename"]),
            sha256=str(kwargs["sha256"]),
        )


class FakeAppleCatalogClient:
    def __init__(self, result: ArtworkAsset | None = None) -> None:
        self.result = result
        self.lookups: list[dict[str, object]] = []

    def lookup(self, **kwargs: object) -> ArtworkAsset | None:
        self.lookups.append(kwargs)
        return self.result


class FakeAppleMusicArtworkExporter:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.exports: list[dict[str, object]] = []

    def export(self, activity: MediaActivity, timeout_seconds: int) -> Path | None:
        self.exports.append({"activity": activity, "timeout_seconds": timeout_seconds})
        return self.path


class FakePlexArtworkFetcher:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.exports: list[dict[str, object]] = []

    def export(self, activity: MediaActivity, settings: Settings) -> Path | None:
        self.exports.append({"activity": activity, "settings": settings})
        return self.path


def _plex_activity() -> MediaActivity:
    return MediaActivity(
        kind=ActivityKind.WATCHING,
        source="Plex",
        media_type=MediaType.MOVIE,
        title="Movie",
        player_state="playing",
        raw={"thumb": "/library/metadata/1/thumb/2", "art": "/library/metadata/1/art/2"},
    )


class ArtworkManagerTests(unittest.TestCase):
    def test_tmpfiles_default_does_nothing_without_artwork(self) -> None:
        tmpfiles = FakeTmpfilesClient()
        catalog = FakeAppleCatalogClient()
        exporter = FakeAppleMusicArtworkExporter()
        manager = ArtworkManager(
            _settings(),
            tmpfiles_client=tmpfiles,
            apple_catalog_client=catalog,
            apple_music_artwork_exporter=exporter,
        )

        artwork = manager.resolve(_activity())

        self.assertIsNone(artwork)
        self.assertEqual(tmpfiles.uploads, [])
        self.assertEqual(len(catalog.lookups), 1)
        self.assertEqual(len(exporter.exports), 1)

    def test_tmpfiles_default_uploads_current_apple_music_artwork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.img"
            path.write_bytes(b"\x89PNG\r\n\x1a\npng-bytes")
            tmpfiles = FakeTmpfilesClient()
            catalog = FakeAppleCatalogClient(ArtworkAsset("https://is1-ssl.mzstatic.com/image.jpg", "Album - Artist"))
            exporter = FakeAppleMusicArtworkExporter(path)
            manager = ArtworkManager(
                _settings(),
                tmpfiles_client=tmpfiles,
                apple_catalog_client=catalog,
                apple_music_artwork_exporter=exporter,
            )

            artwork = manager.resolve(_activity())

            self.assertEqual(len(tmpfiles.uploads), 1)
            self.assertEqual(
                artwork.image_url,
                f"https://tmpfiles.test/dl/{tmpfiles.uploads[0]['filename']}",
            )
            self.assertEqual(tmpfiles.uploads[0]["content_type"], "image/png")
            self.assertTrue(str(tmpfiles.uploads[0]["filename"]).endswith(".png"))
            self.assertEqual(catalog.lookups, [])
            self.assertFalse(path.exists())

    def test_tmpfiles_default_uploads_plex_artwork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "poster.img"
            path.write_bytes(b"\xff\xd8\xffjpeg-bytes")
            tmpfiles = FakeTmpfilesClient()
            plex = FakePlexArtworkFetcher(path)
            manager = ArtworkManager(
                _settings(),
                tmpfiles_client=tmpfiles,
                apple_catalog_client=FakeAppleCatalogClient(),
                apple_music_artwork_exporter=FakeAppleMusicArtworkExporter(),
                plex_artwork_fetcher=plex,
            )

            artwork = manager.resolve(_plex_activity())

            self.assertEqual(len(tmpfiles.uploads), 1)
            self.assertEqual(artwork.image_url, f"https://tmpfiles.test/dl/{tmpfiles.uploads[0]['filename']}")
            self.assertEqual(tmpfiles.uploads[0]["content_type"], "image/jpeg")
            self.assertTrue(str(tmpfiles.uploads[0]["filename"]).endswith(".jpg"))
            self.assertEqual(len(plex.exports), 1)
            self.assertFalse(path.exists())

    def test_tmpfiles_default_reuses_current_apple_music_artwork_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.img"
            path.write_bytes(b"\x89PNG\r\n\x1a\npng-bytes")
            tmpfiles = FakeTmpfilesClient()
            exporter = FakeAppleMusicArtworkExporter(path)
            manager = ArtworkManager(
                _settings(),
                tmpfiles_client=tmpfiles,
                apple_catalog_client=FakeAppleCatalogClient(),
                apple_music_artwork_exporter=exporter,
            )

            first = manager.resolve(_activity())
            second = manager.resolve(_activity())

            self.assertEqual(first, second)
            self.assertEqual(len(tmpfiles.uploads), 1)
            self.assertEqual(len(exporter.exports), 1)

    def test_tmpfiles_default_falls_back_to_apple_catalog(self) -> None:
        tmpfiles = FakeTmpfilesClient()
        catalog = FakeAppleCatalogClient(ArtworkAsset("https://is1-ssl.mzstatic.com/image.jpg", "Album - Artist"))
        manager = ArtworkManager(
            _settings(),
            tmpfiles_client=tmpfiles,
            apple_catalog_client=catalog,
            apple_music_artwork_exporter=FakeAppleMusicArtworkExporter(),
        )

        artwork = manager.resolve(_activity())

        self.assertEqual(artwork.image_url, "https://is1-ssl.mzstatic.com/image.jpg")
        self.assertEqual(tmpfiles.uploads, [])
        self.assertEqual(catalog.lookups[0]["title"], "Song")

    def test_current_apple_music_artwork_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.img"
            path.write_bytes(b"\x89PNG\r\n\x1a\npng-bytes")
            tmpfiles = FakeTmpfilesClient()
            exporter = FakeAppleMusicArtworkExporter(path)
            manager = ArtworkManager(
                _settings(**{"artwork.apple_music.enabled": "false"}),
                tmpfiles_client=tmpfiles,
                apple_catalog_client=FakeAppleCatalogClient(),
                apple_music_artwork_exporter=exporter,
            )

            artwork = manager.resolve(_activity())

            self.assertIsNone(artwork)
            self.assertEqual(tmpfiles.uploads, [])
            self.assertEqual(exporter.exports, [])

    def test_apple_catalog_can_be_used_explicitly(self) -> None:
        catalog = FakeAppleCatalogClient(ArtworkAsset("https://is1-ssl.mzstatic.com/image.jpg", "Album - Artist"))
        manager = ArtworkManager(
            _settings(**{"artwork.provider": "apple_catalog"}),
            apple_catalog_client=catalog,
        )

        artwork = manager.resolve(_activity())

        self.assertEqual(artwork.image_url, "https://is1-ssl.mzstatic.com/image.jpg")

    def test_apple_catalog_can_be_disabled(self) -> None:
        tmpfiles = FakeTmpfilesClient()
        catalog = FakeAppleCatalogClient(ArtworkAsset("https://is1-ssl.mzstatic.com/image.jpg", "Album - Artist"))
        exporter = FakeAppleMusicArtworkExporter()
        manager = ArtworkManager(
            _settings(**{"artwork.apple_catalog.enabled": "false"}),
            tmpfiles_client=tmpfiles,
            apple_catalog_client=catalog,
            apple_music_artwork_exporter=exporter,
        )

        artwork = manager.resolve(_activity())

        self.assertIsNone(artwork)
        self.assertEqual(tmpfiles.uploads, [])
        self.assertEqual(catalog.lookups, [])
        self.assertEqual(len(exporter.exports), 1)

    def test_tmpfiles_upload_response_uses_direct_download_url(self) -> None:
        url = _tmpfiles_image_url(b'{"status":"success","data":{"url":"https://tmpfiles.org/abc/cover.png"}}')

        self.assertEqual(url, "https://tmpfiles.org/dl/abc/cover.png")

    def test_tmpfiles_direct_url_leaves_other_hosts_alone(self) -> None:
        url = _tmpfiles_direct_url("https://example.test/abc/cover.png")

        self.assertEqual(url, "https://example.test/abc/cover.png")

    def test_plex_image_path_uses_configured_field_order(self) -> None:
        activity = MediaActivity(
            kind=ActivityKind.WATCHING,
            source="Plex",
            media_type=MediaType.EPISODE,
            raw={"thumb": "/episode-thumb", "grandparent_thumb": "/show-poster"},
        )

        self.assertEqual(_plex_image_path(activity, ["grandparent_thumb", "thumb"]), "/show-poster")

    def test_plex_image_path_skips_missing_and_invalid_paths(self) -> None:
        activity = MediaActivity(
            kind=ActivityKind.WATCHING,
            source="Plex",
            media_type=MediaType.EPISODE,
            raw={"thumb": "", "grandparent_thumb": "not-a-path", "parent_thumb": "/season-poster", "art": "/fanart"},
        )

        self.assertEqual(_plex_image_path(activity, []), "/season-poster")

    def test_catalog_best_result_ignores_unmatched_results(self) -> None:
        result = _best_catalog_result(
            [{"trackName": "Other", "artistName": "Someone Else", "artworkUrl100": "https://example.test/100x100bb.jpg"}],
            artist="Artist",
            album="Album",
            title="Song",
        )

        self.assertIsNone(result)

    def test_apple_artwork_url_is_resized(self) -> None:
        url = "https://is1-ssl.mzstatic.com/image/thumb/Music/ab/cd/ef/100x100bb.jpg"

        resized = _resize_apple_artwork_url(url, 600)

        self.assertEqual(resized, "https://is1-ssl.mzstatic.com/image/thumb/Music/ab/cd/ef/600x600bb.jpg")

    def test_custom_url_artwork(self) -> None:
        manager = ArtworkManager(
            _settings(
                **{
                    "artwork.provider": "custom_url",
                    "artwork.custom_url": "https://example.test/art.png",
                }
            )
        )

        artwork = manager.resolve(_activity())

        self.assertIsNotNone(artwork)
        self.assertEqual(artwork.image_url, "https://example.test/art.png")
        self.assertEqual(artwork.image_text, "Album - Artist")

    def test_custom_url_does_not_validate_unused_filebin_settings(self) -> None:
        manager = ArtworkManager(
            _settings(
                **{
                    "artwork.provider": "custom_url",
                    "artwork.custom_url": "https://example.test/art.png",
                    "artwork.filebin.base_url": "not-a-url",
                }
            )
        )

        artwork = manager.resolve(_activity())

        self.assertEqual(artwork.image_url, "https://example.test/art.png")

    def test_filebin_upload_reuses_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.png"
            path.write_bytes(b"png-bytes")
            fake = FakeFilebinClient()
            manager = ArtworkManager(
                _settings(
                    **{
                        "artwork.provider": "filebin",
                        "artwork.filebin.path": str(path),
                    }
                ),
                filebin_client=fake,
                apple_catalog_client=FakeAppleCatalogClient(),
            )

            first = manager.resolve(_activity())
            second = manager.resolve(_activity())

            self.assertEqual(first, second)
            self.assertEqual(len(fake.uploads), 1)
            self.assertTrue(fake.uploads[0]["delete_bin"])

    def test_filebin_cleanup_deletes_uploaded_artwork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.jpg"
            path.write_bytes(b"jpg-bytes")
            fake = FakeFilebinClient()
            manager = ArtworkManager(
                _settings(
                    **{
                        "artwork.provider": "filebin",
                        "artwork.filebin.path": str(path),
                        "artwork.filebin.bin": "custom-bin",
                    }
                ),
                filebin_client=fake,
                apple_catalog_client=FakeAppleCatalogClient(),
            )

            manager.resolve(_activity())
            manager.cleanup()

            self.assertEqual(len(fake.deletes), 1)
            self.assertFalse(fake.deletes[0].delete_bin)

    def test_dry_run_does_not_upload_filebin_artwork(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cover.webp"
            path.write_bytes(b"webp-bytes")
            fake = FakeFilebinClient()
            manager = ArtworkManager(
                _settings(
                    **{
                        "artwork.provider": "filebin",
                        "artwork.filebin.path": str(path),
                    }
                ),
                filebin_client=fake,
                apple_catalog_client=FakeAppleCatalogClient(),
                allow_upload=False,
            )

            artwork = manager.resolve(_activity())

            self.assertIsNone(artwork)
            self.assertEqual(fake.uploads, [])


if __name__ == "__main__":
    unittest.main()
