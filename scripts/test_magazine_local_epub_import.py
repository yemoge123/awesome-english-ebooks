import hashlib
import pytest

from magazine_local_epub_import import git_blob_sha1, validate_local_source


def test_git_blob_sha1_matches_git_object_format():
    data = b"hello\n"
    expected = hashlib.sha1(b"blob 6\0hello\n").hexdigest()
    assert git_blob_sha1(data) == expected


def test_validate_local_source_accepts_exact_blob_identity():
    data = b"epub-bytes"
    sha = git_blob_sha1(data)
    path, actual = validate_local_source(
        publication="economist",
        source_file="01_economist/te_2026.09.26/TheEconomist.2026.09.26.epub",
        data=data,
        expected_source_sha=sha,
        expected_size=len(data),
    )
    assert path.endswith("TheEconomist.2026.09.26.epub")
    assert actual == sha


def test_validate_local_source_rejects_wrong_blob_sha():
    with pytest.raises(RuntimeError, match="Git blob SHA mismatch"):
        validate_local_source(
            publication="new_yorker",
            source_file="02_new_yorker/2026.09.28/new_yorker.2026.09.28.epub",
            data=b"epub-bytes",
            expected_source_sha="0" * 40,
        )


def test_validate_local_source_rejects_wrong_root():
    data = b"epub-bytes"
    with pytest.raises(RuntimeError, match="outside authorized root"):
        validate_local_source(
            publication="wired",
            source_file="01_economist/te_2026.09.26/TheEconomist.2026.09.26.epub",
            data=data,
            expected_source_sha=git_blob_sha1(data),
        )
