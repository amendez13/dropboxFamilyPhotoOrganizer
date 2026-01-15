"""Tests for optional provider import handling in face_recognizer module."""

import builtins
import importlib


def test_optional_provider_import_failures(monkeypatch) -> None:
    import scripts.face_recognizer as face_recognizer

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {
            "scripts.face_recognizer.providers.aws_provider",
            "scripts.face_recognizer.providers.azure_provider",
        }:
            raise ImportError("blocked for test")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    reloaded = importlib.reload(face_recognizer)

    assert reloaded.FaceRecognitionFactory.PROVIDERS["aws"] is None
    assert reloaded.FaceRecognitionFactory.PROVIDERS["azure"] is None

    # Restore normal imports for subsequent tests.
    monkeypatch.setattr(builtins, "__import__", original_import)
    importlib.reload(face_recognizer)
