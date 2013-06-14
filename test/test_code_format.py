import pep8
import os


def test_pep8_conformance():
    """Test source code for PEP8 conformance"""
    pep8style = pep8.StyleGuide(max_line_length=1200)
    report = pep8style.options.report
    report.start()
    pep8style.input_dir(os.path.join('..', 'vcstools', 'src'))
    report.stop()
    assert report.total_errors == 0, "Found '{0}' code style errors (and warnings).".format(report.total_errors)
