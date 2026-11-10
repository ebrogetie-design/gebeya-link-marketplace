def test_project_has_expected_modules():
    from pathlib import Path
    assert Path("app/main.py").exists()
    assert Path("app/models.py").exists()
