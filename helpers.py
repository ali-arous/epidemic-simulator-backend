def init_seq(collection, name):
    collection.insert({'_id': name, 'seq': 0})

def get_next_sequence_value(collection, name):
    return collection.find_and_modify(query={'_id': name}, update={'$inc': {'seq': 1}}, new=True).get('seq')