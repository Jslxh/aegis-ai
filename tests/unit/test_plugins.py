"""Unit tests for the tool plugin framework: validation, registry, discovery."""

import pytest

from app.plugins.interface import BaseToolPlugin
from app.plugins.registry import ToolRegistry
from app.plugins.validator import validate_plugin, ensure_valid_plugin, PluginValidationError
from app.plugins.discovery import discover_plugins


class ValidPlugin(BaseToolPlugin):
    name = "test_tool"
    description = "A valid test tool"
    actions = {"run": {"description": "run it", "parameters": {"count": {"type": "integer", "required": True}}}}

    def execute(self, action, params):
        return {"status": "ok"}

    def simulate(self, action, params):
        return {"status": "simulated"}


class NoNamePlugin(BaseToolPlugin):
    name = ""
    description = "missing name"
    actions = {"run": {"description": "x"}}

    def execute(self, action, params):
        return {}

    def simulate(self, action, params):
        return {}


class NoActionsPlugin(BaseToolPlugin):
    name = "no_actions"
    description = "no actions declared"
    actions = {}

    def execute(self, action, params):
        return {}

    def simulate(self, action, params):
        return {}


class BadNamePlugin(BaseToolPlugin):
    name = "UPPER_CASE"
    description = "bad name"
    actions = {"run": {"description": "x"}}

    def execute(self, action, params):
        return {}

    def simulate(self, action, params):
        return {}


@pytest.mark.unit
class TestValidatePlugin:
    def test_valid_plugin_passes(self):
        assert validate_plugin(ValidPlugin) == []

    def test_non_class_rejected(self):
        errors = validate_plugin("not-a-class")
        assert "must be a class" in errors[0]

    def test_base_class_itself_rejected(self):
        errors = validate_plugin(BaseToolPlugin)
        assert len(errors) == 1

    def test_non_subclass_rejected(self):
        class Unrelated:
            pass

        errors = validate_plugin(Unrelated)
        assert any("subclass" in e for e in errors)

    def test_abstract_plugin_rejected(self):
        class Abstract(BaseToolPlugin):
            pass

        errors = validate_plugin(Abstract)
        assert any("abstract" in e for e in errors)

    def test_missing_name(self):
        errors = validate_plugin(NoNamePlugin)
        assert any("name" in e for e in errors)

    def test_invalid_name_pattern(self):
        errors = validate_plugin(BadNamePlugin)
        assert any("Invalid plugin name" in e for e in errors)

    def test_missing_actions(self):
        errors = validate_plugin(NoActionsPlugin)
        assert any("actions" in e for e in errors)

    def test_missing_description(self):
        class NoDesc(BaseToolPlugin):
            name = "no_desc"
            description = ""
            actions = {"run": {"description": "x"}}

            def execute(self, action, params):
                return {}

            def simulate(self, action, params):
                return {}

        errors = validate_plugin(NoDesc)
        assert any("description" in e for e in errors)

    def test_missing_methods(self):
        class MissingMethods(BaseToolPlugin):
            name = "mm"
            description = "missing methods"
            actions = {"run": {"description": "x"}}

        errors = validate_plugin(MissingMethods)
        assert any("execute" in e for e in errors)
        assert any("simulate" in e for e in errors)

    def test_ensure_valid_raises(self):
        with pytest.raises(PluginValidationError):
            ensure_valid_plugin(NoNamePlugin)

    def test_ensure_valid_ok(self):
        ensure_valid_plugin(ValidPlugin)


@pytest.mark.unit
class TestToolRegistry:
    def test_register_and_lookup(self):
        registry = ToolRegistry()
        assert registry.register(ValidPlugin) == []
        assert registry.has("test_tool") is True
        assert registry.get("test_tool").name == "test_tool"
        assert registry.names() == ["test_tool"]

    def test_register_instance(self):
        registry = ToolRegistry()
        assert registry.register_instance(ValidPlugin()) == []
        assert registry.has("test_tool")

    def test_register_invalid_plugin_keeps_error(self):
        registry = ToolRegistry()
        errors = registry.register(NoNamePlugin)
        assert errors
        assert registry.errors
        assert registry.has("") is False

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(ValidPlugin)
        assert registry.unregister("test_tool") is True
        assert registry.unregister("missing") is False

    def test_list_and_info(self):
        registry = ToolRegistry()
        registry.register(ValidPlugin)
        plugins = registry.list()
        assert len(plugins) == 1
        info = registry.info()
        assert info[0]["name"] == "test_tool"
        assert "actions" in info[0]

    def test_discover_only_runs_once(self):
        registry = ToolRegistry()
        registry.discover()
        names1 = registry.names()
        registry.discover()
        assert registry.is_discovered is True
        assert registry.names() == names1

    def test_reset_clears_state(self):
        registry = ToolRegistry()
        registry.discover()
        registry.reset()
        assert registry.is_discovered is False
        assert registry.names() == []


@pytest.mark.unit
class TestDiscovery:
    def test_discover_plugins_from_directory(self, tmp_path):
        module = tmp_path / "my_tool.py"
        module.write_text(
            "from app.plugins.interface import BaseToolPlugin\n"
            "class MyTool(BaseToolPlugin):\n"
            "    name = 'my_tool'\n"
            "    description = 'tool from tmp'\n"
            "    actions = {'run': {'description': 'x'}}\n"
            "    def execute(self, action, params):\n"
            "        return {'status': 'ok'}\n"
            "    def simulate(self, action, params):\n"
            "        return {'status': 'simulated'}\n"
        )
        registry = ToolRegistry()
        registered = discover_plugins([str(tmp_path)], registry)
        assert "my_tool" in registered
        assert registry.has("my_tool")

    def test_discovery_ignores_non_plugin_files(self, tmp_path):
        (tmp_path / "not_a_plugin.py").write_text("VALUE = 42\n")
        registry = ToolRegistry()
        discover_plugins([str(tmp_path)], registry)
        assert registry.names() == []

    def test_discovery_records_load_errors(self, tmp_path):
        (tmp_path / "broken.py").write_text("this is not valid python {{{")
        registry = ToolRegistry()
        discover_plugins([str(tmp_path)], registry)
        assert len(registry.errors) == 1

    def test_register_tool_decorator(self):
        from app.plugins.discovery import register_tool

        @register_tool
        class DecoratedTool(BaseToolPlugin):
            name = "decorated_tool"
            description = "registered via decorator"
            actions = {"run": {"description": "x"}}

            def execute(self, action, params):
                return {}

            def simulate(self, action, params):
                return {}

        registry = ToolRegistry.get_default()
        assert registry.has("decorated_tool")
