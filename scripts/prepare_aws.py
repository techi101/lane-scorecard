"""Stage only allowlisted application sources. Never packages local data or secrets."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
target = root / 'artifacts' / 'aws-src'
target.mkdir(parents=True, exist_ok=True)
for folder, suffixes in [('app', {'.py'}), ('web', {'.html', '.css', '.js', '.svg'})]:
    for source in (root / folder).rglob('*'):
        if source.is_file() and source.suffix in suffixes and '__pycache__' not in source.parts:
            output = target / source.relative_to(root)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, output)
shutil.copy2(root / 'requirements.txt', target / 'requirements.txt')
print(f'Staged application sources: {target}')
print('No AWS calls made. Local databases, photos, access codes and tests were excluded.')
