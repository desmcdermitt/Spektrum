from unittest import mock

from spektrum import Spec, metadata
from spektrum.reporting.testrail import TestRailRenderer


class LeafWithMatchingCase(Spec):
    @metadata(regression=True)
    def can_run_under_regression(self):
        pass

    def can_run_with_no_metadata(self):
        pass


class LeafWithoutMatchingCase(Spec):
    def can_run_with_no_metadata(self):
        pass


class RootSpec(Spec):
    class Selected(LeafWithMatchingCase):
        pass

    class Unselected(LeafWithoutMatchingCase):
        pass


def _make_renderer():
    renderer = TestRailRenderer.__new__(TestRailRenderer)
    renderer.project = 1
    renderer.suite = 1
    renderer.specs = {}
    renderer.tr = mock.Mock()
    renderer.tr.add_section.return_value = mock.Mock(
        json=mock.Mock(return_value={'id': 111, 'suite_id': 1})
    )
    return renderer


def _created_section_names(renderer):
    return [call.kwargs['name'] for call in renderer.tr.add_section.call_args_list]


def test_reconcile_skips_sections_with_no_selected_cases():
    renderer = _make_renderer()
    root = RootSpec()

    renderer.reconcile_spec_and_section(
        root,
        metadata={'regression': True},
        test_names=None,
        exclude=None,
        sections=[],
    )

    created = _created_section_names(renderer)

    assert 'Root Spec' in created
    assert 'Selected' in created
    assert 'Unselected' not in created


def test_reconcile_creates_all_sections_with_no_filter():
    renderer = _make_renderer()
    root = RootSpec()

    renderer.reconcile_spec_and_section(
        root,
        metadata=None,
        test_names=None,
        exclude=None,
        sections=[],
    )

    created = _created_section_names(renderer)

    assert 'Root Spec' in created
    assert 'Selected' in created
    assert 'Unselected' in created
