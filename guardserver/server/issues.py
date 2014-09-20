from . import app
from authentication import requires_auth
from core.elastic_search_helpers import ElasticSearchHelpers
from core.datastore import DataStore, DataStoreException
from flask import request, make_response
import arrow
import json


def get_data_store():
    datastore = DataStore(host=app.config["ELASTIC_HOST"], port=app.config["ELASTIC_PORT"])
    return datastore

@app.route('/issues', methods=['GET'])
@requires_auth
# Takes the time in days as an argument
# TODO (karthik): Allow set time intervals (i.e., between x and y, or before x, etc.)
def get_all_issues():
    from_time = int(request.args.get("time", 1))
    start_time = arrow.utcnow().replace(days=-from_time).float_timestamp * 1000
    end_time = arrow.utcnow().float_timestamp * 1000
    sort_order = ElasticSearchHelpers.create_sort(True)
    time_filter = ElasticSearchHelpers.create_timestamp_filter(start_time, end_time)
    try:
        query = ElasticSearchHelpers.create_elasticsearch_filtered_query(timestamp_filter=time_filter,
                                                                         sort_order=sort_order)
        datastore = get_data_store()
        results = datastore.search(query=query, index=app.config["INDEX"], doc_type=app.config["DOC_TYPE"])
        issues = []
        for result in results["hits"]["hits"]:
            issues.append(result["_source"])
        response = make_response(json.dumps(issues))
        response.headers["Content-Type"] = "application/json"
        return response
    except DataStoreException:
        return "Failed to retrieve issues", 500

@app.route('/issues/<string:commit_id>')
def get_issue(commit_id):
    query = ElasticSearchHelpers.create_elasticsearch_simple_query(search_parameter="commit_id", search_string=commit_id)
    try:
        datastore = get_data_store()
        results = datastore.search(params=query, index=app.config["INDEX"], doc_type=app.config["DOC_TYPE"])
        issues = []
        for result in results["hits"]["hits"]:
            issues.append(result["_source"])
        response = make_response(json.dumps(issues))
        response.headers["Content-Type"] = "application/json"
        return response
    except DataStoreException:
        return "Failed to retrieve issues", 500
