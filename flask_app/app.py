from flask import Flask, jsonify, request

from storage.mongodb_storage import MongoDBStorage as mdb
client = mdb().client
app = Flask(__name__)


@app.route('/api/forecast-categories', methods=['GET'])
def get_forecast_categories():
    aggregate_query = [{'$group': {'categories': {'$addToSet': {'category_name': '$category'}}, '_id': 'categories'}}]
    category_items = list(client['forecasts'].aggregate(aggregate_query))[0]['categories']
    return jsonify(category_items)


@app.route('/api/forecast-types', methods=['GET'])
def get_forecast_types():
    aggregate_query = [{'$group': {'forecast_types': {'$addToSet': {'forecast_type': '$forecast_type'}}, '_id': 'forecast_types'}}]
    forecast_types = list(client['forecasts'].aggregate(aggregate_query))[0]['forecast_types']
    return jsonify(forecast_types)


@app.route('/api/forecast/<forecast_id>', methods=['GET'])
def get_forecast_by_id(forecast_id):
    forecast = client['forecasts'].find_one({'_id': forecast_id})
    return jsonify(forecast)


@app.route('/api/forecasts/', methods=['GET'])
def get_forecasts():
    page = request.args.get('page', 0)
    per_page = request.args.get('per_page', 5)
    forecast_type = request.args.get('forecast_type', 5)
    category = request.args.get('category')
    resource = request.args.get('resource')
    coefficient_lt = request.args.get('coefficient_lt')
    coefficient_gt = request.args.get('coefficient_gt')
    time_lt = request.args.get('time_lt')
    time_gt = request.args.get('time_gt')


@app.route('/api/news/<publication_id>', methods=['GET'])
def get_insta_publication_by_id(publication_id):
    publication = client['forecasts'].find_one({'_id': publication_id})
    publication['resource'] = '@' + publication['resource']
    return jsonify(publication)

@app.route('/api/news/', methods=['GET'])
def get_insta_publications():







if __name__ == '__main__':
    app.run(debug=True)
