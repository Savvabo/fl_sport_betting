from flask import Flask, jsonify, request, send_file
import ast
import os
import sys
from pymongo import DESCENDING
if os.getcwd().split('/')[-1] != 'fl_sport_betting':
    os.chdir("..")
    sys.path.append(os.path.abspath(os.curdir))
from storage.mongodb_storage import MongoDBStorage as mdb
import helpers
config = helpers.parse_config('server')

client = mdb().client
app = Flask(__name__)

def group_forecasts(forecasts):
    grouped = {}
    for forecast in forecasts:
        grouped.setdefault(forecast['forecast_type'], [])
        grouped[forecast['forecast_type']].append(forecast)
    return grouped

def get_file_link(resource, file_name):
    pattern = '{server_domain}/api/files/{resource}/{file_name}'
    file_link = pattern.format(server_domain=config['domain'],
                               resource=resource,
                               file_name=file_name)
    return file_link


def format_forecast_logos(forecast):
    if forecast['resource'] == 'vseprosport.ru':
        if forecast['forecast_type'] == 'Solo':
            images_link = []
            for image in forecast['additional_info']['logos']:
                if image.startswith('http'):
                    images_link.append(image)
                else:
                    images_link.append(get_file_link('vseprosport', image))

            forecast['additional_info']['logos'] = images_link
        elif forecast['forecast_type'] == 'Express':
            for event in forecast['additional_info']['events']:
                images_link = []
                for image in event['event_logos']:
                    images_link.append(get_file_link('vseprosport', image))
                event['event_logos'] = images_link
    elif forecast['resource'] == 'odds.ru' and forecast['forecast_type'] == 'Solo':
        images_link = []
        for image in forecast['additional_info']['logos']:
            if image.startswith('http'):
                images_link.append(image)
            else:
                images_link.append(get_file_link('odds', image))
        forecast['additional_info']['logos'] = images_link
    return forecast


def get_full_resource(resource):
    if resource == 'vseprosport':
        return 'vseprosport.ru'
    elif resource == 'stavka':
        return 'stavka.tv'
    elif resource == 'vprognoze':
        return 'vprognoze.ru'
    elif resource == 'odds':
        return 'odds.ru'
    else:
        return {'$ne': None}


def format_instagram_data(post):
    if post['is_video']:
        post['preview_image'] = get_file_link('instagram', post['preview_image'])
        post['video_url'] = get_file_link('instagram', post['video_url'])
    post['resource'] = '@' + post['resource']
    return post


@app.route('/api/forecast-categories', methods=['GET'])
def get_forecast_categories():
    aggregate_query = [{'$group': {'categories': {'$addToSet': {'category_name': '$category'}}, '_id': 'categories'}}]
    category_items = list(client['forecasts'].aggregate(aggregate_query))[0]['categories']
    return jsonify(category_items)


@app.route('/api/forecast/<forecast_id>', methods=['GET'])
def get_forecast_by_id(forecast_id):
    forecast = format_forecast_logos(client['forecasts'].find_one({'_id': forecast_id}))
    return jsonify(forecast)


@app.route('/api/forecasts', methods=['GET'])
def get_forecasts():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))
    forecast_type = request.args.get('forecast_type', {'$ne': None})
    if type(forecast_type) == str:
        forecast_type = {'$regex': f'^{forecast_type}'}
    category = request.args.get('category', {'$ne': None})
    resource = get_full_resource(request.args.get('resource', None))
    date_from = int(request.args.get('date_from', 0))

    forecasts = list(client['forecasts'].find({'forecast_type': forecast_type,
                                          'category': category,
                                          'resource': resource,
                                          'date': {'$gt': date_from}}).sort("date", -1).skip((page-1)*per_page).limit(per_page))

    formated_forecasts = list(map(format_forecast_logos, forecasts))
    grouped_forecasts = group_forecasts(formated_forecasts)
    return jsonify(grouped_forecasts)


@app.route('/api/news/<post_id>', methods=['GET'])
def get_insta_post_by_id(post_id):
    posts = format_instagram_data(client['instagram'].find_one({'_id': post_id}))
    return jsonify(posts)


@app.route('/api/news', methods=['GET'])
def get_insta_posts():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))
    date_from = int(request.args.get('date_from', 0))
    resource = request.args.get('resource', {'$ne': None})
    is_album = ast.literal_eval(request.args.get('is_album', "{'$ne': None}"))
    is_video = ast.literal_eval(request.args.get('is_video', "{'$ne': None}"))
    posts = list(client['instagram'].find({'is_album': is_album,
                                               'is_video': is_video,
                                               'resource': resource,
                                               'date': {'$gt': date_from}}).sort("date", -1).skip((page - 1) * per_page).limit(per_page))
    formated_posts = list(map(format_instagram_data, posts))
    return jsonify(formated_posts)


@app.route('/api/files/<resource>/<file_name>', methods=['GET'])
def get_stream_file(resource, file_name):
    return send_file(f'../stream/{resource}/{file_name}')



if __name__ == '__main__':
    app.run(debug=True)
