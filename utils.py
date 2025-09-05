def replace_mongo_id(doc):
    doc["_id"] = str(doc["_id"])
    del doc["_id"]
    return doc