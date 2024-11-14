import os
import zipfile

def _zipdir(path, ziph):
    # ziph is zipfile handle
    for root, _, files in os.walk(path):
        for file in files:
            ziph.write(
                os.path.join(root, file), 
                os.path.relpath(os.path.join(root, file), 
                os.path.join(path, '..'))
            )

def compress(source, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
        _zipdir(source, zipf)