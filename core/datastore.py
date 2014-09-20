from elasticsearch import Elasticsearch, ElasticsearchException
import os
import sys
import hashlib


class DataStoreException (Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return repr(self.error)


class DataStore:
    def __init__(self, host, port, username=None, password=None, use_ssl=False):
        if username and password:
            self.es_connection = Elasticsearch(host=host, port=port, http_auth=username + ":" + password,
                                               use_ssl=use_ssl)
        else:
            self.es_connection = Elasticsearch(host=host, port=port, use_ssl=use_ssl)
        if not self.es_connection.ping():
            raise DataStoreException("Connection to ElasticSearch failed.")
            self.es_connection = False

    def store(self, body, index, doc_type):
        try:
            self.es_connection.create(body=body, id=hashlib.sha1(str(body)).hexdigest(), index=index,
                                      doc_type=doc_type)
        except ElasticsearchException, e:
            raise DataStoreException("Exception while storing data in Elastic Search: " + e.getDetail)

    def search(self, index, doc_type, query=None, params=None):
        try:
            if params:
                results = self.es_connection.search(body=query, index=index, doc_type=doc_type, params=params)
            else:
                results = self.es_connection.search(body=query, index=index, doc_type=doc_type)
            return results
        except ElasticsearchException:
            raise DataStoreException("Exception while searching data in Elastic Search")

