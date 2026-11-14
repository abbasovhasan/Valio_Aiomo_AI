"""Prepare private Modal volumes/runtime secret; never print secret values.

Operator must verify current sponsored credits and hard spending cap first.
No payment method, upgrade, billing change, or competition submission occurs.
Run with `uv run --with modal --with python-dotenv python scripts/deploy_sponsored.py`.
Then `uv run --with modal modal deploy deploy_modal.py`.
"""
import hashlib
import json
import os
from pathlib import Path
import modal
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    values = dotenv_values(ROOT / '.env')
    codes = json.loads((ROOT / '.local/access.json').read_text())
    secret = {key: values[key] for key in ['VALIO_API_KEY','NVIDIA_API_KEY','NVIDIA_MODEL','VALIO_API_BASE_URL'] if values.get(key)}
    secret.update(AIMO_BUYER_CODE=os.environ.get('AIMO_BUYER_CODE',codes['buyer']), AIMO_APPROVER_CODE=os.environ.get('AIMO_APPROVER_CODE',codes['approver']), AIMO_STORAGE='sqlite', AIMO_SECURE_COOKIES='1')
    for key in ['AIMO_AUTONOMOUS_LIMIT','AIMO_EXCEPTION_LIMIT','AIMO_CUMULATIVE_LIMIT']:
        if values.get(key): secret[key]=values[key]
    manifest=json.loads((ROOT / 'research/SOURCES.json').read_text())
    files=[]
    for row in manifest['files']:
        path=ROOT / row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise RuntimeError('Authorized source checksum mismatch: '+path.name)
        files.append(path)
    modal.Secret.objects.create('aimo-order-desk-runtime',env_dict=secret,allow_existing=True)
    modal.Secret.from_name('aimo-order-desk-runtime').update(secret)
    volume=modal.Volume.from_name('aimo-private-catalog-v1',create_if_missing=True,version=2)
    with volume.batch_upload(force=True) as upload:
        for path in files:
            upload.put_file(path, '/raw/'+path.name)
    modal.Volume.from_name('aimo-demo-state-v1',create_if_missing=True,version=2)
    print('Prepared runtime secret and 4 verified private catalog files. No secret values printed.')


if __name__=='__main__':
    main()
