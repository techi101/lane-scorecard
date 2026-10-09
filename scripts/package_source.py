"""Create a source-only handoff. Never include runtime data or access codes."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
output = root / 'artifacts' / 'lane-scorecard-source.zip'
output.parent.mkdir(exist_ok=True)
top_files = ['README.md', '.gitignore', 'requirements.txt', 'requirements-dev.txt', 'pytest.ini', 'template.yaml', 'run.py', 'manage.py', 'start.ps1', 'setup.ps1', 'deploy.ps1', 'validate.ps1']
sources = [root / name for name in top_files]
for folder in ['app', 'web', 'scripts', 'docs', 'tests']:
    sources.extend(p for p in (root / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.md','.html','.css','.js','.svg','.json'})
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
    for source in sorted(set(sources)):
        bundle.write(source, 'lane-scorecard/' + source.relative_to(root).as_posix())
with zipfile.ZipFile(output) as bundle:
    names = bundle.namelist()
    assert not any('/.local/' in name or '/.venv/' in name or name.endswith('admin-code.txt') for name in names)
print(f'Created {output} ({len(names)} source files). No credentials, databases or pilot photos included.')
