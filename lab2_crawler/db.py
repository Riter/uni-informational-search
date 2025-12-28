from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from config import DbConfig


def create_mongo(db_cfg: DbConfig) -> Database:
    client = MongoClient(db_cfg.uri)
    return client[db_cfg.database]


def get_documents_collection(db: Database, db_cfg: DbConfig) -> Collection:
    return db[db_cfg.collection]


def get_frontier_collection(db: Database) -> Collection:
    return db["frontier"]
