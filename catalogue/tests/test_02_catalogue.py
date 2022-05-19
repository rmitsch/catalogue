import pytest
import sys
from pathlib import Path
import catalogue


@pytest.fixture(autouse=True)
def cleanup():
    catalogue.registry.REGISTRY = {}
    yield


def test_get_set():
    catalogue.registry._set(("a", "b", "c"), "test")
    assert len(catalogue.registry.REGISTRY) == 1
    assert ("a", "b", "c") in catalogue.registry.REGISTRY
    assert catalogue.registry.check_exists("a", "b", "c")
    assert catalogue.registry.REGISTRY[("a", "b", "c")] == "test"
    assert catalogue.registry._get(("a", "b", "c")) == "test"
    with pytest.raises(catalogue.registry.RegistryError):
        catalogue.registry._get(("a", "b", "d"))
    with pytest.raises(catalogue.registry.RegistryError):
        catalogue.registry._get(("a", "b", "c", "d"))
    catalogue.registry._set(("x", "y", "z1"), "test1")
    catalogue.registry._set(("x", "y", "z2"), "test2")
    assert catalogue.registry._remove(("a", "b", "c")) == "test"
    catalogue.registry._set(("x", "y2"), "test3")
    with pytest.raises(catalogue.registry.RegistryError):
        catalogue.registry._remove(("x", "y"))
    assert catalogue.registry._remove(("x", "y", "z2")) == "test2"


def test_registry_get_set():
    test_registry = catalogue.registry.create("test")
    with pytest.raises(catalogue.registry.RegistryError):
        test_registry.get("foo")
    test_registry.register("foo", func=lambda x: x)
    assert "foo" in test_registry


def test_registry_call():
    test_registry = catalogue.registry.create("test")
    test_registry("foo", func=lambda x: x)
    assert "foo" in test_registry


def test_get_all(cleanup):
    catalogue.registry._set(("a", "b", "c"), "test")
    catalogue.registry._set(("a", "b", "d"), "test")
    catalogue.registry._set(("a", "b"), "test")
    catalogue.registry._set(("b", "a"), "test")
    all_items = catalogue.registry._get_all(("a", "b"))
    assert len(all_items) == 3
    assert ("a", "b", "c") in all_items
    assert ("a", "b", "d") in all_items
    assert ("a", "b") in all_items
    all_items = catalogue.registry._get_all(("a", "b", "c"))
    assert len(all_items) == 1
    assert ("a", "b", "c") in all_items
    assert len(catalogue.registry._get_all(("a", "b", "c", "d"))) == 0


def test_create_single_namespace():
    assert catalogue.registry.REGISTRY == {}
    test_registry = catalogue.registry.create("test")

    @test_registry.register("a")
    def a():
        pass

    def b():
        pass

    test_registry.register("b", func=b)
    items = test_registry.get_all()
    assert len(items) == 2
    assert items["a"] == a
    assert items["b"] == b
    assert catalogue.registry.check_exists("test", "a")
    assert catalogue.registry.check_exists("test", "b")
    assert catalogue.registry._get(("test", "a")) == a
    assert catalogue.registry._get(("test", "b")) == b

    with pytest.raises(TypeError):
        # The decorator only accepts one argument
        @test_registry.register("x", "y")
        def x():
            pass


def test_create_multi_namespace():
    test_registry = catalogue.registry.create("x", "y")

    @test_registry.register("z")
    def z():
        pass

    items = test_registry.get_all()
    assert len(items) == 1
    assert items["z"] == z
    assert catalogue.registry.check_exists("x", "y", "z")
    assert catalogue.registry._get(("x", "y", "z")) == z


@pytest.mark.skipif(sys.version_info >= (3, 10), reason="Test is not yet updated for 3.10 importlib_metadata API")
def test_entry_points(cleanup):
    # Create a new EntryPoint object by pretending we have a setup.cfg and
    # use one of catalogue's util functions as the advertised function
    ep_string = "[options.entry_points]test_foo\n    bar = catalogue.registry:check_exists"
    ep = catalogue.registry.importlib_metadata.EntryPoint._from_text(ep_string)
    catalogue.registry.AVAILABLE_ENTRY_POINTS["test_foo"] = ep
    assert catalogue.registry.REGISTRY == {}
    test_registry = catalogue.registry.create("test", "foo", entry_points=True)
    entry_points = test_registry.get_entry_points()
    assert "bar" in entry_points
    assert entry_points["bar"] == catalogue.registry.check_exists
    assert test_registry.get_entry_point("bar") == catalogue.registry.check_exists
    assert catalogue.registry.REGISTRY == {}
    assert test_registry.get("bar") == catalogue.registry.check_exists
    assert test_registry.get_all() == {"bar": catalogue.registry.check_exists}
    assert "bar" in test_registry


def test_registry_find(cleanup):
    test_registry = catalogue.registry.create("test_registry_find")
    name = "a"

    @test_registry.register(name)
    def a():
        """This is a registered function."""
        pass

    info = test_registry.find(name)
    assert info["module"] == "catalogue.tests.test_02_catalogue"
    assert info["file"] == str(Path(__file__))
    assert info["docstring"] == "This is a registered function."
    assert info["line_no"]
