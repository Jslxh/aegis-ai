"""Unit tests for DB session generators, policy loader fallback, and tool package."""

import pytest

import app.tools  # noqa: F401  (covers the package __init__)


@pytest.mark.unit
class TestDBSessionGenerators:
    def test_get_db_yields_and_closes(self, monkeypatch):
        from app.database import session as sess_mod

        class FakeSession:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        fake = FakeSession()
        monkeypatch.setattr(sess_mod, "SessionLocal", lambda: fake)

        gen = sess_mod.get_db()
        assert next(gen) is fake
        gen.close()
        assert fake.closed is True

    def test_get_db_optional_yields_and_closes(self, monkeypatch):
        from app.database import session as sess_mod

        class FakeSession:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        fake = FakeSession()
        monkeypatch.setattr(sess_mod, "SessionLocal", lambda: fake)

        gen = sess_mod.get_db_optional()
        assert next(gen) is fake
        gen.close()
        assert fake.closed is True

    def test_get_db_optional_yields_none_when_db_down(self, monkeypatch):
        from app.database import session as sess_mod

        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr(sess_mod, "SessionLocal", boom)

        gen = sess_mod.get_db_optional()
        assert next(gen) is None
        with pytest.raises(StopIteration):
            next(gen)


@pytest.mark.unit
class TestPolicyLoader:
    def test_defaults_to_policies_path_when_configs_missing(self, monkeypatch):
        from app.core.loader import PolicyLoader

        monkeypatch.setattr("os.path.exists", lambda path: False)
        loader = PolicyLoader()
        assert loader.policy_file == "policies/default.yaml"

    def test_explicit_policy_file_wins(self, tmp_path):
        from app.core.loader import PolicyLoader

        custom = tmp_path / "custom.yaml"
        loader = PolicyLoader(str(custom))
        assert loader.policy_file == str(custom)

    def test_loads_rules(self):
        from app.core.loader import PolicyLoader

        loader = PolicyLoader("configs/default.yaml")
        rules = loader.load_rules()
        assert isinstance(rules, list)
        assert len(rules) > 0
