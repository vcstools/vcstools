from __future__ import print_function
import os
from pkg_resources import parse_version, get_distribution




def test_pep8_conformance():
    """Test source code for PEP8 conformance"""

    try:
        import pep8
    except:
        print("Skipping pep8 Tests because pep8.py not installed.")
        return

    # Skip test if pep8 is not new enough
    pep8_version = parse_version(get_distribution('pep8').version)
    needed_version = parse_version('1.0')
    if pep8_version < needed_version:
        print("Skipping pep8 Tests because pep8.py is too old")
        return

    pep8style = pep8.StyleGuide(max_line_length=120)
    report = pep8style.options.report
    report.start()
    pep8style.options.exclude.append('git_archive_all.py')
    pep8style.input_dir(os.path.join('..', 'vcstools', 'src'))
    report.stop()
    assert report.total_errors == 0, "Found '{0}' code style errors (and warnings).".format(report.total_errors)
