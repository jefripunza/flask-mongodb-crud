import os
import json
import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response
from pymongo import MongoClient

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.environ.get('DATABASE_URL'))
db = client['python_mongodb_example']
collection = db['users']
auto_increment = db['auto_increment']


def get_next_auto_increment_value(sequence_name):
    sequence_document = auto_increment.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        return_document=True,
        upsert=True
    )
    return sequence_document['sequence_value']


@app.route('/')
def index():
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    sort_by = request.args.get('sort_by', 'id')
    min_age = int(request.args.get('min_age', 0))
    max_age = int(request.args.get('max_age', 100000000000000))
    daterange = request.args.get('daterange', '')

    filter_query = {'usia': {'$gte': min_age, '$lte': max_age}}
    if search_query:
        filter_query['nama'] = {'$regex': f'.*{search_query}.*', '$options': 'i'}
    if daterange:
        start_date, end_date = daterange.split(' - ')
        start_datetime = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_datetime = datetime.datetime.strptime(end_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
        filter_query['created_at'] = {
            '$gte': datetime.datetime.combine(start_datetime, datetime.datetime.min.time()),
            '$lt': datetime.datetime.combine(end_datetime, datetime.datetime.min.time())
        }

    total_count = collection.count_documents(filter_query)
    total_pages = (total_count + size - 1) // size
    offset = (page - 1) * size
    limit = size
    data = list(collection.find(filter_query).sort(sort_by).skip(offset).limit(limit))

    return render_template('index.html', data=data, search_query=search_query, page=page,
                           size=size, sort_by=sort_by, min_age=min_age, max_age=max_age,
                           daterange=daterange, total_pages=total_pages)


@app.route('/add', methods=['POST'])
def add():
    nama = request.form['nama']
    usia = int(request.form['usia'])
    created_at = datetime.datetime.now()

    data = {
        'id': get_next_auto_increment_value('users'),
        'nama': nama,
        'usia': usia,
        'created_at': created_at
    }
    collection.insert_one(data)
    return redirect(url_for('index'))


@app.route('/edit/<id>', methods=['GET', 'POST', 'PUT'])
def edit(id):
    data = collection.find_one({'id': int(id)})
    if request.method == 'PUT' or request.args.get('_method') == 'PUT':
        request_data = json.loads(request.data)
        nama = request_data.get('nama')
        usia = request_data.get('usia')

        if nama is not None and usia is not None:
            collection.update_one({'id': int(id)}, {'$set': {
                'nama': nama,
                'usia': int(usia)
            }})
            return make_response(json.dumps({
                "message": "Berhasil mengedit data!"
            }), 200)
        else:
            return make_response(json.dumps({
                "message": "Nama dan usia harus diisi!"
            }), 400)

    return render_template('edit.html', data=data)


@app.route('/delete/<id>', methods=['GET', 'POST', 'DELETE'])
def delete(id):
    if request.method == 'DELETE' or request.args.get('_method') == 'DELETE':
        collection.delete_one({'id': int(id)})
        return make_response({
            "message": "Berhasil menghapus data!",
        })
    return render_template('delete.html', id=id)


if __name__ == '__main__':
    app.run(debug=True)
