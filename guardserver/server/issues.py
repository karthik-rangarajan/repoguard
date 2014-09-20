from . import app
from authentication import requires_auth
from core.elastic_search_helpers import ElasticSearchHelpers
from core.datastore import DataStore, DataStoreException
from flask import request, make_response
import arrow
import json


def get_data_store():
    datastore = DataStore(host=app.config["ELASTIC_HOST"], port=app.config["ELASTIC_PORT"],
                          default_index=app.config["INDEX"], default_doctype=app.config["DOC_TYPE"])
    return datastore

@app.route('/issues/', methods=['GET'])
@requires_auth
# Takes the time in days as an argument
# TODO (karthik): Allow set time intervals (i.e., between x and y, or before x, etc.)
def get_all_issues():
    from_time = int(request.args.get("time", 1))
    start = int(request.args.get("from", 0))
    end = int(request.args.get("to", 100))
    start_time = arrow.utcnow().replace(days=-from_time).float_timestamp * 1000
    end_time = arrow.utcnow().float_timestamp * 1000
    sort_order = ElasticSearchHelpers.create_sort(True)
    time_filter = ElasticSearchHelpers.create_timestamp_filter(start_time, end_time)
    try:
        query = ElasticSearchHelpers.create_elasticsearch_filtered_query(timestamp_filter=time_filter,
                                                                         sort_order=sort_order)
        datastore = get_data_store()
        params = dict(from_=start)
        params["size"] = end
        results = datastore.search(query=query, params=params)
        issues = make_issues_object(results["hits"]["hits"])
        response = make_response(json.dumps(issues))
        response.headers["Content-Type"] = "application/json"
        return response
    except DataStoreException:
        return "Failed to retrieve issues", 500

@app.route('/issues/<string:issue_id>')
def get_issue(issue_id):
    try:
        datastore = get_data_store()
        result = datastore.get(issue_id=issue_id)
        response = make_response(json.dumps(result))
        response.headers["Content-Type"] = "application/json"
        return response
    except DataStoreException:
        return "Failed to retrieve issues", 500

@app.route('/issues/commit/<string:commit_id>')
def get_issues_by_commit(commit_id):
    start = int(request.args.get("from", 0))
    end = int(request.args.get("to", 100))
    query = ElasticSearchHelpers.create_elasticsearch_simple_query(search_parameter="commit_id",
                                                                   search_string=commit_id)
    query["from_"] = start
    query["size"] = end
    try:
        datastore = get_data_store()
        results = datastore.search(params=query)
        issues = make_issues_object(results["hits"]["hits"])
        response = make_response(json.dumps(issues))
        response.headers["Content-Type"] = "application/json"
        return response
    except DataStoreException:
        return "Failed to retrieve issues by commit", 500


def make_issues_object(results):
    issues = []
    for result in results:
        issue = dict(id=result["_id"])
        issue["_source"] = result["_source"]
        issues.append(issue)
    return issues

