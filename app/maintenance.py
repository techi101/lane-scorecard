"""Remove expired sessions and abandoned photos without deleting observations."""
from datetime import datetime, timedelta, timezone
import os
import time


def cleanup(store, directory):
    removed = {'sessions': 0, 'unattached_photos': 0}
    # Session document keys are derived from tokens and are intentionally not
    # returned by list(). Persist the key inside new session records for cleanup.
    for session in store.list('sessions'):
        if session.get('key') and session['expires'] < time.time():
            store.delete('sessions', session['key'])
            removed['sessions'] += 1
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    bucket = os.getenv('LANE_PHOTO_BUCKET')
    for workspace in ('demo', 'pilot'):
        attached = {p for check in store.list(f'{workspace}:checks') for p in check['photos']}
        for photo in store.list(f'{workspace}:photos'):
            if photo['id'] in attached or datetime.fromisoformat(photo['created_at']) >= cutoff:
                continue
            if bucket:
                import boto3
                boto3.client('s3').delete_object(Bucket=bucket, Key=f"{workspace}/{photo['id']}.jpg")
            else:
                (directory / 'photos' / (photo['id'] + '.jpg')).unlink(missing_ok=True)
            store.delete(f'{workspace}:photos', photo['id'])
            removed['unattached_photos'] += 1
    return removed
