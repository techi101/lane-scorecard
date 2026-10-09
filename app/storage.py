"""Small-pilot document store. SQLite locally; DynamoDB in AWS.

Each document has an entity partition and a unique key. Conditional inserts
keep repeated checks and idempotent requests from creating duplicate records.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, directory: Path):
        self.table = None
        if os.getenv("LANE_TABLE"):
            import boto3
            self.table = boto3.resource("dynamodb").Table(os.environ["LANE_TABLE"])
        else:
            directory.mkdir(parents=True, exist_ok=True)
            self.path = directory / "lane.sqlite3"
            with self.connection() as db:
                db.execute("CREATE TABLE IF NOT EXISTS records (pk TEXT, sk TEXT, data TEXT NOT NULL, PRIMARY KEY(pk, sk))")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            with db:
                yield db
        finally:
            db.close()

    def get(self, pk, sk):
        if self.table:
            item = self.table.get_item(Key={"pk": pk, "sk": sk}, ConsistentRead=True).get("Item")
            return json.loads(item["data"]) if item else None
        with self.connection() as db:
            row = db.execute("SELECT data FROM records WHERE pk=? AND sk=?", (pk, sk)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, pk, sk, value, *, create=False):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if self.table:
            args = {"Item": {"pk": pk, "sk": sk, "data": data}}
            if create:
                args["ConditionExpression"] = "attribute_not_exists(pk)"
            try:
                self.table.put_item(**args)
            except self.table.meta.client.exceptions.ConditionalCheckFailedException:
                return False
        else:
            try:
                with self.connection() as db:
                    db.execute("INSERT INTO records VALUES (?,?,?)" if create else "INSERT OR REPLACE INTO records VALUES (?,?,?)", (pk, sk, data))
            except sqlite3.IntegrityError:
                return False
        return True

    def replace_if_unchanged(self, pk, sk, expected, value):
        """Compare-and-swap prevents one operator tab overwriting another."""
        old = json.dumps(expected, ensure_ascii=False, allow_nan=False)
        data = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if self.table:
            try:
                self.table.put_item(
                    Item={"pk": pk, "sk": sk, "data": data},
                    ConditionExpression="#data = :expected",
                    ExpressionAttributeNames={"#data": "data"},
                    ExpressionAttributeValues={":expected": old})
            except self.table.meta.client.exceptions.ConditionalCheckFailedException:
                return False
            return True
        with self.connection() as db:
            return db.execute("UPDATE records SET data=? WHERE pk=? AND sk=? AND data=?",
                              (data, pk, sk, old)).rowcount == 1

    def list(self, pk):
        if self.table:
            from boto3.dynamodb.conditions import Key
            args = {"KeyConditionExpression": Key("pk").eq(pk), "ConsistentRead": True}
            rows = []
            while True:
                result = self.table.query(**args)
                rows.extend(json.loads(item["data"]) for item in result.get("Items", []))
                if not result.get("LastEvaluatedKey"):
                    return rows
                args["ExclusiveStartKey"] = result["LastEvaluatedKey"]
        with self.connection() as db:
            rows = db.execute("SELECT data FROM records WHERE pk=? ORDER BY sk", (pk,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, pk, sk):
        if self.table:
            self.table.delete_item(Key={"pk": pk, "sk": sk})
        else:
            with self.connection() as db:
                db.execute("DELETE FROM records WHERE pk=? AND sk=?", (pk, sk))

    def put_many(self, pk, values):
        """Batch the deterministic demo seed instead of making 174 cold-start calls."""
        records = [(pk, value['id'], json.dumps(value, ensure_ascii=False, allow_nan=False)) for value in values]
        if self.table:
            with self.table.batch_writer() as batch:
                for partition, key, data in records:
                    batch.put_item(Item={'pk': partition, 'sk': key, 'data': data})
        else:
            with self.connection() as db:
                db.executemany('INSERT OR REPLACE INTO records VALUES (?,?,?)', records)
